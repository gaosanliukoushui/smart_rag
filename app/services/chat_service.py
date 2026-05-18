"""Chat service for RAG-powered conversation."""

import re
from typing import List, Dict, AsyncGenerator, Optional
from datetime import datetime

from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.models.chat import ChatSession, Message


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
    ) -> tuple[str, List[dict]]:
        """
        Process a question and return answer with sources.

        Returns:
            Tuple of (answer, sources)
        """
        query = await self._rewrite_query(question) if use_rewrite else question

        chunks = await self.retrieval_service.retrieve(
            query=query,
            top_k=top_k,
            knowledge_base_id=knowledge_base_id,
        )

        compressed = _compress_context(chunks, self.max_context_tokens)
        context = self._build_context(compressed)
        prompt = self._build_prompt(context, question, session)

        answer = await self.llm_service.generate(prompt)

        sources = [
            {
                "text": text[:300] + "..." if len(text) > 300 else text,
                "score": float(score),
                "document_title": meta.get("document_title", "") if isinstance(meta, dict) else "",
            }
            for text, score, meta in compressed
        ]

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
    ) -> tuple[AsyncGenerator[str, None], List[dict], Optional[ChatSession]]:
        """
        Stream answer for a question, returning chunks generator and sources.

        Returns:
            Tuple of (token_generator, sources, session)
        """
        query = await self._rewrite_query(question) if use_rewrite else question

        chunks = await self.retrieval_service.retrieve(
            query=query,
            top_k=top_k,
            knowledge_base_id=knowledge_base_id,
        )

        compressed = _compress_context(chunks, self.max_context_tokens)
        context = self._build_context(compressed)

        if session:
            self._trim_history(session)
            session.add_message("user", question)

        prompt = self._build_prompt(context, question, session)

        sources = [
            {
                "text": text[:300] + "..." if len(text) > 300 else text,
                "score": float(score),
                "document_title": meta.get("document_title", "") if isinstance(meta, dict) else "",
            }
            for text, score, meta in compressed
        ]

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
