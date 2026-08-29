"""
TRUSTRAG — Real-time evidence integrity audits.

Pulls chunk definitions from MongoDB 'document_chunks' collection and compares
sha256 hashes against retrieved Qdrant text chunks to verify authenticity.
"""

from __future__ import annotations

import hashlib
from typing import Any

from bson import ObjectId

from app.core.logging import get_logger
from app.db.mongodb import Collections, get_collection

logger = get_logger(__name__)


async def audit_evidence_integrity(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Audit retrieved segments by comparing their hashes with MongoDB definitions.

    Sets 'integrity_status' parameter to 'VERIFIED' or 'CORRUPTED'.
    """
    if not chunks:
        return []

    # Map chunks by (document_id, chunk_index) for fast matching
    chunk_keys = []
    chunk_map = {}

    for c in chunks:
        doc_id_str = c.get("document_id")
        chunk_idx = c.get("chunk_index")

        if doc_id_str and chunk_idx is not None:
            try:
                doc_obj = ObjectId(doc_id_str)
                key = (doc_id_str, chunk_idx)
                chunk_keys.append({"document_id": doc_obj, "chunk_index": chunk_idx})
                chunk_map[key] = c
            except Exception:
                # Default to corrupted on invalid object ID formats
                c["integrity_status"] = "CORRUPTED"
        else:
            c["integrity_status"] = "CORRUPTED"

    # Fetch reference hashes from MongoDB document_chunks
    if chunk_keys:
        chunks_coll = get_collection(Collections.DOCUMENT_CHUNKS)
        query = {"$or": chunk_keys}

        async for ref in chunks_coll.find(query):
            doc_id_str = str(ref["document_id"])
            chunk_idx = ref["chunk_index"]
            ref_hash = ref.get("text_hash")

            key = (doc_id_str, chunk_idx)
            retrieved_chunk = chunk_map.get(key)

            if retrieved_chunk and ref_hash:
                text = retrieved_chunk.get("text", "")
                computed_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

                # Check for tamper/alteration
                if computed_hash == ref_hash:
                    retrieved_chunk["integrity_status"] = "VERIFIED"
                else:
                    logger.warning(
                        "Integrity audit mismatch found",
                        document_id=doc_id_str,
                        chunk_index=chunk_idx,
                        computed=computed_hash,
                        expected=ref_hash,
                    )
                    retrieved_chunk["integrity_status"] = "CORRUPTED"

    # Ensure any chunk that didn't get verified is marked corrupted
    for c in chunks:
        if "integrity_status" not in c:
            logger.warning(
                "Reference chunk missing in database",
                document_id=c.get("document_id"),
                chunk_index=c.get("chunk_index"),
            )
            c["integrity_status"] = "CORRUPTED"

    return chunks
