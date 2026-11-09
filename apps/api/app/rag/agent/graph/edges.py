"""
TRUSTRAG — LangGraph edges.

Defines the conditional routing logic between workflow nodes previously
inline in graph.py.
"""

from __future__ import annotations

from app.config import get_model_config
from app.rag.agent.graph.state import AgentState

__all__ = [
    "should_end",
    "should_recover",
    "should_verify",
]


def _remaining_budget_ms(state: AgentState) -> float | None:
    """Milliseconds left before the analysis deadline, or None if unbounded."""
    import time

    deadline = state.get("analysis_deadline_monotonic")
    if deadline is None:
        return None
    return max(0.0, (deadline - time.monotonic()) * 1000.0)


def _deadline_spent(state: AgentState) -> bool:
    """True when the analysis-wide wall-clock budget is exhausted."""
    remaining = _remaining_budget_ms(state)
    return remaining is not None and remaining <= 0.0


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
    if _deadline_spent(state):
        remaining_s = (_remaining_budget_ms(state) or 0) / 1000.0
        if state.get("verdict_status") != "PASS":
            state["diagnosis_type"] = "RECOVERY_BUDGET_EXHAUSTED"
            state["diagnosis_failures"] = [
                f"Analysis latency budget exhausted after {state.get('attempts', 0)} "
                f"recovery attempt(s); stopping to respect the time limit"
            ]
        return "end"
    # Check budget exhaustion (set by recovery_node when budget exceeded)
    if state.get("diagnosis_type") == "RECOVERY_BUDGET_EXHAUSTED":
        return "end"
    return "recover"


def should_end(state: AgentState) -> str:
    """Route after recovery: end if attempts exhausted, else loop back."""
    return "end"
