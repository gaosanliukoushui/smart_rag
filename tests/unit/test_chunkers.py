"""Unit tests for chunk service."""

import pytest

from app.services.chunk_service import ChunkService


class TestChunkService:
    """Tests for ChunkService."""

    def test_chunk_text_basic(self):
        """Test basic chunking on short text returns single chunk."""
        text = "这是一个短句子。"
        chunker = ChunkService(chunk_size=500, overlap=100)
        chunks = chunker.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_multiple(self):
        """Test text is split into multiple chunks at Chinese sentence boundaries."""
        text = "第一个句子。第二个句子。第三个句子。"
        chunker = ChunkService(chunk_size=20, overlap=5)
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_text_with_overlap(self):
        """Test that consecutive chunks share overlapping characters."""
        text = ("第一个句子。第二个句子。第三个句子。" * 10)
        chunker = ChunkService(chunk_size=30, overlap=10)
        chunks = chunker.chunk_text(text)

        if len(chunks) >= 2:
            last_10 = chunks[0][-10:]
            assert any(last_10 in c for c in chunks[1:]), (
                f"Overlap fragment '{last_10}' not found in subsequent chunks"
            )

    def test_chunk_text_empty(self):
        """Test chunking empty text returns empty list."""
        chunker = ChunkService()
        chunks = chunker.chunk_text("")
        assert chunks == []

    def test_chunk_text_whitespace_only(self):
        """Test chunking whitespace-only text returns empty list."""
        chunker = ChunkService()
        chunks = chunker.chunk_text("   \n\t  ")
        assert chunks == []

    def test_create_chunks_returns_chunk_objects(self):
        """Test create_chunks returns Chunk model instances with correct fields."""
        chunker = ChunkService(chunk_size=500, overlap=100)
        chunks = chunker.create_chunks("doc-123", "这是一个测试句子。")

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.document_id == "doc-123"
        assert chunk.content == "这是一个测试句子。"
        assert chunk.chunk_index == 0
        assert chunk.token_count == len("这是一个测试句子。") // 4

    def test_create_chunks_multiple(self):
        """Test create_chunks handles multiple chunks with correct indices."""
        chunker = ChunkService(chunk_size=20, overlap=5)
        text = "第一个句子。第二个句子。第三个句子。"
        chunks = chunker.create_chunks("doc-456", text)

        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.document_id == "doc-456"
            assert chunk.chunk_index == i

    def test_create_chunks_empty(self):
        """Test create_chunks with empty text returns empty list."""
        chunker = ChunkService()
        chunks = chunker.create_chunks("doc-789", "")
        assert chunks == []

    def test_estimate_token_count(self):
        """Test token estimation is len/4."""
        chunker = ChunkService()
        text = "这是一个测试文本。" * 10
        tokens = chunker.estimate_token_count(text)

        assert tokens == len(text) // 4

    def test_overlap_respected(self):
        """Test that overlap parameter affects chunk boundary."""
        text = "第一个句子。第二个句子。第三个句子。"

        chunker_small_overlap = ChunkService(chunk_size=15, overlap=3)
        chunker_big_overlap = ChunkService(chunk_size=15, overlap=8)

        chunks_small = chunker_small_overlap.chunk_text(text)
        chunks_big = chunker_big_overlap.chunk_text(text)

        if len(chunks_small) >= 2 and len(chunks_big) >= 2:
            assert chunks_big[0].endswith(chunks_small[0][-8:])
