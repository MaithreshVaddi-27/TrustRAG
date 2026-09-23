"""
Regression tests for UPGRADE.md follow-up phases (2026-09-23).

Covers: RRF-unified adaptive thresholds, parser encoding slice + chunked AV
scan, NLI per-call timeout helper, internal URL SSRF parity, query-cache
dim-mismatch invalidation.
"""

from __future__ import annotations

import asyncio
import io
import re
from typing import Any

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


async def test_mcp_search_rejects_wrong_bound_kb():
    from app.core.exceptions import AuthenticationError
    from app.core.security import create_service_token
    from app.mcp.server import handle_tool_call

    token = create_service_token(
        "scoped-service",
        permissions=["search:read"],
        bound_kb_id="64ee39d09c6292376e191981",
    )
    with pytest.raises(AuthenticationError, match="not authorized"):
        await handle_tool_call(
            "trustrag_search",
            {
                "kb_id": "64ee39d09c6292376e191982",
                "query": "q",
                "service_token": token,
            },
        )


async def test_mcp_search_rejects_foreign_bound_user():
    from unittest.mock import AsyncMock, patch

    from app.core.exceptions import AuthenticationError, AuthorizationError
    from app.core.security import create_service_token
    from app.mcp.server import handle_tool_call

    token = create_service_token(
        "scoped-service",
        permissions=["search:read"],
        bound_user_id="64ee39d09c6292376e191981",
    )
    with patch(
        "app.services.kb_service.get_kb",
        AsyncMock(side_effect=AuthorizationError("Access denied")),
    ):
        with pytest.raises(AuthenticationError, match="not authorized"):
            await handle_tool_call(
                "trustrag_search",
                {
                    "kb_id": "64ee39d09c6292376e191981",
                    "query": "q",
                    "service_token": token,
                },
            )


async def test_mcp_search_unbound_token_proceeds():
    from unittest.mock import AsyncMock, patch

    from app.core.security import create_service_token
    from app.mcp.server import handle_tool_call

    token = create_service_token("svc", permissions=["search:read"])
    with patch(
        "app.mcp.server.retrieve_hybrid_chunks",
        AsyncMock(return_value=[{"chunk_id": "c1", "text": "t", "rrf_score": 0.03}]),
    ):
        res = await handle_tool_call(
            "trustrag_search",
            {"kb_id": "64ee39d09c6292376e191981", "query": "q", "service_token": token},
        )
        assert res["content"][0]["text"].find("c1") != -1


async def test_mcp_list_kbs_scoped_to_bound_user():
    from unittest.mock import patch

    from app.core.security import create_service_token
    from app.mcp.server import handle_tool_call

    token = create_service_token(
        "scoped-service",
        bound_user_id="64ee39d09c6292376e191981",
    )
    seen: dict[str, Any] = {}

    class _Cursor:
        def __init__(self, docs):
            self._docs = docs

        def __aiter__(self):
            async def _gen():
                for d in self._docs:
                    yield d

            return _gen()

    class _Coll:
        def find(self, filt, proj):
            seen["filter"] = filt
            return _Cursor([])

    with patch("app.mcp.server.get_collection", return_value=_Coll()):
        res = await handle_tool_call("trustrag_list_kbs", {"service_token": token})
        assert res["content"] is not None
    assert "user_id" in seen["filter"]


def test_onnx_model_status_keys():
    from app.core.model_registry import onnx_model_status

    status = onnx_model_status()
    assert status["embedding_provider"] == "onnx"
    assert "embedding_onnx_present" in status
    assert "reranker_onnx_present" in status


def test_onnx_missing_model_points_at_bootstrap():
    from app.core.exceptions import ConfigurationError
    from app.core.model_registry import get_embedding_model

    with pytest.raises(ConfigurationError, match="bootstrap"):
        get_embedding_model(provider="onnx", model="nonexistent-org/nonexistent-model")


def test_memory_fallback_without_psutil_or_resource(monkeypatch):
    import app.core.memory as memory_module

    monkeypatch.setattr(memory_module, "_PSUTIL_AVAILABLE", False)
    monkeypatch.setattr(memory_module, "resource", None)
    assert memory_module.get_memory_usage_mb() == 0.0


def test_export_fn_accepts_model_name():
    import inspect
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    try:
        import export_bge_onnx

        params = inspect.signature(export_bge_onnx.export_bge_to_onnx).parameters
        assert "model_name" in params
    finally:
        sys.path.remove(str(Path(__file__).resolve().parents[3] / "scripts"))


def test_semantic_matrix_rebuilds_when_dirty():
    import app.core.semantic_cache as sc

    sc.reset_module_state()
    try:
        vec_a = [1.0, 0.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0, 0.0]
        sc.store_semantic_cache("q1", "kb1", vec_a, {"answer": "A"}, embedding_model="m")
        sc.store_semantic_cache("q2", "kb1", vec_b, {"answer": "B"}, embedding_model="m")
        # Mutations flag dirty; the next lookup must rebuild (fast path live).
        assert sc._MATRIX_DIRTY is True
        hit = sc.check_semantic_cache("q1", "kb1", vec_a, embedding_model="m")
        assert sc._MATRIX_DIRTY is False
        assert sc._MATRIX_CACHE is not None
        assert hit == {"answer": "A"}
        # Near-duplicate still resolves to the right entry through the matrix.
        hit_b = sc.check_semantic_cache(
            "q2", "kb1", [0.0, 1.0, 0.0, 0.0], embedding_model="m"
        )
        assert hit_b == {"answer": "B"}
    finally:
        sc.reset_module_state()


def test_parse_document_rejects_eicar():
    import io

    from app.core.exceptions import IngestionError
    from app.ingestion.parser import EICAR_TEST_STRING, parse_document

    stream = io.BytesIO(b"clean header " + EICAR_TEST_STRING + b" trailer")
    with pytest.raises(IngestionError, match=r"[Mm]alware|EICAR|blocked"):
        parse_document("notes.txt", stream)


def test_parse_document_rejects_signature_mismatch():
    import io

    from app.core.exceptions import IngestionError
    from app.ingestion.parser import parse_document

    with pytest.raises(IngestionError, match=r"[Ss]ignature|mismatch|format"):
        parse_document("evil.pdf", io.BytesIO(b"hello world, not a pdf"))


def test_parse_docx_rejects_zip_bomb():
    import io
    import zipfile

    from app.core.exceptions import IngestionError
    from app.ingestion.parser import parse_document

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", b"<w:doc>" + b"0" * (2 * 1024 * 1024) + b"</w:doc>")
    with pytest.raises(IngestionError) as exc_info:
        parse_document("bomb.docx", io.BytesIO(buf.getvalue()))
    assert re.search(r"[Bb]omb|ratio", (exc_info.value.detail or "") + str(exc_info.value))


def test_parse_docx_rejects_xxe():
    import io
    import zipfile

    from app.core.exceptions import IngestionError
    from app.ingestion.parser import parse_document

    evil_xml = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        b"<w:p><w:t>&xxe;</w:t></w:p></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", evil_xml)
    with pytest.raises(IngestionError):
        parse_document("xxe.docx", io.BytesIO(buf.getvalue()))


def test_parse_pdf_rejects_oversize():
    import io

    from app.core.exceptions import IngestionError
    from app.ingestion.parser import parse_document

    # Size guard trips before any PDF parsing (fast: no fitz work).
    big = b"%PDF-1.7\n" + b"0" * (21 * 1024 * 1024)
    with pytest.raises(IngestionError) as exc_info:
        parse_document("big.pdf", io.BytesIO(big))
    haystack = (exc_info.value.detail or "") + str(exc_info.value)
    assert re.search(r"[Ss]ize|[Ll]imit|exceeds", haystack)


async def test_qdrant_rejects_schemeless_url_without_mkdir(tmp_path):
    from unittest.mock import patch

    import app.db.qdrant as qdrant_module
    from app.core.exceptions import VectorStoreError

    saved = qdrant_module._client
    qdrant_module._client = None
    bogus = tmp_path / "localhost:6333"
    try:
        settings = type("S", (), {"qdrant_url": "localhost:6333", "qdrant_api_key": ""})()
        with patch.object(qdrant_module, "get_settings", return_value=settings):
            with pytest.raises(VectorStoreError, match="Invalid QDRANT_URL"):
                await qdrant_module.get_qdrant_client()
        assert not bogus.exists()
    finally:
        qdrant_module._client = saved


async def test_shared_http_client_splits_timeouts():
    from app.core.local_llm import _shared_http_client, close_local_llm_clients

    try:
        client = _shared_http_client("http://127.0.0.1:9", 120.0)
        assert float(client.timeout.connect) == 10.0
        assert float(client.timeout.read) == 120.0
    finally:
        await close_local_llm_clients()


def test_ports_registry_includes_mlx():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    try:
        from apply_ports import load_ports

        ports = load_ports()
        assert ports["mlx"] == 8090
    finally:
        sys.path.remove(str(Path(__file__).resolve().parents[3] / "scripts"))
