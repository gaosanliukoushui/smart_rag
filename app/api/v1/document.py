"""Document management API endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List

router = APIRouter()


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document."""
    return {"message": "Document upload endpoint", "filename": file.filename}


@router.get("/documents")
async def list_documents():
    """List all documents."""
    return {"documents": []}


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get document by ID."""
    return {"document_id": document_id}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete document by ID."""
    return {"message": f"Document {document_id} deleted"}
