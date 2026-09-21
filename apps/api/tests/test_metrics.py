"""
Phase 10 — Speed + Production Engineering tests.

Covers: Prometheus /metrics exposition, token estimation, pre-request
budget enforcement, and metrics counters. No live services needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.core import metrics
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_metrics():
    metrics.reset_for_tests()
    yield
    metrics.reset_for_tests()


def test_estimate_tokens_scales_with_length():
    assert metrics.estimate_tokens("") == 0
    assert metrics.estimate_tokens(None) == 0
    assert metrics.estimate_tokens("abcd") == 1
    assert metrics.estimate_tokens("a" * 400) == 100
    assert metrics.estimate_tokens("a" * 4000) > metrics.estimate_tokens("a" * 400)


def test_http_counters_and_render():
    metrics.record_http_request("GET", "/api/v1/health", 200, 12.5)
    metrics.record_http_request("GET", "/api/v1/health", 200, 7.5)
    out = metrics.render_prometheus()
    assert "trustrag_http_requests_total" in out
    assert 'method="GET"' in out
    assert "trustrag_http_request_duration_ms_count" in out
    snap = metrics.snapshot()
    assert snap["http_requests"][("GET", "/api/v1/health", "200")] == 2
    assert snap["http_duration_ms_count"][("GET", "/api/v1/health")] == 2


def test_path_normalization_bounds_cardinality():
    metrics.record_http_request("GET", "/api/v1/knowledge-bases/64ee39d09c6292376e191982", 200, 5.0)
    snap = metrics.snapshot()
    keys = list(snap["http_requests"].keys())
    assert len(keys) == 1
    assert keys[0][1] == "/api/v1/knowledge-bases/:id"


def test_analysis_and_claim_counters():
    metrics.record_analysis_created()
    metrics.record_analysis_created()
    metrics.record_analysis_completed("completed")
    metrics.record_verification_claims(2, 1, 3)
    metrics.record_recovery_attempt("query_rewrite")
    metrics.record_tokens_estimated(500)
    metrics.record_budget_rejection("max_input_tokens")
    out = metrics.render_prometheus()
    assert "trustrag_analyses_created_total 2" in out
    assert 'status="completed"' in out
    assert 'strategy="query_rewrite"' in out
    assert 'verdict="SUPPORTED"' in out
    assert "trustrag_tokens_estimated_total 500" in out
    assert 'reason="max_input_tokens"' in out


def test_metrics_endpoint_public_exposition():
    metrics.record_http_request("GET", "/api/v1/health", 200, 1.0)
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert "trustrag_http_requests_total" in resp.text
    assert "text/plain" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_pre_request_budget_rejects_oversized_query():
    """create_analysis must 422 (InputValidationError) when query exceeds budget."""
    from app.core.exceptions import InputValidationError
    from app.services import analysis_service

    fake_kb = MagicMock()
    fake_kb.embedding_model = None

    with (
        patch.object(analysis_service, "get_kb", AsyncMock(return_value=fake_kb)),
        patch.object(
            analysis_service,
            "get_model_config",
            return_value=MagicMock(
                embedding_provider="huggingface",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_dimensionality=384,
                llm_provider="llama_cpp",
                llm_model="x",
                max_input_tokens=10,  # tiny budget forces rejection
                pre_request_budget_enforcement=True,
                as_snapshot=lambda: {},
            ),
        ),
    ):
        schema = MagicMock()
        schema.knowledge_base_id = str(ObjectId())
        schema.query = "x" * 400  # ~100 tokens > 10 budget
        schema.llm_provider = None
        schema.llm_model = None
        schema.embedding_provider = None
        schema.embedding_model = None
        schema.enable_web_search = False
        schema.web_search_provider = "both"
        with pytest.raises(InputValidationError, match="Query too large"):
            await analysis_service.create_analysis(schema, str(ObjectId()), MagicMock())
    snap = metrics.snapshot()
    assert snap["budget_rejections"].get("max_input_tokens", 0) >= 1


@pytest.mark.asyncio
async def test_pre_request_budget_disabled_allows_large_query():
    """Kill-switch: enforcement off → oversized query proceeds to normal flow."""
    from app.services import analysis_service

    fake_kb = MagicMock()
    fake_kb.embedding_model = None
    fake_kb.name = "KB"

    mock_coll = MagicMock()
    mock_coll.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId("64ee39d09c6292376e191983"))
    )

    with (
        patch.object(analysis_service, "get_kb", AsyncMock(return_value=fake_kb)),
        patch.object(
            analysis_service,
            "get_model_config",
            return_value=MagicMock(
                embedding_provider="huggingface",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_dimensionality=384,
                llm_provider="gemini",  # skip local preflight
                llm_model="x",
                max_input_tokens=10,
                pre_request_budget_enforcement=False,
                as_snapshot=lambda: {},
            ),
        ),
        patch.object(analysis_service, "get_collection", return_value=mock_coll),
        patch.object(analysis_service, "add_trace_event", AsyncMock()),
        patch.object(analysis_service, "serialize_analysis", return_value=MagicMock()),
        # Cloud preflight probe (no network in unit tests) — mirrors the
        # probe_local_llm_server mock pattern in test_analyses.py.
        patch("app.core.local_llm.probe_cloud_llm", AsyncMock(return_value=None)),
    ):
        schema = MagicMock()
        schema.knowledge_base_id = str(ObjectId())
        schema.query = "x" * 400
        schema.llm_provider = None
        schema.llm_model = None
        schema.embedding_provider = None
        schema.embedding_model = None
        schema.enable_web_search = False
        schema.web_search_provider = "both"
        # Should NOT raise — enforcement disabled
        await analysis_service.create_analysis(schema, str(ObjectId()), MagicMock())
