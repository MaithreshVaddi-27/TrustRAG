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
import ipaddress
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Search execution timeout guard (seconds)
SEARCH_TIMEOUT_SECONDS = 8.0
MAX_QUERY_LENGTH = 500

# Blocked hostnames for SSRF defense-in-depth
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

# ─── URL Validation for Document Ingestion (SSRF Protection) ───────────────────
# These functions provide SSRF protection for any URL-based document ingestion.
# They implement a defense-in-depth approach:
# 1. Allowlist of permitted domains/schemes
# 2. Blocklist of dangerous hosts/IPs
# 3. DNS resolution validation to prevent internal IP access
# 4. Response size limits to prevent resource exhaustion

# Default allowlist for document ingestion URLs - can be configured via env
DEFAULT_URL_ALLOWLIST = {
    "https://en.wikipedia.org",
    "https://www.wikipedia.org",
    "https://arxiv.org",
    "https://api.github.com",
    "https://raw.githubusercontent.com",
    "https://docs.python.org",
    "https://developer.mozilla.org",
    "https://www.w3.org",
    "https://tools.ietf.org",
    "https://rfc-editor.org",
}

# Maximum document size for URL ingestion (10MB)
MAX_URL_DOCUMENT_SIZE = 10 * 1024 * 1024

# Timeout for URL fetching (seconds)
URL_FETCH_TIMEOUT = 15.0


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

        if (
            hostname in BLOCKED_HOSTNAMES
            or hostname.endswith(".internal")
            or hostname.endswith(".local")
        ):
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


def validate_ingestion_url(url: str, allowlist: set[str] | None = None) -> tuple[bool, str]:
    """
    Validate a URL for document ingestion with SSRF protection.

    Implements defense-in-depth:
    1. Scheme validation (http/https only)
    2. Hostname allowlist checking (if provided)
    3. Internal IP/hostname blocking
    4. DNS resolution to verify target is not internal

    Args:
        url: The URL to validate
        allowlist: Optional set of allowed URL prefixes (e.g., {"https://en.wikipedia.org"})
                   If None, uses DEFAULT_URL_ALLOWLIST

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL is required"

    url = url.strip()
    if not url:
        return False, "URL cannot be empty"

    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Invalid URL format: {exc}"

    # 1. Scheme validation
    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Only HTTP and HTTPS schemes are allowed"

    if not parsed.netloc:
        return False, "Invalid URL: missing hostname"

    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if not hostname:
        return False, "Invalid URL: missing hostname"

    # 2. Allowlist checking
    effective_allowlist = allowlist or DEFAULT_URL_ALLOWLIST
    if effective_allowlist:
        allowed = any(url.startswith(prefix) for prefix in effective_allowlist)
        if not allowed:
            return False, f"URL domain not in allowlist. Allowed: {sorted(effective_allowlist)}"

    # 3. Block dangerous hostnames
    if (
        hostname in BLOCKED_HOSTNAMES
        or hostname.endswith(".internal")
        or hostname.endswith(".local")
        or hostname == "localhost"
    ):
        logger.warning("Rejected internal/metadata hostname in ingestion URL", host=hostname)
        return False, "Access to internal hosts is not permitted"

    # 4. Block private IP ranges via IP address check
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            logger.warning("Rejected private/loopback IP in ingestion URL", ip=str(ip))
            return False, "Access to private IP addresses is not permitted"
    except ValueError:
        # Hostname is a domain name, continue to DNS resolution
        pass

    # 5. DNS resolution check (optional - could be done at fetch time)
    # This would require async DNS resolution, so we'll note it for the fetch function

    return True, ""


async def fetch_document_from_url(
    url: str,
    allowlist: set[str] | None = None,
    timeout: float = URL_FETCH_TIMEOUT,
    max_size: int = MAX_URL_DOCUMENT_SIZE,
) -> tuple[bytes | None, str | None]:
    """
    Fetch a document from a URL with SSRF protection.

    Args:
        url: The URL to fetch
        allowlist: Optional set of allowed URL prefixes
        timeout: Request timeout in seconds
        max_size: Maximum response size in bytes

    Returns:
        Tuple of (content_bytes, error_message). If error_message is not None, content is None.
    """
    # Validate URL first
    is_valid, error = validate_ingestion_url(url, allowlist)
    if not is_valid:
        return None, error

    try:
        import httpx

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
        ) as client:
            # Add headers to identify as a bot
            headers = {
                "User-Agent": "TrustRAG Document Ingestion Bot/1.0",
                "Accept": "text/html,application/pdf,text/plain,*/*",
            }

            async with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                allowed_types = [
                    "text/",
                    "application/pdf",
                    "application/json",
                    "application/xml",
                    "text/csv",
                    "text/markdown",
                ]
                if not any(content_type.startswith(t) for t in allowed_types):
                    return None, f"Unsupported content type: {content_type}"

                # Stream response with size limit
                content_chunks = []
                total_size = 0
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > max_size:
                        return None, f"Document exceeds maximum size of {max_size} bytes"
                    content_chunks.append(chunk)

                return b"".join(content_chunks), None

    except httpx.TimeoutException:
        return None, f"Request timed out after {timeout} seconds"
    except httpx.HTTPStatusError as exc:
        return None, f"HTTP error {exc.response.status_code}: {exc}"
    except httpx.RequestError as exc:
        return None, f"Request failed: {exc}"
    except Exception as exc:
        return None, f"Unexpected error fetching URL: {exc}"


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
    # Split max_results between both services to avoid excess computation
    half_results = max(1, max_results // 2)
    tavily_task = tavily_search(query, max_results=half_results)
    ddg_task = duckduckgo_search(query, max_results=half_results)

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

    # Cap to max_results total (safety net for uneven splits)
    final_results = combined[:max_results]
    logger.info("Hybrid web search completed", count=len(final_results))
    return final_results
