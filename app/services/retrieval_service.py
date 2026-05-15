"""Retrieval service for RAG retrieval operations."""

from typing import List, Tuple, Optional

from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService


class RetrievalService:
    """Service for retrieval operations in RAG."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store_service: VectorStoreService,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store_service

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Tuple[str, float, dict]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: The search query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score

        Returns:
            List of (text, score, metadata) tuples
        """
        query_embedding = await self.embedding_service.embed_query(query)

        results = await self.vector_store.search(
            query_embedding,
            top_k=top_k,
            threshold=similarity_threshold,
        )

        return results

    async def retrieve_with_rerank(
        self,
        query: str,
        top_k: int = 10,
        final_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> List[Tuple[str, float, dict]]:
        """Retrieve with reranking (placeholder for rerank integration)."""
        return await self.retrieve(query, top_k=final_k, similarity_threshold=similarity_threshold)
