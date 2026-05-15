"""Chat model."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class Message(BaseModel):
    """Chat message model."""

    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    """Chat session model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    knowledge_base_id: str
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    """Schema for creating a chat session."""

    knowledge_base_id: str


class ChatMessage(BaseModel):
    """Schema for a chat message."""

    role: str
    content: str
