"""Unit tests for Search Service and native MCP tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.client import execute_mcp_tool
from app.mcp.server import handle_tool_call
from app.services.search_service import (
    execute_web_search,
    tavily_search,
)


@pytest.mark.asyncio
async def test_tavily_search_success():
    mock_tavily_client = MagicMock()
    mock_tavily_client.search.return_value = {
        "results": [
            {
                "title": "Test Title",
                "url": "https://example.com/test",
                "content": "This is test snippet content.",
                "score": 0.95,
            }
        ]
    }

    with (
        patch("app.services.search_service.get_settings") as mock_settings,
        patch("tavily.TavilyClient", return_value=mock_tavily_client),
    ):
        mock_settings.return_value.tavily_api_key = "tvly-test-12345"  # SYNTHETIC mock
        results = await tavily_search("test query", max_results=3)

        assert len(results) == 1
        assert results[0]["title"] == "Test Title"
        assert results[0]["url"] == "https://example.com/test"
        assert results[0]["source"] == "tavily"


@pytest.mark.asyncio
async def test_tavily_search_empty_key_returns_empty():
    """No key, no fallback provider: auth failure yields [] (never a crash).

    TavilyClient is patched to raise (no live network, no real key): the
    service must convert any client failure into []."""
    with (
        patch("app.services.search_service.get_settings") as mock_settings,
        patch("tavily.TavilyClient", side_effect=Exception("missing API key")),
    ):
        mock_settings.return_value.tavily_api_key = ""
        results = await tavily_search("test query")
        assert results == []


@pytest.mark.asyncio
async def test_duckduckgo_tool_is_gone_tavily_only():
    """DuckDuckGo was removed (Tavily-only service): the tool name must 404
    through the dispatcher instead of AttributeError-ing mid-call."""
    from app.core.security.security import create_service_token

    token = create_service_token("test-service")
    with pytest.raises(Exception, match="Unknown MCP tool"):
        await handle_tool_call("duckduckgo_search", {"query": "ddg query", "service_token": token})


@pytest.mark.asyncio
async def test_execute_web_search_is_tavily_passthrough():
    """Tavily is the sole web-search provider: execute_web_search delegates
    straight through (no fan-out, no dedup layer)."""
    tvly_res = [
        {"title": "Sole Article", "url": "https://solo.com/item", "content": "A", "score": 0.9}
    ]

    mock_tavily = AsyncMock(return_value=tvly_res)
    with patch("app.services.search_service.tavily_search", mock_tavily):
        merged = await execute_web_search("test query")
        assert merged == tvly_res
        mock_tavily.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_tool_execution():
    from app.core.security.security import create_service_token

    token = create_service_token("test-service")
    with patch(
        "app.services.search_service.tavily_search",
        AsyncMock(return_value=[{"title": "MCP TVLY", "url": "https://mcp.com", "content": "MCP"}]),
    ):
        res = await handle_tool_call(
            "tavily_search", {"query": "mcp query", "service_token": token}
        )
        assert "content" in res
        assert "MCP TVLY" in res["content"][0]["text"]


# ─── Audit B-19: execute_mcp_tool had only a tautological test ─────────────────
# The previous test patched `app.mcp.client.handle_tool_call` — the single callee
# of the function under test — then asserted a hardcoded JSON string parsed. It
# would have passed against a broken internal-auth path, a missing `content`
# key, or a body of `return json.loads(handle_tool_call(...))` regardless of
# arguments. These assert the real contract instead.


@pytest.mark.asyncio
async def test_execute_mcp_tool_uses_internal_auth_path():
    """The in-process caller must be authenticated by construction: the real
    call passes `_internal=True`. The old test never checked this."""
    with patch(
        "app.mcp.client.handle_tool_call",
        AsyncMock(return_value={"content": [{"type": "text", "text": "[]"}]}),
    ) as mock_handle:
        await execute_mcp_tool("tavily_search", {"query": "q"})
    mock_handle.assert_awaited_once_with("tavily_search", {"query": "q"}, _internal=True)


@pytest.mark.asyncio
async def test_execute_mcp_tool_returns_none_on_empty_content():
    """A response with no content items must yield None, not raise or return {}."""
    with patch(
        "app.mcp.client.handle_tool_call",
        AsyncMock(return_value={"content": []}),
    ):
        assert await execute_mcp_tool("t", {}) is None
    with patch(
        "app.mcp.client.handle_tool_call",
        AsyncMock(return_value={}),
    ):
        assert await execute_mcp_tool("t", {}) is None


@pytest.mark.asyncio
async def test_execute_mcp_tool_parses_json_content():
    with patch(
        "app.mcp.client.handle_tool_call",
        AsyncMock(return_value={"content": [{"type": "text", "text": '[{"title": "Client Ok"}]'}]}),
    ):
        parsed = await execute_mcp_tool("tavily_search", {"query": "client query"})
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Client Ok"


@pytest.mark.asyncio
async def test_execute_mcp_tool_falls_back_to_raw_text_on_bad_json():
    """Non-JSON text is returned verbatim rather than raising (client.py:41-43)."""
    with patch(
        "app.mcp.client.handle_tool_call",
        AsyncMock(return_value={"content": [{"type": "text", "text": "not json at all"}]}),
    ):
        assert await execute_mcp_tool("t", {}) == "not json at all"


@pytest.mark.asyncio
async def test_execute_mcp_tool_propagates_dispatcher_errors():
    """Dispatcher failures must propagate so the graph can fail the analysis;
    they must not be silently swallowed into a None result."""
    with patch(
        "app.mcp.client.handle_tool_call",
        AsyncMock(side_effect=ValueError("Unknown MCP tool")),
    ):
        with pytest.raises(ValueError, match="Unknown MCP tool"):
            await execute_mcp_tool("nope", {})


def test_sanitize_url_security():
    from app.services.search_service import sanitize_url

    # Malicious injection attempts
    assert sanitize_url("javascript:alert(document.cookie)") == ""
    assert sanitize_url("data:text/html,<script>alert(1)</script>") == ""
    assert sanitize_url("file:///etc/passwd") == ""
    assert sanitize_url("vbscript:MsgBox(1)") == ""
    assert sanitize_url("ftp://malicious.org") == ""
    assert sanitize_url("") == ""
    assert sanitize_url(None) == ""
    assert sanitize_url("http://") == ""
    assert sanitize_url("https://malicious site.com") == ""

    # SSRF / private IP / cloud metadata attempts
    assert sanitize_url("http://127.0.0.1:8080/admin") == ""
    assert sanitize_url("http://localhost:27017") == ""
    assert sanitize_url("http://169.254.169.254/latest/meta-data/") == ""
    assert sanitize_url("http://metadata.google.internal/computeMetadata/v1/") == ""
    assert sanitize_url("http://192.168.1.1/router") == ""
    assert sanitize_url("http://10.0.0.1/internal") == ""

    # Legitimate safe URLs
    assert (
        sanitize_url("https://en.wikipedia.org/wiki/Python")
        == "https://en.wikipedia.org/wiki/Python"
    )
    assert sanitize_url("http://example.com/article?id=123") == "http://example.com/article?id=123"


@pytest.mark.asyncio
async def test_search_service_timeout_returns_empty():
    # Simulate a hanging Tavily client that exceeds timeout: no fallback
    # provider exists, so a hang yields [] (never a crash, never a hang).
    def _hanging_call(*args, **kwargs):
        import time

        time.sleep(1.0)

    with (
        patch("app.services.search_service.get_settings") as mock_settings,
        patch("app.services.search_service.SEARCH_TIMEOUT_SECONDS", 0.05),
        patch("tavily.TavilyClient") as mock_client,
    ):
        mock_settings.return_value.tavily_api_key = "tvly-key"  # SYNTHETIC mock
        mock_instance = mock_client.return_value
        mock_instance.search.side_effect = _hanging_call

        results = await tavily_search("hanging query")
        assert results == []


@pytest.mark.asyncio
async def test_local_llm_mcp_tools():
    from app.core.security.security import create_service_token

    token = create_service_token("test-service")
    # Test local_llm_status tool
    res = await handle_tool_call("local_llm_status", {"provider": "both", "service_token": token})
    assert "content" in res
    assert len(res["content"]) > 0
    data = json.loads(res["content"][0]["text"])
    assert "ollama" in data
    assert "llama_cpp" in data

    # Test local_llm_chat tool with mock
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(content="Mocked response from local LLM")
    with patch("app.llm.model_registry.get_llm", return_value=mock_llm):
        chat_res = await handle_tool_call(
            "local_llm_chat",
            {
                "prompt": "Hello local LLM",
                "provider": "ollama",
                "model": "granite4.2:3b-q4_K_M",
                "service_token": token,
            },
        )
        assert "content" in chat_res
        assert chat_res["content"][0]["text"] == "Mocked response from local LLM"
