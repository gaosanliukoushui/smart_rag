"""Chat schemas."""

from typing import List, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessageRequest(BaseModel):
    """Request schema for chat message."""

    knowledge_base_id: str
    message: str
    session_id: Optional[str] = None
    stream: bool = True


class ChatMessageResponse(BaseModel):
    """Response schema for chat message."""

    session_id: str
    answer: str
    sources: List[dict] = Field(default_factory=list)
    tokens_used: Optional[int] = None


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""

    session_id: str
    messages: List["ChatMessage"]
    created_at: datetime


class ChatMessage(BaseModel):
    """Chat message schema."""

    role: str
    content: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    """Chat session response schema."""

    session_id: str
    knowledge_base_id: str
    message_count: int
    created_at: datetime


ChatHistoryResponse.model_rebuild()
