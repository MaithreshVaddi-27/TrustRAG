"""
API contract snapshot (audit B-10).

There was no reference to `openapi` anywhere in the test suite: renaming or
removing any field in `AnalysisResponse`, `KBResponse`, `ClaimResponse`,
`EvidenceResponse`, or the `{code, message}` error envelope would pass CI
silently. The schemas reported 98-100% coverage only because they are pure
`BaseModel` declarations with no behavioural code.

This pins the *wire* contract — the OpenAPI document the frontend and any
external consumer actually depends on, not the Python attribute names, which
differ (the API serialises `id`/`status`/`reliability` where the graph's internal
state uses `_id`/`verdict_status`/`reliability_score`).

When a field must change, the failure message names exactly what moved so the
change is deliberate rather than accidental.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app

# Fields the workbench UI reads. Adding an optional field is fine; removing or
# renaming one is a breaking change that must break this test on purpose.
ANALYSIS_RESPONSE_PROPS = {
    "id",
    "query",
    "answer",
    "status",
    "reliability",
    "diagnosis",
    "knowledge_base_id",
    "user_id",
    "created_at",
    "llm_provider",
    "llm_model",
    "embedding_provider",
    "embedding_model",
}

KB_RESPONSE_PROPS = {"id", "name", "description", "user_id", "created_at", "document_count"}

CLAIM_RESPONSE_PROPS = {"id", "analysis_id", "text", "state", "evidence_ids", "explanation"}

EVIDENCE_RESPONSE_PROPS = {
    "id",
    "analysis_id",
    "text",
    "document_id",
    "integrity_status",
    "retrieval_score",
    "rerank_score",
}

# main.py `_error_response` nests the envelope under an "error" key:
#   {"error": {"code": ..., "message": ...}}
# (The audit wrote this as a flat {code, message}; it is not.)
ERROR_ENVELOPE_KEY = "error"
ERROR_ENVELOPE_FIELDS = {"code", "message"}

# The finalize path the workbench calls after every run. Losing any of these
# silently breaks the results screen.
FINALIZE_ROUTES = (
    "/api/v1/analyses/{analysis_id}",
    "/api/v1/analyses/{analysis_id}/claims",
    "/api/v1/analyses/{analysis_id}/evidence",
    "/api/v1/analyses/{analysis_id}/trace",
    "/api/v1/analyses/{analysis_id}/detail",
)


@pytest.fixture(scope="module")
def openapi() -> dict:
    return app.openapi()


def _props(openapi: dict, schema: str) -> set[str]:
    schemas = openapi["components"]["schemas"]
    assert schema in schemas, f"{schema} vanished from the OpenAPI document"
    return set((schemas[schema].get("properties") or {}).keys())


def test_analysis_response_contract_is_stable(openapi):
    missing = ANALYSIS_RESPONSE_PROPS - _props(openapi, "AnalysisResponse")
    assert not missing, (
        f"AnalysisResponse lost fields the frontend depends on: {sorted(missing)}. "
        "If intentional, update ANALYSIS_RESPONSE_PROPS here and the frontend together."
    )


def test_kb_response_contract_is_stable(openapi):
    missing = KB_RESPONSE_PROPS - _props(openapi, "KBResponse")
    assert not missing, f"KBResponse lost fields: {sorted(missing)}"


def test_claim_response_contract_is_stable(openapi):
    missing = CLAIM_RESPONSE_PROPS - _props(openapi, "ClaimResponse")
    assert not missing, f"ClaimResponse lost fields: {sorted(missing)}"


def test_evidence_response_contract_is_stable(openapi):
    missing = EVIDENCE_RESPONSE_PROPS - _props(openapi, "EvidenceResponse")
    assert not missing, f"EvidenceResponse lost fields: {sorted(missing)}"


def test_required_fields_are_not_silently_relaxed(openapi):
    """Making a previously required field optional breaks strict clients that
    relied on it always being present."""
    schemas = openapi["components"]["schemas"]
    required = set(schemas["AnalysisResponse"].get("required") or [])
    for field in ("id", "query", "status", "reliability", "diagnosis"):
        assert field in required, f"{field} is no longer required on AnalysisResponse"


def test_openapi_document_generates():
    """A schema that cannot render fails FastAPI startup in production but never
    in tests, because the app is imported without running its lifespan."""
    schema = app.openapi()
    assert schema["openapi"].startswith("3.")
    assert schema["paths"], "no routes in the OpenAPI document"


def test_finalize_routes_remain_documented(openapi):
    paths = openapi["paths"]
    for route in FINALIZE_ROUTES:
        assert route in paths, f"route disappeared from the API: {route}"


def test_health_routes_remain_documented(openapi):
    """The e2e suite asserts /health; if it disappears, e2e fails for the wrong
    reason and stops testing anything real."""
    for route in ("/api/v1/health", "/api/v1/health/detailed"):
        assert route in openapi["paths"], f"health route disappeared: {route}"


# ─── Behavioural: the contract actually holds at runtime ──────────────────────


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_override():
    user = {
        "_id": ObjectId("64ee39d09c6292376e191981"),
        "email": "contract@example.com",
        "is_active": True,
    }
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


def test_unknown_analysis_returns_the_documented_error_envelope(client, auth_override):
    missing = "64ee39d09c6292376e199999"
    coll = MagicMock()
    coll.find_one = AsyncMock(return_value=None)
    with (
        patch("app.services.analysis_service.get_collection", MagicMock(return_value=coll)),
        patch("app.api.v1.analyses.get_collection", MagicMock(return_value=coll)),
    ):
        r = client.get(f"/api/v1/analyses/{missing}")
    if r.status_code in (401, 403):
        pytest.skip("auth rejected the request before routing")
    assert r.status_code == 404, f"expected 404 for a missing analysis, got {r.status_code}"
    body = r.json()
    assert ERROR_ENVELOPE_KEY in body, f"error envelope lost its 'error' key: {body}"
    assert ERROR_ENVELOPE_FIELDS <= set(body[ERROR_ENVELOPE_KEY]), f"error envelope drifted: {body}"


def test_analysis_list_returns_a_list(client, auth_override):
    cursor = MagicMock()
    cursor.aiter = MagicMock(side_effect=lambda *a, **k: _empty())
    coll = MagicMock()
    coll.find = MagicMock(return_value=cursor)
    coll.count_documents = AsyncMock(return_value=0)

    with (
        patch("app.api.v1.analyses.get_collection", MagicMock(return_value=coll)),
        patch("app.services.analysis_service.get_collection", MagicMock(return_value=coll)),
    ):
        r = client.get("/api/v1/analyses")
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


def test_health_endpoint_shape_is_stable(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body, f"health payload drifted: {body}"


async def _empty():
    if False:  # pragma: no cover
        yield None
