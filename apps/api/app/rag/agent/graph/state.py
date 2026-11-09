"""
TRUSTRAG — LangGraph agent state definition.

Centralizes the AgentState TypedDict and all graph-level constants so the
workflow nodes remain thin and focused on their single responsibility.
"""

from __future__ import annotations

from typing import Any, TypedDict

from bson import ObjectId

__all__ = [
    "SELF_HEAL_BATCH_SIZE",
    "AgentState",
    "initial_state",
]


# H-BE-5: self-heal re-index batch size. A 10 k-chunk heal embeds + upserts in
# slices of this many chunks so peak RAM stays flat regardless of KB size.
SELF_HEAL_BATCH_SIZE = 128


class AgentState(TypedDict):
    """Mutable state carried through every LangGraph node."""

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
    recovery_strategy: str | None  # "query_rewrite" | "re_retrieve" | "regenerate" | None
    reliability_score: float | None
    diagnosis_type: str | None
    diagnosis_failures: list[str]
    web_search_enabled: bool
    web_search_provider: str  # accepted for API compat; grounding is Tavily-only
    llm_provider: str | None
    llm_model: str | None
    node_errors: list[dict[str, Any]]
    # Recovery budget tracking
    recovery_tokens_used: int
    recovery_latency_ms: int
    # Wall-clock deadline for the WHOLE analysis (audit L-1), not just the
    # recovery node. Set once in execute_agentic_rag_flow from
    # `cost_controls.max_analysis_seconds`; None disables the bound.
    analysis_deadline_monotonic: float | None
    # Cumulative wall-clock spent in retrieval+generation+verification, so the
    # trace can report where the time actually went.
    analysis_elapsed_ms: int


def initial_state(
    *,
    analysis_id_str: str,
    kb_id_str: str,
    query: str,
    user_id_str: str | None = None,
    web_search_enabled: bool = False,
    web_search_provider: str = "both",
    llm_provider: str | None = None,
    llm_model: str | None = None,
    analysis_deadline_monotonic: float | None = None,
) -> AgentState:
    """Build a fresh AgentState for a new analysis run."""
    return AgentState(
        analysis_id=analysis_id_str,
        user_id=user_id_str,
        kb_id=kb_id_str,
        query=query,
        current_query=query,
        answer=None,
        chunks=[],
        evidence_ids=[],
        claims=[],
        attempts=0,
        verdict_status="FAIL",
        recovery_strategy=None,
        reliability_score=None,
        diagnosis_type=None,
        diagnosis_failures=[],
        web_search_enabled=web_search_enabled,
        web_search_provider=web_search_provider,
        llm_provider=llm_provider,
        llm_model=llm_model,
        node_errors=[],
        recovery_tokens_used=0,
        recovery_latency_ms=0,
        analysis_elapsed_ms=0,
        analysis_deadline_monotonic=analysis_deadline_monotonic,
    )
