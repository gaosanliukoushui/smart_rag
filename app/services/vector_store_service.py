"""Vector store service for managing vector storage."""

from typing import List, Optional, Tuple
import uuid


class VectorStoreService:
    """Service for vector storage operations."""

    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self._embeddings: dict = {}

    async def add_vectors(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: Optional[List[dict]] = None,
    ) -> List[str]:
        """Add vectors to the store."""
        if metadata is None:
            metadata = [{}] * len(texts)

        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            vector_id = str(uuid.uuid4())
            self._embeddings[vector_id] = {
                "text": text,
                "embedding": embedding,
                "metadata": metadata[i],
            }
            ids.append(vector_id)

        return ids

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[Tuple[str, float, dict]]:
        """Search for similar vectors."""
        import numpy as np

        results = []
        for vector_id, data in self._embeddings.items():
            similarity = float(np.dot(query_embedding, data["embedding"]))
            if similarity >= threshold:
                results.append((data["text"], similarity, data["metadata"]))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def delete_vectors(self, vector_ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        for vector_id in vector_ids:
            if vector_id in self._embeddings:
                del self._embeddings[vector_id]
        return True

    async def get_vector(self, vector_id: str) -> Optional[dict]:
        """Get vector by ID."""
        return self._embeddings.get(vector_id)
