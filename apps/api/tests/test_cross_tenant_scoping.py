"""
Cross-tenant scoping for the cross-analysis list endpoints (audit T-8).

`/evidence`, `/claims` and `/conflicts` are the only endpoints that read
ACROSS a user's analyses rather than one analysis at a time. That makes them
a data-leak surface: a missing `user_id` filter exposes every tenant's claims
and evidence text.

These tests seed documents for user A and assert user B sees nothing — on both
the `user_id` path and the legacy `analysis_id` fallback path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from bson import ObjectId

from app.services import analysis_service as svc

USER_A = "64ee39d09c6292376e191981"
USER_B = "64ee39d09c6292376e199001"
ANALYSIS_A = "64ee39d09c6292376e1919aa"


class _Cursor:
    """Minimal async cursor over an in-memory doc list."""

    def __init__(self, docs):
        self._docs = docs

    def sort(self, *_a, **_k):
        return self

    def skip(self, _n):
        return self

    def limit(self, _n):
        return self

    async def to_list(self, *_a, **_k):
        return list(self._docs)

    def __aiter__(self):
        async def _gen():
            for d in self._docs:
                yield d

        return _gen()


def _matches(doc: dict, filt: dict | None) -> bool:
    """Minimal Mongo equality/$in matcher — enough to prove scoping."""
    if not filt:
        return True
    for key, want in filt.items():
        got = doc.get(key)
        if isinstance(want, dict) and "$in" in want:
            if got not in want["$in"]:
                return False
        elif isinstance(want, dict) and "$nin" in want:
            if got in want["$nin"]:
                return False
        elif got != want:
            return False
    return True


class _Coll:
    def __init__(self, docs=None, analyses=None):
        self.docs = docs or []
        self.analyses = analyses or []
        self.find_filter = None

    def find(self, filt=None, *_a, **_k):
        self.find_filter = filt
        if self.analyses:
            return _Cursor([a for a in self.analyses if _matches(a, filt)])
        return _Cursor([d for d in self.docs if _matches(d, filt)])

    def count_documents(self, *_a, **_k):
        async def _c():
            return len(self.docs)

        return _c()

    async def aggregate(self, *_a, **_k):
        if False:  # pragma: no cover - generator protocol
            yield {}


def _evidence_doc(**over):
    doc = {
        "_id": ObjectId(),
        "analysis_id": ObjectId(ANALYSIS_A),
        "user_id": ObjectId(USER_A),
        "text": "secret tenant A evidence",
        "text_hash": "abc",
        "created_at": datetime(2026, 10, 1, tzinfo=UTC),
        "chunk_index": 0,
        "page": 1,
        "character_offset": 0,
        "zone": "body",
        "integrity_status": "VERIFIED",
        "document_id": ObjectId(),
        "chunk_id": "c1",
        "rerank_score": 1.0,
    }
    doc.update(over)
    return doc


def _claim_doc(**over):
    doc = {
        "_id": ObjectId(),
        "analysis_id": ObjectId(ANALYSIS_A),
        "user_id": ObjectId(USER_A),
        "text": "secret tenant A claim",
        "state": "SUPPORTED",
        "explanation": "because",
        "created_at": datetime(2026, 10, 1, tzinfo=UTC),
        "claim_index": 0,
        "evidence_ids": [],
    }
    doc.update(over)
    return doc


@pytest.mark.asyncio
async def test_list_all_user_evidence_is_scoped_to_the_caller():
    """User B must never see user A's evidence rows."""
    ev = _Coll(docs=[_evidence_doc()])
    with patch.object(svc, "get_collection", side_effect=lambda _n: ev):
        await svc.list_all_user_evidence(USER_B, limit=50, skip=0)

    # The tenant filter must be the query, not a post-filter.
    assert ev.find_filter == {"user_id": ObjectId(USER_B)}
    # The filter IS the tenant boundary: Mongo returns nothing for user B. The
    # fake applies the same equality match, so an unscoped query would return
    # the seeded row and fail this assertion.


@pytest.mark.asyncio
async def test_list_all_user_claims_is_scoped_to_the_caller():
    claims = _Coll(docs=[_claim_doc()])
    with patch.object(svc, "get_collection", side_effect=lambda n: claims):
        await svc.list_all_user_claims(USER_B, limit=50, skip=0)
    assert claims.find_filter == {"user_id": ObjectId(USER_B)}


@pytest.mark.asyncio
async def test_legacy_evidence_fallback_stays_scoped():
    """Docs written before the user_id backfill carry only analysis_id. The
    fallback must scope by the CALLER's analyses, never by a global list."""
    legacy_ev = _Coll(docs=[_evidence_doc(user_id=None)])
    analyses = _Coll(analyses=[{"_id": ObjectId(ANALYSIS_A), "user_id": ObjectId(USER_A)}])

    seen_filters = []

    def _collection(name):
        seen_filters.append(name)
        return analyses if name == "analyses" else legacy_ev

    with patch.object(svc, "get_collection", side_effect=_collection):
        rows = await svc.list_all_user_evidence(USER_B, limit=50, skip=0)

    # Fallback was consulted, and it looked up user B's analyses (none), so the
    # second query never ran and no rows leak.
    assert "analyses" in seen_filters
    assert rows == []


@pytest.mark.asyncio
async def test_legacy_claim_fallback_returns_owner_rows_only():
    legacy_claims = _Coll(docs=[_claim_doc(user_id=None)])
    analyses = _Coll(analyses=[{"_id": ObjectId(ANALYSIS_A), "user_id": ObjectId(USER_A)}])

    def _collection(name):
        return analyses if name == "analyses" else legacy_claims

    with patch.object(svc, "get_collection", side_effect=_collection):
        rows_b = await svc.list_all_user_claims(USER_B, limit=50, skip=0)
    assert rows_b == []

    # The owner still sees their legacy rows.
    with patch.object(svc, "get_collection", side_effect=_collection):
        rows_a = await svc.list_all_user_claims(USER_A, limit=50, skip=0)
    assert len(rows_a) == 1
    assert rows_a[0].text == "secret tenant A claim"


@pytest.mark.asyncio
async def test_conflicts_endpoint_never_leaks_foreign_analyses():
    """Conflicts merge two collections keyed on the caller's analysis ids."""
    foreign_claim = _claim_doc(state="CONTRADICTED", analysis_id=ObjectId())
    own_claim = _claim_doc(state="CONTRADICTED")
    claims = _Coll(docs=[own_claim, foreign_claim])
    evidence = _Coll(docs=[])
    analyses = _Coll(
        analyses=[{"_id": ObjectId(ANALYSIS_A), "query": "q", "user_id": ObjectId(USER_A)}]
    )

    def _collection(name):
        return {"analyses": analyses, "claims": claims, "evidence": evidence}[name]

    with patch.object(svc, "get_collection", side_effect=_collection):
        rows = await svc.list_all_user_conflicts(USER_A, limit=50, skip=0)

    # Only the caller's analysis_id may be attached to a conflict row.
    for row in rows:
        assert row["analysis_id"] == ANALYSIS_A
    assert claims.find_filter["analysis_id"] == {"$in": [ObjectId(ANALYSIS_A)]}
