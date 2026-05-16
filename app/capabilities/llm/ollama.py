"""Ollama local LLM implementation."""

from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from app.core.exceptions import LLMError
from app.config import get_settings


class OllamaLLM:
    """Ollama local model wrapper using OpenAI-compatible API."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        num_ctx: int = 4096,
        timeout: int = 120,
    ):
        settings = get_settings()
        self.model = model or settings.OLLAMA_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout = timeout
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create the API client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key="ollama",
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        messages: Optional[list] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 2048,
        num_ctx: Optional[int] = None,
    ) -> str:
        """Non-streaming generation."""
        client = self._get_client()

        if messages:
            all_messages = messages + [{"role": "user", "content": prompt}]
        else:
            all_messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": all_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens,
        }

        if num_ctx is not None:
            kwargs["extra_body"] = {"num_ctx": num_ctx}
        elif self.num_ctx != 4096:
            kwargs["extra_body"] = {"num_ctx": self.num_ctx}

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def stream_generate(
        self,
        prompt: str,
        messages: Optional[list] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 2048,
        num_ctx: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Streaming generation, yields content tokens."""
        client = self._get_client()

        if messages:
            all_messages = messages + [{"role": "user", "content": prompt}]
        else:
            all_messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": all_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if num_ctx is not None:
            kwargs["extra_body"] = {"num_ctx": num_ctx}
        elif self.num_ctx != 4096:
            kwargs["extra_body"] = {"num_ctx": self.num_ctx}

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def list_models(self) -> list[str]:
        """List available models from Ollama."""
        client = self._get_client()
        try:
            models = await client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            raise LLMError(f"Failed to list Ollama models: {e}")

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // 4
