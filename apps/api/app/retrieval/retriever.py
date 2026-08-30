"""
TRUSTRAG — Hybrid dense + sparse search retriever with RRF and temporal filtering.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

from qdrant_client.http import models

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.core.model_registry import get_embedding_model
from app.db.mongodb import Collections, get_collection
from app.db.qdrant import get_collection_name, get_qdrant_client
from app.ingestion.sparse_vector import generate_sparse_vector

logger = get_logger(__name__)


async def dense_search(query: str, kb_id: str, top_k: int = 20) -> list[Any]:
    """Retrieve top_k chunks using dense vector embeddings (sentence-transformers)."""
    try:
        client = get_qdrant_client()
        collection_name = get_collection_name(kb_id)
        embed_model = get_embedding_model()

        # Embed query text
        query_vector = embed_model.embed_query(query)

        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )
            return response.points
        else:
            return client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
    except Exception as exc:
        logger.error("Dense search failed", kb_id=kb_id, error=str(exc))
        return []


async def sparse_search(query: str, kb_id: str, top_k: int = 20) -> list[Any]:
    """Retrieve top_k chunks using token-frequency sparse representations."""
    try:
        client = get_qdrant_client()
        collection_name = get_collection_name(kb_id)

        # Generate token weights with query-noise stopword filtering
        sparse_rep = generate_sparse_vector(query, is_query=True)
        if not sparse_rep["indices"]:
            return []

        sparse_vec = models.SparseVector(indices=sparse_rep["indices"], values=sparse_rep["values"])

        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=collection_name,
                query=sparse_vec,
                using="sparse-text",
                limit=top_k,
                with_payload=True,
            )
            return response.points
        else:
            return client.search(
                collection_name=collection_name,
                query_vector=models.NamedSparseVector(
                    name="sparse-text",
                    vector=sparse_vec,
                ),
                limit=top_k,
                with_payload=True,
            )
    except Exception as exc:
        logger.error("Sparse search failed", kb_id=kb_id, error=str(exc))
        return []


def reciprocal_rank_fusion(
    dense_results: list[Any], sparse_results: list[Any], k: int = 60
) -> list[dict[str, Any]]:
    """
    Fuse dense and sparse rank results using Reciprocal Rank Fusion (RRF).

    RRF score = 1 / (rank_dense + k) + 1 / (rank_sparse + k)
    """
    fusion_map: dict[str, dict[str, Any]] = {}

    # Rank dense results (1-based index), capture score per-list
    for rank, point in enumerate(dense_results, start=1):
        fusion_map[point.id] = {
            "point": point,
            "dense_rank": rank,
            "sparse_rank": None,
            "dense_score": float(point.score),
            "sparse_score": 0.0,
        }

    # Rank sparse results — overwrite point reference only if not seen in dense
    for rank, point in enumerate(sparse_results, start=1):
        if point.id in fusion_map:
            fusion_map[point.id]["sparse_rank"] = rank
            fusion_map[point.id]["sparse_score"] = float(point.score)
        else:
            fusion_map[point.id] = {
                "point": point,
                "dense_rank": None,
                "sparse_rank": rank,
                "dense_score": 0.0,
                "sparse_score": float(point.score),
            }

    fused_results = []
    for pid, entry in fusion_map.items():
        dr = entry["dense_rank"]
        sr = entry["sparse_rank"]

        score_dense = 1.0 / (dr + k) if dr is not None else 0.0
        score_sparse = 1.0 / (sr + k) if sr is not None else 0.0
        rrf_score = score_dense + score_sparse

        # Serialize payload
        point = entry["point"]
        payload = point.payload or {}

        fused_results.append(
            {
                "id": pid,
                "text": payload.get("text", ""),
                "page": payload.get("page", 1),
                "character_offset": payload.get("character_offset", 0),
                "chunk_index": payload.get("chunk_index", 0),
                "document_id": payload.get("document_id"),
                "knowledge_base_id": payload.get("knowledge_base_id"),
                "dense_score": entry["dense_score"],
                "sparse_score": entry["sparse_score"],
                "rrf_score": rrf_score,
            }
        )

    # Sort descending by RRF score
    fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused_results


async def apply_temporal_filtering(
    results: list[dict[str, Any]], reference_time: datetime | None = None
) -> list[dict[str, Any]]:
    """
    Filter retrieved evidence segments using parent document temporal validity dates.

    Excludes chunks from documents where:
      - reference_time < effective_from
      - reference_time > effective_until
    """
    if not results:
        return []

    ref_time = reference_time or datetime.now(UTC)

    # Extract unique document IDs from results
    doc_ids = list({x["document_id"] for x in results if x["document_id"]})
    if not doc_ids:
        return results

    # Fetch document metadata records from MongoDB
    from bson import ObjectId
    from bson.errors import InvalidId

    doc_coll = get_collection(Collections.DOCUMENTS)

    doc_objs = []
    for did in doc_ids:
        with contextlib.suppress(InvalidId):
            doc_objs.append(ObjectId(did))

    docs_cursor = doc_coll.find({"_id": {"$in": doc_objs}})
    docs_map = {}
    async for d in docs_cursor:
        docs_map[str(d["_id"])] = d

    filtered_results = []
    for r in results:
        doc_id_str = r["document_id"]
        doc_meta = docs_map.get(doc_id_str)

        if not doc_meta:
            # Fallback: keep if doc record is missing
            filtered_results.append(r)
            continue

        eff_from = doc_meta.get("effective_from")
        eff_until = doc_meta.get("effective_until")

        # Populate document metadata dynamically
        r["filename"] = doc_meta.get("filename")
        r["effective_from"] = eff_from
        r["effective_until"] = eff_until

        # Apply boundary checks
        if eff_from and ref_time < eff_from:
            logger.debug("Filtered chunk due to effective_from window limit", doc_id=doc_id_str)
            continue
        if eff_until and ref_time > eff_until:
            logger.debug("Filtered chunk due to effective_until window limit", doc_id=doc_id_str)
            continue

        filtered_results.append(r)

    return filtered_results


async def retrieve_hybrid_chunks(
    query: str,
    kb_id: str,
    reference_time: datetime | None = None,
    top_k_override: int | None = None,
) -> list[dict[str, Any]]:
    """
    Primary hybrid dense + sparse retrieval coordinator.

    Performs dual-retrieval, fuses using RRF, and applies temporal validity filters.
    Returns results ready for reranking or direct model generation context.
    """
    cfg = get_model_config()

    dense_top = top_k_override if top_k_override is not None else cfg.dense_top_k
    sparse_top = top_k_override if top_k_override is not None else cfg.sparse_top_k

    # Run dense + sparse searches concurrently
    dense_res, sparse_res = await asyncio.gather(
        dense_search(query, kb_id, top_k=dense_top),
        sparse_search(query, kb_id, top_k=sparse_top),
    )

    # Fuse ranks
    fused = reciprocal_rank_fusion(dense_res, sparse_res, k=cfg.rrf_k)

    # Apply temporal document boundaries
    filtered = await apply_temporal_filtering(fused, reference_time)

    return filtered
