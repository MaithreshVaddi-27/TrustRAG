"""
TRUSTRAG — LangGraph Agentic Adaptive Recovery Workflow.

Coordinates retrieval, generation, verification, and adaptive recovery loops
(query rewriting, expanded retrieval) when reliability thresholds fail.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict

from bson import ObjectId
from langgraph.graph import END, StateGraph

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.core.model_registry import get_verification_model
from app.db.mongodb import Collections, get_collection
from app.generation.generator import generate_grounded_answer
from app.retrieval.reranker import rerank_candidate_chunks
from app.retrieval.retriever import retrieve_hybrid_chunks
from app.services.analysis_service import add_trace_event
from app.verification.integrity import audit_evidence_integrity
from app.verification.verifier import execute_claim_verification

logger = get_logger(__name__)


# ─── LangGraph State Definition ──────────────────────────────────────────────


class AgentState(TypedDict):
    analysis_id: str
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
    diagnosis_type: str | None  # RETRIEVAL_FAILURE | EVIDENCE_CONFLICT | LOW_COVERAGE | None
    diagnosis_failures: list[str]


# ─── Graph Nodes ─────────────────────────────────────────────────────────────


async def retrieval_node(state: AgentState) -> AgentState:
    """Execute hybrid retrieval, evidence integrity audit, and evidence persistence."""
    logger.info("Agent Retrieval Node starting", attempt=state["attempts"] + 1)

    # 1. Hybrid Retrieval
    top_k_override = None
    max_context_override = None
    if state["recovery_strategy"] == "re_retrieve":
        # Double the retrieval search size to fetch more context
        cfg = get_model_config()
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
            {"message": f"Expanding search parameters to double context (top_k={top_k_override})"},
        )

    candidates = await retrieve_hybrid_chunks(
        query=state["current_query"], kb_id=state["kb_id"], top_k_override=top_k_override
    )

    # 2. Rerank
    top_chunks = rerank_candidate_chunks(
        state["current_query"], candidates, max_context_override=max_context_override
    )

    # 3. Evidence Integrity Audit
    audited_chunks = await audit_evidence_integrity(top_chunks)
    verified_chunks = [c for c in audited_chunks if c.get("integrity_status") == "VERIFIED"]

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
                }
                for c in verified_chunks
            ],
        },
    )

    # 4. Save evidence records in MongoDB
    evidence_coll = get_collection(Collections.EVIDENCE)
    evidence_ids = []
    for c in audited_chunks:
        doc_id = ObjectId(c["document_id"]) if c.get("document_id") else None
        evt_doc = {
            "analysis_id": ObjectId(state["analysis_id"]),
            "text": c["text"],
            "document_id": doc_id,
            "filename": c.get("filename"),
            "retrieval_score": c.get("dense_score", 0.0),
            "fusion_score": c.get("rrf_score", 0.0),
            "rerank_score": c.get("rerank_score"),
            "method": "hybrid",
            "integrity_status": c.get("integrity_status", "CORRUPTED"),
            "effective_from": c.get("effective_from"),
            "effective_until": c.get("effective_until"),
            "created_at": datetime.now(UTC),
        }
        res = await evidence_coll.insert_one(evt_doc)
        evidence_ids.append(res.inserted_id)

    # Filter out Mongo IDs for verified evidence only
    verified_evidence_ids = []
    for i, c in enumerate(audited_chunks):
        if c.get("integrity_status") == "VERIFIED":
            verified_evidence_ids.append(evidence_ids[i])

    state["chunks"] = verified_chunks
    state["evidence_ids"] = verified_evidence_ids
    return state


async def generation_node(state: AgentState) -> AgentState:
    """Generate answer grounded in retrieved context."""
    logger.info("Agent Generation Node starting")

    await add_trace_event(
        state["analysis_id"],
        "generation.started",
        {"message": "Reasoning grounded answer from verified context"},
    )

    answer = await generate_grounded_answer(state["current_query"], state["chunks"])

    state["answer"] = answer
    return state


async def verification_node(state: AgentState) -> AgentState:
    """Run claims decomposition and NLI verification, and evaluate reliability thresholds."""
    logger.info("Agent Verification Node starting")

    answer = state["answer"]
    cfg = get_model_config()

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

    claims = await execute_claim_verification(
        analysis_id_str=state["analysis_id"],
        answer=answer,
        chunks=state["chunks"],
        evidence_ids=state["evidence_ids"],
    )

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

    # Evaluate reliability thresholds
    coverage = supported / total
    contradiction_rate = contradicted / total

    logger.info(
        "Evaluating verification thresholds",
        coverage=coverage,
        required_coverage=cfg.minimum_evidence_coverage,
        contradiction_rate=contradiction_rate,
        max_contradiction=cfg.maximum_contradiction_rate,
    )

    if (
        coverage >= cfg.minimum_evidence_coverage
        and contradiction_rate <= cfg.maximum_contradiction_rate
    ):
        state["verdict_status"] = "PASS"
        logger.info("Reliability thresholds verified successfully")
    else:
        state["verdict_status"] = "FAIL"
        logger.info("Reliability thresholds check failed")

    # Reliability score: coverage discounted by contradiction rate, clamped to [0, 1].
    state["reliability_score"] = max(0.0, min(1.0, coverage * (1 - contradiction_rate)))

    failures = []
    if contradiction_rate > cfg.maximum_contradiction_rate:
        failures.append(f"{contradicted}/{total} claims contradicted by evidence")
    if coverage < cfg.minimum_evidence_coverage:
        failures.append(f"Only {supported}/{total} claims supported by evidence")

    if not failures:
        state["diagnosis_type"] = None
    elif contradiction_rate > cfg.maximum_contradiction_rate:
        state["diagnosis_type"] = "EVIDENCE_CONFLICT"
    else:
        state["diagnosis_type"] = "LOW_COVERAGE"
    state["diagnosis_failures"] = failures

    return state


async def recovery_node(state: AgentState) -> AgentState:
    """Determine adaptive strategy and execute recovery step (e.g. Query Rewriting)."""
    state["attempts"] += 1
    cfg = get_model_config()

    # Determine recovery strategy based on priorities configured in models.yaml
    # Fallback to query_rewrite on first attempt, re_retrieve on second
    priority = cfg._get("recovery", "strategy_priority", required=False) or [
        "query_rewrite",
        "re_retrieve",
    ]
    idx = (state["attempts"] - 1) % len(priority)
    strategy = priority[idx]

    logger.info("Triggering adaptive recovery loop", attempt=state["attempts"], strategy=strategy)

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
            rewrite_prompt = f"""You are a search query expansion assistant for an information retrieval system.
The original query did not return sufficient information to answer the question.
Your task is to rewrite and expand the user query by incorporating synonyms, section headers, or conceptual topics that could be present in the document.

Output only the expanded search query string. Do not include markdown headers or commentary.

<ORIGINAL_QUERY>
{state["query"]}
</ORIGINAL_QUERY>
"""
        try:
            model = get_verification_model()
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
                        parts.append(getattr(item, "text"))
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
    analysis_id_str: str, kb_id_str: str, query: str
) -> dict[str, Any]:
    """Compile and execute the full agent graph pipeline."""
    graph = build_agent_graph()

    initial_state: AgentState = {
        "analysis_id": analysis_id_str,
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
    }

    logger.info("Executing Agentic RAG Flow graph", analysis_id=analysis_id_str)
    final_state = await graph.ainvoke(initial_state)
    return final_state
