"""Error tracking service using Redis."""

import json
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client = None


def _get_redis():
    """Lazy Redis client for error tracking."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            settings = get_settings()
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning("redis_unavailable_for_error_tracker", error=str(e))
            _redis_client = None
    return _redis_client


class ErrorTracker:
    """Track recent errors in Redis for debugging and alerting."""

    KEY = "smartrag:errors"

    def __init__(self, max_errors: int = 100):
        self._max_errors = max_errors

    def record(
        self,
        error_type: str,
        message: str,
        context: Optional[dict] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record an error to Redis."""
        redis_client = _get_redis()
        if redis_client is None:
            logger.warning(
                "error_recorded_without_redis",
                error_type=error_type,
                message=message,
            )
            return

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": error_type,
            "message": message,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "context": context or {},
        }
        try:
            redis_client.lpush(self.KEY, json.dumps(entry, ensure_ascii=False))
            redis_client.ltrim(self.KEY, 0, self._max_errors - 1)
        except Exception as e:
            logger.warning("failed_to_record_error_to_redis", error=str(e))

    def get_recent(self, limit: int = 10) -> list:
        """Get recent errors from Redis."""
        redis_client = _get_redis()
        if redis_client is None:
            return []

        try:
            raw = redis_client.lrange(self.KEY, 0, limit - 1)
            return [json.loads(r) for r in raw]
        except Exception as e:
            logger.warning("failed_to_get_recent_errors", error=str(e))
            return []

    def clear(self) -> None:
        """Clear error history."""
        redis_client = _get_redis()
        if redis_client is None:
            return

        try:
            redis_client.delete(self.KEY)
        except Exception as e:
            logger.warning("failed_to_clear_errors", error=str(e))


# Global singleton
error_tracker = ErrorTracker()
