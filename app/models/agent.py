"""Agent runtime ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class AgentTask(Base, UUIDPrimaryKey, TimestampMixin):
    """Top-level agent task created by a user."""

    __tablename__ = "agent_tasks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    plan: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list["AgentStep"]] = relationship(
        "AgentStep",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AgentStep.step_index",
    )
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        "ToolCall",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    artifacts: Mapped[list["AgentArtifact"]] = relationship(
        "AgentArtifact",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    approval_events: Mapped[list["AgentApprovalEvent"]] = relationship(
        "AgentApprovalEvent",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AgentStep(Base, UUIDPrimaryKey, TimestampMixin):
    """One planned/executed step in an agent task."""

    __tablename__ = "agent_steps"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tool_input: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    observation: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    latency_ms: Mapped[float | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped["AgentTask"] = relationship("AgentTask", back_populates="steps")


class ToolCall(Base, UUIDPrimaryKey, TimestampMixin):
    """Detailed record of one tool invocation."""

    __tablename__ = "agent_tool_calls"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agent_steps.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_input: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tool_output: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    latency_ms: Mapped[float | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    task: Mapped["AgentTask"] = relationship("AgentTask", back_populates="tool_calls")


class AgentArtifact(Base, UUIDPrimaryKey, TimestampMixin):
    """Artifact created by an agent task, such as a report."""

    __tablename__ = "agent_artifacts"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)

    task: Mapped["AgentTask"] = relationship("AgentTask", back_populates="artifacts")


class AgentApprovalEvent(Base, UUIDPrimaryKey, TimestampMixin):
    """Human approval/rejection event for high-risk agent actions."""

    __tablename__ = "agent_approval_events"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agent_steps.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)

    task: Mapped["AgentTask"] = relationship("AgentTask", back_populates="approval_events")
