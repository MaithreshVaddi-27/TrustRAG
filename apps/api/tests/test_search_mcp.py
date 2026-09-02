"""Unit tests for Search Service and native MCP tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.client import execute_mcp_tool
from app.mcp.server import handle_tool_call
from app.services.search_service import duckduckgo_search, execute_web_search, tavily_search


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

    with patch("app.services.search_service.get_settings") as mock_settings, patch(
        "tavily.TavilyClient", return_value=mock_tavily_client
    ):
        mock_settings.return_value.tavily_api_key = "tvly-test-12345"
        results = await tavily_search("test query", max_results=3)

        assert len(results) == 1
        assert results[0]["title"] == "Test Title"
        assert results[0]["url"] == "https://example.com/test"
        assert results[0]["source"] == "tavily"


@pytest.mark.asyncio
async def test_tavily_search_fallback_when_no_key():
    fallback_mock = AsyncMock(return_value=[{"title": "Fallback"}])
    with patch("app.services.search_service.get_settings") as mock_settings, patch(
        "app.services.search_service.duckduckgo_search", fallback_mock
    ):
        mock_settings.return_value.tavily_api_key = ""
        results = await tavily_search("test query")
        assert len(results) == 1
        assert results[0]["title"] == "Fallback"


@pytest.mark.asyncio
async def test_duckduckgo_search_success():
    fake_ddg_results = [
        {
            "title": "DDG Title",
            "href": "https://example.org/ddg",
            "body": "DuckDuckGo search snippet text.",
        }
    ]

    with patch("ddgs.DDGS") as mock_ddgs:
        instance = mock_ddgs.return_value
        instance.text.return_value = fake_ddg_results

        results = await duckduckgo_search("ddg query", max_results=2)
        assert len(results) == 1
        assert results[0]["title"] == "DDG Title"
        assert results[0]["url"] == "https://example.org/ddg"
        assert results[0]["source"] == "duckduckgo"


@pytest.mark.asyncio
async def test_execute_web_search_deduplication():
    # Test deduplication across both providers
    tavily_res = [
        {"title": "Common Article", "url": "https://shared.com/item", "content": "A", "score": 0.9}
    ]
    ddg_res = [
        {
            "title": "Common Article Dup",
            "url": "https://shared.com/item",
            "content": "B",
            "score": 0.8,
        },
        {"title": "Unique DDG", "url": "https://unique.org/item", "content": "C", "score": 0.8},
    ]

    mock_tavily = AsyncMock(return_value=tavily_res)
    mock_ddg = AsyncMock(return_value=ddg_res)
    with patch("app.services.search_service.tavily_search", mock_tavily), patch(
        "app.services.search_service.duckduckgo_search", mock_ddg
    ):
        merged = await execute_web_search("test query", provider="both")
        assert len(merged) == 2
        urls = [m["url"] for m in merged]
        assert "https://shared.com/item" in urls
        assert "https://unique.org/item" in urls


@pytest.mark.asyncio
async def test_mcp_tool_execution():
    with patch(
        "app.services.search_service.duckduckgo_search",
        AsyncMock(return_value=[{"title": "MCP DDG", "url": "https://mcp.com", "content": "MCP"}]),
    ):
        res = await handle_tool_call("duckduckgo_search", {"query": "mcp query"})
        assert "content" in res
        assert "MCP DDG" in res["content"][0]["text"]

    with patch(
        "app.mcp.client.handle_tool_call",
        AsyncMock(
            return_value={"content": [{"type": "text", "text": '[{"title": "Client Ok"}]'}]}
        ),
    ):
        parsed = await execute_mcp_tool("duckduckgo_search", {"query": "client query"})
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Client Ok"


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
    assert sanitize_url("https://en.wikipedia.org/wiki/Python") == "https://en.wikipedia.org/wiki/Python"
    assert sanitize_url("http://example.com/article?id=123") == "http://example.com/article?id=123"


@pytest.mark.asyncio
async def test_search_service_timeout_fallback():
    # Simulate a hanging Tavily client that exceeds timeout
    def _hanging_call(*args, **kwargs):
        import time
        time.sleep(1.0)

    fallback_ddg = [{"title": "DDG Fallback", "url": "https://ddg.com", "content": "Ok"}]
    with patch("app.services.search_service.get_settings") as mock_settings, patch(
        "app.services.search_service.duckduckgo_search", AsyncMock(return_value=fallback_ddg)
    ), patch("app.services.search_service.SEARCH_TIMEOUT_SECONDS", 0.05), patch(
        "tavily.TavilyClient"
    ) as mock_client:
        mock_settings.return_value.tavily_api_key = "tvly-key"
        mock_instance = mock_client.return_value
        mock_instance.search.side_effect = _hanging_call

        results = await tavily_search("hanging query")
        assert len(results) == 1
        assert results[0]["title"] == "DDG Fallback"


@pytest.mark.asyncio
async def test_local_llm_mcp_tools():
    # Test local_llm_status tool
    res = await handle_tool_call("local_llm_status", {"provider": "both"})
    assert "content" in res
    assert len(res["content"]) > 0
    data = json.loads(res["content"][0]["text"])
    assert "ollama" in data
    assert "llama_cpp" in data

    # Test local_llm_chat tool with mock
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(content="Mocked response from local LLM")
    with patch("app.core.model_registry.get_llm", return_value=mock_llm):
        chat_res = await handle_tool_call(
            "local_llm_chat",
            {"prompt": "Hello local LLM", "provider": "ollama", "model": "gemma4:e2b"},
        )
        assert "content" in chat_res
        assert chat_res["content"][0]["text"] == "Mocked response from local LLM"
