"""
TRUSTRAG — Hybrid dense + sparse search retriever with RRF and temporal filtering.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from qdrant_client.http import models

from app.core.config import get_model_config
from app.core.exceptions import RetrievalOutageError
from app.core.logging import get_logger
from app.core.model_registry import get_embedding_model
from app.db.mongodb import Collections, get_collection
from app.db.qdrant import get_collection_name, get_qdrant_client
from app.ingestion.sparse_vector import generate_sparse_vector

logger = get_logger(__name__)


# Maximum time allowed for the complete hybrid retrieval operation.
HYBRID_TIMEOUT = 60.0

async def _get_collection_dimension(
    client: Any,
    collection_name: str,
) -> int | None:
    """Read the Qdrant collection vector dimension."""
    col_info = await client.get_collection(collection_name)
    return getattr(col_info.config.params.vectors, "size", None)

def _hybrid_timeout() -> float:
    cfg = get_model_config()
    value = os.environ.get("RETRIEVAL_HYBRID_TIMEOUT_SECONDS") or cfg.hybrid_timeout_seconds

    try:
        return float(value) if value else HYBRID_TIMEOUT
    except (TypeError, ValueError):
        return HYBRID_TIMEOUT

async def dense_search(
    query: str,
    kb_id: str,
    top_k: int = 20,
) -> list[Any]:
    """Retrieve top_k chunks using dense vector embeddings.

    Raises:
        RetrievalOutageError: When the retrieval infrastructure (Qdrant or the
            embedding service) is unavailable. This is an outage, NOT evidence
            that the knowledge base lacks matching content.
        ValueError: When the query embedding dimension does not match the
            collection dimension.
    """
    if top_k <= 0:
        # Zero budget disables the dense leg.
        return []

    try:
        client = await get_qdrant_client()
        collection_name = get_collection_name(kb_id)

        target_dim = await _get_collection_dimension(
            client,
            collection_name,
        )

        try:
            embed_model = get_embedding_model()
            query_vector = await asyncio.to_thread(
                embed_model.embed_query,
                query,
            )
        except Exception as exc:
            logger.error(
                "Embedding service unavailable for dense search",
                error=str(exc),
            )
            raise RetrievalOutageError(
                f"Embedding service unavailable during dense retrieval: {exc}",
                detail=str(exc),
            ) from exc

        if target_dim is not None and len(query_vector) != target_dim:
            raise ValueError(
                "Embedding dimension mismatch: "
                f"query={len(query_vector)}, collection={target_dim}"
            )

        response = await client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )

        # Empty result = valid "no evidence", not an outage.
        return list(getattr(response, "points", []) or [])

    except RetrievalOutageError:
        raise
    except ValueError:
        # Preserve invariant/configuration errors as-is.
        raise
    except Exception as exc:
        logger.error(
            "Dense search failed",
            kb_id=kb_id,
            error=str(exc),
        )
        raise RetrievalOutageError(
            f"Vector store query failed during dense retrieval: {exc}",
            detail=str(exc),
        ) from exc

async def sparse_search(query: str, kb_id: str, top_k: int = 20) -> list[Any]:
    """Retrieve top_k chunks using BM25-style sparse representations.

    Client vectors carry saturated TF weights (see app/ingestion/sparse_vector.py);
    Qdrant multiplies query-time IDF from collection statistics
    (sparse-text uses Modifier.IDF).

    Raises:
        RetrievalOutageError: When the vector store is unavailable. An empty
            sparse representation (query with no indexable tokens) is genuine
            "no evidence" and returns [] instead.
    """
    if top_k <= 0:
        # Zero budget disables the sparse leg (single-leg ablations, e.g.
        # dense-only via sparse_top_k=0). Qdrant rejects limit=0, so never
        # send the query: successful empty — never an outage.
        return []
    try:
        client = await get_qdrant_client()
    except Exception as exc:
        logger.error("Qdrant client unavailable for sparse search", error=str(exc))
        raise RetrievalOutageError(
            f"Vector store unavailable during sparse retrieval: {exc}", detail=str(exc)
        ) from exc
    collection_name = get_collection_name(kb_id)

    try:
        # Generate token weights with query-noise stopword filtering
        sparse_rep = generate_sparse_vector(query, is_query=True)
    except Exception as exc:
        logger.error(
            "Sparse vector generation failed",
            kb_id=kb_id,
            error=str(exc),
        )
        raise RetrievalOutageError(
            f"Sparse vector generation failed during sparse retrieval: {exc}",
            detail=str(exc),
        ) from exc

    sparse_vec = models.SparseVector(indices=sparse_rep["indices"], values=sparse_rep["values"])

    try:
        response = await client.query_points(
            collection_name=collection_name,
            query=sparse_vec,
            using="sparse-text",
            limit=top_k,
            with_payload=True,
        )
        # A successful, empty response is genuine "no evidence" — NOT an outage.
        return list(getattr(response, "points", []) or [])
    except Exception as exc:
        logger.error("Sparse search failed", kb_id=kb_id, error=str(exc))
        raise RetrievalOutageError(
            f"Vector store query failed during sparse retrieval: {exc}", detail=str(exc)
        ) from exc


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
                # OCR provenance: OCR flags + image ref + version ride the
                # fused row so answers stay traceable to page images.
                "ocr_used": bool(payload.get("ocr_used", False)),
                "ocr_confidence": payload.get("ocr_confidence"),
                "page_image_ref": payload.get("page_image_ref"),
                "document_version": payload.get("document_version"),
                "is_snapshot": bool(payload.get("is_snapshot", False)),
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

    # Fetch document metadata records from MongoDB (batched)
    doc_coll = get_collection(Collections.DOCUMENTS)

    doc_objs = []
    for did in doc_ids:
        with contextlib.suppress(InvalidId):
            doc_objs.append(ObjectId(did))

    # Batch fetch all document metadata in parallel
    docs_cursor = doc_coll.find({"_id": {"$in": doc_objs}})
    docs_map = {}
    async for d in docs_cursor:
        docs_map[str(d["_id"])] = d

    filtered_results = []
    for r in results:
        doc_id_str = r.get("document_id")
        doc_meta = docs_map.get(doc_id_str)

        if doc_meta is None and doc_id_str is not None:
            # Retrieval-time stale-evidence guard (historical note): the
            # parent document record is gone (deleted/rolled-back) but its
            # vectors still serve — drop the point, never serve it.
            logger.debug("Dropping orphan point with no parent document", doc_id=doc_id_str)
            continue

        if not doc_meta:
            # No document_id at all: unjudgeable legacy point — fail open.
            filtered_results.append(r)
            continue

        eff_from = doc_meta.get("effective_from")
        eff_until = doc_meta.get("effective_until")

        # Populate document metadata dynamically
        r["filename"] = doc_meta.get("filename")
        r["effective_from"] = eff_from
        r["effective_until"] = eff_until
        # page-image chain: live version truth comes from the parent record.
        r["document_version"] = doc_meta.get("version", "1.0")
        r["is_snapshot"] = bool(doc_meta.get("is_snapshot", False))

        # Apply boundary checks (normalize naive datetimes to UTC-aware
        # so legacy Mongo records never raise TypeError on comparison).
        if eff_from and getattr(eff_from, "tzinfo", None) is None:
            eff_from = eff_from.replace(tzinfo=UTC)
        if eff_until and getattr(eff_until, "tzinfo", None) is None:
            eff_until = eff_until.replace(tzinfo=UTC)
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
    """Retrieve evidence using dense + sparse retrieval and RRF.

    Both retrieval branches are required. Failure of either branch fails
    the entire retrieval operation.
    """
    cfg = get_model_config()

    dense_top = top_k_override if top_k_override is not None else cfg.dense_top_k
    sparse_top = top_k_override if top_k_override is not None else cfg.sparse_top_k
    fusion_top_k = cfg.fusion_top_k

    hybrid_timeout = _hybrid_timeout()
 
    dense_task = asyncio.create_task(
        dense_search(query, kb_id, top_k=dense_top)
    )
    sparse_task = asyncio.create_task(
        sparse_search(query, kb_id, top_k=sparse_top)
    )

    try:
        dense_res, sparse_res = await asyncio.wait_for(
            asyncio.gather(dense_task, sparse_task),
            timeout=hybrid_timeout,
        )
    except TimeoutError as exc:
        dense_task.cancel()
        sparse_task.cancel()

        await asyncio.gather(
            dense_task,
            sparse_task,
            return_exceptions=True,
        )

        raise RetrievalOutageError(
            f"Hybrid retrieval timed out after {hybrid_timeout:g}s",
            detail=str(exc),
        ) from exc
    except Exception:
        dense_task.cancel()
        sparse_task.cancel()

        await asyncio.gather(
            dense_task,
            sparse_task,
            return_exceptions=True,
        )
        raise

    fused = reciprocal_rank_fusion(
        dense_res,
        sparse_res,
        k=cfg.rrf_k,
    )

    filtered = await apply_temporal_filtering(
        fused,
        reference_time,
    )

    if fusion_top_k > 0:
        filtered = filtered[:fusion_top_k]

    return filtered