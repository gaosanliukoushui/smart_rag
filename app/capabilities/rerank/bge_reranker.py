"""BGE Reranker integration."""

from typing import List, Tuple
from sentence_transformers import CrossEncoder
import numpy as np


class BGEReranker:
    """BGE reranker model wrapper."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
    ):
        self.model_name = model_name
        self._model = None

    def load(self) -> "BGEReranker":
        """Load the reranker model."""
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
        return self

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        return_score: bool = True,
    ) -> List[Tuple[str, float]]:
        """
        Rerank documents based on query relevance.

        Args:
            query: The query string
            documents: List of document texts
            top_k: Number of top results to return
            return_score: Whether to return relevance scores

        Returns:
            List of (document, score) tuples sorted by relevance
        """
        if self._model is None:
            self.load()

        pairs = [[query, doc] for doc in documents]
        scores = self._model.predict(pairs)

        if isinstance(scores, np.ndarray):
            scores = scores.tolist()

        ranked = sorted(
            zip(documents, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        if return_score:
            return [(doc, float(score)) for doc, score in ranked[:top_k]]
        else:
            return [(doc, 1.0) for doc, _ in ranked[:top_k]]

    def compute_score(self, query: str, document: str) -> float:
        """Compute relevance score for a single query-document pair."""
        if self._model is None:
            self.load()

        score = self._model.predict([[query, document]])
        if isinstance(score, np.ndarray):
            score = score.tolist()[0]
        return float(score)
