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

import pathlib
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


# ─── README quickstart contract ──────────────────────────────────────────────
# The README's "End-to-end via API" block is the first thing a new user runs.
# It was wrong in three ways at once and no test caught it, because nothing
# connected the documented steps to the real schemas: it POSTed to /auth/register
# and read ['access_token'] (register returns UserResponse — only /auth/login
# returns a token), sent "name" where the schema requires "full_name", and used
# a password that fails complexity validation. Every one of those is a 422 or a
# KeyError on step 1. These tests pin the documented flow to the real contract.


def _readme():
    """Locate README.md from the repo root; skip if packaged without it."""
    readme = pathlib.Path(__file__).resolve().parents[3] / "README.md"
    if not readme.exists():
        pytest.skip("README.md not available")
    return readme


def test_register_returns_a_profile_not_a_token(openapi):
    """The README must not read access_token from /auth/register — it cannot be
    there. Only /auth/login returns TokenResponse."""
    spec = openapi
    register = spec["paths"]["/api/v1/auth/register"]["post"]
    ref = register["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    name = ref.rsplit("/", 1)[-1]
    assert "access_token" not in spec["components"]["schemas"][name]["properties"], (
        f"/auth/register now returns {name} containing access_token — if that is "
        "intentional, update the README quickstart"
    )


def test_login_is_the_only_source_of_an_access_token(openapi):
    login = openapi["paths"]["/api/v1/auth/login"]["post"]
    ref = login["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    name = ref.rsplit("/", 1)[-1]
    assert "access_token" in openapi["components"]["schemas"][name]["properties"]


def test_readme_quickstart_reads_the_token_from_login_not_register():
    """The original quickstart read ['access_token'] out of the /auth/register
    response. Register returns UserResponse and has no such field, so step 1
    died with a KeyError before the user ever got a token. Schema-level tests
    cannot catch a doc that documents the wrong endpoint, so pin the README.
    """
    import re

    text = _readme().read_text()
    # Find whichever endpoint the TOKEN=$( curl ... ) line is pointed at.
    token_lines = [
        line for line in text.splitlines() if "access_token" in line and "curl" not in line
    ]
    assert token_lines, "could not find the quickstart token-extraction line"

    # Walk back from the extraction line to the nearest endpoint.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "access_token" in line and "curl" not in line:
            window = "\n".join(lines[max(0, i - 6) : i + 1])
            m = re.findall(r"/api/v1/auth/(\w+)", window)
            assert m, f"no auth endpoint found near the token extraction: {window[:160]}"
            assert m[-1] == "login", (
                f"quickstart reads the token from /auth/register, which returns a "
                f"profile with no access_token; it must use /auth/login "
                f"(found: /api/v1/auth/{m[-1]})"
            )


def test_readme_registration_payload_matches_the_schema(openapi):
    """The README sent {"email","password","name"}; the schema requires
    full_name. That mismatch is a guaranteed 422 for every new user."""
    readme = _readme()
    text = readme.read_text()

    fields = set(openapi["components"]["schemas"]["UserRegister"]["properties"])
    assert "full_name" in fields, f"schema no longer has full_name: {fields}"

    # Scope to the register call's -d payload only. Other payloads (create-KB)
    # legitimately use a "name" key, and the API Reference table mentions the
    # endpoint without a body.
    import re

    payloads = re.findall(r"auth/register[^\n]*\n(?:[^\n]*\n)*?\s*-d '(\{[^']*\})'", text)
    assert payloads, "no /auth/register request body found in the README"
    for body in payloads:
        assert '"full_name"' in body, (
            f"README register payload does not send full_name: {body[:140]}"
        )
        assert '"name"' not in body, (
            f"README register payload sends 'name'; schema requires 'full_name': {body[:140]}"
        )


def test_readme_example_password_satisfies_complexity():
    """The README's example password was rejected by the very validator it
    documents. A copy-pasted example that 422s is worse than no example."""
    import re

    from app.api.v1.schemas.auth import _validate_password_complexity

    text = _readme().read_text()
    passwords = set(re.findall(r'"password"\s*:\s*"([^"]+)"', text))
    assert passwords, "no example password found in README"
    for pwd in passwords:
        try:
            _validate_password_complexity(pwd)
        except ValueError as exc:
            pytest.fail(f"README example password {pwd!r} is rejected: {exc}")


def test_readme_documented_endpoints_all_exist(openapi):
    """Every path named in the README must be a real route, so the docs cannot
    drift from the app unnoticed. Param names are normalised because they do not
    change the URL a caller actually types.

    /api/v1/metrics is set include_in_schema=False, so it is absent from the
    OpenAPI document even though it serves; it is probed live below.
    """
    import re

    from fastapi.testclient import TestClient

    text = _readme().read_text()
    schema_paths = set(openapi["paths"])

    def _normalise(p: str) -> str:
        return re.sub(r"\{[a-z_]+\}", "{}", p.rstrip("/"))

    schema_norm = {_normalise(p) for p in schema_paths}

    # Only fully-qualified paths from the docs; the table also uses `…/{id}`
    # shorthand which is covered by the explicit check below.
    candidates = {
        c.rstrip("/.")
        for c in re.findall(r"/api/v1/[A-Za-z0-9/_{}.-]+", text)
        if c.rstrip("/.") not in ("/api/v1/analyses", "/api/v1/knowledge-bases")
    }

    client = TestClient(app)
    missing = []
    for cand in sorted(candidates):
        if _normalise(cand) in schema_norm:
            continue
        # Not in the schema: confirm it is at least a live route (auth-gated
        # endpoints answer 401/403, not 404).
        probe = client.get(cand.replace("{id}", "0").replace("{kb_id}", "0"))
        if probe.status_code == 404 and "error" in (probe.text or ""):
            missing.append(cand)
    assert not missing, f"README documents non-existent endpoints: {missing}"


def test_metrics_endpoint_is_live_even_though_hidden_from_schema(openapi):
    """README lists GET /api/v1/metrics, which is include_in_schema=False and so
    missing from the OpenAPI document. A schema-only existence check would call
    the README wrong; the route genuinely serves."""
    from fastapi.testclient import TestClient

    assert "/api/v1/metrics" not in openapi["paths"], (
        "/api/v1/metrics is now in the schema; the README's Ops row can cite it "
        "normally and this test should be removed"
    )
    assert TestClient(app).get("/api/v1/metrics").status_code == 200
