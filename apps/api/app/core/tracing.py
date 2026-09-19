"""
TRUSTRAG — Distributed Tracing and Request Telemetry.

Provides OpenTelemetry / LangSmith instrumentation setup and request lifecycle
tracing middleware for observability across all API and agent workloads.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response

from app.core.logging import get_logger

logger = get_logger(__name__)


def init_tracing() -> None:
    """
    Initialize OpenTelemetry / LangSmith tracing at application startup.
    In local offline mode, sets conservative defaults without throwing errors.
    """
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    langsmith_project = os.getenv("LANGCHAIN_PROJECT", "trustrag-api")

    if langsmith_api_key and os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project
        logger.info("LangSmith tracing enabled", project=langsmith_project)
    else:
        # Keep disabled in offline / local dev mode to prevent external network latency
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.debug("Distributed tracing running in local offline mode")


async def tracing_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """
    HTTP middleware to measure request duration, trace execution paths,
    and attach performance timing metrics to responses.
    """
    start_time = time.perf_counter()
    path = request.url.path
    method = request.method

    try:
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # Phase 10: record Prometheus-style counters (never break the request path)
        try:
            from app.core.metrics import record_http_request

            record_http_request(method, path, response.status_code, duration_ms)
        except Exception:  # noqa: S110
            pass

        # Log trace context for slower requests (> 500ms)
        if duration_ms > 500 and not path.endswith("/metrics"):
            logger.info(
                "Slow request trace recorded",
                method=method,
                path=path,
                duration_ms=duration_ms,
                status_code=response.status_code,
            )

        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            "Request failed during tracing",
            method=method,
            path=path,
            duration_ms=duration_ms,
            error=str(exc),
        )
        try:
            from app.core.metrics import record_http_request

            record_http_request(method, path, 500, duration_ms)
        except Exception:  # noqa: S110
            pass
        raise exc
