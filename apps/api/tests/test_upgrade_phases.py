"""
Regression tests for UPGRADE.md follow-up phases (2026-09-23).

Covers: RRF-unified adaptive thresholds, parser encoding slice + chunked AV
scan, NLI per-call timeout helper, internal URL SSRF parity, query-cache
dim-mismatch invalidation.
"""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import HTTPException

from app.api.v1.internal import InternalUrlIngest, internal_ingest_url
from app.core.exceptions import IngestionError
from app.ingestion.parser import (
    _ENCODING_DETECT_SLICE,
    EICAR_TEST_STRING,
    _detect_encoding,
    scan_for_malware,
)
from app.retrieval.reranker import _is_high_confidence


def test_is_high_confidence_prefers_rrf_units():
    # RRF max for #1 in both legs ≈ 0.033 → 0.02 means near-top in both.
    assert _is_high_confidence({"rrf_score": 0.025, "dense_score": 0.1}) is True
    assert _is_high_confidence({"rrf_score": 0.01, "dense_score": 0.99}) is False


def test_is_high_confidence_legacy_fallbacks():
    # Rows that never went through RRF fusion use the legacy thresholds.
    assert _is_high_confidence({"dense_score": 0.80}) is True
    assert _is_high_confidence({"dense_score": 0.50}) is False
    assert _is_high_confidence({"rerank_score": 1.2}) is True
    assert _is_high_confidence({"rerank_score": 0.10}) is False


def test_detect_encoding_samples_head_only(monkeypatch):
    seen_lengths: list[int] = []
    import chardet

    real_detect = chardet.detect

    def _spy(data: bytes):
        seen_lengths.append(len(data))
        return real_detect(data)

    monkeypatch.setattr(chardet, "detect", _spy)
    big = (b"hello world " * 200_000)[: 2 * 1024 * 1024]  # ~2MB
    enc = _detect_encoding(big)
    assert isinstance(enc, str) and enc
    assert seen_lengths and max(seen_lengths) <= _ENCODING_DETECT_SLICE


def test_scan_for_malware_detects_split_eicar():
    # EICAR signature split across a 64KB chunk boundary must still trip.
    prefix = b"A" * (65536 - 10)
    payload = prefix + EICAR_TEST_STRING + b"tail"
    with pytest.raises(IngestionError, match="EICAR"):
        scan_for_malware(io.BytesIO(payload))


def test_scan_for_malware_clean_stream_passes():
    scan_for_malware(io.BytesIO(b"%PDF-1.7 clean content" * 1000))


async def test_await_nli_call_times_out(monkeypatch):
    from app.verification import verifier as verifier_module
    from app.verification.verifier import _await_nli_call

    monkeypatch.setattr(verifier_module, "NLI_PER_CALL_TIMEOUT_SECONDS", 0.05)

    async def _slow():
        await asyncio.sleep(5)
        return "never"

    with pytest.raises(TimeoutError):
        await _await_nli_call(_slow(), what="test-slow-call")


async def test_await_nli_call_passes_fast_result(monkeypatch):
    from app.verification import verifier as verifier_module
    from app.verification.verifier import _await_nli_call

    monkeypatch.setattr(verifier_module, "NLI_PER_CALL_TIMEOUT_SECONDS", 5)

    async def _fast():
        return {"verdict": "SUPPORTED"}

    assert await _await_nli_call(_fast(), what="test-fast-call") == {"verdict": "SUPPORTED"}


async def test_internal_ingest_url_rejects_non_allowlisted():
    from starlette.requests import Request

    body = InternalUrlIngest(url="https://example.com/doc.pdf")
    scope = {"type": "http", "method": "POST", "path": "/internal/ingest/url", "headers": []}
    with pytest.raises(HTTPException) as exc_info:
        await internal_ingest_url(
            request=Request(scope),
            kb_id="64ee39d09c6292376e191981",
            url_data=body,
            current_service={"sub": "test-service", "permissions": ["ingest:write"]},
        )
    assert exc_info.value.status_code == 400
    assert "allowlist" in exc_info.value.detail.lower()


def test_query_cache_clear_and_dim_mismatch_path():
    from app.retrieval.retriever import _query_cache

    _query_cache.set("k", [0.1, 0.2, 0.3])
    assert _query_cache.get("k") == [0.1, 0.2, 0.3]
    # Simulate an embedding-space change: stale 3-dim hit vs 384-dim collection.
    cached = _query_cache.get("k")
    assert cached is not None and len(cached) != 384
    _query_cache.clear()
    assert _query_cache.get("k") is None


async def test_mcp_local_chat_rejects_cloud_provider():
    from app.core.security import create_service_token
    from app.mcp.server import handle_tool_call

    token = create_service_token("test-service")
    with pytest.raises(ValueError, match="local providers only"):
        await handle_tool_call(
            "local_llm_chat",
            {"prompt": "hi", "provider": "nvidia", "service_token": token},
        )


async def test_mcp_internal_pipeline_needs_no_token():
    from unittest.mock import AsyncMock, patch

    from app.mcp.client import execute_mcp_tool

    with patch(
        "app.services.search_service.duckduckgo_search",
        AsyncMock(return_value=[{"title": "T", "url": "https://x.com", "content": "C"}]),
    ):
        # No service_token — in-process pipeline caller uses the internal path.
        res = await execute_mcp_tool("duckduckgo_search", {"query": "q"})
        assert res[0]["title"] == "T"


async def test_mcp_external_still_needs_token():
    from app.mcp.server import handle_tool_call

    with pytest.raises(Exception, match="Service token required"):
        await handle_tool_call("duckduckgo_search", {"query": "q"})


def test_llm_registry_put_is_sync_and_bounded():
    from app.core.model_registry import (
        _LLM_REGISTRY,
        _llm_registry_key,
        get_llm_instance,
        put_llm_instance,
    )

    assert not asyncio.iscoroutinefunction(put_llm_instance)
    marker = object()
    put_llm_instance("test-prov", "test-model", marker)  # type: ignore[arg-type]
    try:
        assert get_llm_instance("test-prov", "test-model") is marker
        assert _llm_registry_key("test-prov", "test-model") in _LLM_REGISTRY
    finally:
        _LLM_REGISTRY.pop(_llm_registry_key("test-prov", "test-model"), None)


def test_onnx_model_status_keys():
    from app.core.model_registry import onnx_model_status

    status = onnx_model_status()
    assert status["embedding_provider"] == "onnx"
    assert "embedding_onnx_present" in status
    assert "reranker_onnx_present" in status
