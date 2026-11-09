"""
TRUSTRAG — LangGraph verification node.

Encapsulates all claim decomposition + NLI verification logic previously in
graph.py's verification_node: claim extraction, batched NLI calls, verdict
aggregation, and reliability scoring.
"""

from __future__ import annotations

import asyncio
from typing import Any

import app.rag.agent.graph as _graph_mod
from app.config import get_model_config
from app.observability.logging import get_logger
from app.observability.metrics import record_verification_claims
from app.rag.agent.graph.state import AgentState
from app.rag.verification.verdict import Thresholds, compute_verdict
from app.rag.verification.verifier import UNCHECKED_CLAIM_STATE, is_refusal_answer

logger = get_logger(__name__)

__all__ = ["verification_node"]


async def verification_node(state: AgentState) -> AgentState:
    """Run claims decomposition and NLI verification, and evaluate reliability thresholds."""
    logger.info("Agent Verification Node starting")

    cfg = get_model_config()
    verification_timeout = cfg.max_verification_time_seconds

    # Empty-KB fast path: the retrieval node already stored the final answer
    # for a knowledge base with zero chunks.
    if (
        state.get("diagnosis_type") in ("RETRIEVAL_FAILURE", "RETRIEVAL_OUTAGE")
        and state.get("answer")
        and not state.get("chunks")
    ):
        state["attempts"] = cfg.max_recovery_attempts
        if state.get("diagnosis_type") == "RETRIEVAL_OUTAGE":
            state["verdict_status"] = "FAIL"
        else:
            state["verdict_status"] = "PASS"
        return state

    answer = state["answer"]

    if not answer or answer == "ABSTAIN" or is_refusal_answer(answer):
        logger.info(
            "Refusal gate hit: skipping claim verification",
            answer_len=len(answer) if answer else 0,
            has_chunks=bool(state.get("chunks")),
        )
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

    await _graph_mod.add_trace_event(
        state["analysis_id"],
        "claims.started",
        {"message": "Decomposing answer and executing NLI verification checks"},
    )

    async def _run_verification() -> list[dict[str, Any]]:
        return await _graph_mod.execute_claim_verification(
            analysis_id_str=state["analysis_id"],
            answer=answer,
            chunks=state["chunks"],
            evidence_ids=state["evidence_ids"],
            user_id_str=state.get("user_id"),
            provider=state.get("llm_provider"),
            model=state.get("llm_model"),
            attempt=state.get("attempts", 0),
            kb_id_str=state.get("kb_id"),
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
        state["verdict_status"] = "FAIL"
        return state
    except Exception as exc:
        logger.error("Verification node failed with error", error=str(exc))
        state["claims"] = []
        state["reliability_score"] = None
        state["diagnosis_type"] = "VERIFICATION_ERROR"
        state["diagnosis_failures"] = [f"Verification failed: {type(exc).__name__}"]
        state["verdict_status"] = "FAIL"
        return state

    state["claims"] = claims

    total = len(claims)
    if total == 0:
        await _graph_mod.add_trace_event(
            state["analysis_id"],
            "claims.empty",
            {"message": "Answer produced no verifiable claims; marking for recovery"},
        )
        state["verdict_status"] = "FAIL"
        state["reliability_score"] = 0.0
        state["diagnosis_type"] = "RETRIEVAL_FAILURE"
        state["diagnosis_failures"] = ["No claims extracted for verification"]
        return state

    supported = sum(1 for c in claims if c["state"] == "SUPPORTED")
    contradicted = sum(1 for c in claims if c["state"] == "CONTRADICTED")
    neutral = sum(1 for c in claims if c["state"] == "NEUTRAL")
    unchecked = sum(1 for c in claims if c["state"] == UNCHECKED_CLAIM_STATE)

    await _graph_mod.add_trace_event(
        state["analysis_id"],
        "claims.verified",
        {
            "message": f"Verified {total} atomic claims",
            "stats": {
                "supported": supported,
                "contradicted": contradicted,
                "neutral": neutral,
                "unchecked": unchecked,
            },
        },
    )

    thresholds = Thresholds(
        minimum_evidence_coverage=cfg.minimum_evidence_coverage,
        maximum_contradiction_rate=cfg.maximum_contradiction_rate,
        abstain_below=cfg.abstain_below,
    )

    verdict = compute_verdict(
        supported=supported,
        contradicted=contradicted,
        neutral=neutral,
        total=supported + contradicted + neutral,
        thresholds=thresholds,
        answer=state.get("answer"),
        unchecked=unchecked,
        query=state.get("query"),
    )

    state["verdict_status"] = verdict.verdict_status.value
    state["reliability_score"] = verdict.reliability_score
    state["diagnosis_type"] = verdict.diagnosis_type.value
    state["diagnosis_failures"] = verdict.diagnosis_failures

    try:
        record_verification_claims(supported, contradicted, neutral)
    except Exception:
        logger.debug("Failed to record verification claims metrics")

    logger.info(
        "Unified verdict computed",
        verdict=verdict.verdict_status.value,
        reliability_score=verdict.reliability_score,
        diagnosis_type=verdict.diagnosis_type.value,
    )

    return state
