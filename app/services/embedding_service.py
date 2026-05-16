"""Embedding service for generating text embeddings."""

from typing import List, Optional
import numpy as np


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        dimension: int = 1024,
    ):
        self.model_name = model_name
        self.device = device
        self.dimension = dimension
        self._model = None

    async def load_model(self):
        """Load the embedding model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        model = await self.load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Generate embeddings in batches for large text collections.

        Args:
            texts: List of texts to embed.
            batch_size: Number of texts per batch (controls memory usage).
            show_progress: Whether to show a progress bar.

        Returns:
            List of embedding vectors.
        """
        model = await self.load_model()
        all_embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
        )
        return all_embeddings.tolist()

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        embeddings = await self.embed([query])
        return embeddings[0]

    async def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        emb1, emb2 = await self.embed([text1, text2])
        return float(np.dot(emb1, emb2))
