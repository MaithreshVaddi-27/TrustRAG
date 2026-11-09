"""
TRUSTRAG — Analysis service: claims and evidence CRUD.

Read operations for claims, evidence, and conflicts across analyses.
"""

from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.api.v1.schemas.analysis import ClaimResponse
from app.persistence.mongodb import Collections

# Lazy reference to the analysis_service shim, resolved at call time so tests
# that monkeypatch app.services.analysis_service.get_collection take effect.
_svc_mod = None


def _get_collection(name):
    global _svc_mod
    if _svc_mod is None:
        import app.services.analysis_service as _m

        _svc_mod = _m
    return _svc_mod.get_collection(name)


__all__ = [
    "list_all_user_claims",
    "list_all_user_conflicts",
    "list_all_user_evidence",
    "list_analysis_claims",
    "list_analysis_evidence",
]


async def list_analysis_claims(
    analysis_id_str: str, user_id_str: str | None = None, limit: int = 200, skip: int = 0
) -> list[dict[str, Any]]:
    """Fetch claims for a single analysis."""
    claims_coll = _get_collection(Collections.CLAIMS)
    query: dict[str, Any] = {"analysis_id": ObjectId(analysis_id_str)}
    cursor = claims_coll.find(query).sort("created_at", -1).skip(skip).limit(min(limit, 200))
    results = []
    async for c in cursor:
        results.append(_serialize_claim(c))
    return results


def _serialize_claim(c: dict[str, Any]) -> ClaimResponse:
    return ClaimResponse(
        id=str(c["_id"]),
        analysis_id=str(c["analysis_id"]),
        text=c.get("text", ""),
        subject=c.get("subject"),
        predicate=c.get("predicate"),
        object=c.get("object"),
        state=c.get("state"),
        explanation=c.get("explanation", ""),
        evidence_ids=c.get("evidence_ids", []),
        attempt=c.get("attempt", 0),
        created_at=c.get("created_at"),
    )


async def list_all_user_claims(
    user_id_str: str, limit: int = 200, skip: int = 0
) -> list[dict[str, Any]]:
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
) -> list[dict[str, Any]]:
    """Fetch evidence for a single analysis."""
    evidence_coll = _get_collection(Collections.EVIDENCE)
    cursor = (
        evidence_coll.find({"analysis_id": ObjectId(analysis_id_str)})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(limit, 200))
    )
    results = []
    async for e in cursor:
        results.append(_serialize_evidence(e))
    return results


def _serialize_evidence(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(e["_id"]),
        "text": e.get("text", ""),
        "filename": e.get("filename"),
        "document_id": e.get("document_id"),
        "integrity_status": e.get("integrity_status"),
        "retrieval_score": e.get("retrieval_score"),
        "rerank_score": e.get("rerank_score"),
        "created_at": e.get("created_at"),
    }


async def list_all_user_evidence(
    user_id_str: str, limit: int = 200, skip: int = 0
) -> list[dict[str, Any]]:
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
    results = []
    async for e in cursor:
        results.append(_serialize_evidence(e))
    return results


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
