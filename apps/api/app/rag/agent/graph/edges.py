"""
TRUSTRAG — LangGraph edges.

Defines the conditional routing logic between workflow nodes previously
inline in graph.py.
"""

from __future__ import annotations

from app.config import get_model_config
from app.rag.agent.graph.budget import deadline_spent, mark_budget_exhausted
from app.rag.agent.graph.state import AgentState

__all__ = [
    "should_end",
    "should_recover",
    "should_verify",
]


def should_verify(state: AgentState) -> str:
    """Route after retrieval: proceed to verification or handle failures."""
    return "verify"


def should_recover(state: AgentState) -> str:
    """Determine if recovery node should execute or terminate the graph run.

    Checks attempt count, PASS verdict, analysis-wide latency budget (audit
    L-1), AND budget exhaustion (tokens/latency).
    """
    cfg = get_model_config()
    max_recovery = cfg.max_recovery_attempts

    if state["verdict_status"] == "PASS" or state["attempts"] >= max_recovery:
        return "end"
    # Analysis-wide wall-clock budget.
    if deadline_spent(state):
        if state.get("verdict_status") != "PASS":
            mark_budget_exhausted(state)
        return "end"
    # Check budget exhaustion (set by recovery_node when budget exceeded)
    if state.get("diagnosis_type") == "RECOVERY_BUDGET_EXHAUSTED":
        return "end"
    return "recover"


def should_end(state: AgentState) -> str:
    """Route after the recovery node: start another round, or terminate.

    The recovery node owns the recovery budget, so it decides whether another
    round is allowed and records that decision in ``state["recovery_next"]``.
    This router only reads it: LangGraph does **not** propagate state mutations
    made inside a conditional-edge function, so a decision taken here could
    never be written back to the run.
    """
    if state.get("recovery_next") == "retrieve":
        return "retrieve"
    return "end"
