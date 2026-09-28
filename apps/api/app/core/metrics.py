"""
TRUSTRAG — Phase 10: lightweight Prometheus-style metrics (no new dependencies).

In-memory counters + latency accumulators, rendered in Prometheus text
exposition format at GET /metrics. Thread-safe via a single lock.
Keeps the torch-free Docker runtime dependency-free (no prometheus_client).

Tracked:
  - http_requests_total{method,path,status}
  - http_request_duration_ms_sum / _count (avg computable; P50/P95 come from k6/eval, not here)
  - analyses_created_total
  - analyses_completed_total{status}
  - recovery_attempts_total{strategy}
  - verification_claims_total{verdict}
  - tokens_estimated_total
  - budget_rejections_total{reason}
"""

from __future__ import annotations

import threading
import time

_LOCK = threading.Lock()

_http_requests: dict[tuple[str, str, str], int] = {}
_http_duration_ms_sum: dict[tuple[str, str], float] = {}
_http_duration_ms_count: dict[tuple[str, str], int] = {}
_analyses_created_total = 0
_analyses_completed: dict[str, int] = {}
_recovery_attempts: dict[str, int] = {}
_verification_claims: dict[str, int] = {}
_tokens_estimated_total = 0
_budget_rejections: dict[str, int] = {}
_started_at = time.time()


def _norm_path(path: str) -> str:
    """Collapse high-cardinality IDs to templates so series stay bounded."""
    import re

    p = re.sub(r"/[0-9a-fA-F]{24}(?=/|$)", "/:id", path)
    p = re.sub(r"/\d+(?=/|$)", "/:id", p)
    return p or "/"


def record_http_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    key = (method.upper(), _norm_path(path), str(status_code))
    pkey = (method.upper(), _norm_path(path))
    with _LOCK:
        _http_requests[key] = _http_requests.get(key, 0) + 1
        _http_duration_ms_sum[pkey] = _http_duration_ms_sum.get(pkey, 0.0) + max(0.0, duration_ms)
        _http_duration_ms_count[pkey] = _http_duration_ms_count.get(pkey, 0) + 1


def record_analysis_created() -> None:
    global _analyses_created_total
    with _LOCK:
        _analyses_created_total += 1


def record_analysis_completed(status: str) -> None:
    with _LOCK:
        _analyses_completed[status] = _analyses_completed.get(status, 0) + 1


def record_recovery_attempt(strategy: str) -> None:
    with _LOCK:
        _recovery_attempts[strategy or "none"] = _recovery_attempts.get(strategy or "none", 0) + 1


def record_verification_claims(supported: int, contradicted: int, neutral: int) -> None:
    with _LOCK:
        _verification_claims["SUPPORTED"] = _verification_claims.get("SUPPORTED", 0) + int(
            supported
        )
        _verification_claims["CONTRADICTED"] = _verification_claims.get("CONTRADICTED", 0) + int(
            contradicted
        )
        _verification_claims["NEUTRAL"] = _verification_claims.get("NEUTRAL", 0) + int(neutral)


def record_tokens_estimated(n: int) -> None:
    global _tokens_estimated_total
    with _LOCK:
        _tokens_estimated_total += max(0, int(n))


def record_budget_rejection(reason: str) -> None:
    with _LOCK:
        _budget_rejections[reason] = _budget_rejections.get(reason, 0) + 1


def estimate_tokens(text: str | None) -> int:
    """Rough pre-request token estimate (4 chars ≈ 1 token). Zero-LM-call by design."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def reset_for_tests() -> None:
    """Clear all counters (tests only)."""
    global _analyses_created_total, _tokens_estimated_total
    with _LOCK:
        _http_requests.clear()
        _http_duration_ms_sum.clear()
        _http_duration_ms_count.clear()
        _analyses_created_total = 0
        _analyses_completed.clear()
        _recovery_attempts.clear()
        _verification_claims.clear()
        _tokens_estimated_total = 0
        _budget_rejections.clear()


def snapshot() -> dict:
    with _LOCK:
        return {
            "http_requests": dict(_http_requests),
            "http_duration_ms_sum": dict(_http_duration_ms_sum),
            "http_duration_ms_count": dict(_http_duration_ms_count),
            "analyses_created_total": _analyses_created_total,
            "analyses_completed": dict(_analyses_completed),
            "recovery_attempts": dict(_recovery_attempts),
            "verification_claims": dict(_verification_claims),
            "tokens_estimated_total": _tokens_estimated_total,
            "budget_rejections": dict(_budget_rejections),
            "uptime_seconds": round(time.time() - _started_at, 1),
        }


def render_prometheus() -> str:
    """Render counters in Prometheus text exposition format."""
    snap = snapshot()
    lines: list[str] = []
    lines.append("# HELP trustrag_http_requests_total HTTP requests by method/path/status.")
    lines.append("# TYPE trustrag_http_requests_total counter")
    for (method, path, status), val in sorted(snap["http_requests"].items()):
        lines.append(
            f'trustrag_http_requests_total{{method="{method}",'
            f'path="{path}",status="{status}"}} {val}'
        )
    lines.append("# HELP trustrag_http_request_duration_ms_sum Total HTTP latency ms.")
    lines.append("# TYPE trustrag_http_request_duration_ms_sum counter")
    for (method, path), val in sorted(snap["http_duration_ms_sum"].items()):
        lines.append(
            f'trustrag_http_request_duration_ms_sum{{method="{method}",path="{path}"}} {val:.2f}'
        )
    lines.append("# HELP trustrag_http_request_duration_ms_count HTTP request count for avg.")
    lines.append("# TYPE trustrag_http_request_duration_ms_count counter")
    for (method, path), val in sorted(snap["http_duration_ms_count"].items()):
        lines.append(
            f'trustrag_http_request_duration_ms_count{{method="{method}",path="{path}"}} {val}'
        )
    lines.append("# HELP trustrag_analyses_created_total Analyses created.")
    lines.append("# TYPE trustrag_analyses_created_total counter")
    lines.append(f"trustrag_analyses_created_total {snap['analyses_created_total']}")
    lines.append("# HELP trustrag_analyses_completed_total Analyses completed by status.")
    lines.append("# TYPE trustrag_analyses_completed_total counter")
    for status, val in sorted(snap["analyses_completed"].items()):
        lines.append(f'trustrag_analyses_completed_total{{status="{status}"}} {val}')
    lines.append("# HELP trustrag_recovery_attempts_total Recovery attempts by strategy.")
    lines.append("# TYPE trustrag_recovery_attempts_total counter")
    for strategy, val in sorted(snap["recovery_attempts"].items()):
        lines.append(f'trustrag_recovery_attempts_total{{strategy="{strategy}"}} {val}')
    lines.append("# HELP trustrag_verification_claims_total Verified claims by verdict.")
    lines.append("# TYPE trustrag_verification_claims_total counter")
    for verdict, val in sorted(snap["verification_claims"].items()):
        lines.append(f'trustrag_verification_claims_total{{verdict="{verdict}"}} {val}')
    lines.append("# HELP trustrag_tokens_estimated_total Sum of pre-request token estimates.")
    lines.append("# TYPE trustrag_tokens_estimated_total counter")
    lines.append(f"trustrag_tokens_estimated_total {snap['tokens_estimated_total']}")
    lines.append("# HELP trustrag_budget_rejections_total Pre-request budget rejections by reason.")
    lines.append("# TYPE trustrag_budget_rejections_total counter")
    for reason, val in sorted(snap["budget_rejections"].items()):
        lines.append(f'trustrag_budget_rejections_total{{reason="{reason}"}} {val}')
    lines.append("# HELP trustrag_uptime_seconds Process uptime seconds.")
    lines.append("# TYPE trustrag_uptime_seconds gauge")
    lines.append(f"trustrag_uptime_seconds {snap['uptime_seconds']}")
    return "\n".join(lines) + "\n"
