"""Agent planner/executor service."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.metrics import collector
from app.models import Role, User, UserRole
from app.models.agent import AgentApprovalEvent, AgentArtifact, AgentStep, AgentTask, ToolCall
from app.models.knowledge_base import Document
from app.services.agent_planner import AgentPlanner
from app.services.agent_tools import registry


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentService:
    """Plan-and-execute agent service with trace persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        goal: str,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
        auto_run: bool = True,
    ) -> AgentTask:
        task = AgentTask(
            tenant_id=tenant_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            goal=goal,
            status="pending",
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        collector.record_agent_task("created")
        if auto_run:
            self.run_task(task.id)
            task = self.get_task(task.id, tenant_id)
        return task

    def get_task(self, task_id: uuid.UUID, tenant_id: uuid.UUID) -> AgentTask:
        task = (
            self.db.execute(
                select(AgentTask)
                .options(
                    selectinload(AgentTask.steps),
                    selectinload(AgentTask.tool_calls),
                    selectinload(AgentTask.artifacts),
                    selectinload(AgentTask.approval_events),
                )
                .where(AgentTask.id == task_id, AgentTask.tenant_id == tenant_id)
            )
            .scalar_one_or_none()
        )
        if not task:
            raise ValueError(f"Agent task not found: {task_id}")
        return task

    def list_tasks(self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 50) -> tuple[list[AgentTask], int]:
        base = select(AgentTask).where(AgentTask.tenant_id == tenant_id)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        tasks = (
            self.db.execute(
                base.options(
                    selectinload(AgentTask.steps),
                    selectinload(AgentTask.tool_calls),
                    selectinload(AgentTask.artifacts),
                    selectinload(AgentTask.approval_events),
                )
                .order_by(AgentTask.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return list(tasks), total

    def approve_task(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        note: str | None = None,
        approver_user_id: uuid.UUID | None = None,
    ) -> AgentTask:
        task = self.get_task(task_id, tenant_id)
        if task.status != "needs_approval":
            return task
        for step in task.steps:
            if step.status == "needs_approval":
                self.db.add(
                    AgentApprovalEvent(
                        task_id=task.id,
                        step_id=step.id,
                        user_id=approver_user_id or task.user_id,
                        action="approved",
                        tool_name=step.tool_name,
                        note=note,
                        meta={"tool_input": step.tool_input},
                    )
                )
                step.status = "approved"
        task.status = "running"
        task.result = {**(task.result or {}), "approval_note": note, "approved_at": _utc_now().isoformat()}
        self.db.commit()
        self.run_task(task.id, resume=True)
        return self.get_task(task.id, tenant_id)

    def reject_task(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        note: str | None = None,
        approver_user_id: uuid.UUID | None = None,
    ) -> AgentTask:
        task = self.get_task(task_id, tenant_id)
        pending_step = next((step for step in task.steps if step.status == "needs_approval"), None)
        self.db.add(
            AgentApprovalEvent(
                task_id=task.id,
                step_id=pending_step.id if pending_step else None,
                user_id=approver_user_id or task.user_id,
                action="rejected",
                tool_name=pending_step.tool_name if pending_step else None,
                note=note,
            )
        )
        task.status = "failed"
        task.error = note or "Rejected by user"
        task.completed_at = _utc_now()
        self.db.commit()
        collector.record_agent_task("rejected")
        return self.get_task(task.id, tenant_id)

    def pause_task(self, task_id: uuid.UUID, tenant_id: uuid.UUID, note: str | None = None) -> AgentTask:
        task = self.get_task(task_id, tenant_id)
        if task.status in {"completed", "failed", "cancelled"}:
            return task
        task.status = "paused"
        task.result = {**(task.result or {}), "pause_note": note, "paused_at": _utc_now().isoformat()}
        self.db.commit()
        collector.record_agent_task("paused")
        return self.get_task(task.id, tenant_id)

    def cancel_task(self, task_id: uuid.UUID, tenant_id: uuid.UUID, note: str | None = None) -> AgentTask:
        task = self.get_task(task_id, tenant_id)
        if task.status in {"completed", "failed", "cancelled"}:
            return task
        task.status = "cancelled"
        task.error = note or "Cancelled by user"
        task.completed_at = _utc_now()
        for step in task.steps:
            if step.status in {"pending", "planning", "running", "needs_approval", "approved"}:
                step.status = "cancelled"
                step.error = task.error
        self.db.commit()
        collector.record_agent_task("cancelled")
        return self.get_task(task.id, tenant_id)

    def resume_task(self, task_id: uuid.UUID, tenant_id: uuid.UUID, run: bool = True) -> AgentTask:
        task = self.get_task(task_id, tenant_id)
        if task.status not in {"paused", "failed", "pending", "running"}:
            return task
        for step in task.steps:
            if step.status in {"cancelled", "running"}:
                step.status = "pending"
                step.error = None
        task.status = "running"
        task.error = None
        task.completed_at = None
        self.db.commit()
        if run:
            self.run_task(task.id, resume=True)
        return self.get_task(task.id, tenant_id)

    def retry_step(self, task_id: uuid.UUID, step_id: uuid.UUID, tenant_id: uuid.UUID, run: bool = True) -> AgentTask:
        task = self.get_task(task_id, tenant_id)
        target = next((step for step in task.steps if step.id == step_id), None)
        if not target:
            raise ValueError(f"Agent step not found: {step_id}")
        for step in task.steps:
            if step.step_index >= target.step_index:
                step.status = "pending"
                step.observation = {}
                step.error = None
                step.latency_ms = None
        task.status = "running"
        task.error = None
        task.completed_at = None
        task.result = {**(task.result or {}), "retried_step_id": str(step_id), "retried_at": _utc_now().isoformat()}
        self.db.commit()
        if run:
            self.run_task(task.id, resume=True)
        return self.get_task(task.id, tenant_id)

    def _first_document_id(self, kb_id: uuid.UUID | None) -> str | None:
        if not kb_id:
            return None
        doc = (
            self.db.execute(
                select(Document)
                .where(Document.knowledge_base_id == kb_id, Document.is_deleted == False)  # noqa: E712
                .order_by(Document.created_at.desc())
            )
            .scalars()
            .first()
        )
        return str(doc.id) if doc else None

    def _first_two_document_ids(self, kb_id: uuid.UUID | None) -> list[str]:
        if not kb_id:
            return []
        docs = (
            self.db.execute(
                select(Document)
                .where(Document.knowledge_base_id == kb_id, Document.is_deleted == False)  # noqa: E712
                .order_by(Document.created_at.desc())
                .limit(2)
            )
            .scalars()
            .all()
        )
        return [str(doc.id) for doc in docs]

    def plan_task(self, task: AgentTask) -> list[dict[str, Any]]:
        """Create a task plan with optional LLM planning and safe fallback."""
        fallback_plan = self._rule_plan_task(task)
        planner_result = AgentPlanner().plan(task.goal, task.knowledge_base_id, fallback_plan)
        task.result = {
            **(task.result or {}),
            "planner_mode": planner_result.mode,
            "planner_error": planner_result.error,
        }
        return planner_result.plan

    def _rule_plan_task(self, task: AgentTask) -> list[dict[str, Any]]:
        """Create a conservative deterministic plan for v1."""
        goal = task.goal
        kb_id = str(task.knowledge_base_id) if task.knowledge_base_id else ""
        plan: list[dict[str, Any]] = []
        normalized_goal = goal.lower()
        compare_keywords = ["对比", "比较", "差异", "compare", "diff"]
        summary_keywords = ["摘要", "总结", "概括", "summary", "summarize"]
        publish_keywords = ["发布", "发送", "外部", "提交", "publish", "send", "external"]

        if kb_id:
            plan.append({
                "description": "列出知识库文档，确定可用资料范围",
                "tool_name": "list_documents",
                "tool_input": {"knowledge_base_id": kb_id, "limit": 20},
            })
            plan.append({
                "description": "搜索知识库，收集和任务目标相关的证据",
                "tool_name": "search_kb",
                "tool_input": {"knowledge_base_id": kb_id, "query": goal, "top_k": 5},
            })

        if any(word in normalized_goal for word in compare_keywords):
            doc_ids = self._first_two_document_ids(task.knowledge_base_id)
            if len(doc_ids) >= 2:
                plan.append({
                    "description": "对比两个相关文档，提取差异",
                    "tool_name": "compare_documents",
                    "tool_input": {"left_document_id": doc_ids[0], "right_document_id": doc_ids[1]},
                })
        elif any(word in normalized_goal for word in summary_keywords):
            doc_id = self._first_document_id(task.knowledge_base_id)
            if doc_id:
                plan.append({
                    "description": "摘要最相关文档，形成任务背景",
                    "tool_name": "summarize_document",
                    "tool_input": {"document_id": doc_id},
                })

        if kb_id:
            plan.append({
                "description": "基于检索来源回答核心问题",
                "tool_name": "ask_rag",
                "tool_input": {"knowledge_base_id": kb_id, "question": goal, "top_k": 5},
            })

        plan.append({
            "description": "生成结构化 Markdown 报告并附上引用来源",
            "tool_name": "create_report",
            "tool_input": {
                "title": "Agent Task Report",
                "sections": [
                    {"heading": "Task", "content": goal},
                    {"heading": "Findings", "content": "Executor will fill findings from previous observations."},
                ],
                "sources": [],
            },
        })
        if any(word in normalized_goal for word in publish_keywords):
            plan.append({
                "description": "发布报告到外部目标，等待人工审批后执行",
                "tool_name": "publish_report",
                "tool_input": {
                    "title": "Agent Task Report",
                    "content": "Executor will fill report content after approval.",
                    "destination": "internal_demo_channel",
                },
            })
        return plan

    def run_task(self, task_id: uuid.UUID, resume: bool = False) -> AgentTask:
        task_row = self.db.get(AgentTask, task_id)
        if not task_row:
            raise ValueError(f"Agent task not found: {task_id}")
        task = self.get_task(task_id, tenant_id=task_row.tenant_id)
        if task.status == "cancelled":
            return task
        if task.status == "paused" and not resume:
            return task
        task.status = "running"
        self.db.commit()

        try:
            if not task.plan:
                task.status = "planning"
                task.plan = self.plan_task(task)
                self.db.flush()
                for index, item in enumerate(task.plan):
                    self.db.add(
                        AgentStep(
                            task_id=task.id,
                            step_index=index,
                            description=item["description"],
                            tool_name=item.get("tool_name"),
                            tool_input=item.get("tool_input", {}),
                        )
                    )
                self.db.commit()

            steps = (
                self.db.execute(
                    select(AgentStep)
                    .where(AgentStep.task_id == task.id)
                    .order_by(AgentStep.step_index.asc())
                )
                .scalars()
                .all()
            )
            context: dict[str, Any] = {"sources": [], "findings": []}
            task.status = "running"
            self.db.commit()

            for step in steps:
                self.db.refresh(task)
                if task.status == "cancelled":
                    return task
                if task.status == "paused":
                    return task
                if resume and step.status == "completed":
                    if step.observation:
                        self._update_context(context, step.tool_name or "", step.observation)
                    continue
                if not step.tool_name:
                    step.status = "completed"
                    continue

                spec = registry.get(step.tool_name)
                if not self._user_can_run_tool(task.user_id, task.tenant_id, spec.permission):
                    step.status = "failed"
                    step.error = f"Permission denied for tool permission: {spec.permission}"
                    task.status = "failed"
                    task.error = step.error
                    task.completed_at = _utc_now()
                    self.db.commit()
                    collector.record_agent_task("permission_denied")
                    return task

                if spec.requires_approval and step.status != "approved":
                    step.status = "needs_approval"
                    task.status = "needs_approval"
                    self.db.add(
                        AgentApprovalEvent(
                            task_id=task.id,
                            step_id=step.id,
                            user_id=task.user_id,
                            action="requested",
                            tool_name=step.tool_name,
                            meta={"permission": spec.permission, "tool_input": step.tool_input},
                        )
                    )
                    collector.record_agent_approval_required()
                    self.db.commit()
                    return task

                step.status = "running"
                self.db.commit()
                raw_input = dict(step.tool_input or {})
                raw_input = self._repair_tool_input(step.tool_name, raw_input, task)
                if step.tool_name == "create_report":
                    if self._should_stop_for_missing_sources(context):
                        self._create_failure_artifact(task, "No usable sources were retrieved for this task.")
                        task.status = "failed"
                        task.error = "No usable sources were retrieved for this task."
                        task.completed_at = _utc_now()
                        self.db.commit()
                        collector.record_agent_task("failed")
                        return self.get_task(task.id, task.tenant_id)
                    raw_input = self._fill_report_input(raw_input, context)
                elif step.tool_name == "publish_report":
                    raw_input = self._fill_publish_input(raw_input, task)

                started = time.perf_counter()
                result = registry.run(self.db, task.tenant_id, step.tool_name, raw_input)
                if step.tool_name == "search_kb" and result.ok and not result.data.get("results"):
                    repaired_input = self._repair_search_input(raw_input)
                    if repaired_input != raw_input:
                        result = registry.run(self.db, task.tenant_id, step.tool_name, repaired_input)
                        raw_input = repaired_input
                latency_ms = result.latency_ms or ((time.perf_counter() - started) * 1000)
                tool_call = ToolCall(
                    task_id=task.id,
                    step_id=step.id,
                    tool_name=step.tool_name,
                    tool_input=raw_input,
                    tool_output=result.data,
                    status="completed" if result.ok else "failed",
                    latency_ms=latency_ms,
                    error=result.error,
                    token_usage=self._estimate_token_usage(raw_input, result.data),
                )
                self.db.add(tool_call)
                collector.record_agent_tool_call(step.tool_name, ok=result.ok, latency_ms=latency_ms)

                step.latency_ms = latency_ms
                step.observation = result.data
                step.error = result.error
                step.status = "completed" if result.ok else "failed"
                collector.record_agent_step_latency(latency_ms)

                if result.ok:
                    self._update_context(context, step.tool_name, result.data)
                    if step.tool_name == "create_report":
                        artifact = AgentArtifact(
                            task_id=task.id,
                            artifact_type="markdown_report",
                            title=result.data.get("title", "Agent Report"),
                            content=result.data.get("content", ""),
                            meta={"sources": result.data.get("sources", [])},
                        )
                        self.db.add(artifact)
                else:
                    task.retry_count += 1
                    if task.retry_count <= 1:
                        step.status = "pending"
                        self.db.commit()
                        continue
                    task.status = "failed"
                    task.error = result.error
                    task.completed_at = _utc_now()
                    self.db.commit()
                    collector.record_agent_task("failed")
                    return task
                self.db.commit()

            task.status = "completed"
            task.result = {**(task.result or {}), **self._build_final_result(context, task.id)}
            task.completed_at = _utc_now()
            self.db.commit()
            collector.record_agent_task("completed")
            return self.get_task(task.id, task.tenant_id)
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            task.completed_at = _utc_now()
            self.db.commit()
            collector.record_agent_task("failed")
            return self.get_task(task.id, task.tenant_id)

    def _update_context(self, context: dict[str, Any], tool_name: str, data: dict[str, Any]) -> None:
        if tool_name == "search_kb":
            context["sources"].extend(data.get("results", []))
            context["findings"].append(f"检索到 {len(data.get('results', []))} 条相关来源。")
        elif tool_name == "ask_rag":
            context["sources"].extend(data.get("sources", []))
            context["findings"].append(data.get("answer", ""))
        elif tool_name == "list_documents":
            context["findings"].append(f"知识库中共有 {len(data.get('documents', []))} 个可见文档。")
        elif tool_name == "summarize_document":
            context["findings"].append(data.get("summary", ""))
        elif tool_name == "compare_documents":
            context["findings"].append(f"文档相似度：{data.get('similarity')}")

    def _fill_report_input(self, raw_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        findings = "\n".join(f"- {item}" for item in context.get("findings", []) if item)
        if not findings:
            findings = "- 未收集到足够证据。"
        raw_input["sections"] = [
            raw_input.get("sections", [{"heading": "Task", "content": ""}])[0],
            {"heading": "Findings", "content": findings},
            {"heading": "Next Actions", "content": "- 根据引用来源复核结论\n- 补充缺失文档后重新运行任务"},
        ]
        raw_input["sources"] = context.get("sources", [])[:10]
        return raw_input

    def _should_stop_for_missing_sources(self, context: dict[str, Any]) -> bool:
        findings = context.get("findings", [])
        return bool(findings) and not context.get("sources")

    def _create_failure_artifact(self, task: AgentTask, reason: str) -> None:
        self.db.add(
            AgentArtifact(
                task_id=task.id,
                artifact_type="failure_report",
                title="Agent Task Needs More Evidence",
                content=(
                    "# Agent Task Needs More Evidence\n\n"
                    f"## Task\n\n{task.goal}\n\n"
                    f"## Reason\n\n{reason}\n\n"
                    "## Suggested Recovery\n\n"
                    "- Add or re-upload relevant documents.\n"
                    "- Retry the failed retrieval step.\n"
                    "- Re-run the task after evidence is available.\n"
                ),
                meta={"reason": reason},
            )
        )

    def _repair_tool_input(self, tool_name: str | None, raw_input: dict[str, Any], task: AgentTask) -> dict[str, Any]:
        if not tool_name:
            return raw_input
        repaired = dict(raw_input)
        kb_id = str(task.knowledge_base_id) if task.knowledge_base_id else None
        if kb_id and tool_name in {"search_kb", "list_documents", "ask_rag"}:
            repaired.setdefault("knowledge_base_id", kb_id)
        if tool_name == "search_kb":
            repaired.setdefault("query", task.goal)
            repaired.setdefault("top_k", 5)
        elif tool_name == "ask_rag":
            repaired.setdefault("question", task.goal)
            repaired.setdefault("top_k", 5)
        elif tool_name == "list_documents":
            repaired.setdefault("limit", 20)
        elif tool_name == "create_report":
            repaired.setdefault("title", "Agent Task Report")
            repaired.setdefault("sections", [{"heading": "Task", "content": task.goal}])
            repaired.setdefault("sources", [])
        if repaired != raw_input:
            repaired["repair_reason"] = "missing_required_tool_input"
        return repaired

    def _repair_search_input(self, raw_input: dict[str, Any]) -> dict[str, Any]:
        """Rewrite a failed retrieval query once using a simple keyword fallback."""
        query = str(raw_input.get("query", "")).strip()
        if not query:
            return raw_input
        tokens = [token for token in query.replace("，", " ").replace("。", " ").split() if len(token) > 1]
        rewritten = " ".join(tokens[:8]) or query[:80]
        repaired = dict(raw_input)
        repaired["query"] = rewritten
        repaired["top_k"] = max(int(repaired.get("top_k", 5)), 10)
        repaired["retry_reason"] = "empty_retrieval_query_rewrite"
        return repaired

    def _fill_publish_input(self, raw_input: dict[str, Any], task: AgentTask) -> dict[str, Any]:
        artifact = (
            self.db.execute(
                select(AgentArtifact)
                .where(AgentArtifact.task_id == task.id)
                .order_by(AgentArtifact.created_at.desc())
            )
            .scalars()
            .first()
        )
        if artifact:
            raw_input["title"] = artifact.title
            raw_input["content"] = artifact.content
        return raw_input

    def _build_final_result(self, context: dict[str, Any], task_id: uuid.UUID) -> dict[str, Any]:
        token_usage = self._task_token_usage(task_id)
        return {
            "summary": "\n".join(context.get("findings", [])[-3:]),
            "source_count": len(context.get("sources", [])),
            "sources": context.get("sources", [])[:10],
            "token_usage": token_usage,
        }

    def _estimate_token_usage(self, tool_input: dict[str, Any], tool_output: dict[str, Any]) -> dict[str, Any]:
        input_tokens = max(1, len(str(tool_input)) // 4)
        output_tokens = max(1, len(str(tool_output)) // 4)
        total_tokens = input_tokens + output_tokens
        estimated_cost_usd = round(total_tokens * 0.0000005, 6)
        collector.record_token_count(total_tokens)
        collector.record_agent_token_usage(total_tokens, estimated_cost_usd)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        }

    def _task_token_usage(self, task_id: uuid.UUID | None) -> dict[str, Any]:
        if not task_id:
            return {"total_tokens": 0, "estimated_cost_usd": 0.0}
        calls = (
            self.db.execute(select(ToolCall).where(ToolCall.task_id == task_id))
            .scalars()
            .all()
        )
        total_tokens = sum((call.token_usage or {}).get("total_tokens", 0) for call in calls)
        estimated_cost = sum((call.token_usage or {}).get("estimated_cost_usd", 0.0) for call in calls)
        return {"total_tokens": total_tokens, "estimated_cost_usd": round(estimated_cost, 6)}

    def _user_can_run_tool(self, user_id: uuid.UUID, tenant_id: uuid.UUID, permission: str) -> bool:
        if permission == "read":
            return True
        user = self.db.get(User, user_id)
        if user and user.is_superuser:
            return True

        user_roles = (
            self.db.execute(select(UserRole).where(UserRole.user_id == user_id, UserRole.tenant_id == tenant_id))
            .scalars()
            .all()
        )
        if not user_roles:
            return True

        required = {("agent", permission), ("agent_tool", permission), ("agent", "write")}
        for user_role in user_roles:
            role = self.db.get(Role, user_role.role_id)
            if role and role.is_system:
                return True
            for role_permission in role.permissions if role else []:
                if (role_permission.resource, role_permission.action) in required:
                    return True
        return False
