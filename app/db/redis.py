"""Redis connection management."""

from typing import Optional

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


redis_client = RedisClient()
