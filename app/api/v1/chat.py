"""Chat API endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.chat_service import ChatService
from app.services.session_service import get_session_service
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    ChatMessage,
)


router = APIRouter()

_settings = get_settings()
_llm_service = LLMService()
_retrieval_service = RetrievalService()
_chat_service = ChatService(
    retrieval_service=_retrieval_service,
    llm_service=_llm_service,
)
_session_service = get_session_service()


@router.post("/chat", response_model=ChatMessageResponse)
    async def chat(request: ChatMessageRequest):
    """Send a chat message and get a RAG-powered response."""
    if request.session_id:
        session = await _session_service.get_session(request.session_id)
    else:
        session = None

    if not session:
        session = await _chat_service.create_session(request.knowledge_base_id)
        await _session_service.save_session(session)

    answer, sources = await _chat_service.ask(
        question=request.message,
        knowledge_base_id=request.knowledge_base_id,
        session=session,
        top_k=5,
        stream=False,
    )

    await _session_service.save_session(session)
    return ChatMessageResponse(
        session_id=session.id,
        answer=answer,
        sources=sources,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatMessageRequest):
    """SSE stream endpoint for chat responses."""

    async def event_generator():

        if request.session_id:
            session = await _session_service.get_session(request.session_id)
        else:
            session = None

        if not session:
            session = await _chat_service.create_session(request.knowledge_base_id)
            await _session_service.save_session(session)

        session_id = session.id
        yield {"event": "session", "data": session_id}

        token_gen, sources, session = await _chat_service.stream_ask(
            question=request.message,
            knowledge_base_id=request.knowledge_base_id,
            session=session,
            top_k=5,
            use_rewrite=True,
        )

        full_response = []
        async for token in token_gen:
            full_response.append(token)
            yield {"event": "message", "data": token}

        if session:
            session.add_message("assistant", "".join(full_response))
            await _session_service.save_session(session)

        yield {"event": "sources", "data": json.dumps(sources, ensure_ascii=False)}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    session = await _session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return ChatHistoryResponse(
        session_id=session.id,
        messages=[
            ChatMessage(role=m.role, content=m.content, created_at=m.created_at)
            for m in session.messages
        ],
        created_at=session.created_at,
    )


@router.post("/chat/session")
async def create_session(knowledge_base_id: str):
    """Create a new chat session."""
    session = await _chat_service.create_session(knowledge_base_id)
    await _session_service.save_session(session)
    return {"session_id": session.id, "created_at": session.created_at.isoformat()}
