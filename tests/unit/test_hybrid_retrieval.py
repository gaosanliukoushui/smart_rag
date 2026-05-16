"""Unit tests for hybrid retrieval."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.bm25_retriever import BM25Retriever
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.retrieval_service import RetrievalService


class TestBM25Retriever:
    """Tests for BM25Retriever."""

    def test_build_index_and_search(self):
        """Test building index and basic search."""
        corpus = [
            "Python is a high-level programming language",
            "Java is a strongly typed language",
            "Machine learning uses Python and data",
            "Deep learning is a subset of machine learning",
        ]
        retriever = BM25Retriever()
        retriever.build_index(corpus)

        results = retriever.search("Python programming", top_k=2)

        assert len(results) <= 2
        assert all(isinstance(r[0], str) for r in results)
        assert all(isinstance(r[1], float) for r in results)
        assert all(isinstance(r[2], int) for r in results)

    def test_search_with_scores(self):
        """Test search_with_scores returns correct format."""
        corpus = ["apple fruit", "banana yellow", "cherry red"]
        retriever = BM25Retriever()
        retriever.build_index(corpus)

        results = retriever.search_with_scores("fruit", top_k=2)

        assert len(results) <= 2
        for text, score, meta in results:
            assert isinstance(text, str)
            assert isinstance(score, float)
            assert isinstance(meta, dict)
            assert "doc_index" in meta

    def test_empty_corpus(self):
        """Test search on empty corpus returns empty list."""
        retriever = BM25Retriever()
        retriever.build_index([])

        results = retriever.search("query", top_k=5)
        assert results == []

    def test_search_top_k_limit(self):
        """Test that top_k limits results correctly."""
        corpus = [f"Document {i}" for i in range(20)]
        retriever = BM25Retriever()
        retriever.build_index(corpus)

        results = retriever.search("Document", top_k=3)
        assert len(results) == 3


class TestHybridRetrievalService:
    """Tests for HybridRetrievalService."""

    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector retrieval service."""
        service = MagicMock(spec=RetrievalService)
        service.retrieve = AsyncMock(return_value=[
            ("vector doc A", 0.95, {"source": "vector"}),
            ("vector doc B", 0.85, {"source": "vector"}),
            ("shared doc", 0.80, {"source": "vector"}),
        ])
        return service

    @pytest.fixture
    def mock_bm25_retriever(self):
        """Create mock BM25 retriever."""
        retriever = MagicMock(spec=BM25Retriever)
        retriever.search_with_scores = MagicMock(return_value=[
            ("bm25 doc X", 10.5, {"source": "bm25"}),
            ("shared doc", 8.2, {"source": "bm25"}),
            ("bm25 doc Y", 5.1, {"source": "bm25"}),
        ])
        return retriever

    @pytest.fixture
    def hybrid_service(self, mock_vector_service, mock_bm25_retriever):
        """Create HybridRetrievalService with mocks."""
        return HybridRetrievalService(
            retrieval_service=mock_vector_service,
            bm25_retriever=mock_bm25_retriever,
            rrf_k=60,
            vector_weight=0.5,
            bm25_weight=0.5,
        )

    @pytest.mark.asyncio
    async def test_retrieve_rrf_fusion(self, hybrid_service):
        """Test RRF fusion combines results from both retrievers."""
        results = await hybrid_service.retrieve("query", top_k=5, fusion_method="rrf")

        assert len(results) > 0
        shared_docs = [r for r in results if "shared" in r[0]]
        assert len(shared_docs) == 1

    @pytest.mark.asyncio
    async def test_retrieve_score_fusion(self, hybrid_service):
        """Test score fusion combines results correctly."""
        results = await hybrid_service.retrieve("query", top_k=5, fusion_method="score")

        assert len(results) > 0
        scores = [score for _, score, _ in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_retrieve_respects_top_k(self, hybrid_service):
        """Test that top_k parameter limits results."""
        results = await hybrid_service.retrieve("query", top_k=2, fusion_method="rrf")

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_retrieve_with_rerank(self, hybrid_service):
        """Test retrieve with reranking calls both retrievers."""
        results = await hybrid_service.retrieve_with_rerank(
            "query", top_k=5, final_k=2, fusion_method="rrf"
        )

        assert len(results) <= 2

    def test_rrf_fusion_weights(self, hybrid_service):
        """Test RRF fusion with different weights."""
        vector_results = [
            ("doc A", 0.9, {"source": "vector"}),
            ("doc B", 0.8, {"source": "vector"}),
        ]
        bm25_results = [
            ("doc C", 5.0, {"source": "bm25"}),
            ("doc D", 4.0, {"source": "bm25"}),
        ]

        fused_equal = hybrid_service._rrf_fusion(
            [vector_results, bm25_results],
            weights=[0.5, 0.5],
        )
        fused_vector_heavy = hybrid_service._rrf_fusion(
            [vector_results, bm25_results],
            weights=[0.9, 0.1],
        )

        assert len(fused_equal) == 4
        assert len(fused_vector_heavy) == 4

    def test_rrf_fusion_empty_input(self, hybrid_service):
        """Test RRF fusion with empty input returns empty list."""
        result = hybrid_service._rrf_fusion([])
        assert result == []

    def test_normalize_scores(self, hybrid_service):
        """Test min-max score normalization."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = hybrid_service._normalize_scores(scores)

        assert normalized[0] == 0.0
        assert normalized[-1] == 1.0

    def test_normalize_scores_equal_values(self, hybrid_service):
        """Test normalization when all scores are equal."""
        scores = [5.0, 5.0, 5.0]
        normalized = hybrid_service._normalize_scores(scores)

        assert all(s == 1.0 for s in normalized)

    def test_normalize_scores_empty(self, hybrid_service):
        """Test normalization with empty list."""
        normalized = hybrid_service._normalize_scores([])
        assert normalized == []


class TestHybridRetrievalWithRerank:
    """Tests for HybridRetrievalService with rerank integration."""

    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector retrieval service."""
        service = MagicMock(spec=RetrievalService)
        service.retrieve = AsyncMock(return_value=[
            ("Python tutorial", 0.95, {"source": "vector", "doc_id": "1"}),
            ("Java tutorial", 0.85, {"source": "vector", "doc_id": "2"}),
            ("ML overview", 0.80, {"source": "vector", "doc_id": "3"}),
        ])
        return service

    @pytest.fixture
    def mock_bm25_retriever(self):
        """Create mock BM25 retriever."""
        retriever = MagicMock(spec=BM25Retriever)
        retriever.search_with_scores = MagicMock(return_value=[
            ("Python tutorial", 10.5, {"source": "bm25", "doc_id": "1"}),
            ("Java tutorial", 8.2, {"source": "bm25", "doc_id": "2"}),
            ("ML overview", 5.1, {"source": "bm25", "doc_id": "3"}),
        ])
        return retriever

    @pytest.fixture
    def mock_rerank_service(self):
        """Create mock rerank service."""
        from app.services.rerank_service import RerankService
        service = MagicMock(spec=RerankService)
        service.rerank_with_metadata = AsyncMock(return_value=[
            ("Python tutorial", 0.98, {"source": "vector", "doc_id": "1"}),
            ("ML overview", 0.75, {"source": "vector", "doc_id": "3"}),
        ])
        return service

    @pytest.fixture
    def hybrid_service_with_rerank(self, mock_vector_service, mock_bm25_retriever, mock_rerank_service):
        """Create HybridRetrievalService with rerank."""
        return HybridRetrievalService(
            retrieval_service=mock_vector_service,
            bm25_retriever=mock_bm25_retriever,
            rerank_service=mock_rerank_service,
            rrf_k=60,
            vector_weight=0.5,
            bm25_weight=0.5,
        )

    @pytest.mark.asyncio
    async def test_retrieve_with_rerank_calls_reranker(self, hybrid_service_with_rerank, mock_rerank_service):
        """Test that retrieve_with_rerank calls the rerank service."""
        results = await hybrid_service_with_rerank.retrieve_with_rerank(
            "Python programming", top_k=5, final_k=2
        )

        mock_rerank_service.rerank_with_metadata.assert_called_once()
        call_args = mock_rerank_service.rerank_with_metadata.call_args
        assert call_args[0][0] == "Python programming"
        assert len(call_args[0][1]) == 3
        assert call_args[1]["top_k"] == 2
        assert len(results) == 2
        assert results[0][0] == "Python tutorial"

    @pytest.mark.asyncio
    async def test_retrieve_with_rerank_fallback_no_reranker(self, mock_vector_service, mock_bm25_retriever):
        """Test retrieve_with_rerank falls back to truncation when no reranker."""
        hybrid = HybridRetrievalService(
            retrieval_service=mock_vector_service,
            bm25_retriever=mock_bm25_retriever,
            rerank_service=None,
        )
        results = await hybrid.retrieve_with_rerank(
            "Python programming", top_k=5, final_k=2
        )

        assert len(results) == 2
        assert all(isinstance(r[0], str) for r in results)

    @pytest.mark.asyncio
    async def test_retrieve_with_rerank_preserves_metadata(self, hybrid_service_with_rerank):
        """Test reranked results preserve metadata from initial retrieval."""
        results = await hybrid_service_with_rerank.retrieve_with_rerank(
            "Python", top_k=5, final_k=2
        )

        for text, score, meta in results:
            assert isinstance(meta, dict)
            assert "doc_id" in meta
