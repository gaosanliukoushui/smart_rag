"""Redis connection management."""

import json
from typing import Optional, List

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            raise ImportError("redis is required. Install with: pip install redis")

        self._client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        if not self._client:
            await self.connect()
        return await self._client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None,
    ) -> bool:
        """Set a key-value pair with optional expiration."""
        if not self._client:
            await self.connect()
        return await self._client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete a key."""
        if not self._client:
            await self.connect()
        return await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self._client:
            await self.connect()
        return await self._client.exists(key) > 0

    @property
    def client(self) -> redis.Redis:
        """Get the raw Redis client."""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def set_json(
        self,
        key: str,
        value: dict,
        expire: Optional[int] = None,
    ) -> bool:
        """Set a JSON-serializable value with optional expiration."""
        if not self._client:
            await self.connect()
        serialized = json.dumps(value, default=str)
        return await self._client.set(key, serialized, ex=expire)

    async def get_json(self, key: str) -> Optional[dict]:
        """Get a JSON value by key."""
        if not self._client:
            await self.connect()
        raw = await self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_session(
        self,
        session_id: str,
        session_data: dict,
        ttl: int = 86400 * 7,
    ) -> bool:
        """Store a chat session with a 7-day default TTL."""
        return await self.set_json(f"session:{session_id}", session_data, expire=ttl)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a chat session by ID."""
        return await self.get_json(f"session:{session_id}")

    async def delete_session(self, session_id: str) -> int:
        """Delete a chat session by ID."""
        return await self.delete(f"session:{session_id}")

    async def list_sessions(self, pattern: str = "session:*") -> List[str]:
        """List all session keys matching the pattern."""
        if not self._client:
            await self.connect()
        keys = []
        async for key in self._client.scan_iter(match=pattern):
            keys.append(key)
        return keys


redis_client = RedisClient()
