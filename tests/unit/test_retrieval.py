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
        ])

        service = RetrievalService(mock_embedding, mock_vector_store)
        results = await service.retrieve("test query", top_k=5, similarity_threshold=0.7)

        assert len(results) == 1
        assert results[0][0] == "high_score"

    @pytest.mark.asyncio
    async def test_retrieve_with_rerank_calls_reranker(self):
        """Test retrieve_with_rerank calls the rerank service."""
        mock_embedding = AsyncMock()
        mock_embedding.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[
            ("doc A", 0.9, {"id": "1"}),
            ("doc B", 0.8, {"id": "2"}),
            ("doc C", 0.7, {"id": "3"}),
        ])

        mock_rerank = MagicMock()
        mock_rerank.rerank_with_metadata = AsyncMock(return_value=[
            ("doc A", 0.95, {"id": "1"}),
            ("doc B", 0.75, {"id": "2"}),
        ])

        service = RetrievalService(mock_embedding, mock_vector_store, rerank_service=mock_rerank)
        results = await service.retrieve_with_rerank("query", top_k=5, final_k=2)

        mock_rerank.rerank_with_metadata.assert_called_once()
        assert len(results) == 2
        assert results[0][0] == "doc A"

    @pytest.mark.asyncio
    async def test_retrieve_with_rerank_fallback_no_reranker(self):
        """Test retrieve_with_rerank falls back to truncation when no reranker."""
        mock_embedding = AsyncMock()
        mock_embedding.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[
            ("doc A", 0.9, {}),
            ("doc B", 0.8, {}),
        ])

        service = RetrievalService(mock_embedding, mock_vector_store, rerank_service=None)
        results = await service.retrieve_with_rerank("query", top_k=5, final_k=1)

        assert len(results) == 1
        assert results[0][0] == "doc A"

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_knowledge_base(self):
        """Test retrieval does not cross knowledge-base/tenant boundaries."""
        from app.services.vector_store_service import VectorStoreService

        mock_embedding = AsyncMock()
        mock_embedding.embed_query = AsyncMock(return_value=[1.0, 0.0])

        vector_store = VectorStoreService()
        await vector_store.add_vectors(
            ["tenant A chunk", "tenant B chunk"],
            [[1.0, 0.0], [1.0, 0.0]],
            metadata=[
                {"knowledge_base_id": "kb-a", "document_id": "doc-a", "chunk_id": "chunk-a"},
                {"knowledge_base_id": "kb-b", "document_id": "doc-b", "chunk_id": "chunk-b"},
            ],
        )

        service = RetrievalService(mock_embedding, vector_store)
        results = await service.retrieve("same semantic query", top_k=5, knowledge_base_id="kb-a")

        assert len(results) == 1
        assert results[0][2]["document_id"] == "doc-a"
