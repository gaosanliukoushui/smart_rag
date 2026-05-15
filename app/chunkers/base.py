"""Base chunker interface."""

from abc import ABC, abstractmethod
from typing import List


class BaseChunker(ABC):
    """Abstract base class for document chunkers."""

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """
        Split text into chunks.

        Args:
            text: Input text to chunk

        Returns:
            List of text chunks
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // 4
