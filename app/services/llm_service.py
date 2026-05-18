"""LLM service for language model operations."""

import os
from typing import List, Dict, Optional, AsyncGenerator

from app.config import get_settings


class LLMService:
    """Service for LLM operations."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        num_ctx: int = 4096,
        timeout: int = 120,
    ):
        settings = get_settings()
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or self._get_model_for_provider(settings)
        self.api_key = api_key or self._get_api_key_for_provider(settings)
        self.base_url = base_url or self._get_base_url_for_provider(settings)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.num_ctx = num_ctx
        self.timeout = timeout
        self._client = None

    def _get_model_for_provider(self, settings) -> str:
        if self.provider == "deepseek":
            return settings.DEEPSEEK_MODEL
        elif self.provider == "qwen":
            return settings.QWEN_MODEL
        elif self.provider == "openai":
            return settings.OPENAI_MODEL
        elif self.provider == "ollama":
            return settings.OLLAMA_MODEL
        return "gpt-4o"

    def _get_api_key_for_provider(self, settings) -> str:
        if self.provider == "deepseek":
            return settings.DEEPSEEK_API_KEY
        elif self.provider == "qwen":
            return settings.QWEN_API_KEY
        elif self.provider == "openai":
            return settings.OPENAI_API_KEY
        elif self.provider == "ollama":
            return "ollama"
        return ""

    def _get_base_url_for_provider(self, settings) -> str:
        if self.provider == "deepseek":
            return settings.DEEPSEEK_BASE_URL
        elif self.provider == "qwen":
            return settings.QWEN_BASE_URL
        elif self.provider == "openai":
            return "https://api.openai.com/v1"
        elif self.provider == "ollama":
            return settings.OLLAMA_BASE_URL
        return ""

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
