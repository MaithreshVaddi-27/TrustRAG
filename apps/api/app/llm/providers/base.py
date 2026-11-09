"""
TRUSTRAG — Local LLM providers: shared infrastructure.

Base HTTP client pooling, message normalization, and concurrency guards shared
by all local LLM clients (Ollama, llama.cpp, MLX).
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import httpx
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from app.observability.logging import get_logger
from app.security.exceptions import ConfigurationError

logger = get_logger(__name__)

__all__ = [
    "_HTTP_CLIENTS",
    "_HTTP_CLIENTS_LOCK",
    "_convert_messages_to_dict",
    "_shared_http_client",
    "close_local_llm_clients",
]

# Reuse HTTP connections for the Ollama/llama.cpp request fan-out. One analysis
# can perform generation, decomposition, batch NLI, fallback NLI, and recovery;
# per-call clients previously discarded keep-alive connections every time.
_HTTP_CLIENTS: dict[tuple[str, float, int], httpx.AsyncClient] = {}
_HTTP_CLIENTS_LOCK = threading.Lock()


def _shared_http_client(base_url: str, timeout: float) -> httpx.AsyncClient:
    """Return a per-event-loop, per-endpoint pooled AsyncClient with connection limits."""
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = 0
    key = (base_url.rstrip("/"), float(timeout), loop_id)
    with _HTTP_CLIENTS_LOCK:
        client = _HTTP_CLIENTS.get(key)
        if client is None or client.is_closed:
            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0,
            )
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout, connect=10.0, pool=10.0),
                limits=limits,
                follow_redirects=True,
            )
            _HTTP_CLIENTS[key] = client
        return client


async def close_local_llm_clients() -> None:
    """Close all pooled local-LLM HTTP clients during application shutdown."""
    with _HTTP_CLIENTS_LOCK:
        clients = list(_HTTP_CLIENTS.values())
        _HTTP_CLIENTS.clear()
    if clients:
        results = await asyncio.gather(
            *(client.aclose() for client in clients), return_exceptions=True
        )
        errors = [str(result) for result in results if isinstance(result, Exception)]
        if errors:
            logger.debug("One or more local LLM clients failed to close", errors=errors)


def _convert_messages_to_dict(messages: list[Any]) -> list[dict[str, str]]:
    """Normalize LangChain message objects or tuples into OpenAI/Ollama role dicts."""
    converted: list[dict[str, str]] = []
    for m in messages:
        if isinstance(m, tuple) and len(m) == 2:
            role, content = m
            role_norm = (
                "assistant"
                if role in ("ai", "assistant")
                else ("system" if role == "system" else "user")
            )
            converted.append({"role": role_norm, "content": str(content)})
        elif isinstance(m, SystemMessage):
            converted.append({"role": "system", "content": str(m.content)})
        elif isinstance(m, AIMessage):
            converted.append({"role": "assistant", "content": str(m.content)})
        elif isinstance(m, HumanMessage):
            converted.append({"role": "user", "content": str(m.content)})
        elif isinstance(m, BaseMessage):
            role_norm = getattr(m, "role", "user")
            converted.append({"role": str(role_norm), "content": str(m.content)})
        elif isinstance(m, dict):
            converted.append(
                {
                    "role": str(m.get("role", "user")),
                    "content": str(m.get("content", "")),
                }
            )
        elif isinstance(m, str):
            converted.append({"role": "user", "content": m})
        else:
            logger.warning("Dropping unsupported message type", msg_type=type(m).__name__)
    if not converted:
        raise ConfigurationError("No valid messages to send to local LLM (empty prompt)")
    return converted
