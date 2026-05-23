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

_rag_metrics_lock = threading.Lock()
_rag_latencies_ms: dict = defaultdict(list)
_rag_empty_retrieval_count: int = 0
_rag_top_scores: list[float] = []

_agent_metrics_lock = threading.Lock()
_agent_tasks_total: dict = defaultdict(int)
_agent_tool_calls_total: dict = defaultdict(int)
_agent_tool_errors_total: dict = defaultdict(int)
_agent_step_latencies_ms: list[float] = []
_agent_approval_required_total: int = 0
_agent_tokens_total: int = 0
_agent_estimated_cost_usd_total: float = 0.0


class MetricsCollector:
    """Collect and expose Prometheus-format metrics."""

    @staticmethod
    def record_request(status_code: int, duration_ms: float) -> None:
        global _request_duration_ms
        with _metrics_lock:
            _request_count["total"] += 1
            _request_count_by_status["by_status"][status_code] += 1

        with _duration_lock:
            _request_duration_ms.append(duration_ms)
            if len(_request_duration_ms) > 1000:
                _request_duration_ms = _request_duration_ms[-1000:]

    @staticmethod
    def record_token_count(count: int) -> None:
        global _token_count
        with _token_count_lock:
            _token_count += count

    @staticmethod
    def record_error() -> None:
        with _error_count_lock:
            global _error_count
            _error_count += 1

    @staticmethod
    def record_rag_latency(stage: str, duration_ms: float) -> None:
        with _rag_metrics_lock:
            values = _rag_latencies_ms[stage]
            values.append(duration_ms)
            if len(values) > 1000:
                _rag_latencies_ms[stage] = values[-1000:]

    @staticmethod
    def record_retrieval_result(scores: list[float]) -> None:
        global _rag_empty_retrieval_count
        with _rag_metrics_lock:
            if not scores:
                _rag_empty_retrieval_count += 1
                return
            _rag_top_scores.extend(scores[:5])
            if len(_rag_top_scores) > 1000:
                del _rag_top_scores[:-1000]

    @staticmethod
    def record_agent_task(status: str) -> None:
        with _agent_metrics_lock:
            _agent_tasks_total[status] += 1

    @staticmethod
    def record_agent_tool_call(tool_name: str, ok: bool, latency_ms: float) -> None:
        with _agent_metrics_lock:
            _agent_tool_calls_total[tool_name] += 1
            if not ok:
                _agent_tool_errors_total[tool_name] += 1
            _agent_step_latencies_ms.append(latency_ms)
            if len(_agent_step_latencies_ms) > 1000:
                del _agent_step_latencies_ms[:-1000]

    @staticmethod
    def record_agent_step_latency(latency_ms: float) -> None:
        with _agent_metrics_lock:
            _agent_step_latencies_ms.append(latency_ms)
            if len(_agent_step_latencies_ms) > 1000:
                del _agent_step_latencies_ms[:-1000]

    @staticmethod
    def record_agent_approval_required() -> None:
        global _agent_approval_required_total
        with _agent_metrics_lock:
            _agent_approval_required_total += 1

    @staticmethod
    def record_agent_token_usage(tokens: int, estimated_cost_usd: float) -> None:
        global _agent_tokens_total, _agent_estimated_cost_usd_total
        with _agent_metrics_lock:
            _agent_tokens_total += tokens
            _agent_estimated_cost_usd_total += estimated_cost_usd

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

        with _rag_metrics_lock:
            rag_latencies = {
                stage: {
                    "avg": round(sum(values) / len(values), 2) if values else 0.0,
                    "p95": round(sorted(values)[int(len(values) * 0.95)], 2) if values else 0.0,
                }
                for stage, values in _rag_latencies_ms.items()
            }
            top_scores = list(_rag_top_scores)
            avg_top_score = sum(top_scores) / len(top_scores) if top_scores else 0.0
            empty_retrieval_count = _rag_empty_retrieval_count

        with _agent_metrics_lock:
            agent_latencies = list(_agent_step_latencies_ms)
            agent_avg = sum(agent_latencies) / len(agent_latencies) if agent_latencies else 0.0
            agent_p95 = sorted(agent_latencies)[int(len(agent_latencies) * 0.95)] if agent_latencies else 0.0
            agent_tasks = dict(_agent_tasks_total)
            agent_tool_calls = dict(_agent_tool_calls_total)
            agent_tool_errors = dict(_agent_tool_errors_total)
            approval_total = _agent_approval_required_total
            agent_tokens = _agent_tokens_total
            agent_cost = _agent_estimated_cost_usd_total

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
            "rag": {
                "latencies_ms": rag_latencies,
                "empty_retrieval_total": empty_retrieval_count,
                "top_score_avg": round(avg_top_score, 4),
            },
            "agent": {
                "tasks_total": agent_tasks,
                "tool_calls_total": agent_tool_calls,
                "tool_errors_total": agent_tool_errors,
                "step_latency_ms": {
                    "avg": round(agent_avg, 2),
                    "p95": round(agent_p95, 2),
                },
                "approval_required_total": approval_total,
                "tokens_total": agent_tokens,
                "estimated_cost_usd_total": round(agent_cost, 6),
            },
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
        "# HELP smartrag_rag_empty_retrieval_total RAG retrievals with no usable results",
        "# TYPE smartrag_rag_empty_retrieval_total counter",
        f'smartrag_rag_empty_retrieval_total {summary["rag"]["empty_retrieval_total"]}',
        "",
        "# HELP smartrag_rag_top_score_avg Average score across recent top retrieval results",
        "# TYPE smartrag_rag_top_score_avg gauge",
        f'smartrag_rag_top_score_avg {summary["rag"]["top_score_avg"]}',
        "",
    ]

    for stage, values in sorted(summary["rag"]["latencies_ms"].items()):
        lines += [
            f"# HELP smartrag_rag_{stage}_latency_ms_avg Average RAG {stage} latency in ms",
            f"# TYPE smartrag_rag_{stage}_latency_ms_avg gauge",
            f'smartrag_rag_{stage}_latency_ms_avg {values["avg"]}',
            f"# HELP smartrag_rag_{stage}_latency_ms_p95 P95 RAG {stage} latency in ms",
            f"# TYPE smartrag_rag_{stage}_latency_ms_p95 gauge",
            f'smartrag_rag_{stage}_latency_ms_p95 {values["p95"]}',
            "",
        ]

    lines += [
        "# HELP smartrag_agent_approval_required_total Agent tasks requiring human approval",
        "# TYPE smartrag_agent_approval_required_total counter",
        f'smartrag_agent_approval_required_total {summary["agent"]["approval_required_total"]}',
        "",
        "# HELP smartrag_agent_tokens_total Estimated total tokens used by agent tool calls",
        "# TYPE smartrag_agent_tokens_total counter",
        f'smartrag_agent_tokens_total {summary["agent"]["tokens_total"]}',
        "",
        "# HELP smartrag_agent_estimated_cost_usd_total Estimated total agent cost in USD",
        "# TYPE smartrag_agent_estimated_cost_usd_total counter",
        f'smartrag_agent_estimated_cost_usd_total {summary["agent"]["estimated_cost_usd_total"]}',
        "",
        "# HELP smartrag_agent_step_latency_ms_avg Average agent step latency in ms",
        "# TYPE smartrag_agent_step_latency_ms_avg gauge",
        f'smartrag_agent_step_latency_ms_avg {summary["agent"]["step_latency_ms"]["avg"]}',
        "",
        "# HELP smartrag_agent_step_latency_ms_p95 P95 agent step latency in ms",
        "# TYPE smartrag_agent_step_latency_ms_p95 gauge",
        f'smartrag_agent_step_latency_ms_p95 {summary["agent"]["step_latency_ms"]["p95"]}',
        "",
    ]

    for status, count in sorted(summary["agent"]["tasks_total"].items()):
        lines.append(f'smartrag_agent_tasks_total{{status="{status}"}} {count}')
    for tool, count in sorted(summary["agent"]["tool_calls_total"].items()):
        lines.append(f'smartrag_agent_tool_calls_total{{tool="{tool}"}} {count}')
    for tool, count in sorted(summary["agent"]["tool_errors_total"].items()):
        lines.append(f'smartrag_agent_tool_error_total{{tool="{tool}"}} {count}')

    return Response(content="\n".join(lines), media_type="text/plain")


@router.get("/summary")
async def get_metrics_summary():
    """Return metrics as JSON for programmatic consumption."""
    return collector.get_summary()


@router.post("/reset")
async def reset_metrics():
    """Reset all in-memory metrics (use with caution in production)."""
    global _request_count, _request_count_by_status, _request_duration_ms, _token_count, _error_count, _rag_empty_retrieval_count, _agent_approval_required_total

    with _metrics_lock:
        _request_count.clear()
        _request_count_by_status.clear()

    with _duration_lock:
        _request_duration_ms.clear()

    with _token_count_lock:
        _token_count = 0

    with _error_count_lock:
        _error_count = 0

    with _rag_metrics_lock:
        _rag_latencies_ms.clear()
        _rag_top_scores.clear()
        _rag_empty_retrieval_count = 0

    with _agent_metrics_lock:
        _agent_tasks_total.clear()
        _agent_tool_calls_total.clear()
        _agent_tool_errors_total.clear()
        _agent_step_latencies_ms.clear()
        _agent_approval_required_total = 0

    return {"status": "reset"}
