"""Document service for handling document operations."""

from pathlib import Path
from typing import List, Optional, Protocol
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Document, Chunk, KnowledgeBase
from app.core.exceptions import DocumentNotFoundError
from app.core.logging import get_logger
from app.services.vector_store_service import VectorStoreService, get_vector_store

logger = get_logger(__name__)

_vector_store_service = get_vector_store()


class KnowledgeBaseNotFoundError(Exception):
    """Raised when knowledge base is not found."""

    def __init__(self, kb_id: UUID):
        self.kb_id = kb_id
        super().__init__(f"Knowledge base not found: {kb_id}")


class DocumentCreateData:
    """Data class for creating a document."""

    def __init__(
        self,
        title: str,
        file_path: str,
        file_type: str,
        file_size: int,
        knowledge_base_id: UUID,
        metadata: Optional[dict] = None,
    ):
        self.title = title
        self.file_path = file_path
        self.file_type = file_type
        self.file_size = file_size
        self.knowledge_base_id = knowledge_base_id
        self.metadata = metadata or {}


class DocumentService:
    """Service for document operations using SQLAlchemy ORM."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, doc_data: DocumentCreateData) -> Document:
        """Create a new document record."""
        logger.info(
            "document_create",
            title=doc_data.title,
            file_type=doc_data.file_type,
            kb_id=str(doc_data.knowledge_base_id),
        )
        doc = Document(
            title=doc_data.title,
            file_path=doc_data.file_path,
            file_type=doc_data.file_type,
            file_size=doc_data.file_size,
            knowledge_base_id=doc_data.knowledge_base_id,
            meta=doc_data.metadata,
        )
        self.db.add(doc)
        self.db.flush()
        self._update_kb_chunk_count(doc.knowledge_base_id)
        self.db.commit()
        self.db.refresh(doc)
        logger.info("document_created", document_id=str(doc.id), title=doc.title)
        return doc

    def get_by_id(self, doc_id: UUID, tenant_id: UUID) -> Document:
        """Get document by ID, scoped to tenant."""
        doc = (
            self.db.execute(
                select(Document)
                .join(KnowledgeBase)
                .where(Document.id == doc_id, KnowledgeBase.tenant_id == tenant_id)
            )
            .scalar_one_or_none()
        )
        if not doc:
            logger.warning("document_not_found", document_id=str(doc_id), tenant_id=str(tenant_id))
            raise DocumentNotFoundError(str(doc_id))
        return doc

    def list_by_knowledge_base(
        self, kb_id: UUID, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[List[Document], int]:
        """List documents in a knowledge base, scoped to tenant."""
        base_q = (
            select(Document)
            .join(KnowledgeBase)
            .where(Document.knowledge_base_id == kb_id, KnowledgeBase.tenant_id == tenant_id)
        )
        total = self.db.execute(select(func.count()).select_from(base_q.subquery())).scalar_one()
        docs = (
            self.db.execute(
                base_q.offset(skip).limit(limit).order_by(Document.created_at.desc())
            )
            .scalars()
            .all()
        )
        return list(docs), total

    def list_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[List[Document], int]:
        """List all documents for a tenant across all knowledge bases."""
        base_q = (
            select(Document)
            .join(KnowledgeBase)
            .where(KnowledgeBase.tenant_id == tenant_id)
        )
        total = self.db.execute(select(func.count()).select_from(base_q.subquery())).scalar_one()
        docs = (
            self.db.execute(
                base_q.offset(skip).limit(limit).order_by(Document.created_at.desc())
            )
            .scalars()
            .all()
        )
        return list(docs), total

    def delete(self, doc_id: UUID, tenant_id: UUID) -> bool:
        """Delete document by ID, scoped to tenant."""
        doc = self.get_by_id(doc_id, tenant_id)
        kb_id = doc.knowledge_base_id
        doc_title = doc.title

        vector_ids = [str(c.id) for c in doc.chunks if c.embedding_id]
        logger.info("document_delete", document_id=str(doc_id), title=doc_title, kb_id=str(kb_id), vector_count=len(vector_ids))

        self.db.delete(doc)
        self._update_kb_chunk_count(kb_id)
        self.db.commit()

        if vector_ids:
            for vid in vector_ids:
                if vid in _vector_store_service._embeddings:
                    del _vector_store_service._embeddings[vid]
        logger.info("document_deleted", document_id=str(doc_id), vectors_deleted=len(vector_ids))
        return True

    def update_status(self, doc_id: UUID, status: str) -> Document:
        """Update document status."""
        doc = self.db.get(Document, doc_id)
        if not doc:
            raise DocumentNotFoundError(str(doc_id))
        doc.status = status
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_chunk_count(self, doc_id: UUID, count: int) -> Document:
        """Update document chunk count."""
        doc = self.db.get(Document, doc_id)
        if not doc:
            raise DocumentNotFoundError(str(doc_id))
        doc.chunk_count = count
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document_preview(self, doc_id: UUID) -> dict:
        """Get document preview content by re-parsing the file."""
        doc = self.db.get(Document, doc_id)
        if not doc:
            raise DocumentNotFoundError(str(doc_id))
        file_path = Path(doc.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        from app.parsers import get_parser
        parser = get_parser(file_path)
        content = parser.parse(file_path)
        metadata = parser.get_metadata(file_path)

        return {
            "document_id": doc.id,
            "title": doc.title,
            "content": content,
            "file_type": doc.file_type,
            "metadata": metadata,
        }

    def _update_kb_chunk_count(self, kb_id: UUID) -> None:
        """Update knowledge base document and chunk counts."""
        kb = self.db.get(KnowledgeBase, kb_id)
        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id)

        doc_count = (
            self.db.execute(
                select(func.count()).select_from(Document).where(Document.knowledge_base_id == kb_id)
            )
            .scalar_one()
        )
        chunk_count = (
            self.db.execute(
                select(func.count()).select_from(Chunk).where(
                    Chunk.document_id.in_(
                        select(Document.id).where(Document.knowledge_base_id == kb_id)
                    )
                )
            )
            .scalar_one()
        )
        kb.document_count = doc_count
        kb.chunk_count = chunk_count
        self.db.flush()

