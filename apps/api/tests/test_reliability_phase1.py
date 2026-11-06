"""
Reliability Phase 1 regression tests (audit: docs/evaluation/
RELIABILITY_PHASE1_ABSTENTION_AUDIT.md).

Covers the two defects that produced the Gemma + CRAFT false abstentions
(q022/q024) and the degenerate-claim laundering that a naive fix would have
introduced:

  RC-1  a failed batch NLI call left every claim auto-NEUTRAL, so 0/N coverage
        was reported as LOW_COVERAGE ("insufficient evidence") and the answer
        was withheld. Unverifiable claims are now UNCHECKED, excluded from
        coverage, and force VERIFICATION_UNAVAILABLE — never TRUSTED.
  RC-2  gemma3:1b returned {"vericits": [...]} on 8/8 batch calls; the repair
        alias list did not cover it. The batch schema now tolerates the rename
        and drops template placeholders instead of raising.
  RC-3' degenerate label fragments survived filtering, so re-enabling the
        fallback would have delivered document scaffolding as a grounded answer.

Every test here is deterministic and offline: no model, network, or store.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.rag.verification.verdict import (
    DiagnosisType,
    ReliabilityStatus,
    Thresholds,
    VerdictStatus,
    compute_verdict,
    verdict_from_state,
)
from app.rag.verification.verifier import (
    UNCHECKED_CLAIM_STATE,
    BatchNLIVerdict,
    ClaimVerdict,
    _filter_degenerate_claims,
    execute_claim_verification,
)

_THRESHOLDS = Thresholds(
    minimum_evidence_coverage=0.80,
    maximum_contradiction_rate=0.20,
    abstain_below=0.50,
)


# ── F-1: unverified claims can never be TRUSTED ───────────────────────────────


def test_unchecked_claims_are_never_trusted():
    """Any unchecked claim fails the run, however good the verified subset looks."""
    result = compute_verdict(
        supported=4,
        contradicted=0,
        neutral=0,
        total=4,
        thresholds=_THRESHOLDS,
        answer="A grounded sentence. [Segment 1]",
        unchecked=1,
    )
    assert result.verdict_status == VerdictStatus.FAIL
    assert result.reliability_status == ReliabilityStatus.FAILED
    assert result.diagnosis_type == DiagnosisType.VERIFICATION_UNAVAILABLE
    assert result.reliability_score == 0.0
    assert "could not be verified" in result.diagnosis_failures[0]


def test_all_unchecked_claims_report_verification_unavailable_not_low_coverage():
    """The Phase-1 misdiagnosis: 0 support was reported as LOW_COVERAGE."""
    result = compute_verdict(
        supported=0,
        contradicted=0,
        neutral=0,
        total=0,
        thresholds=_THRESHOLDS,
        answer="A drafted answer.",
        unchecked=5,
    )
    assert result.diagnosis_type == DiagnosisType.VERIFICATION_UNAVAILABLE
    assert result.diagnosis_type != DiagnosisType.LOW_COVERAGE
    assert "verification unavailable" in result.diagnosis_failures[0]


def test_unchecked_with_refusal_answer_keeps_abstained_status():
    """A refusal answer plus unchecked claims stays ABSTAINED, not FAILED."""
    result = compute_verdict(
        supported=0,
        contradicted=0,
        neutral=0,
        total=0,
        thresholds=_THRESHOLDS,
        answer="ABSTAIN",
        unchecked=3,
    )
    assert result.reliability_status == ReliabilityStatus.ABSTAINED
    assert result.diagnosis_type == DiagnosisType.VERIFICATION_UNAVAILABLE


def test_verdict_from_state_counts_unchecked_separately():
    state = {
        "answer": "A drafted answer.",
        "claims": [
            {"state": "SUPPORTED"},
            {"state": "SUPPORTED"},
            {"state": UNCHECKED_CLAIM_STATE},
        ],
    }
    result = verdict_from_state(state, _THRESHOLDS)
    assert result.diagnosis_type == DiagnosisType.VERIFICATION_UNAVAILABLE
    assert result.verdict_status == VerdictStatus.FAIL


def test_verdict_from_state_unchanged_when_everything_is_verified():
    """No regression for the healthy path: 2/2 supported stays TRUSTED."""
    state = {"answer": "x", "claims": [{"state": "SUPPORTED"}, {"state": "SUPPORTED"}]}
    result = verdict_from_state(state, _THRESHOLDS)
    assert result.reliability_status == ReliabilityStatus.TRUSTED
    assert result.diagnosis_type == DiagnosisType.NONE
    assert result.verdict_status == VerdictStatus.PASS


# ── F-1: per-claim fallback runs on recovery rounds, and stays bounded ────────


@pytest.mark.asyncio
@patch("app.rag.verification.verifier.fused_decompose_verify", new=AsyncMock(return_value=None))
@patch("app.rag.verification.verifier.verify_claim_nli")
@patch("app.rag.verification.verifier.batch_verify_claims_nli")
@patch("app.rag.verification.verifier.decompose_answer_to_claims")
async def test_recovery_round_still_verifies_via_individual_fallback(
    mock_decompose, mock_batch_verify, mock_individual
):
    """The Phase-1 false abstention: attempt>0 disabled the fallback, so a
    failed batch call left every claim auto-NEUTRAL. Recovery rounds must still
    verify, and the claims must come back SUPPORTED — not NEUTRAL/UNCHECKED.
    """
    mock_decompose.return_value = [
        "Records under a legal hold are exempt from all deletion.",
        "Backups expire after 7 days.",
    ]
    mock_batch_verify.side_effect = Exception("1 validation error for BatchNLIVerdict")
    mock_individual.return_value = {
        "verdict": "SUPPORTED",
        "supporting_segments": [1],
        "explanation": "The premise states it.",
    }

    mock_collection = MagicMock()
    mock_collection.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=[ObjectId("64ee39d09c6292376e191986")] * 2)
    )
    with patch("app.rag.verification.verifier.get_collection", return_value=mock_collection):
        claims = await execute_claim_verification(
            analysis_id_str="64ee39d09c6292376e191983",
            answer="Records under a legal hold are exempt from all deletion. "
            "Backups expire after 7 days.",
            chunks=[{"text": "Records under a legal hold are exempt from all deletion."}],
            evidence_ids=[ObjectId("64ee39d09c6292376e191987")],
            attempt=2,  # recovery round — the case that used to auto-NEUTRAL
        )

    assert mock_batch_verify.call_count == 2  # one retry, as designed
    assert mock_individual.call_count == 2  # <-- was 0 before the fix
    assert [c["state"] for c in claims] == ["SUPPORTED", "SUPPORTED"]
    assert all(c["state"] != UNCHECKED_CLAIM_STATE for c in claims)


@pytest.mark.asyncio
@patch("app.rag.verification.verifier.fused_decompose_verify", new=AsyncMock(return_value=None))
@patch("app.rag.verification.verifier.verify_claim_nli", new=AsyncMock(return_value=None))
@patch("app.rag.verification.verifier.batch_verify_claims_nli")
@patch("app.rag.verification.verifier.decompose_answer_to_claims")
async def test_exhausted_fallback_budget_marks_claims_unchecked_not_neutral(
    mock_decompose, mock_batch_verify
):
    """When the fallback really cannot run, claims are UNCHECKED (an unknown),
    never NEUTRAL (a false claim of insufficient evidence)."""
    from app.core.config.model_config import get_model_config
    from app.llm.llm_ledger import begin_analysis, end_analysis, record_nli_fallback_call

    # The local tier caps verifiable claims (5); the batch then fails, so every
    # claim lands in the per-claim fallback, which the spent ceiling blocks.
    expected_claims = int(get_model_config().tier_caps("ollama")["max_verification_claims"])
    sentences = [
        f"The policy term number {i} permits records within thirty days." for i in range(8)
    ]
    mock_decompose.return_value = sentences
    mock_batch_verify.side_effect = Exception("structured output unsupported")

    mock_collection = MagicMock()
    mock_collection.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=[ObjectId("64ee39d09c6292376e191986")] * expected_claims)
    )

    token = begin_analysis()
    try:
        # Spend the whole-analysis fallback ceiling so nothing can be retried.
        from app.llm.llm_ledger import max_nli_fallback_calls

        for _ in range(max_nli_fallback_calls()):
            record_nli_fallback_call()
        with patch("app.rag.verification.verifier.get_collection", return_value=mock_collection):
            claims = await execute_claim_verification(
                analysis_id_str="64ee39d09c6292376e191983",
                answer=" ".join(sentences),
                chunks=[{"text": "Records are permitted within thirty days."}],
                evidence_ids=[ObjectId("64ee39d09c6292376e191987")],
                attempt=2,
            )
    finally:
        end_analysis(token)

    assert len(claims) == expected_claims
    assert {c["state"] for c in claims} == {UNCHECKED_CLAIM_STATE}
    assert all("fallback budget is exhausted" in c["explanation"] for c in claims)
    # No evidence linkage: an unchecked claim must not look supported.
    assert all(c["evidence_ids"] == [] for c in claims)


def test_nli_fallback_whole_analysis_ceiling_is_derived_from_config():
    """The bound is real and finite, and inert outside an analysis."""
    from app.llm.llm_ledger import (
        begin_analysis,
        current_ledger,
        end_analysis,
        max_nli_fallback_calls,
        nli_fallback_exhausted,
        record_nli_fallback_call,
    )

    assert nli_fallback_exhausted() is False  # no ledger → inert
    ceiling = max_nli_fallback_calls()
    assert ceiling > 0

    token = begin_analysis()
    try:
        for _ in range(ceiling - 1):
            record_nli_fallback_call()
        assert nli_fallback_exhausted() is False
        record_nli_fallback_call()
        assert nli_fallback_exhausted() is True
        assert current_ledger().nli_fallback_calls == ceiling
    finally:
        end_analysis(token)

    assert nli_fallback_exhausted() is False  # reset with the ledger


def test_ledger_resets_between_analyses():
    from app.llm.llm_ledger import (
        begin_analysis,
        current_ledger,
        end_analysis,
        record_nli_fallback_call,
    )

    first = begin_analysis()
    try:
        record_nli_fallback_call()
        assert current_ledger().nli_fallback_calls == 1
    finally:
        end_analysis(first)

    second = begin_analysis()
    try:
        assert current_ledger().nli_fallback_calls == 0
    finally:
        end_analysis(second)


# ── F-2: batch NLI tolerates key typos, rejects template placeholders ─────────


def test_batch_nli_tolerates_top_level_key_typo():
    """gemma3:1b returned {"vericits": [...]} on 8/8 batch calls; that used to
    raise and (with the fallback disabled) silently abstain the run."""
    parsed = BatchNLIVerdict.model_validate(
        {
            "vericits": [
                {
                    "claim_id": 1,
                    "verdict": "SUPPORTED",
                    "supporting_segments": [2],
                    "explanation": "The premise states it.",
                }
            ]
        }
    )
    assert len(parsed.verdicts) == 1
    assert parsed.verdicts[0].verdict == "SUPPORTED"
    assert parsed.verdicts[0].claim_id == 1


@pytest.mark.parametrize(
    "alias", ["vericits", "verdict", "results", "items", "statements", "claims", "data"]
)
def test_batch_nli_tolerates_known_container_aliases(alias):
    parsed = BatchNLIVerdict.model_validate(
        {alias: [{"claim_id": 1, "verdict": "NEUTRAL", "supporting_segments": []}]}
    )
    assert [v.verdict for v in parsed.verdicts] == ["NEUTRAL"]


def test_batch_nli_rejects_template_placeholders():
    """A shape-template echo must not become verdicts: that would mark claims
    NEUTRAL and suppress the individual fallback that would verify them."""
    parsed = BatchNLIVerdict.model_validate({"vericits": ["VERDICT_1", "VERDICT_2"]})
    assert parsed.verdicts == []


def test_batch_nli_drops_placeholder_rows_keeps_valid_siblings():
    parsed = BatchNLIVerdict.model_validate(
        {
            "verdicts": [
                {"claim_id": 1, "verdict": "VERDICT_1", "supporting_segments": []},
                {"claim_id": 2, "verdict": "SUPPORTED", "supporting_segments": [1]},
                {"verdict": "SUPPORTED"},  # no claim id → unusable
                {"claim_id": 3},  # no verdict → unusable
            ]
        }
    )
    assert [v.claim_id for v in parsed.verdicts] == [2]


def test_batch_nli_empty_container_is_not_an_error():
    """An unusable batch response yields an empty verdict list, so the caller
    falls back per claim instead of raising."""
    assert BatchNLIVerdict.model_validate({"verdicts": []}).verdicts == []
    assert BatchNLIVerdict.model_validate({}).verdicts == []


def test_batch_nli_still_coerces_real_aliases_and_string_ids():
    """The tolerant behaviour of the sibling schemas is preserved."""
    parsed = BatchNLIVerdict.model_validate(
        {
            "verdicts": [
                {
                    "claim_id": "1",
                    "verdict": "VERIFIED.",
                    "supporting_segments": ["2"],
                    "explanation": "ok",
                },
                {
                    "claim_id": 2,
                    "verdict": "S",
                    "supporting_segments": [3],
                    "explanation": "ok",
                },
            ]
        }
    )
    assert [(v.claim_id, v.verdict) for v in parsed.verdicts] == [(1, "SUPPORTED"), (2, "SUPPORTED")]
    assert isinstance(parsed.verdicts[0], ClaimVerdict)


# ── F-3: degenerate claims are dropped before they can be delivered ───────────


def test_filter_degenerate_claims_drops_document_scaffolding():
    dropped = _filter_degenerate_claims(
        [
            "Effective from:",
            "Maximum payload size:",
            "Default request rate limit:",
            "Strict endpoints limit callers to:",
            "The Account Service API",
            "Data Retention Policy",
            "Employee Leave Policy",
            "The Account Service API [Segment 3]",
            "[Segment 2]",
            "1. Eligibility",
            "Who is the administrator?",
            "Deletions",
        ]
    )
    assert dropped == []


def test_filter_degenerate_claims_keeps_real_assertions():
    """No legitimate claim may be dropped — these are the real claim texts the
    fixture corpus produced."""
    kept = _filter_degenerate_claims(
        [
            "Deletion requests are completed within 5 business days",
            "Token revocation takes effect within 60 seconds of the revoke call",
            "Backups expire after 7 days",
            "Surface water temperature increased by 2.4 degrees Celsius",
            "The study covered 12 catchments over 4 years",
            "Bearer tokens remain valid for 30 days after they are issued",
            "Records under a legal hold are exempt from all deletion",
            "Parental leave is granted for 6 months at full pay",
            # Title case, but carries a predicate verb → a real assertion.
            "Bearer Tokens Are Valid For 30 Days",
        ]
    )
    assert len(kept) == 9
    assert "Bearer Tokens Are Valid For 30 Days" in kept


# ── End-to-end guard: the exact Phase-1 failure must not recur ────────────────


@pytest.mark.asyncio
@patch("app.rag.verification.verifier.fused_decompose_verify", new=AsyncMock(return_value=None))
@patch("app.rag.verification.verifier.verify_claim_nli")
@patch("app.rag.verification.verifier.batch_verify_claims_nli")
@patch("app.rag.verification.verifier.decompose_answer_to_claims")
async def test_batch_failure_on_recovery_round_is_verified_not_assumed(
    mock_decompose, mock_batch_verify, mock_individual
):
    """The recorded incident, end to end: a batch that raises twice on a
    recovery round used to leave every claim auto-NEUTRAL (0/N coverage → the
    answer withheld). With the bounded fallback restored, those claims are
    actually verified, so the verdict reflects evidence instead of a failure.
    """
    from app.rag.verification.verdict import Thresholds as T
    from app.core.config.model_config import get_model_config

    cfg = get_model_config()
    mock_decompose.return_value = [
        "Records under a legal hold are exempt from all deletion.",
        "Backups expire after 7 days.",
    ]
    mock_batch_verify.side_effect = Exception("1 validation error for BatchNLIVerdict")
    mock_individual.return_value = {
        "verdict": "SUPPORTED",
        "supporting_segments": [1],
        "explanation": "The premise states it.",
    }

    mock_collection = MagicMock()
    mock_collection.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=[ObjectId("64ee39d09c6292376e191986")] * 2)
    )
    with patch("app.rag.verification.verifier.get_collection", return_value=mock_collection):
        claims = await execute_claim_verification(
            analysis_id_str="64ee39d09c6292376e191983",
            answer="Records under a legal hold are exempt from all deletion.",
            chunks=[{"text": "Records under a legal hold are exempt from all deletion."}],
            evidence_ids=[ObjectId("64ee39d09c6292376e191987")],
            attempt=1,
        )

    thresholds = T(
        minimum_evidence_coverage=cfg.minimum_evidence_coverage,
        maximum_contradiction_rate=cfg.maximum_contradiction_rate,
        abstain_below=cfg.abstain_below,
    )
    verdict = compute_verdict(
        supported=sum(1 for c in claims if c["state"] == "SUPPORTED"),
        contradicted=sum(1 for c in claims if c["state"] == "CONTRADICTED"),
        neutral=sum(1 for c in claims if c["state"] == "NEUTRAL"),
        total=sum(
            1 for c in claims if c["state"] in ("SUPPORTED", "CONTRADICTED", "NEUTRAL")
        ),
        thresholds=thresholds,
        answer="Records under a legal hold are exempt from all deletion.",
        unchecked=sum(1 for c in claims if c["state"] == UNCHECKED_CLAIM_STATE),
    )
    # The fallback ran, so the claims are verified and the run is honest either way.
    assert verdict.verdict_status == VerdictStatus.PASS
    assert verdict.reliability_status == ReliabilityStatus.TRUSTED
    assert verdict.diagnosis_type == DiagnosisType.NONE
