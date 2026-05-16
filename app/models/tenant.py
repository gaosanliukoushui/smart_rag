"""Tenant ORM model."""

from sqlalchemy import String, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class Tenant(Base, UUIDPrimaryKey, TimestampMixin):
    """Tenant model for multi-tenancy support."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(
        "KnowledgeBase",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
