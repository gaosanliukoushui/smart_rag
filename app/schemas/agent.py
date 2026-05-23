"""Agent API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentTaskCreate(BaseModel):
    """Request to create and run an agent task."""

    goal: str = Field(min_length=3, max_length=4000)
    knowledge_base_id: UUID | None = None
    auto_run: bool = True


class AgentStepResponse(BaseModel):
    id: UUID
    step_index: int
    description: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    observation: dict[str, Any] | None = None
    status: str
    latency_ms: float | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolCallResponse(BaseModel):
    id: UUID
    step_id: UUID | None = None
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: dict[str, Any] | None = None
    status: str
    latency_ms: float | None = None
    error: str | None = None
    token_usage: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentArtifactResponse(BaseModel):
    id: UUID
    artifact_type: str
    title: str
    content: str
    meta: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentApprovalEventResponse(BaseModel):
    id: UUID
    step_id: UUID | None = None
    user_id: UUID | None = None
    action: str
    tool_name: str | None = None
    note: str | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentTaskResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    knowledge_base_id: UUID | None = None
    goal: str
    status: str
    plan: list[dict[str, Any]] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[AgentStepResponse] = Field(default_factory=list)
    tool_calls: list[ToolCallResponse] = Field(default_factory=list)
    artifacts: list[AgentArtifactResponse] = Field(default_factory=list)
    approval_events: list[AgentApprovalEventResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AgentTaskListResponse(BaseModel):
    tasks: list[AgentTaskResponse]
    total: int


class AgentApprovalRequest(BaseModel):
    note: str | None = None


class ToolSpecResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    requires_approval: bool
    permission: str
