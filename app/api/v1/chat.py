"""Chat API endpoints."""

import json
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_active_user, get_current_tenant
from app.models import User, Tenant
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.chat_service import ChatService
from app.services.session_service import get_session_service
from app.middleware.rate_limit import limiter
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    ChatMessage,
)


router = APIRouter(prefix="/chat", tags=["Chat"])

_llm_service = LLMService()
_retrieval_service = RetrievalService()
_chat_service = ChatService(
    retrieval_service=_retrieval_service,
    llm_service=_llm_service,
)
_session_service = get_session_service()


@router.post("", response_model=ChatMessageResponse)
@limiter.limit("60/minute")
async def chat(
    request: Request,
    chat_request: ChatMessageRequest,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Send a chat message and get a RAG-powered response."""
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

    if chat_request.session_id:
        session = await _session_service.get_session(chat_request.session_id)
    else:
        session = None

    if not session:
        session = await _chat_service.create_session(chat_request.knowledge_base_id)
        await _session_service.save_session(session)

    answer, sources = await _chat_service.ask(
        question=chat_request.message,
        knowledge_base_id=chat_request.knowledge_base_id,
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


@router.post("/stream")
@limiter.limit("60/minute")
async def chat_stream(
    request: Request,
    chat_request: ChatMessageRequest,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """SSE stream endpoint for chat responses."""
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

    async def event_generator():
        try:
            if chat_request.session_id:
                session = await _session_service.get_session(chat_request.session_id)
            else:
                session = None

            if not session:
                session = await _chat_service.create_session(chat_request.knowledge_base_id)
                await _session_service.save_session(session)

            yield {"event": "session", "data": session.id}

            token_gen, sources, session = await _chat_service.stream_ask(
                question=chat_request.message,
                knowledge_base_id=chat_request.knowledge_base_id,
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
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}
            yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get chat history for a session."""
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

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


@router.post("/session")
@limiter.limit("60/minute")
async def create_session(
    request: Request,
    knowledge_base_id: str,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Create a new chat session."""
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

    session = await _chat_service.create_session(knowledge_base_id)
    await _session_service.save_session(session)
    return {"session_id": session.id, "created_at": session.created_at.isoformat()}
