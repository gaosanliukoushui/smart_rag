"""Chat service for RAG-powered conversation."""

import asyncio
import uuid
import re
import time
from typing import List, Dict, AsyncGenerator, Optional
from datetime import datetime

from app.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.services.bm25_retriever import BM25Retriever
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.rerank_service import RerankService
from app.models.chat import ChatSession, Message


# Patterns that indicate the user wants a document list / inventory
_LIST_QUERY_PATTERNS = [
    re.compile(r"有哪些文档", re.IGNORECASE),
    re.compile(r"有什么文档", re.IGNORECASE),
    re.compile(r"文档列表", re.IGNORECASE),
    re.compile(r"上传了哪些", re.IGNORECASE),
    re.compile(r"有哪些文件", re.IGNORECASE),
    re.compile(r"列出.*文档", re.IGNORECASE),
    re.compile(r".*文档.*列表", re.IGNORECASE),
    re.compile(r"知识库.*包含.*文档", re.IGNORECASE),
    re.compile(r"有几.*文档", re.IGNORECASE),
]


def _is_list_query(question: str) -> bool:
    """Return True if the question asks for a list of documents in the knowledge base."""
    q = question.strip()
    return any(p.search(q) for p in _LIST_QUERY_PATTERNS)


async def _list_kb_documents(kb_id: str, tenant_id: str | None = None) -> List[dict]:
    """Query the DB directly for document metadata in a KB (non-blocking)."""
    def _sync_query():
        from app.api.deps import get_db
        from app.models.knowledge_base import Document, KnowledgeBase
        from sqlalchemy import select

        kb_uuid = uuid.UUID(kb_id)
        tenant_uuid = uuid.UUID(tenant_id) if tenant_id else None

        db = next(get_db())
        try:
            stmt = (
                select(Document)
                .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
                .where(
                    Document.knowledge_base_id == kb_uuid,
                    Document.is_deleted == False,  # noqa: E712
                )
                .order_by(Document.created_at.desc())
            )
            if tenant_uuid:
                stmt = stmt.where(KnowledgeBase.tenant_id == tenant_uuid)

            docs = db.execute(stmt).scalars().all()
            return [
                {
                    "title": d.title,
                    "file_type": d.file_type,
                    "chunk_count": d.chunk_count,
                    "file_size": d.file_size,
                    "status": d.status,
                    "created_at": d.created_at.isoformat() if d.created_at else "",
                }
                for d in docs
            ]
        finally:
            db.close()

    return await asyncio.to_thread(_sync_query)


def _format_document_list_answer(doc_list: List[dict]) -> str:
    """Format KB document metadata as a concise chat answer."""
    if not doc_list:
        return "该知识库目前没有任何文档，请先上传文件。"

    lines = []
    for i, doc in enumerate(doc_list, 1):
        size_kb = doc["file_size"] / 1024 if doc["file_size"] else 0
        lines.append(
            f"{i}. **{doc['title']}**（{doc['file_type']}，{doc['chunk_count']}个切片，"
            f"{size_kb:.1f}KB，上传于{doc['created_at'][:10]}）"
        )
    return f"根据知识库记录，当前共有 **{len(doc_list)} 个文档**：\n\n" + "\n".join(lines)


async def _build_bm25_retriever(kb_id: str, tenant_id: str | None = None) -> BM25Retriever:
    """Build a BM25 retriever from persisted chunks for one knowledge base."""
    def _sync_query():
        from app.api.deps import get_db
        from app.models.knowledge_base import Chunk, Document, KnowledgeBase
        from sqlalchemy import select

        kb_uuid = uuid.UUID(kb_id)
        tenant_uuid = uuid.UUID(tenant_id) if tenant_id else None
        db = next(get_db())
        try:
            stmt = (
                select(Chunk, Document)
                .join(Document, Chunk.document_id == Document.id)
                .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
                .where(
                    Document.knowledge_base_id == kb_uuid,
                    Document.is_deleted == False,  # noqa: E712
                )
                .order_by(Document.created_at.desc(), Chunk.chunk_index.asc())
            )
            if tenant_uuid:
                stmt = stmt.where(KnowledgeBase.tenant_id == tenant_uuid)
            rows = db.execute(stmt).all()
            return [
                (
                    chunk.content,
                    {
                        "knowledge_base_id": str(document.knowledge_base_id),
                        "document_id": str(document.id),
                        "chunk_id": str(chunk.id),
                        "chunk_index": chunk.chunk_index,
                        "document_title": document.title,
                    },
                )
                for chunk, document in rows
            ]
        finally:
            db.close()

    rows = await asyncio.to_thread(_sync_query)
    retriever = BM25Retriever(tokenizer=settings.BM25_TOKENIZER)
    retriever.build_index([text for text, _ in rows], [meta for _, meta in rows])
    return retriever


async def _single_message_stream(message: str) -> AsyncGenerator[str, None]:
    yield message


DEFAULT_PROMPT_TEMPLATE = """你是一个专业的知识库问答助手，基于提供的参考信息回答用户问题。

## 参考信息
{context}

## 历史对话
{history}

## 当前问题
{question}

## 回答要求
1. 仅根据参考信息回答，不要编造信息
2. 如果参考信息不足以回答，请明确说明
3. 回答使用清晰的格式，重要内容可加粗
4. 注明每条信息的来源序号（如"[来源1]"）
5. 保持回答简洁、专业、易读

回答："""

MAX_HISTORY_MESSAGES = 20


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token for Chinese/English mix."""
    return len(text) // 4


def _compress_context(chunks: List[tuple], max_tokens: int = 2048) -> List[tuple]:
    """Truncate low-scoring chunks to fit within token budget."""
    result = []
    total_tokens = 0
    for chunk in chunks:
        tokens = _estimate_tokens(chunk[0])
        if total_tokens + tokens <= max_tokens:
            result.append(chunk)
            total_tokens += tokens
        elif total_tokens < max_tokens:
            remaining = (max_tokens - total_tokens) * 4
            result.append((chunk[0][:remaining], chunk[1], chunk[2]))
            break
        else:
            break
    return result


class ChatService:
    """Service for RAG-powered chat."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        prompt_template: Optional[str] = None,
        max_context_tokens: int = 2048,
        max_history_messages: int = MAX_HISTORY_MESSAGES,
    ):
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE
        self.max_context_tokens = max_context_tokens
        self.max_history_messages = max_history_messages

    def _trim_history(self, session: ChatSession) -> None:
        """Apply sliding window to trim old messages, keeping most recent."""
        if len(session.messages) > self.max_history_messages:
            session.messages = session.messages[-self.max_history_messages :]

    def _build_context(self, chunks: List[tuple]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []
        for i, (text, score, meta) in enumerate(chunks):
            source_label = meta.get("document_title", f"文档{i+1}") if isinstance(meta, dict) else f"文档{i+1}"
            context_parts.append(f"[{i+1}] {source_label} (相关度: {float(score):.2f})\n{text}")
        return "\n\n".join(context_parts)

    def _build_sources(self, chunks: List[tuple]) -> List[dict]:
        """Build traceable source payloads for API responses."""
        sources = []
        for rank, (text, score, meta) in enumerate(chunks, start=1):
            meta = meta if isinstance(meta, dict) else {}
            sources.append(
                {
                    "text": text[:300] + "..." if len(text) > 300 else text,
                    "score": float(score),
                    "document_id": meta.get("document_id", ""),
                    "document_title": meta.get("document_title", ""),
                    "chunk_id": meta.get("chunk_id", ""),
                    "chunk_index": meta.get("chunk_index"),
                    "rank": rank,
                }
            )
        return sources

    async def _retrieve_chunks(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int,
        tenant_id: str | None = None,
    ) -> List[tuple]:
        """Retrieve chunks using the configured retrieval mode."""
        mode = settings.RETRIEVAL_MODE.lower()
        if mode == "vector":
            return await self.retrieval_service.retrieve(
                query=query,
                top_k=top_k,
                knowledge_base_id=knowledge_base_id,
            )

        bm25 = await _build_bm25_retriever(knowledge_base_id, tenant_id=tenant_id)
        reranker = RerankService(settings.RERANKER_MODEL) if mode == "hybrid_rerank" else None
        hybrid = HybridRetrievalService(
            retrieval_service=self.retrieval_service,
            bm25_retriever=bm25,
            rerank_service=reranker,
        )
        if mode == "hybrid_rerank":
            return await hybrid.retrieve_with_rerank(
                query,
                top_k=max(top_k * 3, 10),
                final_k=top_k,
                knowledge_base_id=knowledge_base_id,
            )
        return await hybrid.retrieve(query, top_k=top_k, knowledge_base_id=knowledge_base_id)

    def _build_history(self, session: Optional[ChatSession]) -> str:
        """Format conversation history for the prompt."""
        if not session or not session.messages:
            return "（无历史对话）"
        lines = []
        for msg in session.messages:
            role = "用户" if msg.role == "user" else "助手"
            lines.append(f"{role}：{msg.content}")
        return "\n".join(lines)

    def _build_prompt(self, context: str, question: str, session: Optional[ChatSession] = None) -> str:
        """Build prompt from context, question, and history."""
        history = self._build_history(session)
        return self.prompt_template.format(context=context, question=question, history=history)

    async def _rewrite_query(self, question: str) -> str:
        """Rewrite query to improve retrieval quality via LLM."""
        rewrite_prompt = (
            f"请将以下用户问题改写为更适合检索的查询语句。"
            f"保留核心意图，可补充同义词、展开缩写、拆分复杂问题。\n\n"
            f"原始问题：{question}\n\n"
            f"改写后："
        )
        try:
            rewritten = await self.llm_service.generate(rewrite_prompt, max_tokens=256)
            rewritten = rewritten.strip()
            return rewritten if rewritten else question
        except Exception:
            return question

    async def ask(
        self,
        question: str,
        knowledge_base_id: str,
        session: Optional[ChatSession] = None,
        top_k: int = 5,
        stream: bool = True,
        use_rewrite: bool = False,
        tenant_id: str | None = None,
    ) -> tuple[str, List[dict]]:
        """
        Process a question and return answer with sources.

        Returns:
            Tuple of (answer, sources)
        """
        query = await self._rewrite_query(question) if use_rewrite else question

        if _is_list_query(question):
            doc_list = await _list_kb_documents(knowledge_base_id, tenant_id=tenant_id)
            answer = _format_document_list_answer(doc_list)
            if session:
                session.add_message("user", question)
                session.add_message("assistant", answer)
            return answer, []

        chunks = await self._retrieve_chunks(query, knowledge_base_id, top_k, tenant_id=tenant_id)
        if not chunks:
            answer = "未检索到足够相关的知识库内容，无法基于当前资料回答该问题。请补充文档或换一种问法。"
            if session:
                session.add_message("user", question)
                session.add_message("assistant", answer)
            return answer, []

        compressed = _compress_context(chunks, self.max_context_tokens)
        context = self._build_context(compressed)
        prompt = self._build_prompt(context, question, session)

        from app.api.v1.metrics import collector

        llm_start = time.perf_counter()
        answer = await self.llm_service.generate(prompt)
        collector.record_rag_latency("llm", (time.perf_counter() - llm_start) * 1000)

        sources = self._build_sources(compressed)

        if session:
            self._trim_history(session)
            session.add_message("user", question)
            session.add_message("assistant", answer)

        return answer, sources

    async def stream_ask(
        self,
        question: str,
        knowledge_base_id: str,
        session: Optional[ChatSession] = None,
        top_k: int = 5,
        use_rewrite: bool = True,
        tenant_id: str | None = None,
    ) -> tuple[AsyncGenerator[str, None], List[dict], Optional[ChatSession]]:
        """
        Stream answer for a question, returning chunks generator and sources.

        Returns:
            Tuple of (token_generator, sources, session)
        """
        query = await self._rewrite_query(question) if use_rewrite else question

        chunks = await self._retrieve_chunks(query, knowledge_base_id, top_k, tenant_id=tenant_id)

        if not chunks:
            answer = "未检索到足够相关的知识库内容，无法基于当前资料回答该问题。请补充文档或换一种问法。"
            if session:
                session.add_message("user", question)
            return _single_message_stream(answer), [], session

        compressed = _compress_context(chunks, self.max_context_tokens)
        context = self._build_context(compressed)

        if session:
            self._trim_history(session)
            session.add_message("user", question)

        prompt = self._build_prompt(context, question, session)

        sources = self._build_sources(compressed)

        return self.llm_service.stream_generate(prompt), sources, session

    async def create_session(self, knowledge_base_id: str, tenant_id: str) -> ChatSession:
        """Create a new chat session."""
        return ChatSession(knowledge_base_id=knowledge_base_id, tenant_id=tenant_id)

    async def clear_history(self, session: ChatSession) -> None:
        """Clear all messages from a session."""
        session.messages.clear()

    async def regenerate_last_response(
        self,
        session: ChatSession,
        knowledge_base_id: str,
        top_k: int = 5,
    ) -> tuple[str, List[dict]]:
        """Regenerate the last assistant response for the session."""
        if len(session.messages) < 2:
            return "", []

        session.messages.pop()
        question = session.messages.pop().content

        answer, sources = await self.ask(
            question=question,
            knowledge_base_id=knowledge_base_id,
            session=session,
            top_k=top_k,
            use_rewrite=True,
        )
        return answer, sources
