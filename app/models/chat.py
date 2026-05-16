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

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session."""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.utcnow()

    def trim_messages(self, max_count: int) -> None:
        """Trim messages to keep only the most recent `max_count` messages."""
        if len(self.messages) > max_count:
            self.messages = self.messages[-max_count:]
            self.updated_at = datetime.utcnow()

    def get_messages_summary(self) -> dict:
        """Return a summary of messages in the session."""
        user_msgs = [m for m in self.messages if m.role == "user"]
        assistant_msgs = [m for m in self.messages if m.role == "assistant"]
        total_chars = sum(len(m.content) for m in self.messages)
        return {
            "total": len(self.messages),
            "user": len(user_msgs),
            "assistant": len(assistant_msgs),
            "total_characters": total_chars,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    """Schema for creating a chat session."""

    knowledge_base_id: str


class ChatMessage(BaseModel):
    """Schema for a chat message."""

    role: str
    content: str
