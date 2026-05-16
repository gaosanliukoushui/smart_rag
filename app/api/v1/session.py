"""Session management API endpoints."""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query

from app.schemas.chat import ChatSessionResponse
from app.services.session_service import get_session_service


router = APIRouter()


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    knowledge_base_id: Optional[str] = Query(None, description="Filter sessions by knowledge base"),
):
    """List all chat sessions, optionally filtered by knowledge base."""
    service = get_session_service()
    sessions = await service.list_sessions(knowledge_base_id=knowledge_base_id)
    return [
        ChatSessionResponse(
            session_id=s.id,
            knowledge_base_id=s.knowledge_base_id,
            message_count=len(s.messages),
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session and its history."""
    service = get_session_service()
    deleted = await service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {"message": f"Session {session_id} deleted", "session_id": session_id}


@router.delete("/chat/sessions/{session_id}/history")
async def clear_session_history(session_id: str):
    """Clear all messages from a session but keep the session."""
    service = get_session_service()
    cleared = await service.clear_history(session_id)
    if not cleared:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {"message": f"History cleared for session {session_id}", "session_id": session_id}
