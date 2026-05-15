"""Base vector store interface."""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any


class BaseVectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        Add texts with their embeddings to the store.

        Returns:
            List of generated IDs
        """
        pass

    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar texts.

        Returns:
            List of (text, score, metadata) tuples
        """
        pass

    @abstractmethod
    async def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        pass

    @abstractmethod
    async def persist(self) -> bool:
        """Persist the vector store to disk."""
        pass
