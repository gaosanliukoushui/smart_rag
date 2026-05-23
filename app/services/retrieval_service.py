"""Retrieval service for RAG retrieval operations."""

import asyncio
import time
from typing import List, Tuple, Optional

from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService


class RetrievalService:
    """Service for retrieval operations in RAG."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store_service: Optional[VectorStoreService] = None,
        rerank_service: Optional = None,
    ):
        self.embedding_service = embedding_service
        self.vector_store_service = vector_store_service
        self.rerank_service = rerank_service
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazily initialize services on first use."""
        if self._initialized:
            return
        from app.services.embedding_service import EmbeddingService
        from app.services.vector_store_service import get_vector_store
        self.embedding_service = self.embedding_service or EmbeddingService()
        self.vector_store_service = self.vector_store_service or get_vector_store()
        self._initialized = True

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        knowledge_base_id: Optional[str] = None,
    ) -> List[Tuple[str, float, dict]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: The search query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            knowledge_base_id: Optional KB ID to filter results

        Returns:
            List of (text, score, metadata) tuples
        """
        await self._ensure_initialized()
        from app.core.logging import get_logger
        from app.api.v1.metrics import collector
        logger = get_logger(__name__)

        if getattr(self.vector_store_service, "_embeddings", None) == {}:
            logger.warning("[RETRIEVE] No vectors in store, skipping retrieval")
            return []

        try:
            embed_start = time.perf_counter()
            query_embedding = await asyncio.wait_for(
                self.embedding_service.embed_query(query), timeout=30.0
            )
            collector.record_rag_latency("embedding", (time.perf_counter() - embed_start) * 1000)
        except asyncio.TimeoutError:
            logger.error("[RETRIEVE] Embedding timeout for query: %s", query)
            return []
        except Exception as e:
            logger.error("[RETRIEVE] Embedding failed: %s", e)
            return []

        try:
            retrieval_start = time.perf_counter()
            results = await self.vector_store_service.search(
                query_embedding,
                top_k=top_k,
                threshold=similarity_threshold,
                knowledge_base_id=knowledge_base_id,
            )
            collector.record_rag_latency("retrieval", (time.perf_counter() - retrieval_start) * 1000)
            collector.record_retrieval_result([float(score) for _, score, _ in results])
        except Exception as e:
            logger.error("[RETRIEVE] Search failed: %s", e)
            return []

        logger.info("[RETRIEVE] kb_id=%s, threshold=%s, results=%d", knowledge_base_id, similarity_threshold, len(results))
        return results

    async def retrieve_with_rerank(
        self,
        query: str,
        top_k: int = 10,
        final_k: int = 5,
        similarity_threshold: float = 0.5,
        knowledge_base_id: Optional[str] = None,
    ) -> List[Tuple[str, float, dict]]:
        """Retrieve with reranking for higher quality results."""
        await self._ensure_initialized()
        candidates = await self.retrieve(
            query, top_k=top_k, similarity_threshold=similarity_threshold,
            knowledge_base_id=knowledge_base_id,
        )
        if self.rerank_service is None:
            return candidates[:final_k]
        return await self.rerank_service.rerank_with_metadata(
            query, candidates, top_k=final_k
        )
