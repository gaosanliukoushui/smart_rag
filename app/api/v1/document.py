"""Document management API endpoints."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
import aiofiles

from app.config import get_settings
from app.parsers import get_parser
from app.services.document_service import DocumentService
from app.services.chunk_service import ChunkService
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentResponse,
    ChunkListResponse,
    ChunkResponse,
    DocumentPreviewResponse,
)
from app.core.exceptions import DocumentNotFoundError


router = APIRouter()

_settings = get_settings()
_document_service = DocumentService(upload_dir=_settings.upload_dir)
_chunk_service = ChunkService(
    chunk_size=_settings.CHUNK_SIZE,
    overlap=_settings.CHUNK_OVERLAP,
)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    knowledge_base_id: Optional[str] = Query(None),
):
    """Upload and parse a document."""
    settings = get_settings()
    file_ext = Path(file.filename).suffix.lower()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    if file_ext not in [".pdf", ".md", ".markdown", ".docx", ".txt", ".text"]:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file_ext}",
        )

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = settings.upload_dir / unique_filename

    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        parser = get_parser(file_path)
        content = parser.parse(file_path)
        metadata = parser.get_metadata(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse document: {str(e)}",
        )

    title = metadata.get("title", Path(file.filename).stem)
    doc = await _document_service.create_document(
        type("CreateDoc", (), {
            "title": title,
            "file_path": str(file_path),
            "file_type": file_ext,
            "file_size": len(content),
            "metadata": metadata,
        })()
    )

    chunks = _chunk_service.create_chunks(doc.id, content)
    await _document_service.update_chunk_count(doc.id, len(chunks))
    await _document_service.update_status(doc.id, "parsed")

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=file.filename,
        status=doc.status,
        message=f"Successfully parsed into {len(chunks)} chunks",
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    knowledge_base_id: Optional[str] = Query(None),
):
    """List all documents."""
    documents = await _document_service.list_documents()
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                title=d.title,
                file_type=d.file_type,
                file_size=d.file_size,
                status=d.status,
                chunk_count=d.chunk_count,
                created_at=d.created_at,
            )
            for d in documents
        ],
        total=len(documents),
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Get document by ID."""
    try:
        doc = await _document_service.get_document(document_id)
        return DocumentResponse(
            id=doc.id,
            title=doc.title,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete document by ID."""
    try:
        doc = await _document_service.get_document(document_id)
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
        await _document_service.delete_document(document_id)
        return {"message": f"Document {document_id} deleted"}
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")


@router.get("/documents/{document_id}/preview", response_model=DocumentPreviewResponse)
async def preview_document(document_id: str, max_chars: int = Query(5000, ge=100, le=50000)):
    """
    Preview document content.

    Returns raw text content of the document, truncated to max_chars.
    """
    try:
        preview = await _document_service.get_document_preview(document_id)
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
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
