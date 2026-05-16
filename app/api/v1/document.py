"""Document management API endpoints."""

import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_tenant, get_db
from app.models import User, Tenant
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentPreviewResponse,
)
from app.schemas.document_update import (
    DocumentReparseResponse,
    DocumentReloadRequest,
    DocumentReloadResponse,
    DocumentVersionResponse,
)
from app.services.document_service import DocumentService, DocumentCreateData
from app.services.chunk_service import ChunkService
from app.services.knowledge_base_service import KnowledgeBaseService, KnowledgeBaseNotFoundError
from app.services.document_update_service import DocumentUpdateService
from app.config import get_settings
from app.core.exceptions import DocumentNotFoundError
from app.middleware.rate_limit import limiter


router = APIRouter(prefix="/documents", tags=["documents"])


def _get_doc_service(db: Session) -> DocumentService:
    return DocumentService(db)


def _get_kb_service(db: Session) -> KnowledgeBaseService:
    return KnowledgeBaseService(db)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    knowledge_base_id: uuid.UUID = Query(..., description="Knowledge base ID to upload to"),
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Upload and parse a document into a knowledge base."""
    settings = get_settings()
    file_ext = Path(file.filename or "").suffix.lower()

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename cannot be empty")

    if file_ext not in [".pdf", ".md", ".markdown", ".docx", ".txt", ".text"]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file_ext}",
        )

    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

    kb_service = _get_kb_service(db)
    try:
        kb = kb_service.get_by_id(knowledge_base_id, tenant.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base not found: {knowledge_base_id}",
        )

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = settings.upload_dir / unique_filename

    try:
        content = await file.read()
        file_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {e}")

    try:
        from app.parsers import get_parser
        parser = get_parser(file_path)
        text = parser.parse(file_path)
        metadata = parser.get_metadata(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse document: {e}",
        )

    title = metadata.get("title", Path(file.filename).stem)
    doc_data = DocumentCreateData(
        title=title,
        file_path=str(file_path),
        file_type=file_ext,
        file_size=len(content),
        knowledge_base_id=knowledge_base_id,
        metadata=metadata,
    )
    doc_service = _get_doc_service(db)
    doc = doc_service.create(doc_data)

    chunk_service = ChunkService(chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)
    chunks = chunk_service.create_chunks(doc.id, text)
    for chunk in chunks:
        db.add(chunk)
    doc_service.update_chunk_count(doc.id, len(chunks))
    doc_service.update_status(doc.id, "parsed")
    db.commit()

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=file.filename,
        status=doc.status,
        message=f"Successfully parsed into {len(chunks)} chunks",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    knowledge_base_id: Optional[uuid.UUID] = Query(None, description="Filter by knowledge base ID"),
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """List documents, optionally filtered by knowledge base, scoped to current tenant."""
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})
    doc_service = _get_doc_service(db)
    if knowledge_base_id:
        docs, total = doc_service.list_by_knowledge_base(knowledge_base_id, tenant.id, skip, limit)
    else:
        docs, total = doc_service.list_by_tenant(tenant.id, skip, limit)
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                title=d.title,
                file_type=d.file_type,
                file_size=d.file_size,
                status=d.status,
                chunk_count=d.chunk_count,
                knowledge_base_id=d.knowledge_base_id,
                created_at=d.created_at,
            )
            for d in docs
        ],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get document by ID within current tenant."""
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})
    doc_service = _get_doc_service(db)
    try:
        doc = doc_service.get_by_id(document_id, tenant.id)
        return DocumentResponse(
            id=doc.id,
            title=doc.title,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            chunk_count=doc.chunk_count,
            knowledge_base_id=doc.knowledge_base_id,
            created_at=doc.created_at,
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document not found: {document_id}")


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Delete document by ID within current tenant."""
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})
    doc_service = _get_doc_service(db)
    try:
        doc = doc_service.get_by_id(document_id, tenant.id)
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
        doc_service.delete(document_id, tenant.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document not found: {document_id}")


@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
async def preview_document(
    document_id: uuid.UUID,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    max_chars: int = Query(5000, ge=100, le=50000),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Preview document content, scoped to current tenant."""
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})
    doc_service = _get_doc_service(db)
    try:
        doc_service.get_by_id(document_id, tenant.id)
        preview = doc_service.get_document_preview(document_id)
        content = preview["content"]
        truncated = len(content) > max_chars
        return DocumentPreviewResponse(
            document_id=document_id,
            title=preview["title"],
            content=content[:max_chars],
            truncated=truncated,
            total_chars=len(content),
            file_type=preview["file_type"],
            metadata=preview["metadata"],
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document not found: {document_id}")
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


_update_service = DocumentUpdateService()


@router.post("/{document_id}/reparse", response_model=DocumentReparseResponse)
@limiter.limit("10/minute")
async def reparse_document(
    request: Request,
    document_id: uuid.UUID,
    force: bool = Query(False, description="Force reparse even if file unchanged"),
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """
    Reparse a document if the file has changed.

    Automatically detects changes via SHA-256 file hash comparison.
    Re-embeds chunks into the vector store after re-parsing.
    """
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

    doc_service = _get_doc_service(db)
    try:
        doc_service.get_by_id(document_id, tenant.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document not found: {document_id}")

    try:
        result = await _update_service.reparse_document(document_id, force=force)
        return DocumentReparseResponse(
            document_id=document_id,
            status=result["status"],
            old_chunk_count=result["old_chunk_count"],
            new_chunk_count=result["new_chunk_count"],
            new_version=result["new_version"],
            message=result.get("message"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Reparse failed: {e}")


@router.get("/{document_id}/version", response_model=DocumentVersionResponse)
async def get_document_version(
    document_id: uuid.UUID,
    tenant: Annotated[Optional[Tenant], Depends(get_current_tenant)] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get version info for a document."""
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found in token", headers={"WWW-Authenticate": "Bearer"})

    doc_service = _get_doc_service(db)
    try:
        doc_service.get_by_id(document_id, tenant.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document not found: {document_id}")

    try:
        info = _update_service.get_version_info(document_id)
        return DocumentVersionResponse(**info)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
