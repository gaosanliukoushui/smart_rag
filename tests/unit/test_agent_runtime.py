"""Tests for the Agent runtime."""

import uuid

from app.models import Chunk, Document, KnowledgeBase, Role, Tenant, User, UserRole
from app.config import get_settings
from app.core.security import get_password_hash
from app.services.agent_planner import AgentPlanner
from app.services.agent_service import AgentService


def _seed_agent_fixture(db):
    tenant = Tenant(name="Agent Tenant", slug=f"agent-{uuid.uuid4().hex[:8]}")
    user = User(
        username=f"agent-user-{uuid.uuid4().hex[:8]}",
        email=f"agent-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
    )
    db.add_all([tenant, user])
    db.flush()
    kb = KnowledgeBase(name="Agent KB", description="Agent test KB", tenant_id=tenant.id)
    db.add(kb)
    db.flush()
    doc = Document(
        title="deployment",
        file_path="demo.md",
        file_type=".md",
        file_size=120,
        status="ready",
        chunk_count=1,
        knowledge_base_id=kb.id,
    )
    db.add(doc)
    db.flush()
    chunk = Chunk(
        document_id=doc.id,
        content="部署 checklist 需要包含健康检查、Prometheus 指标、回滚计划和日志监控。",
        chunk_index=0,
        token_count=20,
    )
    db.add(chunk)
    db.commit()
    return tenant, user, kb


def test_agent_task_runs_plan_and_persists_trace(db):
    tenant, user, kb = _seed_agent_fixture(db)
    service = AgentService(db)

    task = service.create_task(
        goal="根据部署文档生成上线 checklist，并指出缺失的监控项",
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=True,
    )

    assert task.status == "completed"
    assert len(task.steps) >= 4
    assert len(task.tool_calls) >= 4
    assert task.artifacts
    assert task.result["source_count"] >= 1
    assert task.result["planner_mode"] == "rule"
    assert task.result["token_usage"]["total_tokens"] > 0
    assert any(call.tool_name == "search_kb" for call in task.tool_calls)
    assert "Findings" in task.artifacts[0].content


def test_agent_task_is_tenant_scoped(db):
    tenant, user, kb = _seed_agent_fixture(db)
    other_tenant = Tenant(name="Other Tenant", slug=f"other-{uuid.uuid4().hex[:8]}")
    db.add(other_tenant)
    db.commit()
    service = AgentService(db)
    task = service.create_task(
        goal="总结部署要求",
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=False,
    )

    try:
        service.get_task(task.id, other_tenant.id)
        found = True
    except ValueError:
        found = False

    assert found is False


def test_agent_task_requires_approval_for_publish(db):
    tenant, user, kb = _seed_agent_fixture(db)
    service = AgentService(db)

    task = service.create_task(
        goal="根据部署文档生成报告并发布到外部渠道",
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=True,
    )

    assert task.status == "needs_approval"
    assert any(step.tool_name == "publish_report" and step.status == "needs_approval" for step in task.steps)
    assert any(event.action == "requested" and event.tool_name == "publish_report" for event in task.approval_events)

    approved = service.approve_task(task.id, tenant.id, note="demo approval")

    assert approved.status == "completed"
    assert any(call.tool_name == "publish_report" for call in approved.tool_calls)
    assert any(event.action == "approved" and event.tool_name == "publish_report" for event in approved.approval_events)


def test_agent_tool_permission_denied_for_write_tool(db):
    tenant, user, kb = _seed_agent_fixture(db)
    viewer_role = Role(name=f"viewer-{uuid.uuid4().hex[:8]}", description="Viewer")
    db.add(viewer_role)
    db.flush()
    db.add(UserRole(user_id=user.id, tenant_id=tenant.id, role_id=viewer_role.id))
    db.commit()
    service = AgentService(db)

    task = service.create_task(
        goal="根据部署文档生成报告并发布到外部渠道",
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=True,
    )

    assert task.status == "failed"
    assert "Permission denied" in task.error


def test_agent_task_pause_cancel_resume_and_retry(db):
    tenant, user, kb = _seed_agent_fixture(db)
    service = AgentService(db)

    task = service.create_task(
        goal="总结部署要求",
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=False,
    )
    paused = service.pause_task(task.id, tenant.id, note="pause test")
    assert paused.status == "paused"

    resumed = service.resume_task(task.id, tenant.id)
    assert resumed.status == "completed"
    assert resumed.steps

    retried = service.retry_step(resumed.id, resumed.steps[0].id, tenant.id)
    assert retried.status == "completed"
    assert retried.result["retried_step_id"] == str(resumed.steps[0].id)

    cancel_task = service.create_task(
        goal="总结部署要求",
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=False,
    )
    cancelled = service.cancel_task(cancel_task.id, tenant.id, note="cancel test")
    assert cancelled.status == "cancelled"
    assert cancelled.error == "cancel test"


def test_agent_creates_failure_artifact_when_no_sources(db):
    tenant = Tenant(name="Empty Tenant", slug=f"empty-{uuid.uuid4().hex[:8]}")
    user = User(
        username=f"empty-user-{uuid.uuid4().hex[:8]}",
        email=f"empty-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("password123"),
    )
    db.add_all([tenant, user])
    db.flush()
    kb = KnowledgeBase(name="Empty KB", description="No docs", tenant_id=tenant.id)
    db.add(kb)
    db.commit()
    service = AgentService(db)

    task = service.create_task(
        goal="根据知识库生成上线 checklist",
        tenant_id=tenant.id,
        user_id=user.id,
        knowledge_base_id=kb.id,
        auto_run=True,
    )

    assert task.status == "failed"
    assert task.artifacts
    assert task.artifacts[0].artifact_type == "failure_report"


def test_agent_planner_validates_tool_inputs(db):
    tenant, user, kb = _seed_agent_fixture(db)
    _ = tenant, user
    raw_plan = [
        {
            "description": "Search evidence.",
            "tool_name": "search_kb",
            "tool_input": {"query": "deployment checklist"},
        },
        {
            "description": "Create final report.",
            "tool_name": "create_report",
            "tool_input": {"title": "Demo", "sections": [{"heading": "Result", "content": "ok"}]},
        },
    ]

    plan = AgentPlanner().validate_plan(raw_plan, kb.id, "deployment checklist")

    assert plan[0]["tool_input"]["knowledge_base_id"] == str(kb.id)
    assert plan[0]["tool_input"]["top_k"] == 5
    assert plan[-1]["tool_name"] == "create_report"


def test_agent_planner_falls_back_when_llm_fails(monkeypatch):
    settings = get_settings()
    original_mode = settings.AGENT_PLANNER_MODE
    monkeypatch.setattr(settings, "AGENT_PLANNER_MODE", "llm_fallback")
    monkeypatch.setattr(AgentPlanner, "_call_llm", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    fallback = [{"description": "Create report.", "tool_name": "create_report", "tool_input": {"title": "Demo", "sections": []}}]
    result = AgentPlanner().plan("demo task", None, fallback)

    assert result.mode == "rule_fallback"
    assert result.plan == fallback
    assert "boom" in result.error
    monkeypatch.setattr(settings, "AGENT_PLANNER_MODE", original_mode)
