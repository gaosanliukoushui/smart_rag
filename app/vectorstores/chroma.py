"""Chroma vector store implementation."""

from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import uuid

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from app.vectorstores.base import BaseVectorStore


class ChromaVectorStore(BaseVectorStore):
    """Chroma vector store implementation."""

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        collection_name: str = "smartrag",
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _get_client(self):
        """Get or create Chroma client."""
        if self._client is None:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    def _get_collection(self):
        """Get or create collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "SmartRAG knowledge base"},
            )
        return self._collection

    async def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """Add texts with embeddings to Chroma."""
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb is required. Install with: pip install chromadb"
            )

        collection = self._get_collection()
        ids = [str(uuid.uuid4()) for _ in texts]

        if metadatas is None:
            metadatas = [{}] * len(texts)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        return ids

    async def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar texts in Chroma."""
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb is required")

        collection = self._get_collection()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter_metadata,
        )

        output = []
        if results["documents"] and results["documents"][0]:
            for doc, distance, metadata in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
            ):
                score = 1.0 - distance
                output.append((doc, score, metadata or {}))

        return output

    async def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        collection = self._get_collection()
        collection.delete(ids=ids)
        return True

    async def persist(self) -> bool:
        """Chroma persists automatically, this is a no-op."""
        return True

    async def get_count(self) -> int:
        """Get the number of items in the collection."""
        collection = self._get_collection()
        return collection.count()
