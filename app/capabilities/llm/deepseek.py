"""DeepSeek LLM integration."""

from typing import List, Dict, Optional, AsyncGenerator
from openai import AsyncOpenAI


class DeepSeekLLM:
    """DeepSeek language model wrapper."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create the API client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response from the model."""
        client = self._get_client()

        if messages:
            all_messages = messages + [{"role": "user", "content": prompt}]
        else:
            all_messages = [{"role": "user", "content": prompt}]

        response = await client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        return response.choices[0].message.content

    async def stream_generate(
        self,
        prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generate a response from the model."""
        client = self._get_client()

        if messages:
            all_messages = messages + [{"role": "user", "content": prompt}]
        else:
            all_messages = [{"role": "user", "content": prompt}]

        stream = await client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // 4
