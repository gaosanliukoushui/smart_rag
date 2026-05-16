"""Session management service for persistent chat history storage."""

from typing import List, Optional
from datetime import datetime

from app.db.redis import redis_client, REDIS_AVAILABLE
from app.models.chat import ChatSession, Message


class SessionService:
    """Service for managing chat session persistence via Redis."""

    def __init__(self):
        self._memory_store: dict = {}
        self._use_redis = REDIS_AVAILABLE

    def _to_dict(self, session: ChatSession) -> dict:
        """Serialize a ChatSession to a dictionary."""
        return {
            "id": session.id,
            "knowledge_base_id": session.knowledge_base_id,
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
                for m in session.messages
            ],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    def _from_dict(self, data: dict) -> ChatSession:
        """Deserialize a dictionary to a ChatSession."""
        return ChatSession(
            id=data["id"],
            knowledge_base_id=data["knowledge_base_id"],
            messages=[
                Message(
                    role=m["role"],
                    content=m["content"],
                    created_at=datetime.fromisoformat(m["created_at"]) if isinstance(m["created_at"], str) else m["created_at"],
                )
                for m in data.get("messages", [])
            ],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"],
        )

    async def save_session(self, session: ChatSession) -> None:
        """Persist a chat session."""
        data = self._to_dict(session)
        if self._use_redis:
            await redis_client.set_session(session.id, data)
        self._memory_store[session.id] = session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieve a chat session by ID, falling back to memory."""
        if self._use_redis:
            data = await redis_client.get_session(session_id)
            if data:
                session = self._from_dict(data)
                self._memory_store[session_id] = session
                return session
        return self._memory_store.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session by ID."""
        if self._use_redis:
            await redis_client.delete_session(session_id)
        if session_id in self._memory_store:
            del self._memory_store[session_id]
            return True
        return False

    async def list_sessions(self, knowledge_base_id: Optional[str] = None) -> List[ChatSession]:
        """List all sessions, optionally filtered by knowledge base."""
        sessions = []

        if self._use_redis:
            keys = await redis_client.list_sessions("session:*")
            for key in keys:
                sid = key.replace("session:", "")
                data = await redis_client.get_session(sid)
                if data:
                    session = self._from_dict(data)
                    self._memory_store[sid] = session

        for session in self._memory_store.values():
            if knowledge_base_id is None or session.knowledge_base_id == knowledge_base_id:
                sessions.append(session)

        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def clear_history(self, session_id: str) -> bool:
        """Clear all messages from a session but keep it alive."""
        session = await self.get_session(session_id)
        if not session:
            return False
        session.messages.clear()
        session.updated_at = datetime.utcnow()
        await self.save_session(session)
        return True

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        if self._use_redis:
            data = await redis_client.get_session(session_id)
            if data:
                return True
        return session_id in self._memory_store


_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """Get or create the singleton SessionService instance."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
