"""Resource quota management service using Redis."""

from typing import Optional, Tuple

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client = None


def _get_redis():
    """Lazy Redis client for quota management."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            settings = get_settings()
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning("redis_unavailable_for_quota", error=str(e))
            _redis_client = None
    return _redis_client


class QuotaExceeded(Exception):
    """Raised when a quota limit is exceeded."""

    def __init__(self, resource: str, limit: int, window: int, remaining: int):
        self.resource = resource
        self.limit = limit
        self.window = window
        self.remaining = remaining
        super().__init__(f"Quota exceeded for {resource}: {limit}/{window}s")


class QuotaService:
    """Manage per-user / per-tenant resource quotas using Redis sliding window counters."""

    def __init__(self):
        self._redis = _get_redis()

    def check_quota(
        self,
        user_id: str,
        resource: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, int]:
        """
        Check if user is within quota for a resource.

        Args:
            user_id: User identifier
            resource: Resource name (e.g., "document_upload", "chat")
            limit: Maximum requests allowed in the window
            window: Window size in seconds

        Returns:
            Tuple of (allowed: bool, remaining: int)
            If Redis is unavailable, allows by default.
        """
        if self._redis is None:
            return True, limit

        key = f"quota:{user_id}:{resource}"
        try:
            current = self._redis.get(key)

            if current is None:
                self._redis.setex(key, window, 1)
                return True, limit - 1

            count = int(current)
            if count >= limit:
                ttl = self._redis.ttl(key)
                return False, 0

            self._redis.incr(key)
            return True, limit - count - 1

        except Exception as e:
            logger.warning("quota_check_failed", error=str(e))
            return True, limit

    def get_quota_status(
        self,
        user_id: str,
        resource: str,
        limit: int,
    ) -> dict:
        """Get current quota status without consuming a request."""
        if self._redis is None:
            return {"remaining": limit, "used": 0, "limit": limit, "available": True}

        key = f"quota:{user_id}:{resource}"
        try:
            current = self._redis.get(key)
            used = int(current) if current else 0
            return {
                "remaining": max(0, limit - used),
                "used": used,
                "limit": limit,
                "available": used < limit,
            }
        except Exception:
            return {"remaining": limit, "used": 0, "limit": limit, "available": True}

    def reset_quota(self, user_id: str, resource: str) -> None:
        """Reset quota for a user/resource."""
        if self._redis is None:
            return

        key = f"quota:{user_id}:{resource}"
        try:
            self._redis.delete(key)
            logger.info("quota_reset", user_id=user_id, resource=resource)
        except Exception as e:
            logger.warning("quota_reset_failed", error=str(e))


# Pre-defined quota rules
QUOTA_RULES = {
    "document_upload": {"limit": 30, "window": 60},       # 30 uploads/minute
    "chat": {"limit": 60, "window": 60},                   # 60 chats/minute
    "reparse": {"limit": 10, "window": 60},                # 10 reparses/minute
    "reload": {"limit": 5, "window": 60},                 # 5 reloads/minute
    "auth_login": {"limit": 10, "window": 60},            # 10 logins/minute
    "auth_register": {"limit": 5, "window": 3600},        # 5 registrations/hour
}

# Global singleton
quota_service = QuotaService()
