"""Vector store service for managing vector storage."""

from typing import List, Optional, Tuple
import uuid

from app.config import settings

# Module-level singleton instance shared across all imports
_vector_store: "VectorStoreService" | None = None


def get_vector_store() -> "VectorStoreService":
    """Get the global singleton VectorStoreService instance."""
    global _vector_store
    if _vector_store is None:
        if settings.VECTOR_DB_TYPE == "memory":
            _vector_store = VectorStoreService()
        else:
            _vector_store = PersistentVectorStoreService()
    return _vector_store


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
        """Add vectors to the store in batch."""
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

    async def add_vectors_batch(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: Optional[List[dict]] = None,
        batch_size: int = 32,
    ) -> List[str]:
        """
        Add vectors in batches for better performance with large datasets.

        Processes texts in chunks of batch_size to control memory usage.
        """
        if metadata is None:
            metadata = [{}] * len(texts)

        ids = []
        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            batch_texts = texts[start:end]
            batch_embeddings = embeddings[start:end]
            batch_metadata = metadata[start:end]

            batch_ids = await self.add_vectors(batch_texts, batch_embeddings, batch_metadata)
            ids.extend(batch_ids)

        return ids

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
        knowledge_base_id: Optional[str] = None,
    ) -> List[Tuple[str, float, dict]]:
        """Search for similar vectors, optionally filtered by knowledge base."""
        import numpy as np

        results = []
        for vector_id, data in self._embeddings.items():
            if knowledge_base_id is not None:
                if data["metadata"].get("knowledge_base_id") != knowledge_base_id:
                    continue
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


class PersistentVectorStoreService:
    """Vector service backed by the configured persistent vector store."""

    def __init__(self, vector_store=None):
        if vector_store is None:
            if settings.VECTOR_DB_TYPE != "chroma":
                raise ValueError(f"Unsupported VECTOR_DB_TYPE: {settings.VECTOR_DB_TYPE}")
            from app.vectorstores.chroma import ChromaVectorStore

            vector_store = ChromaVectorStore(persist_directory=settings.CHROMA_PERSIST_DIR)
        self.vector_store = vector_store
        self._embeddings = None

    async def add_vectors(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: Optional[List[dict]] = None,
    ) -> List[str]:
        return await self.vector_store.add_texts(texts, embeddings, metadata)

    async def add_vectors_batch(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: Optional[List[dict]] = None,
        batch_size: int = 32,
    ) -> List[str]:
        ids = []
        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            ids.extend(
                await self.add_vectors(
                    texts[start:end],
                    embeddings[start:end],
                    metadata[start:end] if metadata else None,
                )
            )
        return ids

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
        knowledge_base_id: Optional[str] = None,
    ) -> List[Tuple[str, float, dict]]:
        filter_metadata = {"knowledge_base_id": knowledge_base_id} if knowledge_base_id else None
        results = await self.vector_store.similarity_search(
            query_embedding,
            k=top_k,
            filter_metadata=filter_metadata,
        )
        return [r for r in results if r[1] >= threshold]

    async def delete_vectors(self, vector_ids: List[str]) -> bool:
        return await self.vector_store.delete(vector_ids)

    async def get_vector(self, vector_id: str) -> Optional[dict]:
        return None
