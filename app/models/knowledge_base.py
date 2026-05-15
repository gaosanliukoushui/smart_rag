"""Knowledge base model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class KnowledgeBase(BaseModel):
    """Knowledge base model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = ""
    vector_store_id: Optional[str] = None
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a knowledge base."""

    name: str
    description: Optional[str] = ""


class KnowledgeBaseResponse(BaseModel):
    """Schema for knowledge base response."""

    id: str
    name: str
    description: Optional[str]
    document_count: int
    chunk_count: int
    created_at: datetime
