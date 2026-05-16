"""SQLAlchemy ORM base and shared utilities."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    type_annotation_map = {
        uuid.UUID: Uuid,
    }


def _utc_now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps.

    Uses Python-side defaults for cross-database compatibility
    (SQLite does not support server-side CURRENT_TIMESTAMP variants well).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )


class UUIDPrimaryKey:
    """Mixin to add a UUID primary key.

    Uses SQLAlchemy's Uuid type which maps to native UUID on PostgreSQL
    and uses String(36) storage on SQLite, while always returning
    Python uuid.UUID objects to the application.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
