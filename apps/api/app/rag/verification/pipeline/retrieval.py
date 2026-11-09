"""
TRUSTRAG — Claim verification pipeline: retrieval.

Targeted claim evidence retrieval and persistence operations.
Extracted from the flat ``verifier.py`` module into its own focused file.
"""

from __future__ import annotations

from typing import Any

from app.observability.logging import get_logger
from app.persistence.mongodb import Collections, get_collection
from app.rag.retrieval import retriever as retriever_mod
from app.rag.verification import integrity as integrity_mod
from app.rag.verification.pipeline.infra import _chunk_identity, _safe_object_id

logger = get_logger(__name__)

__all__ = [
    "_persist_claim_evidence",
    "retrieve_evidence_for_claim",
]


async def retrieve_evidence_for_claim(
    claim_text: str,
    kb_id_str: str,
    seen_keys: set[tuple[str, Any, str]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Targeted hybrid retrieval for one unverified claim."""
    try:
        results = await retriever_mod.retrieve_hybrid_chunks(
            claim_text, kb_id_str, top_k_override=top_k
        )
    except Exception:
        logger.warning("Targeted claim retrieval failed; keeping original verdict", exc_info=True)
        return []
    fresh = [c for c in results if _chunk_identity(c) not in seen_keys]
    return fresh[:top_k]


async def _persist_claim_evidence(
    analysis_id: Any,
    user_id_str: str | None,
    chunks: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], Any]]:
    """Integrity-audit, deduplicate, and persist targeted-retrieval chunks."""
    from datetime import UTC, datetime

    from bson import ObjectId

    audited = await integrity_mod.audit_evidence_integrity(chunks)
    verified = [c for c in audited if c.get("integrity_status") == "VERIFIED"]
    if not verified:
        return []

    evidence_coll = get_collection(Collections.EVIDENCE)
    pairs: list[tuple[dict[str, Any], Any]] = []
    missing_docs: list[dict[str, Any]] = []
    missing_positions: list[int] = []
    for position, chunk in enumerate(verified):
        doc_id = _safe_object_id(chunk.get("document_id"))
        existing = await evidence_coll.find_one(
            {"analysis_id": analysis_id, "document_id": doc_id, "text": chunk.get("text", "")}
        )
        if existing is not None and existing.get("_id") is not None:
            pairs.append((chunk, existing["_id"]))
        else:
            missing_positions.append(position)
            missing_docs.append(
                {
                    "analysis_id": analysis_id,
                    "user_id": ObjectId(user_id_str) if user_id_str else None,
                    "text": chunk.get("text", ""),
                    "document_id": doc_id,
                    "filename": chunk.get("filename"),
                    "url": chunk.get("url"),
                    "retrieval_score": chunk.get("dense_score", 0.0),
                    "fusion_score": chunk.get("rrf_score", 0.0),
                    "rerank_score": chunk.get("rerank_score"),
                    "method": chunk.get("method", "claim_retrieval"),
                    "integrity_status": "VERIFIED",
                    "effective_from": chunk.get("effective_from"),
                    "effective_until": chunk.get("effective_until"),
                    "created_at": datetime.now(UTC),
                }
            )

    if missing_docs:
        try:
            insert_res = await evidence_coll.insert_many(missing_docs)
            new_ids = list(insert_res.inserted_ids)
        except TypeError:
            new_ids = []
            for doc in missing_docs:
                res = await evidence_coll.insert_one(doc)
                new_ids.append(res.inserted_id)
        for position, new_id in zip(missing_positions, new_ids, strict=False):
            pairs.append((verified[position], new_id))

    order = {id(chunk): i for i, chunk in enumerate(verified)}
    pairs.sort(key=lambda pair: order[id(pair[0])])
    return pairs
