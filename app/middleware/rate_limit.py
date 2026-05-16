"""Rate limiting middleware and utilities using slowapi."""

from typing import Callable, Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, supporting X-Forwarded-For and X-Real-IP."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"


# Global limiter instance — shared across all API routers
limiter = Limiter(key_func=get_client_ip, default_limits=["60/minute"])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors with a clean JSON response."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please slow down.",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "retry_after_seconds": _parse_retry_after(exc.detail),
        },
        headers={
            "Retry-After": str(_parse_retry_after(exc.detail)),
            "X-RateLimit-Limit": str(exc.detail) if exc.detail else "unknown",
        },
    )


def _parse_retry_after(detail) -> int:
    """Parse retry-after value from slowapi detail."""
    if detail is None:
        return 60
    detail_str = str(detail)
    # Try to extract number from strings like "5 per 1 minute"
    import re
    match = re.search(r"(\d+)\s*(?:per|/)\s*(minute|second|hour|day)", detail_str)
    if match:
        count, unit = match.groups()
        multipliers = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
        return int(count) * multipliers.get(unit, 60)
    return 60
