"""Document schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """Request schema for document upload."""

    knowledge_base_id: str
    title: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""

    document_id: str
    filename: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    """Response schema for document list."""

    documents: List["DocumentResponse"]
    total: int


class DocumentResponse(BaseModel):
    """Document response schema."""

    id: str
    title: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: datetime


class ChunkResponse(BaseModel):
    """Chunk response schema."""

    id: str
    content: str
    chunk_index: int
    metadata: dict


class ChunkListResponse(BaseModel):
    """Response schema for chunk list."""

    chunks: List[ChunkResponse]
    total: int


DocumentUploadResponse.model_rebuild()
DocumentListResponse.model_rebuild()
