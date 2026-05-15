"""Document model."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import uuid4


class Document(BaseModel):
    """Document model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    file_path: str
    file_type: str
    file_size: int
    status: str = "pending"
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    """Schema for creating a document."""

    title: str
    file_path: str
    file_type: str
    file_size: int
    metadata: Optional[dict] = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: str
    title: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: datetime
