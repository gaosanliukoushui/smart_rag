"""Document schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """Request schema for document upload."""

    knowledge_base_id: UUID
    title: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""

    document_id: UUID
    filename: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    """Response schema for document list."""

    documents: List["DocumentResponse"]
    total: int


class DocumentResponse(BaseModel):
    """Document response schema."""

    id: UUID
    title: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    knowledge_base_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ChunkResponse(BaseModel):
    """Chunk response schema."""

    id: UUID
    content: str
    chunk_index: int
    token_count: int
    metadata: dict


class ChunkDetailResponse(ChunkResponse):
    """Chunk detail with document context for citation backtracking."""

    document_id: UUID
    document_title: str
    knowledge_base_id: UUID


class ChunkListResponse(BaseModel):
    """Response schema for chunk list."""

    chunks: List[ChunkResponse]
    total: int


class DocumentPreviewResponse(BaseModel):
    """Response schema for document preview."""

    document_id: UUID
    title: str
    content: str
    truncated: bool
    total_chars: int
    file_type: str
    metadata: dict


DocumentUploadResponse.model_rebuild()
DocumentListResponse.model_rebuild()
