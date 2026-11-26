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

    # One round-trip instead of one per chunk. The lookup key is
    # (document_id, text) within the analysis, so a single $or over the
    # candidate keys returns every already-persisted chunk at once. With
    # top_k chunks per claim and up to `max_verification_claims` claims, the
    # old per-chunk find_one cost dozens of round-trips per analysis.
    doc_ids = [_safe_object_id(chunk.get("document_id")) for chunk in verified]
    texts = [chunk.get("text", "") for chunk in verified]
    or_clauses = [
        {"document_id": doc_id, "text": text} for doc_id, text in zip(doc_ids, texts, strict=True)
    ]
    existing_by_key: dict[tuple[Any, str], Any] = {}
    if or_clauses:
        cursor = evidence_coll.find({"analysis_id": analysis_id, "$or": or_clauses})
        found = [doc async for doc in cursor]
        # Sort by _id so "the first match" is the earliest persisted row,
        # matching what a per-chunk find_one would have returned.
        found.sort(key=lambda doc: str(doc.get("_id")))
        for doc in found:
            if doc.get("_id") is None:
                continue
            key = (doc.get("document_id"), doc.get("text", ""))
            existing_by_key.setdefault(key, doc["_id"])

    for position, chunk in enumerate(verified):
        doc_id = doc_ids[position]
        text = texts[position]
        existing_id = existing_by_key.get((doc_id, text))
        if existing_id is not None:
            pairs.append((chunk, existing_id))
        else:
            missing_positions.append(position)
            missing_docs.append(
                {
                    "analysis_id": analysis_id,
                    "user_id": ObjectId(user_id_str) if user_id_str else None,
                    "text": text,
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
