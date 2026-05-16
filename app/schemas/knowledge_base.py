"""Knowledge base schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a knowledge base."""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a knowledge base."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    """Schema for knowledge base response."""

    id: UUID
    name: str
    description: Optional[str] = None
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseListResponse(BaseModel):
    """Schema for knowledge base list response."""

    knowledge_bases: List[KnowledgeBaseResponse]
    total: int


class KnowledgeBaseWithDocuments(KnowledgeBaseResponse):
    """Schema for knowledge base with documents."""

    documents: List["DocumentBrief"] = []


class DocumentBrief(BaseModel):
    """Brief document info for KB detail."""

    id: UUID
    title: str
    file_type: str
    status: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


KnowledgeBaseWithDocuments.model_rebuild()
