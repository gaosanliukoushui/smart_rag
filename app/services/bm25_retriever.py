"""BM25 retrieval service for keyword-based search."""

import math
from typing import List, Tuple, Optional

from rank_bm25 import BM25Okapi


class BM25Retriever:
    """BM25-based keyword retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 retriever.

        Args:
            k1: Term frequency saturation parameter (higher = more impact of repeats).
            b: Length normalization parameter (0-1, higher = stronger penalty for long docs).
        """
        self.k1 = k1
        self.b = b
        self._bm25: Optional[BM25Okapi] = None
        self._corpus: List[str] = []
        self._tokenized_corpus: List[List[str]] = []
        self._avgdl: float = 0.0
        self._doc_lengths: List[int] = []

    def build_index(self, texts: List[str]) -> None:
        """
        Build BM25 index from documents.

        Args:
            texts: List of document texts to index.
        """
        if not texts:
            self._bm25 = None
            self._corpus = []
            self._tokenized_corpus = []
            self._doc_lengths = []
            self._avgdl = 0.0
            return

        self._corpus = texts
        self._tokenized_corpus = [self._tokenize(doc) for doc in texts]
        self._doc_lengths = [len(tokens) for tokens in self._tokenized_corpus]
        self._avgdl = sum(self._doc_lengths) / len(self._doc_lengths) if self._doc_lengths else 0.0
        self._bm25 = BM25Okapi(self._tokenized_corpus)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        return text.lower().split()

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float, int]]:
        """
        Search for relevant documents using BM25.

        Args:
            query: Search query string.
            top_k: Number of top results to return.

        Returns:
            List of (text, score, index) tuples sorted by score descending.
        """
        if self._bm25 is None or not self._corpus:
            return []

        tokenized_query = self._tokenize(query)
        raw_scores = self._bm25.get_scores(tokenized_query)

        scored = [(self._corpus[i], float(raw_scores[i]), i) for i in range(len(raw_scores))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_with_scores(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float, dict]]:
        """
        Search and return results with metadata.

        Args:
            query: Search query string.
            top_k: Number of top results to return.

        Returns:
            List of (text, score, metadata) tuples.
        """
        results = self.search(query, top_k)
        return [
            (text, score, {"doc_index": idx})
            for text, score, idx in results
        ]
