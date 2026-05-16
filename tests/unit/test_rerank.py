"""Unit tests for rerank service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rerank_service import RerankService


class TestRerankService:
    """Tests for RerankService."""

    @pytest.fixture
    def rerank_service(self):
        """Create RerankService instance."""
        return RerankService(model_name="BAAI/bge-reranker-v2-m3")

    def test_init(self, rerank_service):
        """Test service initializes with correct defaults."""
        assert rerank_service.model_name == "BAAI/bge-reranker-v2-m3"
        assert rerank_service._model is None

    @pytest.mark.asyncio
    async def test_rerank_orders_by_score(self, rerank_service):
        """Test rerank returns documents sorted by relevance score."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.3, 0.6]
        rerank_service._model = mock_model

        docs = ["doc A", "doc B", "doc C"]
        results = await rerank_service.rerank("query", docs, top_k=3)

        assert len(results) == 3
        assert results[0][0] == "doc A"
        assert results[0][1] == 0.9
        assert results[1][0] == "doc C"
        assert results[2][0] == "doc B"

    @pytest.mark.asyncio
    async def test_rerank_respects_top_k(self, rerank_service):
        """Test rerank respects top_k limit."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5, 0.4, 0.3, 0.2, 0.1]
        rerank_service._model = mock_model

        docs = ["doc A", "doc B", "doc C", "doc D", "doc E"]
        results = await rerank_service.rerank("query", docs, top_k=2)

        assert len(results) == 2
        assert results[0][0] == "doc A"
        assert results[1][0] == "doc B"

    @pytest.mark.asyncio
    async def test_rerank_empty_list(self, rerank_service):
        """Test rerank with empty document list."""
        mock_model = MagicMock()
        rerank_service._model = mock_model

        results = await rerank_service.rerank("query", [], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_loads_model_on_first_call(self, rerank_service):
        """Test model is loaded lazily on first rerank call."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]
        rerank_service._model = None

        with patch("sentence_transformers.CrossEncoder", return_value=mock_model):
            results = await rerank_service.rerank("query", ["doc"], top_k=1)

        assert results[0][0] == "doc"

    @pytest.mark.asyncio
    async def test_rerank_with_metadata(self, rerank_service):
        """Test rerank_with_metadata preserves metadata."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.6, 0.3]
        rerank_service._model = mock_model

        results = [
            ("Python guide", 0.95, {"source": "vector", "doc_id": "1"}),
            ("Java guide", 0.85, {"source": "vector", "doc_id": "2"}),
            ("Ruby guide", 0.75, {"source": "vector", "doc_id": "3"}),
        ]
        reranked = await rerank_service.rerank_with_metadata("Python", results, top_k=2)

        assert len(reranked) == 2
        assert reranked[0][0] == "Python guide"
        assert reranked[0][2]["doc_id"] == "1"
        assert reranked[1][2]["doc_id"] == "2"

    @pytest.mark.asyncio
    async def test_rerank_with_metadata_handles_missing_doc(self, rerank_service):
        """Test rerank_with_metadata handles missing metadata gracefully."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.5]
        rerank_service._model = mock_model

        results = [
            ("doc A", 0.9, {"id": "1"}),
            ("doc B", 0.8, {"id": "2"}),
        ]
        reranked = await rerank_service.rerank_with_metadata("query", results, top_k=2)

        for _, _, meta in reranked:
            assert isinstance(meta, dict)

    @pytest.mark.asyncio
    async def test_rerank_raises_on_missing_dependency(self, rerank_service):
        """Test rerank raises ImportError when sentence-transformers is not installed."""
        rerank_service._model = None

        with patch("sentence_transformers.CrossEncoder", side_effect=ImportError):
            with pytest.raises(ImportError, match="sentence-transformers"):
                await rerank_service.rerank("query", ["doc"], top_k=1)
