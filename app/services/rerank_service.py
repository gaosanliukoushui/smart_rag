"""Rerank service for result reranking."""

from typing import List, Tuple, Optional


class RerankService:
    """Service for reranking retrieval results."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None

    async def load_model(self):
        """Load the reranker model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except ImportError:
                raise ImportError("Please install sentence-transformers for reranking")

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Rerank documents based on query relevance."""
        await self.load_model()

        pairs = [[query, doc] for doc in documents]
        scores = self._model.predict(pairs)

        ranked = sorted(
            zip(documents, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        return [(doc, float(score)) for doc, score in ranked[:top_k]]

    async def rerank_with_metadata(
        self,
        query: str,
        results: List[Tuple[str, float, dict]],
        top_k: int = 5,
    ) -> List[Tuple[str, float, dict]]:
        """Rerank results that include metadata."""
        documents = [r[0] for r in results]
        reranked = await self.rerank(query, documents, top_k)

        doc_to_meta = {r[0]: r[2] for r in results}
        return [(doc, score, doc_to_meta.get(doc, {})) for doc, score in reranked]
