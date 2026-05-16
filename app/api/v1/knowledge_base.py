"""Knowledge base API endpoints."""

import uuid
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.knowledge_base import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseResponse


router = APIRouter()

_kb_store: dict[str, KnowledgeBase] = {}


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(payload: KnowledgeBaseCreate):
    """Create a new knowledge base."""
    kb = KnowledgeBase(name=payload.name, description=payload.description or "")
    _kb_store[kb.id] = kb
    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=kb.document_count,
        chunk_count=kb.chunk_count,
        created_at=kb.created_at,
    )


@router.get("/knowledge-bases")
async def list_knowledge_bases() -> dict:
    """List all knowledge bases."""
    return {
        "knowledge_bases": [
            KnowledgeBaseResponse(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                document_count=kb.document_count,
                chunk_count=kb.chunk_count,
                created_at=kb.created_at,
            )
            for kb in _kb_store.values()
        ],
        "total": len(_kb_store),
    }


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str):
    """Get knowledge base by ID."""
    kb = _kb_store.get(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail=f"Knowledge base not found: {kb_id}")
    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=kb.document_count,
        chunk_count=kb.chunk_count,
        created_at=kb.created_at,
    )


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """Delete knowledge base by ID."""
    if kb_id not in _kb_store:
        raise HTTPException(status_code=404, detail=f"Knowledge base not found: {kb_id}")
    del _kb_store[kb_id]
    return {"message": f"Knowledge base {kb_id} deleted"}
