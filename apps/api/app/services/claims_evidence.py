"""
TRUSTRAG — Analysis service: claims and evidence CRUD.

Read operations for claims, evidence, and conflicts across analyses.
"""

from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.api.v1.schemas.analysis import ClaimResponse, EvidenceResponse
from app.persistence.mongodb import Collections

# Lazy reference to the analysis_service shim, resolved at call time so tests
# that monkeypatch app.services.analysis_service.get_collection take effect.
# Importing it at module scope would be circular: analysis_service imports this
# module.
_svc_mod = None


def _svc():
    global _svc_mod
    if _svc_mod is None:
        import app.services.analysis_service as _m

        _svc_mod = _m
    return _svc_mod


def _get_collection(name):
    return _svc().get_collection(name)


__all__ = [
    "list_all_user_claims",
    "list_all_user_conflicts",
    "list_all_user_evidence",
    "list_analysis_claims",
    "list_analysis_evidence",
]


async def list_analysis_claims(
    analysis_id_str: str, user_id_str: str | None = None, limit: int = 200, skip: int = 0
) -> list[ClaimResponse]:
    """Fetch claims for a single analysis."""
    claims_coll = _get_collection(Collections.CLAIMS)
    query: dict[str, Any] = {"analysis_id": ObjectId(analysis_id_str)}
    cursor = claims_coll.find(query).sort("created_at", -1).skip(skip).limit(min(limit, 200))
    results = []
    async for c in cursor:
        results.append(_serialize_claim(c))
    return results


def _serialize_claim(c: dict[str, Any]) -> ClaimResponse:
    """Serialize a stored claim.

    The canonical serializer lives in ``pipeline.py`` and is re-exported by
    the analysis_service shim. It is the one that knows a Mongo ObjectId
    has to become a string before Pydantic will accept it. This module
    used to carry a second copy that did not, which is why every claim
    with an evidence reference failed validation and the endpoint answered
    500.
    """
    return _svc().serialize_claim(c)


async def list_all_user_claims(
    user_id_str: str, limit: int = 200, skip: int = 0
) -> list[ClaimResponse]:
    """Fetch all claims for a user across all analyses."""
    analyses_coll = _get_collection(Collections.ANALYSES)
    user_analyses = await analyses_coll.find(
        {"user_id": ObjectId(user_id_str)}, {"_id": 1}
    ).to_list(1000)
    if not user_analyses:
        return []
    a_ids = [a["_id"] for a in user_analyses]

    claims_coll = _get_collection(Collections.CLAIMS)
    cursor = (
        claims_coll.find({"analysis_id": {"$in": a_ids}})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(limit, 200))
    )
    results = []
    async for c in cursor:
        results.append(_serialize_claim(c))
    return results


async def list_analysis_evidence(
    analysis_id_str: str, limit: int = 200, skip: int = 0
) -> list[EvidenceResponse]:
    """Fetch evidence for a single analysis."""
    evidence_coll = _get_collection(Collections.EVIDENCE)
    cursor = (
        evidence_coll.find({"analysis_id": ObjectId(analysis_id_str)})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(limit, 200))
    )
    rows = [e async for e in cursor]
    await _fill_document_metadata(rows)
    return [_serialize_evidence(e) for e in rows]


async def _fill_document_metadata(rows: list[dict[str, Any]]) -> None:
    """Fill in the document fields an evidence row does not carry.

    The agent graph used to write a narrower evidence document than the one
    the claim-retrieval path writes, so every run it produced has no
    filename and no scores — the vault could only show a raw ObjectId. The
    writer is fixed, but the rows that are already stored still need the
    names, so they are joined back to their parent document here, in one
    batched lookup per request.
    """
    if not rows:
        return

    doc_ids: list[ObjectId] = []
    for row in rows:
        if row.get("filename"):
            continue
        raw_id = row.get("document_id")
        if not isinstance(raw_id, ObjectId):
            continue
        if raw_id not in doc_ids:
            doc_ids.append(raw_id)

    if not doc_ids:
        return

    documents_coll = _get_collection(Collections.DOCUMENTS)
    docs_map: dict[str, dict[str, Any]] = {}
    async for doc in documents_coll.find({"_id": {"$in": doc_ids}}):
        docs_map[str(doc["_id"])] = doc

    if not docs_map:
        return

    for row in rows:
        raw_id = row.get("document_id")
        if not isinstance(raw_id, ObjectId):
            continue
        meta = docs_map.get(str(raw_id))
        if not meta:
            continue
        if not row.get("filename"):
            row["filename"] = meta.get("filename")
        if row.get("effective_from") is None:
            row["effective_from"] = meta.get("effective_from")
        if row.get("effective_until") is None:
            row["effective_until"] = meta.get("effective_until")


def _serialize_evidence(e: dict[str, Any]) -> EvidenceResponse:
    """Serialize a stored evidence chunk.

    The canonical serializer lives in ``pipeline.py``. This module used to
    carry a second copy that dropped ``analysis_id`` and handed the raw
    ObjectId straight to the response model, so every evidence row failed
    validation and the vault answered 500.
    """
    return _svc().serialize_evidence(e)


async def list_all_user_evidence(
    user_id_str: str, limit: int = 200, skip: int = 0
) -> list[EvidenceResponse]:
    """Fetch all evidence for a user across all analyses."""
    analyses_coll = _get_collection(Collections.ANALYSES)
    user_analyses = await analyses_coll.find(
        {"user_id": ObjectId(user_id_str)}, {"_id": 1}
    ).to_list(1000)
    if not user_analyses:
        return []
    a_ids = [a["_id"] for a in user_analyses]

    evidence_coll = _get_collection(Collections.EVIDENCE)
    cursor = (
        evidence_coll.find({"analysis_id": {"$in": a_ids}})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(limit, 200))
    )
    rows = [e async for e in cursor]
    await _fill_document_metadata(rows)
    return [_serialize_evidence(e) for e in rows]


async def list_all_user_conflicts(
    user_id_str: str, limit: int = 50, skip: int = 0
) -> list[dict[str, Any]]:
    """Fetch all detected conflicts across all analyses for this user."""
    analyses_coll = _get_collection(Collections.ANALYSES)
    user_analyses = await analyses_coll.find(
        {"user_id": ObjectId(user_id_str)}, {"_id": 1, "query": 1}
    ).to_list(1000)
    if not user_analyses:
        return []

    analysis_map = {str(a["_id"]): a.get("query", "") for a in user_analyses}
    a_ids = [a["_id"] for a in user_analyses]

    claims_coll = _get_collection(Collections.CLAIMS)
    evidence_coll = _get_collection(Collections.EVIDENCE)

    conflicts = []

    per_source = min(skip + limit, 100)
    cursor_claims = (
        claims_coll.find({"analysis_id": {"$in": a_ids}, "state": "CONTRADICTED"})
        .sort("created_at", -1)
        .limit(per_source)
    )
    async for c in cursor_claims:
        conflicts.append(
            {
                "id": str(c["_id"]),
                "type": "claim_contradiction",
                "title": "Claim Contradicted by Retrieved Evidence",
                "claim": c["text"],
                "explanation": c.get("explanation") or "Evidence contradicts this assertion.",
                "analysis_id": str(c["analysis_id"]),
                "query": analysis_map.get(str(c["analysis_id"]), ""),
                "created_at": c.get("created_at"),
            }
        )

    cursor_evidence = (
        evidence_coll.find(
            {"analysis_id": {"$in": a_ids}, "integrity_status": {"$nin": ["VERIFIED", None]}}
        )
        .sort("created_at", -1)
        .limit(per_source)
    )
    async for e in cursor_evidence:
        conflicts.append(
            {
                "id": str(e["_id"]),
                "type": "integrity_compromise",
                "title": f"Evidence Integrity Compromised: {e.get('integrity_status')}",
                "claim": (e["text"][:200] + "...")
                if len(e.get("text", "")) > 200
                else e.get("text", ""),
                "explanation": f"Integrity check flagged status: {e.get('integrity_status')}",
                "analysis_id": str(e["analysis_id"]),
                "query": analysis_map.get(str(e["analysis_id"]), ""),
                "created_at": c.get("created_at") if c else None,
            }
        )

    conflicts.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    return conflicts[skip : skip + limit]
