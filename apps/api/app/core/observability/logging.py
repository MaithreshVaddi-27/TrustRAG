"""
TRUSTRAG — structured JSON logging.

Uses structlog to emit machine-parseable JSON logs.
All application code must use get_logger(__name__) — never bare print().
Sensitive values (tokens, passwords, API keys) must never be logged.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config.settings import get_settings

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

# ─── Value patterns for secrets embedded in free text ─────────────────────────
# Key-name scrubbing alone is not enough. Vendor SDKs and pydantic embed the
# offending value inside the *message*: a failed ChatGoogleGenerativeAI
# construction yields "... input_value=<the api key> ...", which then reaches
# logger.error(..., error=str(exc)). That is a log-side credential leak
# (audit B-17). These patterns catch the value wherever it appears.
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # Gemini API key
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),  # OpenAI-style key
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"),  # Authorization header echo
    re.compile(r"hf_[A-Za-z0-9]{20,}"),  # HuggingFace token
)

_REDACTED = "[REDACTED]"


def scrub_secret_values(text: str) -> str:
    """Replace anything matching a known credential shape inside free text.

    Used by the structlog processor and safe to call directly on an exception
    string before it is logged.
    """
    if not text:
        return text
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub(_REDACTED, text)
    return text


def _scrub_sensitive(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Structlog processor: redact sensitive keys AND secret-shaped values."""
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS):
            event_dict[key] = _REDACTED
            continue
        value = event_dict[key]
        # Scrub long strings too: exception text and message fields are where a
        # vendor SDK most often echoes the credential back at us.
        if isinstance(value, str):
            event_dict[key] = scrub_secret_values(value)
        elif isinstance(value, dict):
            scrubbed = {}
            for k, v in value.items():
                if any(s in str(k).lower() for s in _SENSITIVE_KEYS):
                    scrubbed[k] = _REDACTED
                elif isinstance(v, str):
                    scrubbed[k] = scrub_secret_values(v)
                else:
                    scrubbed[k] = v
            event_dict[key] = scrubbed
        elif isinstance(value, list):
            event_dict[key] = [scrub_secret_values(v) if isinstance(v, str) else v for v in value]
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
