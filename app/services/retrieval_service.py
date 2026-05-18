"""Retrieval service for RAG retrieval operations."""

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
        logger = get_logger(__name__)
        logger.info(f"[RETRIEVE] kb_id={knowledge_base_id}, threshold={similarity_threshold}, total_vectors_in_store={len(self.vector_store_service._embeddings)}")
        query_embedding = await self.embedding_service.embed_query(query)
        logger.info(f"[RETRIEVE] query_emb dim={len(query_embedding)}, query='{query}'")

        results = await self.vector_store_service.search(
            query_embedding,
            top_k=top_k,
            threshold=similarity_threshold,
            knowledge_base_id=knowledge_base_id,
        )
        logger.info(f"[RETRIEVE] search returned {len(results)} results")
        for r in results:
            logger.info(f"[RETRIEVE]   score={r[1]:.4f}, meta={r[2]}")

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
