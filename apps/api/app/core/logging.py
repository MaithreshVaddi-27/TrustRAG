"""
TRUSTRAG — structured JSON logging.

Uses structlog to emit machine-parseable JSON logs.
All application code must use get_logger(__name__) — never bare print().
Sensitive values (tokens, passwords, API keys) must never be logged.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import get_settings

# ─── Fields that must be scrubbed from log context ────────────────────────────
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "access_token",
        "api_key",
        "gemini_api_key",
        "jwt_secret",
        "authorization",
        "cookie",
        "secret",
    }
)


def _scrub_sensitive(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Structlog processor: replace sensitive values with [REDACTED]."""
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for structured JSON output.

    Call once at application startup (in main.py lifespan).
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # stdlib logging baseline
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    # Silence overly verbose libraries
    for noisy_logger in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_logger_name,
        _scrub_sensitive,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production():
        # JSON output for log aggregation (Datadog, Cloud Logging, etc.)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Human-readable in development
        renderer = structlog.dev.ConsoleRenderer(colors=True)  # type: ignore[assignment]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[renderer],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to the given module name."""
    return structlog.get_logger(name)
