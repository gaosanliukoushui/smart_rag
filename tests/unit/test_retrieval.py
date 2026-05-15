"""Unit tests for retrieval service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.retrieval_service import RetrievalService


class TestRetrievalService:
    """Tests for RetrievalService."""

    @pytest.mark.asyncio
    async def test_retrieve_basic(self):
        """Test basic retrieval."""
        mock_embedding = AsyncMock()
        mock_embedding.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[
            ("text1", 0.9, {}),
            ("text2", 0.8, {}),
        ])

        service = RetrievalService(mock_embedding, mock_vector_store)
        results = await service.retrieve("test query", top_k=5)

        assert len(results) == 2
        assert results[0][0] == "text1"
        assert results[0][1] == 0.9

    @pytest.mark.asyncio
    async def test_retrieve_with_threshold(self):
        """Test retrieval with similarity threshold."""
        mock_embedding = AsyncMock()
        mock_embedding.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[
            ("high_score", 0.95, {}),
            ("low_score", 0.5, {}),
        ])

        service = RetrievalService(mock_embedding, mock_vector_store)
        results = await service.retrieve("test query", top_k=5, similarity_threshold=0.7)

        assert len(results) == 1
        assert results[0][0] == "high_score"
