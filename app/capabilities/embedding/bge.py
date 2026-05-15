"""BGE Embedding model integration."""

from typing import List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np


class BGEEmbedding:
    """BGE embedding model wrapper."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        normalize_embeddings: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        self.normalize_embeddings = normalize_embeddings
        self._model = None

    def load(self) -> "BGEEmbedding":
        """Load the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if self._model is None:
            self.load()

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        return self.embed([query])[0]

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if self._model is None:
            self.load()
        return self._model.get_sentence_embedding_dimension()

    def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        emb1, emb2 = self.embed([text1, text2])
        return float(np.dot(emb1, emb2))

    def batch_embed(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Batch embed texts with batching for large datasets."""
        if self._model is None:
            self.load()

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.tolist()
