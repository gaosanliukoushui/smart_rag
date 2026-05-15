"""Chat API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    knowledge_base_id: str
    stream: bool = True


class ChatResponse(BaseModel):
    answer: str


@router.post("/chat")
async def chat(request: ChatRequest):
    """Send a chat message."""
    return ChatResponse(answer="Chat endpoint - to be implemented")


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    return {"session_id": session_id, "messages": []}
