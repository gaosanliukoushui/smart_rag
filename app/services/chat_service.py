"""Chat service for RAG-powered conversation."""

from typing import List, Dict, AsyncGenerator, Optional
from datetime import datetime

from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.models.chat import ChatSession, Message


DEFAULT_PROMPT_TEMPLATE = """你是一个专业的知识库问答助手。

参考信息：
{context}

用户问题：{question}

请根据参考信息回答用户的问题。如果参考信息中没有相关内容，请如实说明。
回答："""


class ChatService:
    """Service for RAG-powered chat."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        prompt_template: Optional[str] = None,
    ):
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE
        self._sessions: Dict[str, ChatSession] = {}

    def _build_context(self, chunks: List[tuple]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []
        for i, (text, score, _) in enumerate(chunks):
            context_parts.append(f"[文档 {i+1}]\n{text}")
        return "\n\n".join(context_parts)

    def _build_prompt(self, context: str, question: str) -> str:
        """Build prompt from context and question."""
        return self.prompt_template.format(context=context, question=question)

    async def ask(
        self,
        question: str,
        knowledge_base_id: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
        stream: bool = True,
    ) -> tuple[str, List[dict]]:
        """
        Process a question and return answer with sources.

        Returns:
            Tuple of (answer, sources)
        """
        chunks = await self.retrieval_service.retrieve(
            query=question,
            top_k=top_k,
        )

        context = self._build_context(chunks)
        prompt = self._build_prompt(context, question)

        answer = await self.llm_service.generate(prompt)

        sources = [
            {"text": text[:200] + "..." if len(text) > 200 else text, "score": float(score)}
            for text, score, _ in chunks
        ]

        return answer, sources

    async def stream_ask(
        self,
        question: str,
        knowledge_base_id: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
    ) -> AsyncGenerator[str, None]:
        """Stream answer for a question."""
        chunks = await self.retrieval_service.retrieve(
            query=question,
            top_k=top_k,
        )

        context = self._build_context(chunks)
        prompt = self._build_prompt(context, question)

        async for token in self.llm_service.stream_generate(prompt):
            yield token

    async def create_session(self, knowledge_base_id: str) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(knowledge_base_id=knowledge_base_id)
        self._sessions[session.id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        return self._sessions.get(session_id)
