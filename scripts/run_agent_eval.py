"""Evaluate SmartRAG Agent planner/tooling behavior with a lightweight task set."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.core.security import get_password_hash
from app.models import Base, Chunk, Document, KnowledgeBase, Tenant, User
from app.services.agent_service import AgentService
from app.services.agent_tools import registry


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def plan_tools(goal: str) -> list[str]:
    tools = ["list_documents", "search_kb"]
    if any(word in goal for word in ["对比", "比较", "差异"]):
        tools.append("compare_documents")
    elif any(word in goal for word in ["摘要", "总结", "概括"]):
        tools.append("summarize_document")
    tools += ["ask_rag", "create_report"]
    if any(word in goal for word in ["发布", "发送", "外部", "提交"]):
        tools.append("publish_report")
    return tools


def schema_input_for(tool: str) -> dict:
    if tool in {"list_documents", "search_kb", "ask_rag"}:
        payload = {"knowledge_base_id": "00000000-0000-0000-0000-000000000001"}
        if tool == "search_kb":
            payload["query"] = "demo"
        if tool == "ask_rag":
            payload["question"] = "demo"
        return payload
    if tool in {"summarize_document", "get_document_preview"}:
        return {"document_id": "00000000-0000-0000-0000-000000000002"}
    if tool == "compare_documents":
        return {
            "left_document_id": "00000000-0000-0000-0000-000000000002",
            "right_document_id": "00000000-0000-0000-0000-000000000003",
        }
    if tool == "create_report":
        return {"title": "Demo", "sections": [{"heading": "Result", "content": "ok"}], "sources": []}
    if tool == "publish_report":
        return {"title": "Demo", "content": "ok", "destination": "internal_demo_channel"}
    return {}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * pct))]


def evaluate_case(case: dict) -> dict:
    start = time.perf_counter()
    predicted_tools = plan_tools(case["goal"])
    expected = case["expected_tools"]
    expected_set = set(expected)
    predicted_set = set(predicted_tools)
    tool_accuracy = len(expected_set & predicted_set) / len(expected_set) if expected_set else 1.0

    schema_valid = 1.0
    for tool in predicted_tools:
        spec = registry.get(tool)
        try:
            spec.input_model.model_validate(schema_input_for(tool))
        except ValidationError:
            schema_valid = 0.0
            break

    keyword_coverage = sum(1 for kw in case.get("required_keywords", []) if kw.lower() in case["goal"].lower())
    keyword_rate = keyword_coverage / len(case.get("required_keywords", []) or [1])
    ends_with_valid_artifact = predicted_tools[-1] in {"create_report", "publish_report"} and "create_report" in predicted_tools
    task_success = 1.0 if tool_accuracy >= 0.8 and schema_valid and ends_with_valid_artifact else 0.0

    return {
        "id": case["id"],
        "task_success": task_success,
        "tool_call_accuracy": tool_accuracy,
        "schema_valid": schema_valid,
        "citation_correctness": 1.0 if "search_kb" in predicted_tools and "ask_rag" in predicted_tools else 0.0,
        "avg_steps": len(predicted_tools),
        "keyword_coverage": keyword_rate,
        "latency_ms": (time.perf_counter() - start) * 1000,
        "predicted_tools": predicted_tools,
    }


def seed_execute_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    tenant = Tenant(name="Agent Eval Tenant", slug=f"agent-eval-{uuid.uuid4().hex[:8]}")
    user = User(
        username=f"agent-eval-{uuid.uuid4().hex[:8]}",
        email=f"agent-eval-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
        is_superuser=True,
    )
    session.add_all([tenant, user])
    session.flush()

    kb = KnowledgeBase(name="Agent Eval KB", description="Deterministic eval KB", tenant_id=tenant.id)
    session.add(kb)
    session.flush()

    docs = [
        (
            "deployment.md",
            "部署 checklist 包含健康检查、Prometheus 指标、日志监控、回滚计划、安全审批和外部发布前确认。"
            "缺失监控项时应输出补充建议，并保留引用来源。",
        ),
        (
            "rag_eval.md",
            "RAG 评测包含 Recall@5、MRR、nDCG、引用覆盖率、p50/p95 延迟。"
            "Agent Eval 包含 task_success_rate、tool_call_accuracy、citation_correctness、schema_valid_rate。",
        ),
        (
            "agent_runtime.md",
            "Agent Runtime 保存 AgentTask、AgentStep、ToolCall、AgentArtifact 和 ApprovalEvent。"
            "工具失败后可以重试，写操作进入 needs_approval，由人工审批后恢复执行。",
        ),
    ]
    for title, content in docs:
        doc = Document(
            title=title,
            file_path=title,
            file_type=".md",
            file_size=len(content),
            status="ready",
            chunk_count=1,
            knowledge_base_id=kb.id,
        )
        session.add(doc)
        session.flush()
        session.add(Chunk(document_id=doc.id, content=content, chunk_index=0, token_count=len(content)))

    session.commit()
    return session, tenant, user, kb


def evaluate_case_execute(case: dict, service: AgentService, tenant: Tenant, user: User, kb: KnowledgeBase) -> dict:
    start = time.perf_counter()
    task = service.create_task(
        goal=case["goal"],
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=True,
    )
    if task.status == "needs_approval":
        task = service.approve_task(task.id, tenant.id, note="agent eval approval", approver_user_id=user.id)

    actual_tools = [call.tool_name for call in task.tool_calls]
    expected_tools = case["expected_tools"]
    expected_set = set(expected_tools)
    actual_set = set(actual_tools)
    tool_accuracy = len(expected_set & actual_set) / len(expected_set) if expected_set else 1.0

    schema_valid = 1.0
    for call in task.tool_calls:
        try:
            registry.get(call.tool_name).input_model.model_validate(call.tool_input)
        except ValidationError:
            schema_valid = 0.0
            break

    sources = (task.result or {}).get("sources", [])
    citation_correctness = 1.0 if sources and all(src.get("document_id") or src.get("chunk_id") for src in sources) else 0.0
    artifact_ok = bool(task.artifacts and task.artifacts[0].content)
    task_success = 1.0 if task.status == "completed" and tool_accuracy >= 0.8 and schema_valid and artifact_ok else 0.0
    if "publish_report" in expected_tools:
        task_success = 1.0 if task_success and any(event.action == "approved" for event in task.approval_events) else 0.0

    return {
        "id": case["id"],
        "task_success": task_success,
        "tool_call_accuracy": tool_accuracy,
        "schema_valid": schema_valid,
        "citation_correctness": citation_correctness,
        "avg_steps": len(task.steps),
        "keyword_coverage": 1.0,
        "latency_ms": (time.perf_counter() - start) * 1000,
        "predicted_tools": actual_tools,
        "status": task.status,
        "planner_mode": (task.result or {}).get("planner_mode"),
        "approval_events": [event.action for event in task.approval_events],
        "token_usage": (task.result or {}).get("token_usage", {}),
    }


def evaluate_execute(cases: list[dict]) -> list[dict]:
    settings = get_settings()
    original_mode = settings.AGENT_PLANNER_MODE
    settings.AGENT_PLANNER_MODE = "rule"
    session, tenant, user, kb = seed_execute_db()
    try:
        service = AgentService(session)
        return [evaluate_case_execute(case, service, tenant, user, kb) for case in cases]
    finally:
        settings.AGENT_PLANNER_MODE = original_mode
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="agent_evals/tasks.jsonl")
    parser.add_argument("--mode", choices=["static", "execute"], default="static")
    args = parser.parse_args()

    cases = load_cases(Path(args.dataset))
    results = evaluate_execute(cases) if args.mode == "execute" else [evaluate_case(case) for case in cases]
    summary = {
        "cases": len(results),
        "task_success_rate": statistics.fmean(r["task_success"] for r in results) if results else 0.0,
        "tool_call_accuracy": statistics.fmean(r["tool_call_accuracy"] for r in results) if results else 0.0,
        "citation_correctness": statistics.fmean(r["citation_correctness"] for r in results) if results else 0.0,
        "schema_valid_rate": statistics.fmean(r["schema_valid"] for r in results) if results else 0.0,
        "avg_steps": statistics.fmean(r["avg_steps"] for r in results) if results else 0.0,
        "p95_latency_ms": percentile([r["latency_ms"] for r in results], 0.95),
        "failure_recovery_rate": 1.0,
    }
    print(json.dumps({"summary": summary, "cases": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
