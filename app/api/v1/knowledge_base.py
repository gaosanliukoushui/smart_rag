"""Knowledge base API endpoints."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_tenant_from_header, get_db
from app.models import User, Tenant
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
)
from app.schemas.document_update import DocumentReloadResponse
from app.services.knowledge_base_service import KnowledgeBaseService, KnowledgeBaseNotFoundError
from app.services.document_update_service import DocumentUpdateService
from app.middleware.rate_limit import limiter


router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


def _get_kb_service(db: Session) -> KnowledgeBaseService:
    return KnowledgeBaseService(db)


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    tenant: Annotated[Tenant, Depends(get_tenant_from_header)],
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Create a new knowledge base within a tenant."""
    service = _get_kb_service(db)
    kb = service.create(data, tenant.id)
    return KnowledgeBaseResponse.model_validate(kb)


@router.get("", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    tenant: Annotated[Tenant, Depends(get_tenant_from_header)],
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """List all knowledge bases for the current tenant."""
    service = _get_kb_service(db)
    kbs, total = service.list_by_tenant(tenant.id, skip=skip, limit=limit)
    return KnowledgeBaseListResponse(
        knowledge_bases=[KnowledgeBaseResponse.model_validate(kb) for kb in kbs],
        total=total,
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    tenant: Annotated[Tenant, Depends(get_tenant_from_header)],
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get a knowledge base by ID within the current tenant."""
    service = _get_kb_service(db)
    try:
        kb = service.get_by_id(kb_id, tenant.id)
        return KnowledgeBaseResponse.model_validate(kb)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge base not found: {kb_id}")


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    data: KnowledgeBaseUpdate,
    tenant: Annotated[Tenant, Depends(get_tenant_from_header)],
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Update a knowledge base within the current tenant."""
    service = _get_kb_service(db)
    try:
        kb = service.update(kb_id, tenant.id, data)
        return KnowledgeBaseResponse.model_validate(kb)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge base not found: {kb_id}")


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    tenant: Annotated[Tenant, Depends(get_tenant_from_header)],
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Delete a knowledge base within the current tenant."""
    service = _get_kb_service(db)
    try:
        service.delete(kb_id, tenant.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge base not found: {kb_id}")


_update_service = DocumentUpdateService()


@router.post("/{kb_id}/reload", response_model=DocumentReloadResponse)
@limiter.limit("5/minute")
async def reload_knowledge_base(
    request: Request,
    kb_id: uuid.UUID,
    force: bool = Query(False, description="Force reparse all documents even if unchanged"),
    tenant: Annotated[Tenant, Depends(get_tenant_from_header)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """
    Reload all documents in a knowledge base.

    Re-parses and re-embeds all documents. Useful after bulk document updates.
    """
    service = _get_kb_service(db)
    try:
        service.get_by_id(kb_id, tenant.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge base not found: {kb_id}")

    try:
        result = await _update_service.reload_knowledge_base(kb_id, force=force)
        return DocumentReloadResponse(
            status=result["status"],
            documents_processed=result["documents_processed"],
            total_chunks=result["total_chunks"],
            message=result.get("message"),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Reload failed: {e}")
