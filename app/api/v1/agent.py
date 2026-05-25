"""Agent task API endpoints."""

import json
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_tenant, get_db
from app.db.session import get_db_context
from app.models import AgentTask, Tenant, User
from app.schemas.agent import (
    AgentApprovalRequest,
    AgentTaskCreate,
    AgentTaskListResponse,
    AgentTaskResponse,
    ToolSpecResponse,
)
from app.services.agent_service import AgentService
from app.services.agent_tools import registry

router = APIRouter(prefix="/agent", tags=["Agent"])


def _run_task_background(task_id: uuid.UUID) -> None:
    """Run an agent task in a fresh DB session after the HTTP response returns."""
    with get_db_context() as background_db:
        AgentService(background_db).run_task(task_id)


def _resume_task_background(task_id: uuid.UUID) -> None:
    """Resume an existing task in a fresh DB session."""
    with get_db_context() as background_db:
        task = background_db.get(AgentTask, task_id)
        if task:
            AgentService(background_db).run_task(task_id, resume=True)


def _require_tenant(tenant: Optional[Tenant]) -> Tenant:
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return tenant


@router.get("/tools", response_model=list[ToolSpecResponse])
async def list_tools(
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """List registered agent tools and JSON schemas."""
    _require_tenant(tenant)
    return [
        ToolSpecResponse(
            name=spec.name,
            description=spec.description,
            input_schema=spec.input_schema,
            requires_approval=spec.requires_approval,
            permission=spec.permission,
        )
        for spec in registry.list_specs()
    ]


@router.post("/tasks", response_model=AgentTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: Request,
    payload: AgentTaskCreate,
    background_tasks: BackgroundTasks,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Create an agent task and optionally schedule it for background execution."""
    tenant = _require_tenant(tenant)
    service = AgentService(db)
    try:
        task = service.create_task(
            goal=payload.goal,
            tenant_id=tenant.id,
            user_id=current_user.id,
            knowledge_base_id=payload.knowledge_base_id,
            auto_run=False,
        )
        if payload.auto_run:
            task.status = "pending"
            db.commit()
            db.refresh(task)
            background_tasks.add_task(_run_task_background, task.id)
        return task
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/tasks", response_model=AgentTaskListResponse)
async def list_tasks(
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List agent tasks for the current tenant."""
    tenant = _require_tenant(tenant)
    tasks, total = AgentService(db).list_tasks(tenant.id, skip=skip, limit=limit)
    return AgentTaskListResponse(tasks=tasks, total=total)


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(
    task_id: uuid.UUID,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get one agent task with trace, tool calls, and artifacts."""
    tenant = _require_tenant(tenant)
    try:
        return AgentService(db).get_task(task_id, tenant.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent task not found: {task_id}")


@router.get("/tasks/{task_id}/events")
async def task_events(
    task_id: uuid.UUID,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Return task trace as an SSE event stream."""
    tenant = _require_tenant(tenant)

    async def event_generator():
        try:
            task = AgentService(db).get_task(task_id, tenant.id)
            yield {"event": "task", "data": json.dumps({"task_id": str(task.id), "status": task.status}, ensure_ascii=False)}
            for step in task.steps:
                yield {
                    "event": "step",
                    "data": json.dumps(
                        {
                            "id": str(step.id),
                            "index": step.step_index,
                            "description": step.description,
                            "tool_name": step.tool_name,
                            "status": step.status,
                            "latency_ms": step.latency_ms,
                            "observation": step.observation,
                            "error": step.error,
                        },
                        ensure_ascii=False,
                    ),
                }
            yield {"event": "done", "data": ""}
        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"error": str(exc)}, ensure_ascii=False)}
            yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@router.post("/tasks/{task_id}/approve", response_model=AgentTaskResponse)
async def approve_task(
    task_id: uuid.UUID,
    payload: AgentApprovalRequest | None = None,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Approve a task waiting for human confirmation."""
    tenant = _require_tenant(tenant)
    try:
        return AgentService(db).approve_task(
            task_id,
            tenant.id,
            note=payload.note if payload else None,
            approver_user_id=current_user.id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent task not found: {task_id}")


@router.post("/tasks/{task_id}/reject", response_model=AgentTaskResponse)
async def reject_task(
    task_id: uuid.UUID,
    payload: AgentApprovalRequest | None = None,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Reject a task waiting for human confirmation."""
    tenant = _require_tenant(tenant)
    try:
        return AgentService(db).reject_task(
            task_id,
            tenant.id,
            note=payload.note if payload else None,
            approver_user_id=current_user.id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent task not found: {task_id}")


@router.post("/tasks/{task_id}/pause", response_model=AgentTaskResponse)
async def pause_task(
    task_id: uuid.UUID,
    payload: AgentApprovalRequest | None = None,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Pause a task after the current running tool completes."""
    tenant = _require_tenant(tenant)
    try:
        return AgentService(db).pause_task(task_id, tenant.id, note=payload.note if payload else None)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent task not found: {task_id}")


@router.post("/tasks/{task_id}/cancel", response_model=AgentTaskResponse)
async def cancel_task(
    task_id: uuid.UUID,
    payload: AgentApprovalRequest | None = None,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Cancel a task and mark remaining steps as cancelled."""
    tenant = _require_tenant(tenant)
    try:
        return AgentService(db).cancel_task(task_id, tenant.id, note=payload.note if payload else None)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent task not found: {task_id}")


@router.post("/tasks/{task_id}/resume", response_model=AgentTaskResponse)
async def resume_task(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Resume a paused or failed task in the background."""
    tenant = _require_tenant(tenant)
    try:
        task = AgentService(db).resume_task(task_id, tenant.id, run=False)
        background_tasks.add_task(_resume_task_background, task.id)
        return task
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent task not found: {task_id}")


@router.post("/tasks/{task_id}/steps/{step_id}/retry", response_model=AgentTaskResponse)
async def retry_step(
    task_id: uuid.UUID,
    step_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Retry one step and all following steps in the background."""
    tenant = _require_tenant(tenant)
    try:
        task = AgentService(db).retry_step(task_id, step_id, tenant.id, run=False)
        background_tasks.add_task(_resume_task_background, task.id)
        return task
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
