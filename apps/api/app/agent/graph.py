"""
TRUSTRAG — LangGraph Agentic Adaptive Recovery Workflow.

Coordinates retrieval, generation, verification, and adaptive recovery loops
(query rewriting, expanded retrieval) when reliability thresholds fail.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, TypedDict

from bson import ObjectId
from langgraph.graph import END, StateGraph

from app.core.config import get_model_config
from app.core.context import ContextManager, Message, get_context_config
from app.core.logging import get_logger
from app.core.model_registry import get_verification_model
from app.db.mongodb import Collections, get_collection
from app.generation.generator import generate_grounded_answer
from app.retrieval.reranker import rerank_candidate_chunks
from app.retrieval.retriever import _query_cache, retrieve_hybrid_chunks
from app.services.analysis_service import add_trace_event
from app.verification.integrity import audit_evidence_integrity
from app.verification.verdict import Thresholds, compute_verdict
from app.verification.verifier import execute_claim_verification

logger = get_logger(__name__)


# ─── LangGraph State Definition ──────────────────────────────────────────────


class AgentState(TypedDict):
    analysis_id: str
    user_id: str | None
    kb_id: str
    query: str
    current_query: str
    answer: str | None
    chunks: list[dict[str, Any]]
    evidence_ids: list[ObjectId]
    claims: list[dict[str, Any]]
    attempts: int
    verdict_status: str  # "PASS" | "FAIL"
    recovery_strategy: str | None  # "query_rewrite" | "re_retrieve" | None
    reliability_score: float | None
    diagnosis_type: (
        str | None
    )  # RETRIEVAL_FAILURE | EVIDENCE_CONFLICT | LOW_COVERAGE | VERIFICATION_TIMEOUT
     # | VERIFICATION_ERROR | RETRIEVAL_ERROR | GENERATION_ERROR | None
    diagnosis_failures: list[str]
    web_search_enabled: bool
    web_search_provider: str  # "tavily" | "duckduckgo" | "both"
    llm_provider: str | None
    llm_model: str | None
    embedding_provider: str | None
    embedding_model: str | None
    # Error tracking for fallback paths
    node_errors: list[dict[str, Any]]


# ─── Standardized Error Handling ─────────────────────────────────────────────
# TEST COMMENT


async def _execute_with_fallback(
    state: AgentState,
    node_name: str,
    operation: callable,
    fallback_state: AgentState | None = None,
    timeout_seconds: int | None = None,
) -> AgentState:
    """
    Execute a node operation with standardized error handling and fallback.

    Args:
        state: Current agent state
        node_name: Name of the node for logging/tracing
        operation: Async callable that performs the node's work
        fallback_state: Optional state to return on failure
        timeout_seconds: Optional timeout for the operation

    Returns:
        Updated state (either from operation or fallback)
    """
    await add_trace_event(
        state["analysis_id"],
        f"{node_name}.started",
        {"message": f"Starting {node_name} node"},
    )

    try:
        if timeout_seconds:
            result = await asyncio.wait_for(operation(), timeout=timeout_seconds)
        else:
            result = await operation()

        await add_trace_event(
            state["analysis_id"],
            f"{node_name}.completed",
            {"message": f"{node_name} completed successfully"},
        )
        return result

    except TimeoutError:
        logger.warning(f"{node_name} node timed out", timeout_seconds=timeout_seconds)
        error_info = {
            "node": node_name,
            "error_type": "TIMEOUT",
            "message": f"{node_name} exceeded {timeout_seconds}s timeout",
        }
        state["node_errors"] = [*state.get("node_errors", []), error_info]

        await add_trace_event(
            state["analysis_id"],
            f"{node_name}.timeout",
            {"message": error_info["message"]},
        )

        if fallback_state is not None:
            return fallback_state
        # Default fallback: mark as failed but allow recovery
        state["verdict_status"] = "FAIL"
        return state

    except Exception as exc:
        logger.error(f"{node_name} node failed", error=str(exc), exc_info=True)
        error_info = {
            "node": node_name,
            "error_type": type(exc).__name__,
            "message": f"{node_name} failed: {type(exc).__name__}",
        }
        state["node_errors"] = [*state.get("node_errors", []), error_info]

        await add_trace_event(
            state["analysis_id"],
            f"{node_name}.error",
            {"message": error_info["message"], "error_type": error_info["error_type"]},
        )

        if fallback_state is not None:
            return fallback_state
        # Default fallback: mark as failed but allow recovery
        state["verdict_status"] = "FAIL"
        return state


# ─── Graph Nodes ─────────────────────────────────────────────────────────────


async def retrieval_node(state: AgentState) -> AgentState:
    """Execute hybrid retrieval, evidence integrity audit, and evidence persistence."""
    cfg = get_model_config()
    retrieval_timeout = cfg.llm_timeout_seconds  # Reuse LLM timeout for retrieval

    async def _run_retrieval() -> AgentState:
        logger.info("Agent Retrieval Node starting", attempt=state["attempts"] + 1)

        await add_trace_event(
            state["analysis_id"],
            "retrieval.started",
            {"message": f"Searching knowledge base for query: '{state['current_query']}'"},
        )

        # 1. Hybrid Retrieval
        top_k_override = None
        max_context_override = None
        if state["recovery_strategy"] == "re_retrieve":
            # Double the retrieval search size to fetch more context
            top_k_override = cfg.dense_top_k * 2
            max_context_override = cfg.max_context_chunks * 2
            logger.info(
                "Recovery: expanded search retrieval size triggered",
                top_k=top_k_override,
                max_context=max_context_override,
            )

            await add_trace_event(
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
        if state.get("embedding_provider"):
            retrieve_kwargs["embedding_provider"] = state.get("embedding_provider")
        if state.get("embedding_model"):
            retrieve_kwargs["embedding_model"] = state.get("embedding_model")

        candidates = await retrieve_hybrid_chunks(**retrieve_kwargs)

        if not candidates and state.get("attempts", 0) == 0:
            from app.db.qdrant import get_collection_name, get_qdrant_client, init_kb_collection

            try:
                q_client = await get_qdrant_client()
                col_name = get_collection_name(state["kb_id"])
                col_exists = await q_client.collection_exists(col_name)
                col_info = await q_client.get_collection(col_name) if col_exists else None
                points_count = col_info.points_count if col_info else 0

                # Check if MongoDB has chunks for this KB
                chunks_coll = get_collection(Collections.DOCUMENT_CHUNKS)
                mongo_chunks_count = await chunks_coll.count_documents(
                    {"knowledge_base_id": ObjectId(state["kb_id"])}
                )

                if points_count == 0 and mongo_chunks_count > 0:
                    logger.info(
                        "Self-healing: Re-indexing chunks from MongoDB into Qdrant",
                        kb_id=state["kb_id"],
                        chunks_count=mongo_chunks_count,
                    )
                    from qdrant_client.http import models

                    from app.core.model_registry import get_embedding_model
                    from app.ingestion.pipeline import hashlib_qdrant_id
                    from app.ingestion.sparse_vector import generate_sparse_vector

                    await init_kb_collection(state["kb_id"])
                    chunks = (
                        await chunks_coll.find({"knowledge_base_id": ObjectId(state["kb_id"])})
                        .sort("chunk_index", 1)
                        .to_list(10_000)  # Support large KBs; pipeline.py batches upserts anyway
                    )

                    doc_coll = get_collection(Collections.DOCUMENTS)
                    doc_map = {}
                    for c in chunks:
                        d_id = str(c["document_id"])
                        if d_id not in doc_map:
                            d_obj = await doc_coll.find_one({"_id": c["document_id"]})
                            doc_map[d_id] = (
                                d_obj.get("filename", "document") if d_obj else "document"
                            )

                    contextual_texts = [
                        f"[{doc_map.get(str(c['document_id']), 'document')} | "
                        f"{c.get('zone', 'body').upper()}] {c['text']}"
                        for c in chunks
                    ]
                    embed_model = get_embedding_model()
                    dense_vectors = await asyncio.to_thread(
                        embed_model.embed_documents, contextual_texts
                    )

                    sync_points = []
                    for i, c in enumerate(chunks):
                        doc_id_str = str(c["document_id"])
                        chunk_zone = c.get("zone", "body")
                        sparse_vec = generate_sparse_vector(contextual_texts[i], zone=chunk_zone)
                        point_id = hashlib_qdrant_id(doc_id_str, c["chunk_index"])
                        payload = {
                            "document_id": doc_id_str,
                            "knowledge_base_id": state["kb_id"],
                            "user_id": str(c.get("user_id", "")),
                            "chunk_index": c["chunk_index"],
                            "page": c.get("page", 1),
                            "character_offset": c.get("character_offset", 0),
                            "zone": chunk_zone,
                            "text": c["text"],
                        }
                        sync_points.append(
                            models.PointStruct(
                                id=point_id,
                                vector={
                                    "": dense_vectors[i],
                                    "sparse-text": models.SparseVector(
                                        indices=sparse_vec["indices"], values=sparse_vec["values"]
                                    ),
                                },
                                payload=payload,
                            )
                        )
                    await q_client.upsert(collection_name=col_name, points=sync_points)
                    candidates = await retrieve_hybrid_chunks(
                        query=state["current_query"],
                        kb_id=state["kb_id"],
                        top_k_override=top_k_override,
                    )
                elif points_count == 0 and mongo_chunks_count == 0:
                    logger.warning("Knowledge base collection is empty", kb_id=state["kb_id"])
                    await add_trace_event(
                        state["analysis_id"],
                        "retrieval.empty",
                        {"message": "Knowledge base has 0 indexed chunks. Upload documents first."},
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
                logger.warning("Error during collection point verification/sync", error=str(exc))

        # 2. Rerank
        top_chunks = await rerank_candidate_chunks(
            state["current_query"], candidates, max_context_override=max_context_override
        )

        # 3. Evidence Integrity Audit
        audited_chunks = await audit_evidence_integrity(top_chunks)
        verified_chunks = [c for c in audited_chunks if c.get("integrity_status") == "VERIFIED"]

        # 3b. Live Web Search Grounding via MCP (Tavily / DuckDuckGo / Both)
        if state.get("web_search_enabled"):
            search_prov = state.get("web_search_provider", "both")
            await add_trace_event(
                state["analysis_id"],
                "web_search.started",
                {"message": f"Executing live web search grounding via MCP ({search_prov.upper()})"},
            )
            try:
                from app.mcp.client import execute_mcp_tool

                tool_name = (
                    "tavily_search"
                    if search_prov == "tavily"
                    else (
                        "duckduckgo_search" if search_prov == "duckduckgo" else "hybrid_web_search"
                    )
                )
                tool_args: dict[str, Any] = {"query": state["current_query"], "max_results": 5}
                if tool_name == "hybrid_web_search":
                    tool_args["provider"] = "both"

                web_items = await execute_mcp_tool(tool_name, tool_args)
                if web_items and isinstance(web_items, list):
                    logger.info("Web search MCP returned results", count=len(web_items))
                    from app.services.search_service import sanitize_url

                    for w_idx, w in enumerate(web_items):
                        w_title = str(w.get("title") or "Web Source").strip()[:150]
                        w_url = sanitize_url(w.get("url"))
                        w_content = str(w.get("content") or "").strip()
                        if not w_content:
                            continue
                        w_chunk = {
                            "chunk_id": f"web_{w_idx}",
                            "document_id": None,
                            "filename": w_title,
                            "url": w_url,
                            "text": f"[WEB CITATION: {w_title}] {w_content}",
                            "dense_score": float(w.get("score", 0.8)),
                            "rrf_score": float(w.get("score", 0.8)),
                            "rerank_score": float(w.get("score", 0.8)),
                            "method": f"mcp_{w.get('source', search_prov)}",
                            "integrity_status": "VERIFIED",
                            "page": 1,
                        }
                        audited_chunks.append(w_chunk)
                        verified_chunks.append(w_chunk)

                    web_sources = [
                        {"title": w.get("title"), "url": w.get("url")} for w in web_items
                    ]
                    await add_trace_event(
                        state["analysis_id"],
                        "web_search.completed",
                        {
                            "message": f"Retrieved {len(web_items)} live web search citations via MCP",
                            "sources": web_sources,
                        },
                    )
                await add_trace_event(
                    state["analysis_id"],
                    "web_search.completed",
                    {
                        "message": f"Live web search grounding completed via MCP ({search_prov.upper()})",
                        "count": len(web_items) if web_items else 0,
                    },
                )
            except Exception as web_exc:
                logger.error("Web search MCP grounding failed", error=str(web_exc))

        # Trace log outcomes
        corrupted_count = len(audited_chunks) - len(verified_chunks)
        if corrupted_count > 0:
            await add_trace_event(
                state["analysis_id"],
                "integrity.failed",
                {"message": f"Excluded {corrupted_count} corrupted or tampered segments"},
            )

        await add_trace_event(
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

        # 4. Save evidence records in MongoDB (Batch Optimized)
        evidence_coll = get_collection(Collections.EVIDENCE)
        evidence_ids: list[ObjectId] = []
        if audited_chunks:
            evidence_docs = []
            for c in audited_chunks:
                doc_id = ObjectId(c["document_id"]) if c.get("document_id") else None
                evt_doc = {
                    "analysis_id": ObjectId(state["analysis_id"]),
                    "user_id": ObjectId(state["user_id"]) if state.get("user_id") else None,
                    "text": c["text"],
                    "document_id": doc_id,
                    "filename": c.get("filename"),
                    "url": c.get("url"),
                    "retrieval_score": c.get("dense_score", 0.0),
                    "fusion_score": c.get("rrf_score", 0.0),
                    "rerank_score": c.get("rerank_score"),
                    "method": c.get("method", "hybrid"),
                    "integrity_status": c.get("integrity_status", "CORRUPTED"),
                    "effective_from": c.get("effective_from"),
                    "effective_until": c.get("effective_until"),
                    "created_at": datetime.now(UTC),
                }
                evidence_docs.append(evt_doc)

            try:
                insert_res = await evidence_coll.insert_many(evidence_docs)
                evidence_ids = list(insert_res.inserted_ids)
            except TypeError:
                for doc in evidence_docs:
                    res = await evidence_coll.insert_one(doc)
                    evidence_ids.append(res.inserted_id)

        # Filter out Mongo IDs for verified evidence only
        verified_evidence_ids = []
        for i, c in enumerate(audited_chunks):
            if c.get("integrity_status") == "VERIFIED" and i < len(evidence_ids):
                verified_evidence_ids.append(evidence_ids[i])

        state["chunks"] = verified_chunks
        state["evidence_ids"] = verified_evidence_ids
        return state

    # Fallback state for retrieval failure
    fallback_state = {
        **state,
        "chunks": [],
        "evidence_ids": [],
        "verdict_status": "FAIL",
        "diagnosis_type": "RETRIEVAL_ERROR",
        "diagnosis_failures": ["Retrieval failed due to internal error"],
    }

    return await _execute_with_fallback(
        state=state,
        node_name="retrieval",
        operation=_run_retrieval,
        fallback_state=fallback_state,
        timeout_seconds=retrieval_timeout,
    )


async def generation_node(state: AgentState) -> AgentState:
    """Generate answer grounded in retrieved context with context management."""
    cfg = get_model_config()
    generation_timeout = cfg.llm_timeout_seconds

    # Get context management config
    context_cfg = get_context_config()

    async def _run_generation() -> AgentState:
        logger.info("Agent Generation Node starting")

        # If answer was already formulated by the 0-chunk empty KB guard, preserve it
        empty_kb_guard = state.get("diagnosis_failures") == [
            "Knowledge base contains 0 indexed chunks"
        ]
        if state.get("answer") and not state.get("chunks") and empty_kb_guard:
            return state

        await add_trace_event(
            state["analysis_id"],
            "generation.started",
            {"message": "Reasoning grounded answer from verified context"},
        )

        # Build context with conversation history management
        context_manager = ContextManager(
            strategy=context_cfg.get("strategy", "hybrid"),
            max_tokens=context_cfg.get("max_tokens", cfg.max_input_tokens),
        )

        # Add current query as user message
        context_manager.add_message(Message(role="user", content=state["current_query"]))

        # Get managed context (with sliding window/summarization)
        await context_manager.get_context(reserve_tokens=2000)

        answer = await generate_grounded_answer(
            state["current_query"],
            state["chunks"],
            provider=state.get("llm_provider"),
            model=state.get("llm_model"),
            # Pass managed context if generator supports it
        )

        # Add assistant response to context
        context_manager.add_message(Message(role="assistant", content=answer))

        state["answer"] = answer
        if context_manager.manager:
            state["context"] = [m.to_dict() for m in context_manager.manager.messages]
        elif context_manager.window_manager:
            state["context"] = [m.to_dict() for m in context_manager.window_manager.messages]
        else:
            state["context"] = []
        return state

    # Fallback state for generation failure
    fallback_state = {
        **state,
        "answer": "ABSTAIN",
        "verdict_status": "FAIL",
        "diagnosis_type": "GENERATION_ERROR",
        "diagnosis_failures": ["Generation failed due to internal error"],
    }

    return await _execute_with_fallback(
        state=state,
        node_name="generation",
        operation=_run_generation,
        fallback_state=fallback_state,
        timeout_seconds=generation_timeout,
    )


async def verification_node(state: AgentState) -> AgentState:
    """Run claims decomposition and NLI verification, and evaluate reliability thresholds."""
    logger.info("Agent Verification Node starting")

    cfg = get_model_config()
    verification_timeout = cfg.max_verification_time_seconds

    # If already diagnosed as empty KB, terminate cleanly
    if state.get("diagnosis_type") == "RETRIEVAL_FAILURE" and state.get("answer"):
        state["attempts"] = cfg.max_recovery_attempts
        state["verdict_status"] = "PASS"
        return state

    answer = state["answer"]

    if not answer or answer == "ABSTAIN":
        state["claims"] = []
        state["reliability_score"] = None
        state["diagnosis_type"] = "RETRIEVAL_FAILURE"
        state["diagnosis_failures"] = (
            ["No relevant evidence segments were retrieved"]
            if not state["chunks"]
            else ["Retrieved segments contained insufficient information to answer the query"]
        )
        attempts = state.get("attempts", 0)
        if attempts < cfg.max_recovery_attempts:
            state["verdict_status"] = "FAIL"
            logger.info(
                "Generation abstained due to insufficient context, triggering adaptive recovery",
                attempt=attempts + 1,
                max_attempts=cfg.max_recovery_attempts,
            )
        else:
            state["verdict_status"] = "PASS"
            logger.info("Generation abstained and maximum recovery attempts reached")
        return state

    await add_trace_event(
        state["analysis_id"],
        "claims.started",
        {"message": "Decomposing answer and executing NLI verification checks"},
    )

    async def _run_verification() -> list[dict[str, Any]]:
        """Inner verification logic with timeout protection."""
        return await execute_claim_verification(
            analysis_id_str=state["analysis_id"],
            answer=answer,
            chunks=state["chunks"],
            evidence_ids=state["evidence_ids"],
            user_id_str=state.get("user_id"),
            provider=state.get("llm_provider"),
            model=state.get("llm_model"),
        )

    try:
        claims = await asyncio.wait_for(_run_verification(), timeout=verification_timeout)
    except TimeoutError:
        logger.warning(
            "Verification node timed out, triggering recovery",
            timeout_seconds=verification_timeout,
            attempt=state.get("attempts", 0) + 1,
        )
        state["claims"] = []
        state["reliability_score"] = None
        state["diagnosis_type"] = "VERIFICATION_TIMEOUT"
        state["diagnosis_failures"] = [f"Verification exceeded {verification_timeout}s timeout"]
        attempts = state.get("attempts", 0)
        if attempts < cfg.max_recovery_attempts:
            state["verdict_status"] = "FAIL"
        else:
            state["verdict_status"] = "PASS"
        return state
    except Exception as exc:
        logger.error("Verification node failed with error", error=str(exc))
        state["claims"] = []
        state["reliability_score"] = None
        state["diagnosis_type"] = "VERIFICATION_ERROR"
        state["diagnosis_failures"] = [f"Verification failed: {type(exc).__name__}"]
        attempts = state.get("attempts", 0)
        if attempts < cfg.max_recovery_attempts:
            state["verdict_status"] = "FAIL"
        else:
            state["verdict_status"] = "PASS"
        return state

    state["claims"] = claims

    total = len(claims)
    if total == 0:
        state["verdict_status"] = "PASS"
        state["reliability_score"] = 1.0
        state["diagnosis_type"] = None
        state["diagnosis_failures"] = []
        return state

    supported = sum(1 for c in claims if c["state"] == "SUPPORTED")
    contradicted = sum(1 for c in claims if c["state"] == "CONTRADICTED")
    neutral = sum(1 for c in claims if c["state"] == "NEUTRAL")

    await add_trace_event(
        state["analysis_id"],
        "claims.verified",
        {
            "message": f"Verified {total} atomic claims",
            "stats": {"supported": supported, "contradicted": contradicted, "neutral": neutral},
        },
    )

    # Compute unified verdict
    thresholds = Thresholds(
        minimum_evidence_coverage=cfg.minimum_evidence_coverage,
        maximum_contradiction_rate=cfg.maximum_contradiction_rate,
        abstain_below=cfg.abstain_below,
    )

    verdict = compute_verdict(
        supported=supported,
        contradicted=contradicted,
        neutral=neutral,
        total=total,
        thresholds=thresholds,
        answer=state.get("answer"),
    )

    state["verdict_status"] = verdict.verdict_status.value
    state["reliability_score"] = verdict.reliability_score
    state["diagnosis_type"] = verdict.diagnosis_type.value
    state["diagnosis_failures"] = verdict.diagnosis_failures

    logger.info(
        "Unified verdict computed",
        verdict=verdict.verdict_status.value,
        reliability_score=verdict.reliability_score,
        diagnosis_type=verdict.diagnosis_type.value,
    )

    return state


async def recovery_node(state: AgentState) -> AgentState:
    """Determine adaptive strategy and execute recovery step (e.g. Query Rewriting)."""
    cfg = get_model_config()
    recovery_timeout = cfg.llm_timeout_seconds

    async def _run_recovery() -> AgentState:
        state["attempts"] += 1

        # Clear prior failed/abstained answer and claims so recovery generates and verifies freshly
        state["answer"] = None
        state["claims"] = []

        # Determine recovery strategy from public config property
        priority = cfg.recovery_strategy_priority
        idx = (state["attempts"] - 1) % len(priority)
        strategy = priority[idx]

        logger.info(
            "Triggering adaptive recovery loop", attempt=state["attempts"], strategy=strategy
        )

        if strategy == "query_rewrite":
            # Invoke Gemini to rewrite the query targeting the missing facts
            missing_claims = [c["text"] for c in state["claims"] if c["state"] != "SUPPORTED"]
            if missing_claims:
                missing_str = "\n".join(f"- {c}" for c in missing_claims)
                rewrite_prompt = f"""You are a query expansion assistant.
Your task is to rewrite the original user query to search for the missing
factual details listed below.
Combine the original query with context requirements. Generate a single,
concise search query.

Output only the expanded search query string. Do not include markdown headers or commentary.

<ORIGINAL_QUERY>
{state["query"]}
</ORIGINAL_QUERY>
<MISSING_CLAIMS>
{missing_str}
</MISSING_CLAIMS>
"""
            else:
                # Query rewrite triggered because generation abstained / insufficient context
                rewrite_prompt = f"""You are a search query expansion assistant for an IR system.
The original query did not return sufficient information to answer the question.
Your task is to expand the query by resolving ambiguous acronyms and terms.
Keep the query focused and concise (5 to 12 words), ideal for search engines.

Output only the expanded search query string. Do not include markdown or quotes.

<ORIGINAL_QUERY>
{state["query"]}
</ORIGINAL_QUERY>
"""
            try:
                model = get_verification_model(
                    provider=state.get("llm_provider"), model=state.get("llm_model")
                )
                response = await model.ainvoke(rewrite_prompt)
                new_query = response.content
                if isinstance(new_query, bytes):
                    new_query = new_query.decode("utf-8")
                elif isinstance(new_query, list):
                    parts = []
                    for item in new_query:
                        if isinstance(item, dict) and "text" in item:
                            parts.append(item["text"])
                        elif isinstance(item, str):
                            parts.append(item)
                        elif hasattr(item, "text"):
                            parts.append(item.text)
                    new_query = "".join(parts)
                new_query = str(new_query).strip()

                logger.info(
                    "Query rewritten successfully", original=state["query"], rewritten=new_query
                )
                state["current_query"] = new_query
                state["recovery_strategy"] = "query_rewrite"

                await add_trace_event(
                    state["analysis_id"],
                    "recovery.rewrite",
                    {
                        "message": "Rewriting query to target missing details",
                        "original_query": state["query"],
                        "rewritten_query": new_query,
                    },
                )
            except Exception as exc:
                logger.error("Query rewrite failed, falling back to original query", error=str(exc))
                state["recovery_strategy"] = None

        elif strategy == "re_retrieve":
            state["recovery_strategy"] = "re_retrieve"
            # Strategy re_retrieve is executed inside retrieval_node by doubling search parameters

        else:
            state["recovery_strategy"] = None

        # Persist recovery run record in MongoDB
        run_doc = {
            "analysis_id": ObjectId(state["analysis_id"]),
            "attempt": state["attempts"],
            "strategy": strategy,
            "query_used": state["current_query"],
            "created_at": datetime.now(UTC),
        }
        await get_collection(Collections.RECOVERY_RUNS).insert_one(run_doc)

        return state

    # Fallback state for recovery failure
    fallback_state = {
        **state,
        "recovery_strategy": None,
        "verdict_status": "FAIL",
        "diagnosis_type": "RECOVERY_ERROR",
        "diagnosis_failures": ["Recovery failed due to internal error"],
    }

    return await _execute_with_fallback(
        state=state,
        node_name="recovery",
        operation=_run_recovery,
        fallback_state=fallback_state,
        timeout_seconds=recovery_timeout,
    )


# ─── Conditional Edge Router ──────────────────────────────────────────────────


def should_recover(state: AgentState) -> str:
    """Determine if recovery node should execute or terminate the graph run."""
    cfg = get_model_config()
    max_recovery = cfg.max_recovery_attempts

    if state["verdict_status"] == "PASS" or state["attempts"] >= max_recovery:
        return "end"
    return "recover"


# ─── Graph Construction ────────────────────────────────────────────────────────

# Module-level compiled graph singleton — built once, reused per request.
_compiled_graph: Any = None


def build_agent_graph() -> Any:
    """Assemble and compile LangGraph State Graph workflow (cached singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        builder = StateGraph(AgentState)

        # Register nodes
        builder.add_node("retrieval", retrieval_node)
        builder.add_node("generation", generation_node)
        builder.add_node("verification", verification_node)
        builder.add_node("recovery", recovery_node)

        # Map edges
        builder.set_entry_point("retrieval")
        builder.add_edge("retrieval", "generation")
        builder.add_edge("generation", "verification")

        builder.add_conditional_edges(
            "verification", should_recover, {"recover": "recovery", "end": END}
        )

        builder.add_edge("recovery", "retrieval")

        _compiled_graph = builder.compile()
        logger.info("LangGraph agent graph compiled and cached")
    return _compiled_graph


# ─── Coordinator Run ──────────────────────────────────────────────────────────


async def execute_agentic_rag_flow(
    analysis_id_str: str,
    kb_id_str: str,
    query: str,
    user_id_str: str | None = None,
    web_search_enabled: bool = False,
    web_search_provider: str = "both",
    llm_provider: str | None = None,
    llm_model: str | None = None,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
) -> dict[str, Any]:
    """Compile and execute the full agent graph pipeline."""
    graph = build_agent_graph()

    initial_state: AgentState = {
        "analysis_id": analysis_id_str,
        "user_id": user_id_str,
        "kb_id": kb_id_str,
        "query": query,
        "current_query": query,
        "answer": None,
        "chunks": [],
        "evidence_ids": [],
        "claims": [],
        "attempts": 0,
        "verdict_status": "FAIL",
        "recovery_strategy": None,
        "reliability_score": None,
        "diagnosis_type": None,
        "diagnosis_failures": [],
        "web_search_enabled": web_search_enabled,
        "web_search_provider": web_search_provider,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "embedding_provider": embedding_provider,
        "embedding_model": embedding_model,
    }

    # ── Semantic Response Cache Fast-Path (0% Compute Load) ────────────────────
    q_vec: list[float] = []
    if not web_search_enabled:
        try:
            from app.core.model_registry import get_embedding_model
            from app.core.semantic_cache import check_semantic_cache

            cache_key = f"{embedding_provider or ''}:{embedding_model or ''}:{query}"
            q_vec = _query_cache.get(cache_key)
            if q_vec is None:
                emb_model = get_embedding_model(provider=embedding_provider, model=embedding_model)
                try:
                    q_vec = await emb_model.aembed_query(query)
                except Exception:
                    q_vec = emb_model.embed_query(query)
                _query_cache.set(cache_key, q_vec)

            cached_resp = check_semantic_cache(query, kb_id_str, q_vec, similarity_threshold=0.94)
            if cached_resp:
                await add_trace_event(
                    analysis_id_str,
                    "cache.hit",
                    {
                        "message": (
                            "Semantic cache match (similarity >= 94%). "
                            "Serving verified answer with 0% compute load."
                        ),
                        "cached_query": query,
                    },
                )
                return {
                    **initial_state,
                    "answer": cached_resp["answer"],
                    "reliability_score": cached_resp.get("reliability_score", 1.0),
                    "verdict_status": cached_resp.get("verdict_status", "PASS"),
                    "chunks": cached_resp.get("chunks", []),
                    "evidence_ids": cached_resp.get("evidence_ids", []),
                    "claims": cached_resp.get("claims", []),
                }
        except Exception as cache_err:
            logger.debug("Semantic cache check bypassed", error=str(cache_err))

    logger.info("Executing Agentic RAG Flow graph", analysis_id=analysis_id_str)
    try:
        final_state = await graph.ainvoke(initial_state)

        # Store in semantic cache if verified and valid
        if (
            q_vec
            and final_state.get("verdict_status") == "PASS"
            and final_state.get("answer")
            and final_state["answer"] != "ABSTAIN"
            and not web_search_enabled
        ):
            try:
                from app.core.semantic_cache import store_semantic_cache

                store_semantic_cache(
                    query=query,
                    kb_id=kb_id_str,
                    query_vector=q_vec,
                    response_data={
                        "answer": final_state["answer"],
                        "reliability_score": final_state.get("reliability_score"),
                        "verdict_status": final_state.get("verdict_status"),
                        "chunks": final_state.get("chunks", []),
                        "evidence_ids": final_state.get("evidence_ids", []),
                        "claims": final_state.get("claims", []),
                    },
                )
            except Exception as store_err:
                logger.debug("Semantic cache store skipped", error=str(store_err))

        return final_state
    finally:
        import asyncio

        from app.core.memory import trim_memory

        await asyncio.to_thread(trim_memory)
