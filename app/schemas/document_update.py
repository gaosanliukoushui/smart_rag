"""Document update schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUpdate(BaseModel):
    """Schema for updating a document's metadata."""

    description: Optional[str] = None
    metadata: Optional[dict] = None


class DocumentReparseResponse(BaseModel):
    """Response for document reparse operation."""

    document_id: UUID
    status: str  # "success", "unchanged", or "failed"
    old_chunk_count: int = Field(default=0)
    new_chunk_count: int = Field(default=0)
    new_version: int = Field(default=1)
    message: Optional[str] = None


class DocumentReloadRequest(BaseModel):
    """Request to reload knowledge base in vector store."""

    force: bool = False  # If True, delete all chunks and re-embed


class DocumentReloadResponse(BaseModel):
    """Response for knowledge base reload."""

    status: str
    documents_processed: int = 0
    total_chunks: int = 0
    message: Optional[str] = None


class DocumentVersionResponse(BaseModel):
    """Response for document version info."""

    document_id: UUID
    version: int
    file_hash: Optional[str]
    chunk_count: int
    is_deleted: bool
    updated_at: datetime
