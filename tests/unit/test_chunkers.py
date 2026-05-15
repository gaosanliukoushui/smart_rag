"""Unit tests for chunkers."""

import pytest

from app.chunkers.recursive_chunker import RecursiveChunker


class TestRecursiveChunker:
    """Tests for RecursiveChunker."""

    def test_chunk_basic(self, sample_text):
        """Test basic chunking."""
        chunker = RecursiveChunker(chunk_size=100, overlap=20)
        chunks = chunker.chunk(sample_text)

        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_with_overlap(self, sample_long_text):
        """Test that chunks have overlap."""
        chunker = RecursiveChunker(chunk_size=100, overlap=30)
        chunks = chunker.chunk(sample_long_text)

        if len(chunks) > 1:
            assert chunks[0][-30:] in chunks[1] or chunks[1][:30] in chunks[0]

    def test_empty_text(self):
        """Test chunking empty text."""
        chunker = RecursiveChunker()
        chunks = chunker.chunk("")

        assert len(chunks) == 0

    def test_small_text(self):
        """Test chunking text smaller than chunk size."""
        chunker = RecursiveChunker(chunk_size=500)
        chunks = chunker.chunk("短文本。")

        assert len(chunks) == 1

    def test_estimate_tokens(self):
        """Test token estimation."""
        chunker = RecursiveChunker()
        text = "这是测试文本内容。" * 10
        tokens = chunker.estimate_tokens(text)

        assert tokens > 0
        assert tokens == len(text) // 4
