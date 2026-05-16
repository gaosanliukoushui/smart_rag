"""Integration tests for API endpoints."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "SmartRAG" in response.json()["message"]


@pytest.mark.asyncio
async def test_document_list():
    """Test document list endpoint.

    Note: Requires a real database and authentication token to pass.
    This is a placeholder that verifies the route is registered.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/documents")

    assert response.status_code in (200, 401)


@pytest.mark.asyncio
async def test_knowledge_base_list():
    """Test knowledge base list endpoint.

    Note: Requires a real database and authentication token to pass.
    This is a placeholder that verifies the route is registered.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/knowledge-bases")

    assert response.status_code in (200, 401)
