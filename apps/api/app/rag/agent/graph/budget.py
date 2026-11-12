"""
TRUSTRAG — Analysis-wide latency budget.

The budget is a wall-clock deadline for the WHOLE analysis (not just the
recovery node): ``cost_controls.max_analysis_seconds``. Both the routing edges
and the recovery node have to respect it, so it lives in its own small module
instead of being duplicated in each of them.
"""

from __future__ import annotations

import time

from app.rag.agent.graph.state import AgentState

__all__ = [
    "deadline_spent",
    "mark_budget_exhausted",
    "remaining_budget_ms",
]


def remaining_budget_ms(state: AgentState) -> float | None:
    """Milliseconds left before the analysis deadline, or None if unbounded."""
    deadline = state.get("analysis_deadline_monotonic")
    if deadline is None:
        return None
    return max(0.0, (deadline - time.monotonic()) * 1000.0)


def deadline_spent(state: AgentState) -> bool:
    """True when the analysis-wide wall-clock budget is exhausted."""
    remaining = remaining_budget_ms(state)
    return remaining is not None and remaining <= 0.0


def mark_budget_exhausted(state: AgentState) -> None:
    """Record that the analysis stopped because its wall-clock budget ran out.

    This has to be written from a *node*, not from a conditional-edge router:
    LangGraph does not propagate state mutations made inside a routing
    function, so a router can decide but not record.
    """
    state["diagnosis_type"] = "RECOVERY_BUDGET_EXHAUSTED"
    state["diagnosis_failures"] = [
        f"Analysis latency budget exhausted after {state.get('attempts', 0)} "
        f"recovery attempt(s); stopping to respect the time limit"
    ]
