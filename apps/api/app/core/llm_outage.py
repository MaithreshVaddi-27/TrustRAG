"""
TRUSTRAG — LLM provider-outage classification.

A revoked API key, an exhausted quota, or a provider 5xx is an *infrastructure
outage*, not a finding about the evidence. Before this module, a dead key fell
through `generation_node`'s generic `except Exception`, was converted to
`verdict_status=FAIL`, and drove up to three more recovery rounds against the
live API before terminating as `abstained` — telling the user the knowledge base
lacked supporting evidence when the real cause was a dead credential
(audit B-5).

`classify_llm_exception` maps vendor SDK and transport failures onto the typed
`LLMUnavailableError` so the graph can short-circuit with a terminal
`LLM_OUTAGE` diagnosis, mirroring the `RETRIEVAL_OUTAGE` fast path.

Deliberately conservative: an unrecognised exception returns `None` so the
caller keeps its existing behaviour. A misclassification would be worse than
the status quo — it would turn a recoverable model error into a hard abort.
"""

from __future__ import annotations

import socket

import httpx

from app.core.exceptions import LLMUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Transport-level failures that mean "the provider could not be reached",
# independent of credentials. Matched by exception type, not message.
_TRANSPORT_ERRORS: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
    socket.timeout,
    ConnectionError,
)

# Auth/credential failures. Checked before the generic status-code path because
# they need a different user-facing remedy (fix the key) than an outage
# (retry later).
_CREDENTIAL_MARKERS = (
    "api key not valid",
    "api_key_invalid",
    "unauthenticated",
    "unauthorized",
    "permission denied",
    # Lowercasing strips separators, so google.api_core's `PermissionDenied`
    # arrives as "permissiondenied" — match the compact forms too.
    "permissiondenied",
    "invalid authentication",
    "invalidargument",
    "invalid api key",
    "expired token",
    "credential",
)

_QUOTA_MARKERS = (
    "resource_exhausted",
    "resourceexhausted",
    "quota",
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "overloaded",
    "overloaded_error",
    "capacity",
    "billing",
)

_SERVER_MARKERS = (
    "internal error",
    "internalservererror",
    "service unavailable",
    "serviceunavailable",
    "bad gateway",
    "gateway timeout",
    "overloaded_error",
    "deadline exceeded",
    "deadlineexceeded",
    "unavailable",
    "503",
    "500",
)


def _status_code_of(exc: BaseException) -> int | None:
    """Best-effort HTTP status from a vendor SDK or transport exception.

    Handles google.api_core (`.code`), openai (`.status_code`), and anything
    exposing a `.response` (aiohttp, requests).
    """
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, bool):  # bool is an int subclass; never a status
            continue
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _text_of(exc: BaseException) -> str:
    """Lowercased message text for marker matching."""
    try:
        return f"{type(exc).__name__}: {exc}".lower()
    except Exception:  # pragma: no cover - defensive
        return type(exc).__name__.lower()


def classify_llm_exception(exc: BaseException, *, context: str = "") -> LLMUnavailableError | None:
    """Return an LLMUnavailableError for provider-outage failures, else None.

    Args:
        exc: The exception raised by an LLM call or client construction.
        context: Optional node/phase label included in the message.

    Returns:
        LLMUnavailableError when the failure is a credential, quota, server, or
        transport problem. None for anything else — including ordinary parsing
        errors and non-LLM failures — so the caller can fall through to its
        existing handling.
    """
    if isinstance(exc, LLMUnavailableError):
        return exc  # already classified upstream (e.g. by probe_cloud_llm)
    if isinstance(exc, (httpx.HTTPStatusError,)):
        # An explicit HTTP error response is a provider-side problem.
        pass
    elif isinstance(exc, _TRANSPORT_ERRORS):
        where = f" during {context}" if context else ""
        return LLMUnavailableError(
            f"Could not reach the LLM provider{where}. The endpoint may be down, "
            "firewalled, or the base URL may be wrong."
        )

    status = _status_code_of(exc)
    text = _text_of(exc)
    where = f" during {context}" if context else ""

    if status in (401, 403) or any(m in text for m in _CREDENTIAL_MARKERS):
        return LLMUnavailableError(
            f"The LLM provider rejected the request{where} (HTTP {status or 'n/a'}). "
            "The API key is missing, invalid, revoked, or not permitted for this "
            "model. Check the provider's key and its model allowlist."
        )

    if status == 429 or any(m in text for m in _QUOTA_MARKERS):
        return LLMUnavailableError(
            f"The LLM provider is rate-limited or out of quota{where} "
            f"(HTTP {status or 'n/a'}). Wait a few minutes or switch provider."
        )

    if (status is not None and 500 <= status < 600) or any(m in text for m in _SERVER_MARKERS):
        return LLMUnavailableError(
            f"The LLM provider returned a server error{where} "
            f"(HTTP {status or 'n/a'}). This is usually transient — retry shortly."
        )

    return None
