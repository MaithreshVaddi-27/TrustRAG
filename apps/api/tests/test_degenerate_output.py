"""
Degenerate-output guard + degenerate pipeline config (audit T-10, R-7).

`_looks_like_scaffold_echo` is the only thing standing between a small model
that echoed its prompt (or looped a block until max_tokens) and a user reading
it as a real synthesis. It is pure string logic, so it is tested directly and
at the point where the answer is persisted.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import analysis_service as svc

ANALYSIS_ID = "64ee39d09c6292376e191983"


# ── The detector itself ───────────────────────────────────────────────────────


def test_prompt_echo_is_detected():
    """A model that regurgitates the prompt scaffolding must be flagged."""
    echo = (
        "### Context\n---\nSegment 1 [Source: doc.md, Page 1] ---\nretention is 30 days\n"
        "### Role\nAnswer only from the Context."
    )
    assert svc._looks_like_scaffold_echo(echo) is True


def test_repetition_loop_is_detected():
    """A block repeated until max_tokens is not synthesis either."""
    loop = "the limit is thirty days. " * 12
    assert svc._looks_like_scaffold_echo(loop) is True


def test_real_answer_is_not_flagged():
    """A genuine grounded answer must survive the guard (no false positives)."""
    answer = (
        "Records are retained for 30 days after account closure. "
        "Deletion requests are processed within 45 days."
    )
    assert svc._looks_like_scaffold_echo(answer) is False


@pytest.mark.parametrize(
    "value",
    ["", None, "ABSTAIN", "The limit is 30 days."],
)
def test_short_or_empty_answers_are_not_degenerate(value):
    """The guard must not fire on legitimately short answers."""
    assert svc._looks_like_scaffold_echo(value) is False


# ── The persist path ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_degenerate_answer_is_replaced_before_persist(monkeypatch):
    """End-to-end: an echoed answer must reach Mongo as _UNVERIFIED_ANSWER,
    with the run marked abstained and a generation.degenerate trace event."""
    from app.rag.verification.verdict import DiagnosisType, ReliabilityStatus

    async def _fake_flow(**_kwargs):
        return {
            "answer": (
                "### Context\n---\nSegment 1 [Source: d.md, Page 1] ---\nx\n### Role\nAnswer."
            ),
            "claims": [{"state": "SUPPORTED"}],
            "diagnosis_type": None,
            "diagnosis_failures": [],
            "reliability_score": 0.9,
        }

    coll = MagicMock()
    coll.update_one = AsyncMock()
    trace_events: list[tuple] = []

    async def _trace(_id, event, data):
        trace_events.append((event, data))

    monkeypatch.setattr("app.rag.agent.graph.execute_agentic_rag_flow", _fake_flow)
    monkeypatch.setattr(svc, "get_collection", lambda _n: coll, raising=False)
    monkeypatch.setattr(svc, "add_trace_event", _trace, raising=False)
    monkeypatch.setattr(
        svc,
        "verdict_from_state",
        lambda _s, _t: __import__("types").SimpleNamespace(
            reliability_status=ReliabilityStatus.TRUSTED,
            reliability_score=0.9,
            diagnosis_type=DiagnosisType.NONE,
            diagnosis_failures=[],
        ),
    )
    monkeypatch.setattr(
        "app.core.observability.metrics.record_analysis_completed", lambda *_a, **_k: None
    )

    await svc.run_analysis_pipeline(
        analysis_id_str=ANALYSIS_ID,
        kb_id_str="64ee39d09c6292376e191982",
        query="What is the retention period?",
    )

    set_arg = coll.update_one.call_args_list[-1].args[1]["$set"]
    assert set_arg["answer"] == svc._UNVERIFIED_ANSWER
    assert set_arg["status"] == "abstained"
    assert any(e[0] == "generation.degenerate" for e in trace_events)


@pytest.mark.asyncio
async def test_clean_answer_is_stored_verbatim(monkeypatch):
    """The guard must not swallow a good answer (false-positive guard)."""
    from app.rag.verification.verdict import DiagnosisType, ReliabilityStatus

    answer = "Records are retained for 30 days after account closure."
    captured: dict = {}

    async def _fake_flow(**_kwargs):
        return {
            "answer": answer,
            "claims": [{"state": "SUPPORTED"}],
            "diagnosis_type": None,
            "diagnosis_failures": [],
            "reliability_score": 0.95,
        }

    coll = MagicMock()
    coll.update_one = AsyncMock(side_effect=lambda *a, **k: captured.update(k) or a)
    monkeypatch.setattr("app.rag.agent.graph.execute_agentic_rag_flow", _fake_flow)
    monkeypatch.setattr(svc, "get_collection", lambda _n: coll, raising=False)
    monkeypatch.setattr(svc, "add_trace_event", AsyncMock(return_value=None), raising=False)
    monkeypatch.setattr(
        svc,
        "verdict_from_state",
        lambda _s, _t: __import__("types").SimpleNamespace(
            reliability_status=ReliabilityStatus.TRUSTED,
            reliability_score=0.95,
            diagnosis_type=DiagnosisType.NONE,
            diagnosis_failures=[],
        ),
    )
    monkeypatch.setattr(
        "app.core.observability.metrics.record_analysis_completed", lambda *_a, **_k: None
    )

    await svc.run_analysis_pipeline(
        analysis_id_str=ANALYSIS_ID,
        kb_id_str="64ee39d09c6292376e191982",
        query="What is the retention period?",
    )

    set_arg = coll.update_one.call_args_list[-1].args[1]["$set"]
    assert set_arg["status"] == "completed"
    assert set_arg["answer"] == answer
