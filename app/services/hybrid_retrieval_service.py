"""Hybrid retrieval service combining vector and BM25 search with RRF fusion."""

from typing import List, Tuple, Optional

from app.services.retrieval_service import RetrievalService
from app.services.bm25_retriever import BM25Retriever
from app.services.rerank_service import RerankService


class HybridRetrievalService:
    """Hybrid retrieval combining semantic (vector) and keyword (BM25) search."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        bm25_retriever: BM25Retriever,
        rerank_service: Optional[RerankService] = None,
        rrf_k: int = 60,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
    ):
        """
        Initialize hybrid retrieval service.

        Args:
            retrieval_service: Vector retrieval service.
            bm25_retriever: BM25 retriever instance.
            rerank_service: Optional reranker for post-retrieval reranking.
            rrf_k: RRF constant (default 60), higher = more weight to lower-ranked results.
            vector_weight: Weight for vector search scores in fusion (0-1).
            bm25_weight: Weight for BM25 scores in fusion (0-1).
        """
        self.retrieval_service = retrieval_service
        self.bm25_retriever = bm25_retriever
        self.rerank_service = rerank_service
        self.rrf_k = rrf_k
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Min-max normalize a list of scores to [0, 1].

        Returns same list if all scores are identical or list is empty.
        """
        if not scores:
            return []
        min_s, max_s = min(scores), max(scores)
        if max_s == min_s:
            return [1.0] * len(scores)
        return [(s - min_s) / (max_s - min_s) for s in scores]

    def _rrf_fusion(
        self,
        ranked_lists: List[List[Tuple[str, float, dict]]],
        weights: Optional[List[float]] = None,
    ) -> List[Tuple[str, float, dict]]:
        """
        Reciprocal Rank Fusion (RRF) to combine ranked results from multiple retrievers.

        Formula: RRF(d) = sum(weight_i / (k + rank_i(d))) for each retriever i

        Args:
            ranked_lists: List of ranked result lists from different retrievers.
            weights: Optional weights for each retriever's contribution.

        Returns:
            Combined ranked list of (text, score, merged_metadata) tuples.
        """
        if not ranked_lists:
            return []

        if weights is None:
            weights = [1.0] * len(ranked_lists)

        scores: dict[str, float] = {}
        metadata_map: dict[str, dict] = {}

        for retriever_idx, results in enumerate(ranked_lists):
            weight = weights[retriever_idx]
            for rank, (text, score, meta) in enumerate(results, start=1):
                rrf_score = weight / (self.rrf_k + rank)
                if text in scores:
                    scores[text] += rrf_score
                    metadata_map[text].update(meta)
                else:
                    scores[text] = rrf_score
                    metadata_map[text] = dict(meta)

        fused = [
            (text, final_score, metadata_map[text])
            for text, final_score in scores.items()
        ]
        fused.sort(key=lambda x: x[1], reverse=True)
        return fused

    def _score_fusion(
        self,
        ranked_lists: List[List[Tuple[str, float, dict]]],
        weights: Optional[List[float]] = None,
    ) -> List[Tuple[str, float, dict]]:
        """
        Weighted score fusion using normalized scores.

        Args:
            ranked_lists: List of ranked result lists from different retrievers.
            weights: Weights for each retriever's contribution.

        Returns:
            Combined ranked list of (text, score, merged_metadata) tuples.
        """
        if not ranked_lists:
            return []

        if weights is None:
            weights = [1.0] * len(ranked_lists)

        combined: dict[str, List[float]] = {}
        metadata_map: dict[str, dict] = {}

        for results in ranked_lists:
            raw_scores = [score for _, score, _ in results]
            norm_scores = self._normalize_scores(raw_scores)

            for (text, _, meta), norm_score in zip(results, norm_scores):
                if text not in combined:
                    combined[text] = []
                    metadata_map[text] = dict(meta)
                combined[text].append(norm_score)

        total_weight = sum(weights)
        fused = [
            (
                text,
                sum(w * s for w, s in zip(weights, text_scores)) / total_weight,
                metadata_map[text],
            )
            for text, text_scores in combined.items()
        ]
        fused.sort(key=lambda x: x[1], reverse=True)
        return fused

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        fusion_method: str = "rrf",
    ) -> List[Tuple[str, float, dict]]:
        """
        Retrieve relevant documents using hybrid search.

        Args:
            query: Search query.
            top_k: Number of final results to return.
            fusion_method: Fusion method - "rrf" (Reciprocal Rank Fusion) or "score" (weighted score).

        Returns:
            List of (text, fused_score, merged_metadata) tuples.
        """
        fetch_k = top_k * 3

        vector_results = await self.retrieval_service.retrieve(
            query, top_k=fetch_k, similarity_threshold=0.0
        )
        bm25_results = self.bm25_retriever.search_with_scores(query, top_k=fetch_k)

        if fusion_method == "score":
            fused = self._score_fusion(
                [vector_results, bm25_results],
                weights=[self.vector_weight, self.bm25_weight],
            )
        else:
            fused = self._rrf_fusion(
                [vector_results, bm25_results],
                weights=[self.vector_weight, self.bm25_weight],
            )

        return fused[:top_k]

    async def retrieve_with_rerank(
        self,
        query: str,
        top_k: int = 5,
        final_k: int = 3,
        fusion_method: str = "rrf",
    ) -> List[Tuple[str, float, dict]]:
        """
        Retrieve with reranking step for higher quality results.

        Args:
            query: Search query.
            top_k: Number of candidates to fetch before reranking.
            final_k: Final number of results after reranking.
            fusion_method: Fusion method for initial retrieval.

        Returns:
            List of (text, score, metadata) tuples after reranking.
        """
        candidates = await self.retrieve(query, top_k=top_k, fusion_method=fusion_method)

        if self.rerank_service is None:
            return candidates[:final_k]

        return await self.rerank_service.rerank_with_metadata(
            query, candidates, top_k=final_k
        )
