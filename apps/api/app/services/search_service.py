"""
TRUSTRAG — Web Search Grounding Service.

Provides unified, secure web search capabilities using:
  1. Tavily AI Search (AI-curated RAG search with clean snippets)
  2. DuckDuckGo Search (100% Free, zero-API-key fallback)
  3. Hybrid Web Search (executes both and deduplicates by URL)

Includes SSRF/XSS URL sanitization, query boundary enforcement, and timeout guards.
"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Search execution timeout guard (seconds)
SEARCH_TIMEOUT_SECONDS = 8.0
MAX_QUERY_LENGTH = 500


import ipaddress

# Blocked hostnames for SSRF defense-in-depth
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


def sanitize_url(raw_url: str | None) -> str:
    """
    Sanitize and validate search citation URLs.
    Strictly permits only http:// and https:// schemes.
    Discards dangerous pseudo-schemes (javascript:, data:, file:, vbscript:).
    Protects against SSRF by blocking loopback, private, and cloud metadata IPs/hosts.
    """
    if not raw_url or not isinstance(raw_url, str):
        return ""
    clean = raw_url.strip()
    try:
        parsed = urlparse(clean)
        if parsed.scheme.lower() not in ("http", "https"):
            logger.warning("Rejected non-HTTP URL from search result", scheme=parsed.scheme)
            return ""
        if not parsed.netloc or " " in parsed.netloc:
            return ""

        hostname = parsed.hostname.lower() if parsed.hostname else ""
        if not hostname:
            return ""

        if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".internal") or hostname.endswith(".local"):
            logger.warning("Rejected internal/metadata hostname in search citation", host=hostname)
            return ""

        # Block private IP ranges, loopback, link-local, and cloud metadata
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                logger.warning("Rejected private/loopback IP in search citation", ip=str(ip))
                return ""
        except ValueError:
            # Domain name, allowed
            pass

        return clean
    except Exception:
        return ""


async def tavily_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Execute AI-native web search using Tavily.
    Requires TAVILY_API_KEY.
    """
    safe_query = (query or "").strip()[:MAX_QUERY_LENGTH]
    if not safe_query:
        return []

    settings = get_settings()
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY is not configured, falling back to DuckDuckGo")
        return await duckduckgo_search(safe_query, max_results=max_results)

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
            "Tavily search timed out, falling back to DuckDuckGo",
            timeout=SEARCH_TIMEOUT_SECONDS,
        )
        return await duckduckgo_search(safe_query, max_results=max_results)
    except Exception as exc:
        logger.error("Tavily search failed, falling back to DuckDuckGo", error=str(exc))
        return await duckduckgo_search(safe_query, max_results=max_results)


async def duckduckgo_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Execute free web search using DuckDuckGo (Zero API Key required).
    """
    safe_query = (query or "").strip()[:MAX_QUERY_LENGTH]
    if not safe_query:
        return []

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        def _do_ddg_search() -> list[dict[str, Any]]:
            ddgs = DDGS()
            raw = ddgs.text(safe_query, max_results=max_results)
            return list(raw) if raw else []

        raw_results = await asyncio.wait_for(
            asyncio.to_thread(_do_ddg_search),
            timeout=SEARCH_TIMEOUT_SECONDS,
        )

        results: list[dict[str, Any]] = []
        for idx, item in enumerate(raw_results):
            raw_href = item.get("href") or item.get("url") or ""
            safe_url = sanitize_url(raw_href)
            snippet = str(item.get("body") or item.get("snippet") or "").strip()
            if not snippet:
                continue

            results.append(
                {
                    "title": str(item.get("title") or "Untitled Web Result").strip(),
                    "url": safe_url,
                    "content": snippet,
                    "score": round(max(0.5, 0.9 - (idx * 0.08)), 2),
                    "source": "duckduckgo",
                }
            )

        logger.info("DuckDuckGo search complete", query=safe_query, count=len(results))
        return results

    except TimeoutError:
        logger.warning("DuckDuckGo search timed out", timeout=SEARCH_TIMEOUT_SECONDS)
        return []
    except Exception as exc:
        logger.error("DuckDuckGo search failed", error=str(exc))
        return []


async def execute_web_search(
    query: str,
    provider: str = "both",
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """
    High-level search dispatcher supporting:
      - 'tavily': Only Tavily AI search
      - 'duckduckgo': Only DuckDuckGo free search
      - 'both': Runs both concurrently and fuses results deduplicated by URL
    """
    provider_clean = (provider or "both").lower().strip()

    if provider_clean in ("tavily", "tavily_mcp"):
        return await tavily_search(query, max_results=max_results)

    if provider_clean in ("duckduckgo", "ddg", "duckduckgo_mcp"):
        return await duckduckgo_search(query, max_results=max_results)

    # ── Hybrid Mode: Run Both Concurrently ──────────────────────────────────
    logger.info("Executing hybrid web search (Tavily + DuckDuckGo)", query=query)
    tavily_task = tavily_search(query, max_results=max_results)
    ddg_task = duckduckgo_search(query, max_results=max_results)

    tavily_res, ddg_res = await asyncio.gather(tavily_task, ddg_task, return_exceptions=True)

    combined: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    t_items = tavily_res if isinstance(tavily_res, list) else []
    d_items = ddg_res if isinstance(ddg_res, list) else []

    max_len = max(len(t_items), len(d_items))
    for i in range(max_len):
        if i < len(t_items):
            url = t_items[i].get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                combined.append(t_items[i])
            elif not url:
                combined.append(t_items[i])
        if i < len(d_items):
            url = d_items[i].get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                combined.append(d_items[i])
            elif not url:
                combined.append(d_items[i])

    # Cap to max_results * 2
    final_results = combined[: max_results * 2]
    logger.info("Hybrid web search completed", count=len(final_results))
    return final_results
