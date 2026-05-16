"""Knowledge base service."""

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import KnowledgeBase, Document, Chunk, Tenant
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseNotFoundError(Exception):
    """Raised when knowledge base is not found."""

    def __init__(self, kb_id: uuid.UUID):
        self.kb_id = kb_id
        super().__init__(f"Knowledge base not found: {kb_id}")


class KnowledgeBaseService:
    """Service for knowledge base operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: KnowledgeBaseCreate, tenant_id: uuid.UUID) -> KnowledgeBase:
        """Create a new knowledge base for a tenant."""
        kb = KnowledgeBase(
            name=data.name,
            description=data.description or "",
            tenant_id=tenant_id,
        )
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[KnowledgeBase], int]:
        """List all knowledge bases for a tenant with pagination."""
        base_q = select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant_id)
        total = self.db.execute(select(func.count()).select_from(base_q.subquery())).scalar_one()
        kbs = (
            self.db.execute(
                select(KnowledgeBase)
                .where(KnowledgeBase.tenant_id == tenant_id)
                .offset(skip)
                .limit(limit)
                .order_by(KnowledgeBase.created_at.desc())
            )
            .scalars()
            .all()
        )
        return list(kbs), total

    def get_by_id(self, kb_id: uuid.UUID, tenant_id: uuid.UUID) -> KnowledgeBase:
        """Get a knowledge base by ID, scoped to tenant."""
        kb = self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id)
        return kb

    def update(
        self, kb_id: uuid.UUID, tenant_id: uuid.UUID, data: KnowledgeBaseUpdate
    ) -> KnowledgeBase:
        """Update a knowledge base."""
        kb = self.get_by_id(kb_id, tenant_id)
        if data.name is not None:
            kb.name = data.name
        if data.description is not None:
            kb.description = data.description
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def delete(self, kb_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Delete a knowledge base and all its documents/chunks."""
        kb = self.get_by_id(kb_id, tenant_id)
        self.db.delete(kb)
        self.db.commit()

    def get_document_count(self, kb_id: uuid.UUID) -> int:
        """Get document count for a knowledge base."""
        return (
            self.db.execute(
                select(func.count()).select_from(Document).where(Document.knowledge_base_id == kb_id)
            )
            .scalar_one()
        )

    def get_chunk_count(self, kb_id: uuid.UUID) -> int:
        """Get total chunk count for a knowledge base."""
        return (
            self.db.execute(
                select(func.count()).select_from(Chunk).where(
                    Chunk.document_id.in_(
                        select(Document.id).where(Document.knowledge_base_id == kb_id)
                    )
                )
            )
            .scalar_one()
        )
