"""Tests for vector store integrations."""

import pytest

from app.vectorstores.chroma import CHROMADB_AVAILABLE, ChromaVectorStore


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb is not installed")
@pytest.mark.asyncio
async def test_chroma_persists_vectors_across_instances(temp_dir):
    """Uploaded vectors remain searchable after recreating the Chroma wrapper."""
    first = ChromaVectorStore(
        persist_directory=str(temp_dir / "chroma"),
        collection_name="test_persistence",
    )
    ids = await first.add_texts(
        ["SmartRAG supports persistent retrieval"],
        [[1.0, 0.0, 0.0]],
        [{"document_id": "doc-1", "chunk_id": "chunk-1", "knowledge_base_id": "kb-1"}],
    )

    second = ChromaVectorStore(
        persist_directory=str(temp_dir / "chroma"),
        collection_name="test_persistence",
    )
    results = await second.similarity_search(
        [1.0, 0.0, 0.0],
        k=1,
        filter_metadata={"knowledge_base_id": "kb-1"},
    )

    assert ids
    assert results[0][0] == "SmartRAG supports persistent retrieval"
    assert results[0][2]["chunk_id"] == "chunk-1"
