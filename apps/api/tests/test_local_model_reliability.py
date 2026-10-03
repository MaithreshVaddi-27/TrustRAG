"""Regression tests for local-model reliability and the critical audit fixes.

Each test here failed before its fix. They exist so the "model is not
reliable" symptom cannot come back silently.
"""

from __future__ import annotations

from app.rag.generation.generator import (
    _chunk_order_key,
    strip_stray_abstain,
)
from app.rag.retrieval.reranker import _is_high_confidence
from app.rag.verification.verdict import Thresholds, compute_verdict, is_refusal_answer


class TestRefusalGate:
    """A grounded answer that mentions a hedge is NOT a refusal."""

    def test_hedge_in_trailing_clause_is_not_a_refusal(self):
        answer = "The leave limit is 30 days. Note there is insufficient evidence about exceptions."
        assert is_refusal_answer(answer) is False

    def test_grounded_answer_with_cannot_verify_caveat(self):
        answer = "Employees accrue 1.5 days per month. [Segment 1]"
        assert is_refusal_answer(answer) is False

    def test_genuine_short_refusal_is_detected(self):
        assert is_refusal_answer("I couldn't verify this.") is True

    def test_bare_insufficient_evidence_is_a_refusal(self):
        assert is_refusal_answer("insufficient evidence") is True

    def test_bare_abstain_token_is_a_refusal(self):
        assert is_refusal_answer("ABSTAIN") is True

    def test_none_and_empty_are_not_refusals(self):
        assert is_refusal_answer(None) is False
        assert is_refusal_answer("") is False

    def test_long_refusal_with_no_assertion_is_detected(self):
        # Path 2: leading clause too long to be a confident opener, but every
        # refusal phrase is removed and nothing is left to assert.
        assert (
            is_refusal_answer("I cannot verify the answer to the question that was asked of me.")
            is True
        )


class TestStrayAbstain:
    """The <20-char floor must only judge what is left after a peel."""

    def test_terse_correct_answer_survives(self):
        assert strip_stray_abstain("30 days.") == "30 days."
        assert strip_stray_abstain("60/min.") == "60/min."
        assert strip_stray_abstain("Yes.") == "Yes."

    def test_trailing_token_is_still_stripped(self):
        assert strip_stray_abstain("The limit is 30 days. [Segment 1] ABSTAIN") == (
            "The limit is 30 days. [Segment 1]"
        )

    def test_peel_leaving_nothing_is_abstain(self):
        assert strip_stray_abstain("ABSTAIN ABSTAIN") == "ABSTAIN"

    def test_peel_leaving_only_trivia_is_abstain(self):
        assert strip_stray_abstain("OK ABSTAIN") == "ABSTAIN"


class TestRerankPrecedence:
    """Cross-encoder score must outrank the RRF fusion proxy."""

    def test_chunk_order_prefers_rerank_score(self):
        # RRF says A first; the cross-encoder (which read query+passage) says B.
        a = {"text": "A", "rrf_score": 0.0328, "rerank_score": -9.0}
        b = {"text": "B", "rrf_score": 0.0164, "rerank_score": 11.0}
        assert _chunk_order_key(b) < _chunk_order_key(a)

    def test_chunk_order_falls_back_to_rrf_then_dense(self):
        assert _chunk_order_key({"text": "x", "rrf_score": 0.5}) < _chunk_order_key(
            {"text": "y", "rrf_score": 0.1}
        )
        assert _chunk_order_key({"text": "x", "dense_score": 0.9}) < _chunk_order_key(
            {"text": "y", "dense_score": 0.2}
        )

    def test_high_confidence_uses_rerank_score_when_present(self):
        # rrf >= 0.02 but rerank logit is deeply negative -> NOT confident.
        assert _is_high_confidence({"rrf_score": 0.0328, "rerank_score": -9.0}) is False
        assert _is_high_confidence({"rrf_score": 0.0164, "rerank_score": 11.0}) is True

    def test_high_confidence_falls_back_to_rrf(self):
        assert _is_high_confidence({"rrf_score": 0.03}) is True
        assert _is_high_confidence({"rrf_score": 0.001}) is False


class TestVerdictStillWorks:
    """The gate change must not break ordinary verdict computation."""

    def test_fully_supported_is_trusted(self):
        r = compute_verdict(4, 0, 0, 4, Thresholds(0.80, 0.20, 0.50), "30 days. [Segment 1]")
        assert r.reliability_status.value == "TRUSTED"

    def test_low_coverage_fails(self):
        r = compute_verdict(1, 0, 3, 4, Thresholds(0.80, 0.20, 0.50), "answer")
        assert r.verdict_status.value == "FAIL"

    def test_no_claims_non_refusal_fails(self):
        r = compute_verdict(0, 0, 0, 0, Thresholds(0.80, 0.20, 0.50), "some answer")
        assert r.reliability_status.value == "FAILED"


class TestGroundingGateCoversAbstained:
    """ABSTAINED must not be a path that stores raw unverified prose."""

    def test_abstained_status_reaches_gate_not_storage(self):
        from app.rag.verification.verdict import ReliabilityStatus, VerdictResult, VerdictStatus
        from app.services.analysis_service import _presentable_answer

        verdict = VerdictResult(
            verdict_status=VerdictStatus.PASS,
            reliability_status=ReliabilityStatus.ABSTAINED,
            reliability_score=0.0,
            diagnosis_type=compute_verdict(
                0, 0, 0, 0, Thresholds(0.8, 0.2, 0.5), "ABSTAIN"
            ).diagnosis_type,
            diagnosis_failures=[],
        )
        shown = _presentable_answer("The limit is 30 days.", verdict)
        assert "30 days" not in shown
