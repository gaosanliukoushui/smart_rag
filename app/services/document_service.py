"""Document service for handling document operations."""

from pathlib import Path
from typing import List, Optional
import uuid
from datetime import datetime

from app.models.document import Document, DocumentCreate
from app.core.exceptions import DocumentNotFoundError


class DocumentService:
    """Service for document operations."""

    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self._documents: dict = {}

    async def create_document(self, doc_data: DocumentCreate) -> Document:
        """Create a new document record."""
        doc = Document(
            title=doc_data.title,
            file_path=doc_data.file_path,
            file_type=doc_data.file_type,
            file_size=doc_data.file_size,
            metadata=doc_data.metadata or {},
        )
        self._documents[doc.id] = doc
        return doc

    async def get_document(self, doc_id: str) -> Document:
        """Get document by ID."""
        if doc_id not in self._documents:
            raise DocumentNotFoundError(doc_id)
        return self._documents[doc_id]

    async def list_documents(self) -> List[Document]:
        """List all documents."""
        return list(self._documents.values())

    async def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    async def update_status(self, doc_id: str, status: str) -> Document:
        """Update document status."""
        doc = await self.get_document(doc_id)
        doc.status = status
        doc.updated_at = datetime.utcnow()
        return doc

    async def update_chunk_count(self, doc_id: str, count: int) -> Document:
        """Update document chunk count."""
        doc = await self.get_document(doc_id)
        doc.chunk_count = count
        doc.updated_at = datetime.utcnow()
        return doc
