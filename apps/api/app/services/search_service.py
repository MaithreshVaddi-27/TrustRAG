"""
TRUSTRAG — Web Search Grounding Service.

Provides web search grounding using Tavily AI Search.

Applies query length limits, search timeouts, and sanitization
of citation URLs returned by the search provider.
"""

from __future__ import annotations

import asyncio
import ipaddress
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Search execution timeout guard (seconds)
SEARCH_TIMEOUT_SECONDS = 8.0
MAX_QUERY_LENGTH = 500

# Hostnames that never leave the host (no DNS involved — pure string match).
_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
        "169.254.169.254",  # also caught as IP below; listed for clarity
    }
)


def _host_is_blocked(host: str) -> bool:
    host = (host or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # public DNS name: no resolution here (lightweight path)
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_reserved
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    )


def sanitize_url(raw_url: str | None) -> str:
    """Allow only valid, non-internal HTTP(S) citation URLs.

    Lightweight by design (no DNS lookups on this path): blocks private /
    loopback / reserved IP literals and metadata hostnames by string, and
    lets public DNS names through for the caller to fetch.
    """
    if not raw_url or not isinstance(raw_url, str):
        return ""

    clean = raw_url.strip()
    try:
        parsed = urlparse(clean)
        if parsed.scheme.lower() not in ("http", "https"):
            return ""

        if not parsed.netloc or " " in parsed.netloc:
            return ""
        host = parsed.hostname or ""
        if _host_is_blocked(host):
            return ""
        return clean

    except Exception:
        return ""


# ─── Search Functions ──────────────────────────────────────────────────────────


async def tavily_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Execute AI-native web search using Tavily.
    Requires TAVILY_API_KEY.
    """
    safe_query = (query or "").strip()[:MAX_QUERY_LENGTH]
    if not safe_query:
        return []

    settings = get_settings()

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)

        async def _call_tavily() -> dict[str, Any]:
            return await asyncio.to_thread(
                client.search,
                query=safe_query,
                search_depth="basic",
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
            )

        response = await asyncio.wait_for(_call_tavily(), timeout=SEARCH_TIMEOUT_SECONDS)

        results: list[dict[str, Any]] = []
        for item in response.get("results", []):
            safe_url = sanitize_url(item.get("url"))
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            results.append(
                {
                    "title": str(item.get("title") or "Untitled Web Result").strip(),
                    "url": safe_url,
                    "content": content,
                    "score": float(item.get("score", 0.8)),
                    "source": "tavily",
                }
            )

        logger.info("Tavily search complete", query=safe_query, count=len(results))
        return results

    except TimeoutError:
        logger.warning(
            "Tavily search timed out",
            timeout=SEARCH_TIMEOUT_SECONDS,
        )
        return []

    except Exception as exc:
        logger.error("Tavily search failed", error=str(exc))
        return []


async def execute_web_search(
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    return await tavily_search(query, max_results=max_results)
