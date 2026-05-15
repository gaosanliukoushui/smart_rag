"""Chunk model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class Chunk(BaseModel):
    """Document chunk model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    content: str
    chunk_index: int
    token_count: int = 0
    embedding_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    """Schema for chunk response."""

    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict
