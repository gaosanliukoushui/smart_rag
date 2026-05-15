"""Chunk service for document chunking operations."""

from typing import List
from app.models.chunk import Chunk


class ChunkService:
    """Service for document chunking operations."""

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            if end < text_length:
                last_period = text.rfind("。", start, end)
                last_newline = text.rfind("\n", start, end)
                cut_point = max(last_period, last_newline)

                if cut_point > start + self.chunk_size // 2:
                    end = cut_point + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.overlap

        return [c for c in chunks if c]

    def create_chunks(self, document_id: str, text: str) -> List[Chunk]:
        """Create chunk objects from text."""
        chunk_texts = self.chunk_text(text)
        chunks = []

        for i, content in enumerate(chunk_texts):
            chunk = Chunk(
                document_id=document_id,
                content=content,
                chunk_index=i,
                token_count=len(content) // 4,
            )
            chunks.append(chunk)

        return chunks

    def estimate_token_count(self, text: str) -> int:
        """Estimate token count for text (rough estimate)."""
        return len(text) // 4
