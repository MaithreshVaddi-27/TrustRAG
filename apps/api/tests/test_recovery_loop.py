"""
Regression tests for the adaptive recovery loop (audit change B2.1).

Three things about the loop were broken and are pinned here:

1. **The loop never looped.** ``should_end`` always returned ``"end"``, so the
   graph could never re-enter retrieval — every analysis was single-shot, and
   the recovery strategy the recovery node computed was thrown away.
2. **The final verdict was destroyed.** The recovery node clears
   ``answer``/``claims`` so the next round starts clean, but the graph can end
   right after a recovery round. The final verdict was then recomputed from
   the cleared state, so a run that had verified (and contradicted) real
   claims was reported as ``RETRIEVAL_FAILURE / "No claims extracted for
   verification"`` instead of the real diagnosis.
3. **The routing decision could not be written back.** LangGraph does not
   propagate state mutations made inside a conditional-edge function, so the
   "run another round?" decision has to live in the state.

The tests below cover the three scenarios that matter operationally:
recovery exhaustion, successful recovery, and failed recovery.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_model_config
from app.rag.agent.graph.edges import should_end
from app.rag.agent.graph.state import initial_state
from app.rag.agent.graph.verification_snapshot import (
    SNAPSHOT_KEY,
    capture_verification_snapshot,
    clear_verification_snapshot,
    restore_verification_snapshot,
)
from app.rag.verification.verdict import (
    DiagnosisType,
    Thresholds,
    verdict_from_state,
)

ANALYSIS_ID = "64ee39d09c6292376e191983"
KB_ID = "64ee39d09c6292376e191982"
QUERY = "What is the reciprocal rank fusion constant?"

ANSWER = "The reciprocal rank fusion constant is sixty."


def _thresholds() -> Thresholds:
    cfg = get_model_config()
    return Thresholds(
        minimum_evidence_coverage=cfg.minimum_evidence_coverage,
        maximum_contradiction_rate=cfg.maximum_contradiction_rate,
        abstain_below=cfg.abstain_below,
    )


def _initial_state() -> dict:
    return dict(
        initial_state(
            analysis_id_str=ANALYSIS_ID,
            kb_id_str=KB_ID,
            query=QUERY,
            user_id_str="64ee39d09c6292376e191981",
            llm_provider="ollama",
            llm_model="gemma3:1b",
        )
    )


# ─── Unit: the routing decision ─────────────────────────────────────────────


def test_should_end_loops_back_when_another_round_was_recorded():
    """The recovery node records "another round is allowed" in the state."""
    state = _initial_state()
    state["recovery_next"] = "retrieve"
    assert should_end(state) == "retrieve"


def test_should_end_terminates_when_no_further_round_was_recorded():
    """Default (no recorded decision) must fail closed, never loop."""
    state = _initial_state()
    assert should_end(state) == "end"
    state["recovery_next"] = "end"
    assert should_end(state) == "end"


# ─── Unit: the verification snapshot ─────────────────────────────────────────


def test_snapshot_capture_and_restore_round_trip():
    state = _initial_state()
    state["answer"] = ANSWER
    state["claims"] = [{"text": "Sixty is a number", "state": "CONTRADICTED"}]
    state["verdict_status"] = "FAIL"
    state["reliability_score"] = 0.0
    state["diagnosis_type"] = "EVIDENCE_CONFLICT"
    state["diagnosis_failures"] = ["1/1 claims contradicted by evidence"]

    capture_verification_snapshot(state)

    # The recovery node clears the round...
    state["answer"] = None
    state["claims"] = []
    state["diagnosis_type"] = None
    state["diagnosis_failures"] = []
    state["verdict_status"] = "FAIL"
    state["reliability_score"] = None

    assert restore_verification_snapshot(state) is True
    assert state["answer"] == ANSWER
    assert state["claims"] == [{"text": "Sixty is a number", "state": "CONTRADICTED"}]
    assert state["diagnosis_type"] == "EVIDENCE_CONFLICT"
    assert state["diagnosis_failures"] == ["1/1 claims contradicted by evidence"]
    assert state["reliability_score"] == 0.0


def test_snapshot_restore_keeps_a_terminal_recovery_diagnosis():
    """RECOVERY_BUDGET_EXHAUSTED explains why the run stopped; it survives."""
    state = _initial_state()
    state["diagnosis_type"] = "EVIDENCE_CONFLICT"
    state["diagnosis_failures"] = ["1/1 claims contradicted by evidence"]
    capture_verification_snapshot(state)

    state["diagnosis_type"] = "RECOVERY_BUDGET_EXHAUSTED"
    state["diagnosis_failures"] = ["Recovery budget exhausted"]

    restore_verification_snapshot(state)
    assert state["diagnosis_type"] == "RECOVERY_BUDGET_EXHAUSTED"
    # ...but the verified claims are still restored.
    assert state["claims"] == []


def test_snapshot_clear_drops_a_superseded_verification():
    state = _initial_state()
    capture_verification_snapshot(state)
    assert SNAPSHOT_KEY in state
    clear_verification_snapshot(state)
    # The key is cleared to None rather than deleted: AgentState declares it
    # as an optional field and a TypedDict key cannot be removed. A None value
    # means exactly what a missing key meant — nothing to restore.
    assert state[SNAPSHOT_KEY] is None
    assert restore_verification_snapshot(state) is False


# ─── Graph level: the three recovery scenarios ───────────────────────────────


def _compiled_graph():
    """A fresh graph whose retrieval/generation nodes are instrumented.

    The verification and recovery nodes stay real — they are the parts under
    test.
    """
    from app.rag.agent.graph import build as build_mod

    calls: list[str] = []

    async def _retrieval(state):
        calls.append("retrieval")
        state["chunks"] = [{"text": "The RRF constant is sixty.", "filename": "policy.txt"}]
        state["evidence_ids"] = []
        return state

    async def _generation(state):
        calls.append("generation")
        state["answer"] = ANSWER
        return state

    with (
        patch.object(build_mod, "retrieval_node", _retrieval),
        patch.object(build_mod, "generation_node", _generation),
    ):
        graph = build_mod.build_graph().compile()
    return graph, calls


def _patched_runtime(claims_sequence):
    """Patch the collaborators the real nodes reach for.

    ``claims_sequence`` is consumed one entry per verification round; each
    entry is the list of claim dicts the verification node should receive.
    """
    claims_iter = iter(claims_sequence)

    async def _execute_claim_verification(**kwargs):
        return list(next(claims_iter))

    db = MagicMock()
    db.insert_one = AsyncMock()

    model = MagicMock()
    model.bind.return_value = model
    model.ainvoke = AsyncMock()
    model.ainvoke.return_value.content = "expanded query for missing facts"

    return (
        patch("app.rag.agent.graph.execute_claim_verification", _execute_claim_verification),
        patch("app.rag.agent.graph.add_trace_event", AsyncMock()),
        patch("app.rag.agent.graph.get_collection", MagicMock(return_value=db)),
        patch("app.rag.agent.graph.get_verification_model", MagicMock(return_value=model)),
    )


CONTRADICTED_CLAIM = [
    {
        "text": "Sixty is a number",
        "state": "CONTRADICTED",
        "explanation": "The premise contradicts the hypothesis.",
        "evidence_ids": [],
    }
]

SUPPORTED_CLAIM = [
    {
        "text": "The reciprocal rank fusion constant is sixty",
        "state": "SUPPORTED",
        "explanation": "The premise supports the hypothesis.",
        "evidence_ids": [],
    }
]


@pytest.mark.asyncio
async def test_recovery_exhaustion_keeps_the_last_real_verification():
    """When the recovery budget runs out, the run ends with the verdict it earned.

    Before the fix the recovery node cleared the claims and the final verdict
    was recomputed from the empty list, so the stored diagnosis became
    "No claims extracted for verification" instead of the real
    EVIDENCE_CONFLICT.
    """
    graph, calls = _compiled_graph()
    cfg = get_model_config()
    rounds = cfg.max_recovery_attempts

    # Every verification round contradicts the same claim.
    patched = _patched_runtime([CONTRADICTED_CLAIM] * (rounds + 1))
    with patched[0], patched[1], patched[2], patched[3]:
        final = await graph.ainvoke(_initial_state())

    # The loop really ran: retrieval was entered more than once.
    assert calls.count("retrieval") == rounds, calls
    assert final["attempts"] == cfg.max_recovery_attempts

    # The final verdict reflects the claims that were actually verified.
    assert final["claims"], "the verified claims were lost"
    assert final["claims"][0]["state"] == "CONTRADICTED"
    assert final["diagnosis_type"] == "EVIDENCE_CONFLICT"

    verdict = verdict_from_state(final, _thresholds())
    assert verdict.diagnosis_type is DiagnosisType.EVIDENCE_CONFLICT
    assert verdict.diagnosis_failures == [
        "1/1 claims contradicted by evidence",
        "Only 0/1 claims supported by evidence",
    ]
    assert "No claims extracted for verification" not in verdict.diagnosis_failures


@pytest.mark.asyncio
async def test_successful_recovery_loops_back_and_reports_the_fresh_verdict():
    """A recovery round that fixes the problem must produce the fresh verdict.

    This is the routing fix: before it, the graph never re-entered retrieval,
    so a second (successful) verification round could never happen.
    """
    graph, calls = _compiled_graph()

    patched = _patched_runtime([CONTRADICTED_CLAIM, SUPPORTED_CLAIM])
    with patched[0], patched[1], patched[2], patched[3]:
        final = await graph.ainvoke(_initial_state())

    # The graph looped back to retrieval for a second round.
    assert calls.count("retrieval") == 2, calls
    assert calls.count("generation") == 2, calls

    # The final state carries the SECOND round's verdict, not the first.
    assert final["verdict_status"] == "PASS"
    assert final["claims"][0]["state"] == "SUPPORTED"

    verdict = verdict_from_state(final, _thresholds())
    assert verdict.diagnosis_type is DiagnosisType.NONE
    assert verdict.reliability_score == 1.0


@pytest.mark.asyncio
async def test_failed_recovery_ends_with_the_real_diagnosis():
    """A recovery strategy that blows up must not destroy the verdict.

    The recovery node catches the failure and ends the run. The claims that
    were verified before the failure must still be there.
    """
    graph, calls = _compiled_graph()

    patched = _patched_runtime([CONTRADICTED_CLAIM] * 4)
    with (
        patched[0],
        patched[1],
        patched[2],
        patched[3],
        patch(
            "app.rag.agent.graph.nodes.recovery._execute_re_retrieve",
            side_effect=RuntimeError("recovery exploded"),
        ),
    ):
        final = await graph.ainvoke(_initial_state())

    # The recovery strategy failed, so the run ended instead of looping.
    assert calls.count("retrieval") == 1, calls

    # The verdict of the round that actually ran is preserved.
    assert final["claims"], "the verified claims were lost"
    assert final["diagnosis_type"] == "EVIDENCE_CONFLICT"
    verdict = verdict_from_state(final, _thresholds())
    assert verdict.diagnosis_type is DiagnosisType.EVIDENCE_CONFLICT


@pytest.mark.asyncio
async def test_recovery_node_records_the_next_step_in_the_state():
    """The recovery node owns the routing decision and writes it to the state."""
    from app.rag.agent.graph.nodes.recovery import recovery_node

    graph, _calls = _compiled_graph()
    del graph

    db = MagicMock()
    db.insert_one = AsyncMock()
    model = MagicMock()
    model.bind.return_value = model
    model.ainvoke = AsyncMock()
    model.ainvoke.return_value.content = "expanded query for missing facts"

    state = _initial_state()
    state["answer"] = ANSWER
    state["claims"] = list(CONTRADICTED_CLAIM)
    state["verdict_status"] = "FAIL"
    state["reliability_score"] = 0.0
    state["diagnosis_type"] = "EVIDENCE_CONFLICT"
    state["diagnosis_failures"] = ["1/1 claims contradicted by evidence"]

    with (
        patch("app.rag.agent.graph.add_trace_event", AsyncMock()),
        patch("app.rag.agent.graph.get_collection", MagicMock(return_value=db)),
        patch("app.rag.agent.graph.get_verification_model", MagicMock(return_value=model)),
    ):
        result = await recovery_node(state)

    # A strategy was found and budget remains → another round is allowed.
    assert result["recovery_next"] == "retrieve"
    # ...and the snapshot of the completed verification was kept.
    assert SNAPSHOT_KEY in result
    assert result[SNAPSHOT_KEY]["claims"][0]["state"] == "CONTRADICTED"


@pytest.mark.asyncio
async def test_recovery_node_restores_the_verification_when_the_loop_ends():
    """When no further round is allowed, the last verification is restored."""
    from app.rag.agent.graph.nodes.recovery import recovery_node

    db = MagicMock()
    db.insert_one = AsyncMock()
    model = MagicMock()
    model.bind.return_value = model
    model.ainvoke = AsyncMock()
    model.ainvoke.return_value.content = "expanded query for missing facts"

    cfg = get_model_config()
    state = _initial_state()
    state["answer"] = ANSWER
    state["claims"] = list(CONTRADICTED_CLAIM)
    state["verdict_status"] = "FAIL"
    state["reliability_score"] = 0.0
    state["diagnosis_type"] = "EVIDENCE_CONFLICT"
    state["diagnosis_failures"] = ["1/1 claims contradicted by evidence"]
    # Budget spent: this recovery round is the last one.
    state["attempts"] = cfg.max_recovery_attempts - 1
    state["recovery_tokens_used"] = cfg.max_recovery_tokens + 1

    with (
        patch("app.rag.agent.graph.add_trace_event", AsyncMock()),
        patch("app.rag.agent.graph.get_collection", MagicMock(return_value=db)),
        patch("app.rag.agent.graph.get_verification_model", MagicMock(return_value=model)),
    ):
        result = await recovery_node(state)

    assert result["diagnosis_type"] == "RECOVERY_BUDGET_EXHAUSTED"
    assert result["recovery_next"] == "end"
    # The verified claims survived the recovery round.
    assert result["claims"], "the verified claims were lost"


def test_probe_contract_is_unchanged():
    """The cloud probe keeps its keyword-only signature (call sites rely on it).

    The full cloud-probe suite lives in ``tests/test_cloud_probe.py``.
    """
    import inspect

    from app.llm.providers.health import probe_cloud_llm

    params = inspect.signature(probe_cloud_llm).parameters
    assert next(iter(params.values())).kind is inspect.Parameter.KEYWORD_ONLY
    assert set(params) == {"norm", "model", "base_url", "timeout", "hint"}
