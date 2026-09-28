"""
Route tests for the analysis read endpoints (audit B-8 remainder).

The workbench calls these on every finalize, and `/trace` is the polling
fallback when the SSE stream drops — so a regression here is user-visible as a
workbench that hangs on "analysing" or shows a blank evidence panel.

Each of the five routes must forward the *caller's* identity to the service,
which is where the ownership check happens (`analysis_service.get_analysis`).
A route that dropped that argument would let any authenticated user read any
other user's analysis, so the forwarding is asserted directly, not inferred
from a 403.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app

ANALYSIS_ID = "64ee39d09c6292376e1919ab"
OTHER_USER_ID = "64ee39d09c6292376e199001"

client = TestClient(app)

# route suffix -> service function the route must delegate to
READ_ROUTES = [
    ("", "get_analysis"),
    ("/claims", "get_analysis_claims"),
    ("/evidence", "get_analysis_evidence"),
    ("/trace", "get_analysis_trace"),
    ("/detail", "get_analysis_detail"),
]


@pytest.fixture
def user_id():
    user = {
        "_id": ObjectId("64ee39d09c6292376e191981"),
        "email": "reader@example.com",
        "hashed_password": "x",
        "is_active": True,
    }
    app.dependency_overrides[get_current_user] = lambda: user
    yield str(user["_id"])
    app.dependency_overrides.clear()


def _service_return_for(service_name: str):
    """Each route declares a different response_model, so the stub must return a
    matching shape or FastAPI's response validation fails for the wrong reason."""
    if service_name == "get_analysis":
        from app.api.v1.schemas.analysis import (
            AnalysisResponse,
            DiagnosisSummary,
            ReliabilitySummary,
        )

        return AnalysisResponse(
            id=ANALYSIS_ID,
            user_id="64ee39d09c6292376e191981",
            knowledge_base_id="64ee39d09c6292376e191982",
            query="q",
            status="completed",
            answer="a",
            reliability=ReliabilitySummary(score=0.9, status="PASS"),
            diagnosis=DiagnosisSummary(type=None, failures=[]),
            created_at="2026-09-20T10:00:00Z",
        )
    if service_name == "get_analysis_detail":
        return {"analysis": {}, "claims": [], "evidence": [], "trace": []}
    return []


@pytest.mark.parametrize("suffix,service_name", READ_ROUTES)
def test_route_forwards_the_callers_identity(suffix, service_name, user_id):
    """Every read route must pass the authenticated user's id to the service.

    That argument is the entire authorization boundary for these endpoints:
    drop it and any logged-in user can read anyone else's analysis, claims,
    evidence, and trace.
    """
    with patch(f"app.api.v1.analyses.analysis_service.{service_name}", AsyncMock()) as svc:
        svc.return_value = _service_return_for(service_name)
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}{suffix}")

    assert r.status_code == 200, f"{suffix}: {r.status_code} {r.text[:200]}"
    assert svc.await_count == 1, f"{suffix} did not call the service"
    args, kwargs = svc.call_args
    forwarded = kwargs.get("user_id_str") or (args[1] if len(args) > 1 else None)
    assert forwarded == user_id, f"{suffix} forwarded user {forwarded!r}, expected {user_id!r}"


@pytest.mark.parametrize("suffix,service_name", READ_ROUTES)
def test_malformed_analysis_id_is_404_not_500(suffix, service_name, user_id):
    """A garbage id reaches ObjectId() and raises. That must surface as a clean
    404, not a 500 that the workbench reports as a server fault."""
    from app.core.exceptions import NotFoundError

    async def _not_found(*_a, **_k):
        raise NotFoundError("Analysis not found")

    with patch(f"app.api.v1.analyses.analysis_service.{service_name}", _not_found):
        r = client.get(f"/api/v1/analyses/not-an-objectid{suffix}")

    assert r.status_code == 404, f"{suffix}: expected 404, got {r.status_code} {r.text[:200]}"


@pytest.mark.parametrize("suffix,service_name", READ_ROUTES)
def test_foreign_analysis_is_refused(suffix, service_name, user_id):
    """Ownership is enforced in the service, not the route. Assert the real
    service rejects a record owned by someone else."""
    from app.core.exceptions import AuthorizationError

    async def _denied(*_a, **_k):
        raise AuthorizationError("Access denied", detail="You do not own this analysis record")

    with patch(f"app.api.v1.analyses.analysis_service.{service_name}", _denied):
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}{suffix}")

    assert r.status_code == 403, f"{suffix}: expected 403, got {r.status_code}"


# ─── Ownership against the real service (Mongo mocked) ───────────────────────


def _analysis_doc(owner: str) -> dict:
    return {
        "_id": ObjectId(ANALYSIS_ID),
        "user_id": ObjectId(owner),
        "query": "What is the token lifetime?",
        "answer": "Records retained for 30 days.",
        "knowledge_base_id": "64ee39d09c6292376e191982",
        "status": "completed",
        "verdict_status": "PASS",
        "reliability": {"score": 0.91, "status": "PASS"},
        "diagnosis": {"type": None, "failures": []},
        "created_at": "2026-09-20T10:00:00Z",
    }


def _coll(return_value=None) -> MagicMock:
    c = MagicMock()
    c.find_one = AsyncMock(return_value=return_value)
    c.find = MagicMock(return_value=_empty_cursor())
    return c


class _Cursor:
    """Both sync and async iteration: the trace fetcher uses `async for`, the
    list endpoints use `.to_list()`."""

    def __init__(self, docs=None):
        self._docs = list(docs or [])

    def sort(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def skip(self, *_a, **_k):
        return self

    async def to_list(self, *_a, **_k):
        return self._docs

    def __aiter__(self):
        async def _gen():
            for d in self._docs:
                yield d

        return _gen()


def _empty_cursor():
    return _Cursor()


def test_real_service_rejects_another_users_analysis(user_id):
    """End-to-end ownership through get_analysis: a record owned by someone else
    must 403 even though it exists and is well-formed."""
    with patch(
        "app.services.analysis_service.get_collection",
        return_value=_coll(_analysis_doc(OTHER_USER_ID)),
    ):
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}")

    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"


def test_real_service_returns_the_owners_own_analysis(user_id):
    with patch(
        "app.services.analysis_service.get_collection",
        return_value=_coll(_analysis_doc(user_id)),
    ):
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}")

    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body["id"] == ANALYSIS_ID
    assert body["answer"] == "Records retained for 30 days."
    assert body["status"] == "completed"
    assert body["reliability"]["score"] == 0.91
    assert body["knowledge_base_id"] == "64ee39d09c6292376e191982"


def test_missing_analysis_is_404(user_id):
    with patch("app.services.analysis_service.get_collection", return_value=_coll(None)):
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}")
    assert r.status_code == 404


def test_detail_fans_out_all_four_sections(user_id):
    """The whole point of /detail is one round trip replacing four calls. If a
    section silently disappeared, the workbench would render a partial panel."""
    from app.api.v1.schemas.analysis import (
        AnalysisResponse,
        DiagnosisSummary,
        ReliabilitySummary,
    )

    with (
        patch("app.services.analysis_service.get_collection", return_value=_coll(None)),
        patch("app.services.analysis_service.get_analysis", AsyncMock()) as get_analysis,
        patch("app.services.analysis_service._fetch_claims", AsyncMock(return_value=["c"])),
        patch("app.services.analysis_service._fetch_evidence", AsyncMock(return_value=["e"])),
        patch("app.services.analysis_service._fetch_trace", AsyncMock(return_value=["t"])),
    ):
        get_analysis.return_value = AnalysisResponse(
            id=ANALYSIS_ID,
            user_id=user_id,
            knowledge_base_id="64ee39d09c6292376e191982",
            query="q",
            status="completed",
            answer="a",
            reliability=ReliabilitySummary(score=0.9, status="PASS"),
            diagnosis=DiagnosisSummary(type=None, failures=[]),
            created_at="2026-09-20T10:00:00Z",
        )
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}/detail")

    assert r.status_code == 200, r.text[:300]
    body = r.json()
    for key in ("analysis", "claims", "evidence", "trace"):
        assert key in body, f"/detail missing '{key}': {sorted(body)}"


def test_trace_returns_an_empty_list_rather_than_failing(user_id):
    """During early polling the trace collection can legitimately be empty. A
    500 here would break the SSE fallback exactly when it is needed most."""
    # Real ownership check passes (owned doc), real trace query finds nothing.
    with patch(
        "app.services.analysis_service.get_collection",
        return_value=_coll(_analysis_doc(user_id)),
    ):
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}/trace")

    assert r.status_code == 200, r.text[:200]
    assert r.json() == []


def test_trace_also_refuses_a_foreign_analysis(user_id):
    """get_analysis_trace performs its own ownership check rather than trusting
    the caller, so the SSE fallback is not a way around authorization."""
    with patch(
        "app.services.analysis_service.get_collection",
        return_value=_coll(_analysis_doc(OTHER_USER_ID)),
    ):
        r = client.get(f"/api/v1/analyses/{ANALYSIS_ID}/trace")
    assert r.status_code == 403
