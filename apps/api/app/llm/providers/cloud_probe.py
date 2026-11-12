"""
TRUSTRAG — Cloud LLM provider probes.

A cloud probe answers one question: "can this provider actually serve the
requested model right now?". Every cloud provider has its own request
contract, so each one owns its probe here instead of sharing a single
OpenAI-shaped POST that only some providers accept.

- ``gemini`` uses the native Gemini REST contract
  (``POST {base}/v1beta/models/{model}:generateContent`` with an
  ``x-goog-api-key`` header), which is the same contract
  ``langchain-google-genai`` speaks at runtime.
- Anything else falls back to the OpenAI-compatible
  ``POST {base}/v1/chat/completions`` contract.

The public entry point ``probe_cloud_llm`` keeps the keyword-only signature
it has always had, so existing call sites and tests that patch
``app.llm.local_llm.probe_cloud_llm`` keep working.
"""

from __future__ import annotations

import httpx

from app.observability.logging import get_logger
from app.security.exceptions import LLMUnavailableError

logger = get_logger(__name__)

__all__ = [
    "CLOUD_PROBE_TIMEOUT_SECONDS",
    "GEMINI_BASE_URL",
    "_classify_cloud_probe_error",
    "_record_probe_success",
    "_status_code_of",
    "probe_cloud_llm",
]

# Gemini's public REST host. There is no user-configurable base URL: the
# Gemini API is reached at one well-known endpoint.
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"

# API version segment for the native Gemini REST contract.
GEMINI_API_VERSION = "v1beta"

# A probe is a liveness check, not an inference run. Keep it short so a dead
# provider fails fast instead of holding the request open for the full
# generation timeout.
CLOUD_PROBE_TIMEOUT_SECONDS = 10.0

# Prompt and token budget for the probe call: one word is enough to prove the
# endpoint works, and the ceiling keeps the probe cheap.
_PROBE_PROMPT = "Reply with the word OK."
_PROBE_MAX_OUTPUT_TOKENS = 8


def _status_code_of(exc: Exception) -> int | None:
    """Extract an HTTP status code from an exception, if any.

    ``httpx.HTTPStatusError`` carries the code on ``exc.response``, not on the
    exception itself, so both shapes are checked.
    """
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _classify_cloud_probe_error(exc: Exception, norm: str, model: str, hint: str) -> str:
    """Classify a cloud probe error into a user-visible message."""
    status = _status_code_of(exc)
    if status in (401, 403):
        return f"Cloud LLM '{norm}' model '{model}' rejected credentials (HTTP {status}). {hint}"
    if status == 404:
        return f"Cloud LLM '{norm}' model '{model}' not found (HTTP 404). {hint}"
    if status == 429:
        return f"Cloud LLM '{norm}' model '{model}' rate limited (HTTP 429). {hint}"
    if status and status >= 500:
        return f"Cloud LLM '{norm}' provider error (HTTP {status}). {hint}"
    return f"Cloud LLM '{norm}' model '{model}' probe failed: {exc}. {hint}"


def _record_probe_success(norm: str, model: str) -> None:
    """Record a successful provider probe."""
    logger.debug("Cloud LLM probe succeeded", provider=norm, model=model)


def _gemini_api_key() -> str:
    """The configured Gemini credential, or "" when none is set."""
    try:
        from app.config.settings import get_settings

        return (get_settings().gemini_api_key or "").strip()
    except Exception:  # pragma: no cover - settings failure must not mask the probe
        logger.debug("Could not read the Gemini API key from settings")
        return ""


def _raise_for_status(res: httpx.Response, norm: str, model: str, hint: str) -> None:
    """Translate a non-2xx probe response into a typed, user-facing error."""
    try:
        res.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise LLMUnavailableError(_classify_cloud_probe_error(exc, norm, model, hint)) from exc


async def _probe_gemini(*, norm: str, model: str, base_url: str, timeout: float, hint: str) -> None:
    """Probe Gemini using its native ``generateContent`` contract.

    Mirrors what ``langchain-google-genai`` sends at runtime: the model id in
    the URL path, the credential in the ``x-goog-api-key`` header, and the
    prompt in ``contents[].parts[].text``.
    """
    api_key = _gemini_api_key()
    if not api_key:
        raise LLMUnavailableError(
            f"Cloud LLM '{norm}' model '{model}' cannot be probed: GEMINI_API_KEY "
            f"is not configured. {hint}"
        )

    url = f"{base_url.rstrip('/')}/{GEMINI_API_VERSION}/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": _PROBE_PROMPT}]}],
        "generationConfig": {"maxOutputTokens": _PROBE_MAX_OUTPUT_TOKENS},
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        try:
            res = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Cloud LLM '{norm}' model '{model}' probe failed: {exc}. {hint}"
            ) from exc

    if res.status_code >= 400:
        _raise_for_status(res, norm, model, hint)
    _record_probe_success(norm, model)


async def _probe_openai_compatible(
    *, norm: str, model: str, base_url: str, timeout: float, hint: str
) -> None:
    """Probe an OpenAI-compatible cloud endpoint (``/v1/chat/completions``)."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        try:
            res = await client.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": _PROBE_PROMPT}],
                    "max_tokens": _PROBE_MAX_OUTPUT_TOKENS,
                },
            )
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Cloud LLM '{norm}' model '{model}' probe failed: {exc}. {hint}"
            ) from exc

    if res.status_code >= 400:
        _raise_for_status(res, norm, model, hint)
    _record_probe_success(norm, model)


async def probe_cloud_llm(
    *,
    norm: str,
    model: str,
    base_url: str,
    timeout: float,
    hint: str = "",
) -> None:
    """Probe a cloud LLM provider to confirm it is reachable and responsive.

    Raises ``LLMUnavailableError`` (HTTP 503) when the provider cannot serve
    the requested model — bad credentials, unknown model, rate limiting, or a
    provider outage. The message never contains the credential.
    """
    if norm == "gemini":
        await _probe_gemini(norm=norm, model=model, base_url=base_url, timeout=timeout, hint=hint)
        return
    await _probe_openai_compatible(
        norm=norm, model=model, base_url=base_url, timeout=timeout, hint=hint
    )
