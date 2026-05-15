"""Recursive text chunker."""

from typing import List
from app.chunkers.base import BaseChunker


class RecursiveChunker(BaseChunker):
    """Recursive character-based text chunker with sentence boundary awareness."""

    def chunk(self, text: str) -> List[str]:
        """Split text into chunks with overlap, trying to respect sentence boundaries."""
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            if end < text_length:
                cut_point = self._find_best_cut_point(text, start, end)

                if cut_point > start:
                    end = cut_point

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.overlap

        return [c for c in chunks if c]

    def _find_best_cut_point(self, text: str, start: int, end: int) -> int:
        """Find the best point to cut text (preferring sentence boundaries)."""
        separators = [
            ("。", 1),
            ("！", 1),
            ("？", 1),
            ("！", 1),
            ("\n\n", 2),
            (". ", 2),
            ("! ", 2),
            ("? ", 2),
            ("\n", 1),
        ]

        best_point = end
        best_priority = -1

        for sep, priority in separators:
            pos = text.rfind(sep, start, end)
            if pos > start and priority > best_priority:
                best_point = pos + len(sep)
                best_priority = priority

        return best_point
