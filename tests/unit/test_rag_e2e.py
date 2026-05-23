"""Service-level RAG flow tests."""

import pytest
from unittest.mock import AsyncMock

from app.services.chat_service import ChatService
from app.services.retrieval_service import RetrievalService
from app.services.vector_store_service import VectorStoreService
from app.models.chat import ChatSession


class FakeLLM:
    """Minimal LLM stub that validates prompt grounding."""

    def __init__(self):
        self.generate = AsyncMock(return_value="SmartRAG 支持来源追溯。[来源1]")

    async def stream_generate(self, prompt):
        yield await self.generate(prompt)


@pytest.mark.asyncio
async def test_rag_answer_returns_traceable_sources(monkeypatch):
    """End-to-end service flow returns an answer and source identifiers."""
    monkeypatch.setattr("app.config.settings.RETRIEVAL_MODE", "vector")

    embedding = AsyncMock()
    embedding.embed_query = AsyncMock(return_value=[1.0, 0.0])
    vector_store = VectorStoreService()
    await vector_store.add_vectors(
        ["SmartRAG 的 sources 包含 document_id、chunk_id、rank 和 score。"],
        [[1.0, 0.0]],
        metadata=[
            {
                "knowledge_base_id": "kb-demo",
                "document_id": "doc-demo",
                "document_title": "demo",
                "chunk_id": "chunk-demo",
                "chunk_index": 0,
            }
        ],
    )
    retrieval = RetrievalService(embedding, vector_store)
    service = ChatService(retrieval, FakeLLM())
    session = ChatSession(knowledge_base_id="kb-demo", tenant_id="tenant-demo")

    answer, sources = await service.ask(
        "sources 包含哪些字段？",
        knowledge_base_id="kb-demo",
        session=session,
        tenant_id="tenant-demo",
    )

    assert "来源追溯" in answer
    assert sources[0]["document_id"] == "doc-demo"
    assert sources[0]["chunk_id"] == "chunk-demo"
    assert sources[0]["rank"] == 1
    assert len(session.messages) == 2


@pytest.mark.asyncio
async def test_rag_refuses_when_retrieval_is_empty(monkeypatch):
    """RAG flow refuses grounded answering when retrieval returns no chunks."""
    monkeypatch.setattr("app.config.settings.RETRIEVAL_MODE", "vector")

    embedding = AsyncMock()
    embedding.embed_query = AsyncMock(return_value=[0.0, 1.0])
    retrieval = RetrievalService(embedding, VectorStoreService())
    service = ChatService(retrieval, FakeLLM())

    answer, sources = await service.ask("不存在的问题", knowledge_base_id="missing-kb")

    assert "未检索到足够相关" in answer
    assert sources == []
