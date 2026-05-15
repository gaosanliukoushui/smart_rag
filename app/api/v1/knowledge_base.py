"""Knowledge base API endpoints."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/knowledge-bases")
async def create_knowledge_base(name: str, description: str = ""):
    """Create a new knowledge base."""
    return {"name": name, "description": description}


@router.get("/knowledge-bases")
async def list_knowledge_bases():
    """List all knowledge bases."""
    return {"knowledge_bases": []}


@router.get("/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """Get knowledge base by ID."""
    return {"kb_id": kb_id}


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """Delete knowledge base by ID."""
    return {"message": f"Knowledge base {kb_id} deleted"}
