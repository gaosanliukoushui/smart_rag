"""LLM service for language model operations."""

from typing import List, Dict, Optional, AsyncGenerator
import os


class LLMService:
    """Service for LLM operations."""

    def __init__(
        self,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        num_ctx: int = 4096,
        timeout: int = 120,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.num_ctx = num_ctx
        self.timeout = timeout
        self._client = None

    async def load_client(self):
        """Load the LLM client."""
        if self._client is None:
            if self.provider == "openai":
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            elif self.provider == "deepseek":
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url or "https://api.deepseek.com",
                )
            elif self.provider == "qwen":
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                )
            elif self.provider == "ollama":
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key="ollama",
                    base_url=self.base_url or "http://localhost:11434/v1",
                    timeout=self.timeout,
                )

    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a response from the LLM."""
        await self.load_client()

        all_messages = messages + [{"role": "user", "content": prompt}] if messages else [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": all_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        if self.provider == "ollama" and self.num_ctx != 4096:
            kwargs["extra_body"] = {"num_ctx": self.num_ctx}

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def stream_generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generate a response from the LLM."""
        await self.load_client()

        all_messages = messages + [{"role": "user", "content": prompt}] if messages else [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": all_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": True,
        }

        if self.provider == "ollama" and self.num_ctx != 4096:
            kwargs["extra_body"] = {"num_ctx": self.num_ctx}

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
