"""Chat API endpoints."""

import json
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_active_user, get_current_tenant
from app.models import User, Tenant
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.chat_service import ChatService, _format_document_list_answer, _is_list_query, _list_kb_documents
from app.services.session_service import get_session_service
from app.middleware.rate_limit import limiter
from app.core.logging import get_logger
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    ChatMessage,
    ChatSessionListResponse,
    SessionSummary,
)

logger = get_logger(__name__)


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
        session = await _session_service.get_session_for_tenant(chat_request.session_id, str(tenant.id))
    else:
        session = None

    if not session:
        session = await _chat_service.create_session(chat_request.knowledge_base_id, str(tenant.id))
        await _session_service.save_session(session)

    answer, sources = await _chat_service.ask(
        question=chat_request.message,
        knowledge_base_id=chat_request.knowledge_base_id,
        session=session,
        top_k=5,
        stream=False,
        tenant_id=str(tenant.id),
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
                session = await _session_service.get_session_for_tenant(chat_request.session_id, str(tenant.id))
            else:
                session = None

            if not session:
                session = await _chat_service.create_session(chat_request.knowledge_base_id, str(tenant.id))
                await _session_service.save_session(session)

            yield {"event": "session", "data": session.id}

            if _is_list_query(chat_request.message):
                doc_list = await _list_kb_documents(chat_request.knowledge_base_id, tenant_id=str(tenant.id))
                answer = _format_document_list_answer(doc_list)
                session.add_message("user", chat_request.message)
                session.add_message("assistant", answer)
                await _session_service.save_session(session)
                yield {"event": "message", "data": answer}
                yield {"event": "sources", "data": []}
                yield {"event": "done", "data": ""}
                return

            token_gen, sources, session = await _chat_service.stream_ask(
                question=chat_request.message,
                knowledge_base_id=chat_request.knowledge_base_id,
                session=session,
                top_k=5,
                use_rewrite=True,
                tenant_id=str(tenant.id),
            )

            full_response = []
            async for token in token_gen:
                full_response.append(token)
                yield {"event": "message", "data": token if token.startswith("{") else token}

            if session:
                session.add_message("assistant", "".join(full_response))
                await _session_service.save_session(session)

            yield {"event": "sources", "data": sources}
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

    session = await _session_service.get_session_for_tenant(session_id, str(tenant.id))
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

    session = await _chat_service.create_session(knowledge_base_id, str(tenant.id))
    await _session_service.save_session(session)
    return {"session_id": session.id, "created_at": session.created_at.isoformat()}


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    request: Request,
    knowledge_base_id: Optional[str] = None,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """List all chat sessions for the current tenant."""
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

    sessions = await _session_service.list_sessions(knowledge_base_id=knowledge_base_id)
    tenant_sessions = [s for s in sessions if s.tenant_id == str(tenant.id)]
    return ChatSessionListResponse(
        sessions=[
            SessionSummary(
                session_id=s.id,
                knowledge_base_id=s.knowledge_base_id,
                message_count=len(s.messages),
                first_message=s.messages[0].content if s.messages else None,
                last_message=s.messages[-1].content if s.messages else None,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in tenant_sessions
        ]
    )
