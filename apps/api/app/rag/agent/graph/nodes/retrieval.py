"""
TRUSTRAG — LangGraph retrieval node.

Encapsulates all retrieval logic previously in graph.py's retrieval_node:
hybrid dense/sparse search, Qdrant rerank, web-search fallback, recovery
strategy handling (regenerate/re_retrieve), and self-heal re-indexing.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

from bson import ObjectId
from qdrant_client.http import models as qdrant_models

import app.rag.agent.graph as _graph_mod
from app.config import get_model_config
from app.llm import model_registry
from app.observability.logging import get_logger
from app.persistence import qdrant as qdrant_db
from app.persistence.mongodb import Collections
from app.rag.agent.graph.state import AgentState
from app.rag.ingestion import pipeline as pipeline_mod
from app.rag.ingestion.sparse_vector import generate_sparse_vector

logger = get_logger(__name__)

__all__ = ["retrieval_node"]


async def retrieval_node(state: AgentState) -> AgentState:
    """Execute hybrid retrieval, evidence integrity audit, and evidence persistence."""
    cfg = get_model_config()
    retrieval_timeout = cfg.llm_timeout_seconds  # Reuse LLM timeout for retrieval

    async def _run_retrieval() -> AgentState:
        logger.info("Agent Retrieval Node starting", attempt=state["attempts"] + 1)

        # Regenerate path: evidence already sufficient, prior failure was
        # generation-side. Skip retrieval entirely (no embedding, Qdrant,
        # rerank, or web-search spend) and retry generation on saved chunks.
        if state.get("recovery_strategy") == "regenerate" and state.get("chunks"):
            await _graph_mod.add_trace_event(
                state["analysis_id"],
                "retrieval.reused",
                {
                    "message": f"Reusing {len(state['chunks'])} saved segments — "
                    "no retrieval spend on regeneration retry",
                },
            )
            return state

        await _graph_mod.add_trace_event(
            state["analysis_id"],
            "retrieval.started",
            {"message": f"Searching knowledge base for query: '{state['current_query']}'"},
        )

        # 1. Hybrid Retrieval
        top_k_override = None
        max_context_override = None

        # Get tier-aware caps based on provider
        provider = state.get("llm_provider", cfg.llm_provider)
        caps = cfg.tier_caps(provider)
        max_context_chunks = caps["max_context_chunks"]

        if state["recovery_strategy"] == "re_retrieve":
            # Second layer (see recovery_node downgrade): only widen search when
            # evidence is actually thin — doubling on top of sufficient chunks
            # just burns embedding/rerank compute and overflows small contexts.
            if len(state.get("chunks") or []) >= max_context_chunks:
                await _graph_mod.add_trace_event(
                    state["analysis_id"],
                    "recovery.re_retrieve_skipped",
                    {
                        "message": "Evidence already sufficient — keeping narrow "
                        "retrieval instead of doubling search"
                    },
                )
            else:
                # OPT (local-LLM load): cap widened retrieval so recovery does
                # not pay 2x Qdrant/rerank/Mongo for chunks the generation cap
                # throws away anyway.
                top_k_override = min(cfg.dense_top_k * 2, max_context_chunks + 16)
                max_context_override = min(max_context_chunks * 2, max_context_chunks + 4)
                logger.info(
                    "Recovery: expanded search retrieval size triggered",
                    top_k=top_k_override,
                    max_context=max_context_override,
                )

                await _graph_mod.add_trace_event(
                    state["analysis_id"],
                    "recovery.re_retrieve",
                    {
                        "message": f"Expanding search parameters to double context "
                        f"(top_k={top_k_override})"
                    },
                )

        retrieve_kwargs: dict[str, Any] = {
            "query": state["current_query"],
            "kb_id": state["kb_id"],
            "top_k_override": top_k_override,
        }

        try:
            candidates = await _graph_mod.retrieve_hybrid_chunks(**retrieve_kwargs)
        except _graph_mod.RetrievalOutageError as exc:
            # Infra outage (Qdrant / embedding service unreachable) — NOT
            # "no evidence". Surface it distinctly, store a clear message,
            # and exhaust recovery budget so the graph ends instead of
            # burning LLM calls on rewrites that cannot fix an outage.
            logger.error("Retrieval outage — vector search unavailable", error=str(exc))
            await _graph_mod.add_trace_event(
                state["analysis_id"],
                "retrieval.outage",
                {"message": f"Search service unavailable: {exc}"},
            )
            state["chunks"] = []
            state["evidence_ids"] = []
            state["claims"] = []
            state["answer"] = (
                "The knowledge base search service is temporarily unavailable, "
                "so I could not search for evidence. Please wait a few minutes "
                "and try again — this is not a finding of 'no evidence'."
            )
            state["verdict_status"] = "FAIL"
            state["reliability_score"] = 0.0
            state["diagnosis_type"] = "RETRIEVAL_OUTAGE"
            state["diagnosis_failures"] = [str(exc)]
            state["attempts"] = cfg.max_recovery_attempts
            return state

        if not candidates and state.get("attempts", 0) == 0:
            try:
                q_client = await qdrant_db.get_qdrant_client()
                col_name = qdrant_db.get_collection_name(state["kb_id"])
                col_exists = await q_client.collection_exists(col_name)
                col_info = await q_client.get_collection(col_name) if col_exists else None
                points_count = col_info.points_count if col_info else 0

                # Check if MongoDB has chunks for this KB
                chunks_coll = _graph_mod.get_collection(Collections.DOCUMENT_CHUNKS)
                mongo_chunks_count = await chunks_coll.count_documents(
                    {"knowledge_base_id": ObjectId(state["kb_id"])}
                )

                _healed_recently = False
                try:
                    _kb_doc = _graph_mod.get_collection(
                        Collections.KNOWLEDGE_BASES
                    ).find_one({"_id": ObjectId(state["kb_id"])})
                    _healed_at = (_kb_doc or {}).get("self_healed_at")
                    if _healed_at and (datetime.now(UTC) - _healed_at).total_seconds() < 3600:
                        _healed_recently = True
                        logger.info("Self-heal skipped: recently healed", kb_id=state["kb_id"])
                except Exception:
                    _healed_recently = False

                if points_count == 0 and mongo_chunks_count > 0 and not _healed_recently:
                    logger.info(
                        "Self-healing: Re-indexing chunks from MongoDB into Qdrant",
                        kb_id=state["kb_id"],
                        chunks_count=mongo_chunks_count,
                    )
                    await qdrant_db.init_kb_collection(state["kb_id"])
                    chunks = await (
                        chunks_coll.find({"knowledge_base_id": ObjectId(state["kb_id"])})
                        .sort("chunk_index", 1)
                        .to_list(10_000)  # Support large KBs; embedded below in batches
                    )

                    doc_coll = _graph_mod.get_collection(Collections.DOCUMENTS)
                    # Single batched lookup (was N+1 find_one per distinct
                    # document — thousands of round trips on large KBs).
                    doc_ids = list({c["document_id"] for c in chunks})
                    doc_map: dict[str, str] = {}
                    if doc_ids:
                        async for d_obj in doc_coll.find(
                            {"_id": {"$in": doc_ids}}, {"filename": 1}
                        ):
                            doc_map[str(d_obj["_id"])] = d_obj.get("filename", "document")

                    embed_model = model_registry.get_embedding_model()
                    # H-BE-5: embed + upsert in bounded batches so a 10 k-chunk
                    # self-heal never holds all vectors/points in RAM at once.
                    # Progress events keep the trace UI honest on long heals
                    # (the feed compacts consecutive same-type events).
                    total_chunks = len(chunks)

                    for batch_start in range(0, total_chunks, _graph_mod.SELF_HEAL_BATCH_SIZE):
                        batch = chunks[batch_start : batch_start + _graph_mod.SELF_HEAL_BATCH_SIZE]
                        batch_texts = [
                            f"[{doc_map.get(str(c['document_id']), 'document')} | "
                            f"{c.get('zone', 'body').upper()}] {c['text']}"
                            for c in batch
                        ]
                        batch_vectors = await asyncio.to_thread(
                            embed_model.embed_documents, batch_texts
                        )
                        sync_points = []
                        for i, c in enumerate(batch):
                            doc_id_str = str(c["document_id"])
                            chunk_zone = c.get("zone", "body")
                            sparse_vec = generate_sparse_vector(batch_texts[i], zone=chunk_zone)
                            point_id = pipeline_mod.hashlib_qdrant_id(
                                doc_id_str, c["chunk_index"]
                            )
                            payload = {
                                "document_id": doc_id_str,
                                "knowledge_base_id": state["kb_id"],
                                "user_id": str(c.get("user_id", "")),
                                "chunk_index": c["chunk_index"],
                                "page": c.get("page", 1),
                                "character_offset": c.get("character_offset", 0),
                                "zone": chunk_zone,
                                "text": c["text"],
                                # Self-heal must not strip OCR provenance.
                                "ocr_used": bool(c.get("ocr_used", False)),
                                "ocr_confidence": c.get("ocr_confidence"),
                                "page_image_ref": c.get("page_image_ref"),
                                "document_version": c.get("document_version", "1.0"),
                                "is_snapshot": bool(c.get("is_snapshot", False)),
                            }
                            sync_points.append(
                                qdrant_models.PointStruct(
                                    id=point_id,
                                    vector={
                                        "": batch_vectors[i],
                                        "sparse-text": qdrant_models.SparseVector(
                                            indices=sparse_vec["indices"],
                                            values=sparse_vec["values"],
                                        ),
                                    },
                                    payload=payload,
                                )
                            )
                        await q_client.upsert(collection_name=col_name, points=sync_points)
                        healed_count = min(
                            batch_start + _graph_mod.SELF_HEAL_BATCH_SIZE, total_chunks
                        )
                        await _graph_mod.add_trace_event(
                            state["analysis_id"],
                            "retrieval.self_heal_batch",
                            {
                                "message": (
                                    "Self-heal re-indexed "
                                    f"{healed_count} of {total_chunks}"
                                ),
                                "completed": healed_count,
                                "total": total_chunks,
                            },
                        )
                    candidates = await _graph_mod.retrieve_hybrid_chunks(**retrieve_kwargs)
                    try:
                        await _graph_mod.get_collection(
                            Collections.KNOWLEDGE_BASES
                        ).update_one(
                            {"_id": ObjectId(state["kb_id"])},
                            {"$set": {"self_healed_at": datetime.now(UTC)}},
                        )
                    except Exception as exc:
                        logger.debug("self_healed_at marker skipped", error=str(exc))
                elif points_count == 0 and mongo_chunks_count == 0:
                    logger.warning("Knowledge base collection is empty", kb_id=state["kb_id"])
                    await _graph_mod.add_trace_event(
                        state["analysis_id"],
                        "retrieval.empty",
                        {
                            "message": "Knowledge base has 0 indexed chunks. "
                            "Upload documents first."
                        },
                    )
                    state["answer"] = (
                        "This knowledge base has no indexed document content. "
                        "Please upload a document to this knowledge base on the "
                        "Knowledge Bases page before running an analysis."
                    )
                    state["chunks"] = []
                    state["evidence_ids"] = []
                    state["claims"] = []
                    state["verdict_status"] = "PASS"
                    state["reliability_score"] = 0.0
                    state["diagnosis_type"] = "RETRIEVAL_FAILURE"
                    state["diagnosis_failures"] = ["Knowledge base contains 0 indexed chunks"]
                    return state
            except Exception as exc:
                # Self-heal is best-effort bookkeeping, so a failure here must not
                # abort the analysis — we fall through and answer from whatever
                # was already retrieved. But it used to be invisible: the only
                # trace was a server log line, so a half-reindexed collection and
                # a skipped empty-KB guard looked identical to a healthy run in
                # the UI. Emit a trace event so the degradation is attributable.
                logger.warning("Error during collection point verification/sync", error=str(exc))
                try:
                    await _graph_mod.add_trace_event(
                        state["analysis_id"],
                        "retrieval.self_heal_failed",
                        {
                            "message": (
                                "Collection-point self-heal did not complete; continuing "
                                "with the previously retrieved results. Evidence may be "
                                "stale until the next run."
                            ),
                            "error": str(exc)[:200],
                        },
                    )
                except Exception:  # pragma: no cover - trace must not mask the cause
                    logger.debug("Could not record self-heal failure trace event")

        # 2. Rerank
        top_chunks = await _graph_mod.rerank_candidate_chunks(
            state["current_query"], candidates, max_context_override=max_context_override
        )

        # 3. Evidence Integrity Audit
        audited_chunks = await _graph_mod.audit_evidence_integrity(top_chunks)
        verified_chunks = [c for c in audited_chunks if c.get("integrity_status") == "VERIFIED"]

        # Trace log outcomes
        corrupted_count = len(audited_chunks) - len(verified_chunks)
        if corrupted_count > 0:
            await _graph_mod.add_trace_event(
                state["analysis_id"],
                "integrity.failed",
                {"message": f"Excluded {corrupted_count} corrupted or tampered segments"},
            )

        await _graph_mod.add_trace_event(
            state["analysis_id"],
            "retrieval.completed",
            {
                "message": f"Retrieved {len(verified_chunks)} verified segments for reasoning",
                "segments": [
                    {
                        "filename": c.get("filename") or "unknown_doc",
                        "page": c.get("page", 1),
                        "score": c.get("rerank_score") or c.get("rrf_score", 0.0),
                        "url": c.get("url"),
                    }
                    for c in verified_chunks
                ],
            },
        )

        # 4. Save evidence records in MongoDB
        evidence_coll = _graph_mod.get_collection(Collections.EVIDENCE)
        evidence_ids: list[ObjectId] = []
        if audited_chunks:
            evidence_docs = []
            for c in audited_chunks:
                doc_id = ObjectId(c["document_id"]) if c.get("document_id") else None
                evt_doc = {
                    "analysis_id": ObjectId(state["analysis_id"]),
                    "kb_id": ObjectId(state["kb_id"]),
                    "document_id": doc_id,
                    "chunk_index": c.get("chunk_index", 0),
                    "text": c.get("text", ""),
                    "score": c.get("rerank_score") or c.get("rrf_score", 0.0),
                    "integrity_status": c.get("integrity_status", "UNKNOWN"),
                    "created_at": datetime.now(UTC),
                }
                evidence_docs.append(evt_doc)
            if evidence_docs:
                try:
                    result = await evidence_coll.insert_many(evidence_docs)
                    evidence_ids = list(result.inserted_ids)
                except TypeError:
                    # insert_many is not awaitable (e.g. mocked as insert_one);
                    # fall back to per-document inserts.
                    for evt_doc in evidence_docs:
                        result = await evidence_coll.insert_one(evt_doc)
                        evidence_ids.append(result.inserted_id)

        state["chunks"] = verified_chunks
        state["evidence_ids"] = evidence_ids
        return state

    fallback_state: AgentState = cast(
        AgentState,
        {
            **state,
            "chunks": [],
            "evidence_ids": [],
            "verdict_status": "FAIL",
            "diagnosis_type": "RETRIEVAL_ERROR",
            "diagnosis_failures": ["Retrieval failed due to internal error"],
        },
    )

    from app.rag.agent.graph.build import _execute_with_fallback

    return await _execute_with_fallback(
        state=state,
        node_name="retrieval",
        operation=_run_retrieval,
        fallback_state=fallback_state,
        timeout_seconds=retrieval_timeout,
    )
