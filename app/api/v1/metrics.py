"""Metrics endpoint for monitoring."""

import threading
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

router = APIRouter(prefix="/metrics", tags=["monitoring"])


# ---------------------------------------------------------------------------
# In-memory metrics (process-level). Thread-safe via defaultdict + locks.
# ---------------------------------------------------------------------------

_metrics_lock = threading.Lock()
_request_count: dict = defaultdict(int)
_request_count_by_status: dict = defaultdict(lambda: defaultdict(int))
_request_duration_ms: list[float] = []
_duration_lock = threading.Lock()

# Token count metrics
_token_count: int = 0
_token_count_lock = threading.Lock()

# Error count
_error_count: int = 0
_error_count_lock = threading.Lock()


class MetricsCollector:
    """Collect and expose Prometheus-format metrics."""

    @staticmethod
    def record_request(status_code: int, duration_ms: float) -> None:
        with _metrics_lock:
            _request_count["total"] += 1
            _request_count_by_status["by_status"][status_code] += 1

        with _duration_lock:
            _request_duration_ms.append(duration_ms)
            if len(_request_duration_ms) > 1000:
                _request_duration_ms = _request_duration_ms[-1000:]

    @staticmethod
    def record_token_count(count: int) -> None:
        with _token_count_lock:
            nonlocal _token_count
            _token_count += count

    @staticmethod
    def record_error() -> None:
        with _error_count_lock:
            global _error_count
            _error_count += 1

    @staticmethod
    def get_summary() -> dict:
        with _metrics_lock:
            total = _request_count["total"]
            by_status = dict(_request_count_by_status["by_status"])

        with _duration_lock:
            durations = list(_request_duration_ms)
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            max_duration = max(durations) if durations else 0.0
            p95_duration = sorted(durations)[int(len(durations) * 0.95)] if durations else 0.0

        with _token_count_lock:
            tokens = _token_count

        with _error_count_lock:
            errors = _error_count

        return {
            "requests": {
                "total": total,
                "by_status": by_status,
            },
            "duration_ms": {
                "avg": round(avg_duration, 2),
                "max": round(max_duration, 2),
                "p95": round(p95_duration, 2),
            },
            "tokens_total": tokens,
            "errors_total": errors,
        }


collector = MetricsCollector()


@router.get("", response_class=Response)
async def get_metrics():
    """Return current metrics in Prometheus text format."""
    summary = collector.get_summary()

    lines = [
        "# HELP smartrag_http_requests_total Total HTTP requests",
        "# TYPE smartrag_http_requests_total counter",
        f'smartrag_http_requests_total {summary["requests"]["total"]}',
    ]

    for status, count in sorted(summary["requests"]["by_status"].items()):
        lines.append(f'smartrag_http_requests_total{{status="{status}"}} {count}')

    lines += [
        "",
        "# HELP smartrag_http_request_duration_ms_avg Average HTTP request duration in ms",
        "# TYPE smartrag_http_request_duration_ms_avg gauge",
        f'smartrag_http_request_duration_ms_avg {summary["duration_ms"]["avg"]}',
        "",
        "# HELP smartrag_http_request_duration_ms_p95 P95 HTTP request duration in ms",
        "# TYPE smartrag_http_request_duration_ms_p95 gauge",
        f'smartrag_http_request_duration_ms_p95 {summary["duration_ms"]["p95"]}',
        "",
        "# HELP smartrag_tokens_total Total tokens processed",
        "# TYPE smartrag_tokens_total counter",
        f'smartrag_tokens_total {summary["tokens_total"]}',
        "",
        "# HELP smartrag_errors_total Total errors",
        "# TYPE smartrag_errors_total counter",
        f'smartrag_errors_total {summary["errors_total"]}',
        "",
    ]

    return Response(content="\n".join(lines), media_type="text/plain")


@router.get("/summary")
async def get_metrics_summary():
    """Return metrics as JSON for programmatic consumption."""
    return collector.get_summary()


@router.post("/reset")
async def reset_metrics():
    """Reset all in-memory metrics (use with caution in production)."""
    global _request_count, _request_count_by_status, _request_duration_ms, _token_count, _error_count

    with _metrics_lock:
        _request_count.clear()
        _request_count_by_status.clear()

    with _duration_lock:
        _request_duration_ms.clear()

    with _token_count_lock:
        _token_count = 0

    with _error_count_lock:
        _error_count = 0

    return {"status": "reset"}
