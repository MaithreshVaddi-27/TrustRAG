"""
TRUSTRAG — Local LLM provider: health & status checks.

Probe functions for Ollama, llama.cpp, and MLX servers. Each returns a
dict with connection status, discovered models, and a default model id.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from app.config import get_model_config
from app.config.settings import (
    _DEFAULT_LLAMACPP_BASE_URL,
    _DEFAULT_MLX_BASE_URL,
    _DEFAULT_OLLAMA_BASE_URL,
)
from app.observability.logging import get_logger
from app.security.exceptions import LLMUnavailableError
from app.llm.providers.base import _shared_http_client
from app.llm.providers.capabilities import _is_embedding_model_name
from app.llm.providers.discovery import (
    discover_llamacpp_cache_models,
    discover_mlx_cache_models,
    merge_discovered_llms,
)

logger = get_logger(__name__)

__all__ = [
    "_classify_cloud_probe_error",
    "_record_probe_success",
    "_status_code_of",
    "check_llamacpp_status",
    "check_mlx_status",
    "check_ollama_status",
    "probe_cloud_llm",
]


def _status_code_of(exc: Exception) -> int | None:
    """Extract HTTP status code from an exception, if any."""
    return getattr(exc, "status_code", None)


def _classify_cloud_probe_error(exc: Exception, norm: str, model: str, hint: str) -> str:
    """Classify a cloud probe error into a user-visible message."""
    status = _status_code_of(exc)
    if status in (401, 403):
        return f"Cloud LLM '{norm}' model '{model}' rejected credentials (HTTP {status}). {hint}"
    if status == 404:
        return f"Cloud LLM '{norm}' model '{model}' not found (HTTP 404). {hint}"
    if status and status >= 500:
        return f"Cloud LLM '{norm}' provider error (HTTP {status}). {hint}"
    return f"Cloud LLM '{norm}' model '{model}' probe failed: {exc}. {hint}"


def _record_probe_success(norm: str, model: str) -> None:
    """Record a successful provider probe."""
    logger.debug("Cloud LLM probe succeeded", provider=norm, model=model)


async def _fetch_json_with_retry(endpoint: str) -> httpx.Response:
    """Fetch JSON from an endpoint with one retry."""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.0)) as client:
                res = await client.get(endpoint)
            return res
        except (httpx.ConnectError, httpx.TimeoutException):
            if attempt == 0:
                await asyncio.sleep(0.5)
            raise
    raise RuntimeError("unreachable")


async def check_ollama_status(
    base_url: str = _DEFAULT_OLLAMA_BASE_URL,
) -> dict[str, Any]:
    """Probe Ollama server status and discover installed models."""
    from app.llm.local_llm import discover_ollama_cli_models

    cli_models = [m for m in await discover_ollama_cli_models() if not _is_embedding_model_name(m)]

    try:
        async with _shared_http_client(base_url, 10.0) as client:
            # Retry once on transient timeout, matching legacy _fetch_json_with_retry behavior
            for attempt in range(2):
                try:
                    res = await client.get(f"{base_url.rstrip('/')}/api/tags")
                    break
                except (httpx.ConnectError, httpx.TimeoutException):
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                    else:
                        raise
        # Use status_code check for compatibility with test mocks (which may not have is_success)
        if getattr(res, "status_code", 500) < 400:
            data = res.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            api_models = [m for m in models if m]
            if api_models:
                cli_models.extend(m for m in api_models if not _is_embedding_model_name(m))
            merge_discovered_llms("ollama", cli_models, replace=True)
            return {
                "connected": True,
                "provider": "ollama",
                "base_url": base_url,
                "models": cli_models,
                "default_model": cli_models[0] if cli_models else "",
            }
    except Exception as exc:
        logger.debug("Ollama status check failed", error=str(exc))

    if cli_models:
        merge_discovered_llms("ollama", cli_models, replace=True)
        return {
            "connected": True,
            "provider": "ollama",
            "base_url": base_url,
            "models": cli_models,
            "default_model": cli_models[0] if cli_models else "",
        }

    return {
        "connected": False,
        "provider": "ollama",
        "base_url": base_url,
        "models": [],
        "default_model": "",
    }


async def check_llamacpp_status(
    base_url: str = _DEFAULT_LLAMACPP_BASE_URL,
) -> dict[str, Any]:
    """Probe llama.cpp server status and discover cached models."""
    cache_models = await discover_llamacpp_cache_models()
    try:
        api_models: list[str] = []
        connected = False
        try:
            async with _shared_http_client(base_url, 10.0) as client:
                res = await client.get(f"{base_url.rstrip('/')}/v1/models")
            if res.status_code == 200:
                connected = True
                data = res.json()
                api_models = [m.get("id") for m in data.get("data", []) if m.get("id")]
        except (httpx.ConnectError, httpx.TimeoutException):
            pass

        api_llms = [m for m in api_models if m]
        if connected and api_llms:
            combined = list(dict.fromkeys(api_llms))
        else:
            quantified_bases = {m.split(":")[0] for m in api_models + cache_models if ":" in m}
            hf_llms = [m for m in cache_models if (":" in m or m not in quantified_bases)]
            combined = list(dict.fromkeys(api_llms + hf_llms))

        try:
            _preferred = get_model_config().llm_model_for("llama_cpp")
        except Exception:
            _preferred = "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M"
        default_model = _preferred if _preferred in combined else (combined[0] if combined else "")

        merge_discovered_llms("llama_cpp", combined, replace=True)

        return {
            "connected": connected,
            "provider": "llama_cpp",
            "base_url": base_url,
            "models": combined,
            "cache_models": cache_models,
            "default_model": default_model,
        }
    except Exception:
        logger.debug("llama.cpp status check failed", exc_info=True)
        return {
            "connected": False,
            "provider": "llama_cpp",
            "base_url": base_url,
            "models": [],
            "cache_models": cache_models,
            "default_model": "",
        }


async def check_mlx_status(
    base_url: str = _DEFAULT_MLX_BASE_URL, max_ports: int = 5
) -> dict[str, Any]:
    """Discover MLX status and generative models by checking multiple server ports."""
    cache_models = discover_mlx_cache_models()
    all_api_models: list[str] = []
    any_connected = False

    base_port_match = re.search(r":(\d+)", base_url)
    start_port = int(base_port_match.group(1)) if base_port_match else 8080

    for port_offset in range(max_ports):
        port = start_port + port_offset
        endpoint = f"http://127.0.0.1:{port}/v1/models"

        try:
            res = await _fetch_json_with_retry(endpoint)
            if res.status_code == 200:
                any_connected = True
                data = res.json()
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                all_api_models.extend(models)
        except (httpx.ConnectError, httpx.TimeoutException):
            continue

    api_llms = [m for m in all_api_models if m]
    if any_connected and api_llms:
        combined = list(dict.fromkeys(api_llms))
    else:
        combined = list(dict.fromkeys(api_llms + cache_models))

    try:
        _preferred_mlx = get_model_config().llm_model_for("mlx")
    except Exception:
        _preferred_mlx = "mlx-community/Llama-3.2-1B-Instruct-4bit"
    default_model = (
        _preferred_mlx if _preferred_mlx in combined else (combined[0] if combined else "")
    )

    merge_discovered_llms("mlx", combined, replace=True)

    return {
        "connected": any_connected,
        "provider": "mlx",
        "base_url": base_url,
        "models": combined,
        "cache_models": cache_models,
        "default_model": default_model,
    }


async def probe_cloud_llm(
    *,
    norm: str,
    model: str,
    base_url: str,
    timeout: float,
    hint: str = "",
) -> None:
    """Probe a cloud LLM provider to confirm it is reachable and responsive."""
    try:
        from app.llm.local_llm import _local_chat_models

        llm = _local_chat_models[norm]
    except Exception:
        pass

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        res = await client.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with the word OK."}],
                "max_tokens": 5,
            },
        )
    if res.status_code == 404:
        raise LLMUnavailableError(
            f"Cloud LLM '{norm}' model '{model}' not found (HTTP 404). {hint}"
        )
    res.raise_for_status()
    _record_probe_success(norm, model)
