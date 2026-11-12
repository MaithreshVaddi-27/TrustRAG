"""
TRUSTRAG — Verification snapshot across recovery rounds.

The recovery node clears ``answer`` and ``claims`` so the next round starts
from a clean slate. That is right *while another round follows*, but the graph
can also end right after a recovery round — recovery budget exhausted, the
analysis deadline spent, or no viable recovery strategy. In that case the
cleared state is all that survives, and the final verdict is recomputed from an
empty claim list: a run that verified (and contradicted) real claims is then
reported as ``RETRIEVAL_FAILURE / "No claims extracted for verification"``,
which is a different — and wrong — diagnosis.

This module keeps the last completed verification so the run can end with the
verdict it actually earned. The snapshot lives in the graph state, so it is
carried across node boundaries like any other state field.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "SNAPSHOT_KEY",
    "capture_verification_snapshot",
    "clear_verification_snapshot",
    "restore_verification_snapshot",
]

# State key holding the snapshot of the last completed verification.
SNAPSHOT_KEY = "verification_snapshot"

# Diagnoses set by the recovery machinery itself. They explain WHY the run
# stopped rather than what the answer scored, so a restore keeps them instead
# of overwriting them with the pre-recovery diagnosis.
_TERMINAL_RECOVERY_DIAGNOSES = frozenset({"RECOVERY_BUDGET_EXHAUSTED", "RECOVERY_ERROR"})


def capture_verification_snapshot(state: dict[str, Any]) -> None:
    """Record the completed verification the recovery node is about to clear."""
    state[SNAPSHOT_KEY] = {
        "verdict_status": state.get("verdict_status"),
        "reliability_score": state.get("reliability_score"),
        "diagnosis_type": state.get("diagnosis_type"),
        "diagnosis_failures": list(state.get("diagnosis_failures") or []),
        "answer": state.get("answer"),
        "claims": list(state.get("claims") or []),
    }


def clear_verification_snapshot(state: dict[str, Any]) -> None:
    """Drop the snapshot — a fresh verification supersedes the previous one."""
    state.pop(SNAPSHOT_KEY, None)


def restore_verification_snapshot(state: dict[str, Any]) -> bool:
    """Restore the last completed verification into ``state``.

    Returns ``True`` when a snapshot was restored, ``False`` when there was
    nothing to restore (the run never reached a verification).
    """
    snapshot = state.get(SNAPSHOT_KEY)
    if not snapshot:
        return False

    state["verdict_status"] = snapshot.get("verdict_status")
    state["reliability_score"] = snapshot.get("reliability_score")
    state["answer"] = snapshot.get("answer")
    state["claims"] = list(snapshot.get("claims") or [])

    # A terminal recovery diagnosis describes why the run stopped; it survives.
    if state.get("diagnosis_type") not in _TERMINAL_RECOVERY_DIAGNOSES:
        state["diagnosis_type"] = snapshot.get("diagnosis_type")
        state["diagnosis_failures"] = list(snapshot.get("diagnosis_failures") or [])
    return True
