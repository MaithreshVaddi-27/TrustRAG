"""
TRUSTRAG — Unified Trust Verdict Module.

Single source of truth for reliability verdict computation.
Eliminates split-brain between graph.py and analysis_service.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# ─── Refusal gate (deterministic, zero LLM calls) ────────────────────────────
# Small local models (≤3B) usually refuse with hedged prose ("I couldn't
# verify…", "insufficient evidence…") rather than the exact ABSTAIN token.
# Comparing against the bare string therefore misclassifies a correct refusal
# as an unverifiable answer, which FAILs the run and blames retrieval for a
# non-retrieval problem. Lives here so verdict computation and the verifier
# share one definition.
_REFUSAL_REGEXES = (
    re.compile(r"couldn.?t verify"),
    re.compile(r"could not verify"),
    re.compile(r"cann?ot (provide|give|answer|verify|ground)"),
    re.compile(r"can.?t answer"),
    re.compile(r"unable to (answer|verify|provide|ground)"),
    re.compile(r"do n[o']t have (enough|sufficient)"),
    re.compile(r"insufficient (evidence|information|context|grounding|support)"),
    re.compile(
        r"no (verifiable|sufficient|relevant) (claims|evidence|information|context|support)"
    ),
    re.compile(r"cannot be (verified|grounded|supported)"),
)


# A refusal is the model opening by saying it cannot answer. The
# discriminator is the FIRST sentence, not length: a grounded answer states its
# fact first and hedges afterwards ("30 days. Note there is insufficient
# evidence…"), whereas a refusal leads with the refusal and the rest is
# meta-commentary about the answer rather than an assertion about the subject.
_SENTENCE_SPLIT = re.compile(r"[.;!?\n]")


def is_refusal_answer(answer: str | None) -> bool:
    """True when the answer IS a refusal, not merely when it hedges.

    Small local models (≤3B) refuse with hedged prose rather than the exact
    ABSTAIN token, so a substring match is necessary — but not sufficient. A
    grounded answer routinely carries the same hedge in a trailing clause, and
    matching the substring alone abstains precisely the better-hedged answer,
    which surfaces to the user as "model not reliable".

    So the refusal must lead: it appears in the first sentence, or removing
    every refusal phrase leaves nothing at all to assert.
    """
    if not answer:
        return False
    text = answer.strip()
    if text == "ABSTAIN":
        return True

    lead = _SENTENCE_SPLIT.split(text, maxsplit=1)[0]
    if any(rx.search(lead.lower()) for rx in _REFUSAL_REGEXES):
        return True

    # A refusal that does not lead (e.g. it opens with a preamble) still counts
    # when it left no assertion behind.
    residual = text
    for rx in _REFUSAL_REGEXES:
        residual = rx.sub(" ", residual)
    residual = re.sub(r"\[(?:Segment\s+)?\d+\]", " ", residual)
    return not re.sub(r"\W", "", residual)


class VerdictStatus(StrEnum):
    """Normalized verdict outcomes from the reliability engine."""

    PASS = "PASS"  # noqa: S105 — verdict outcome string, not a credential
    FAIL = "FAIL"


class ReliabilityStatus(StrEnum):
    """Final user-facing reliability statuses."""

    TRUSTED = "TRUSTED"
    UNCERTAIN = "UNCERTAIN"
    FAILED = "FAILED"
    ABSTAINED = "ABSTAINED"


class DiagnosisType(StrEnum):
    """Diagnosis categories for failed/abstained analyses."""

    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    RETRIEVAL_OUTAGE = "RETRIEVAL_OUTAGE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    LOW_COVERAGE = "LOW_COVERAGE"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Immutable reliability thresholds from models.yaml."""

    minimum_evidence_coverage: float
    maximum_contradiction_rate: float
    abstain_below: float


@dataclass(frozen=True, slots=True)
class VerdictResult:
    """Complete verdict computation result."""

    verdict_status: VerdictStatus
    reliability_status: ReliabilityStatus
    reliability_score: float
    diagnosis_type: DiagnosisType
    diagnosis_failures: list[str]


def compute_verdict(
    supported: int,
    contradicted: int,
    neutral: int,
    total: int,
    thresholds: Thresholds,
    answer: str | None = None,
) -> VerdictResult:
    """
    Compute the unified trust verdict from claim verification counts.

    Args:
        supported: Number of SUPPORTED claims
        contradicted: Number of CONTRADICTED claims
        neutral: Number of NEUTRAL claims
        total: Total number of claims verified
        thresholds: Reliability thresholds from config
        answer: Optional answer text (used to detect explicit ABSTAIN)

    Returns:
        VerdictResult with all computed fields
    """
    if total == 0:
        # No claims verified. An explicit model ABSTAIN is correct behavior
        # (abstained), not a failure — only a non-empty unverifiable answer fails.
        if is_refusal_answer(answer):
            return VerdictResult(
                verdict_status=VerdictStatus.PASS,
                reliability_status=ReliabilityStatus.ABSTAINED,
                reliability_score=0.0,
                diagnosis_type=DiagnosisType.RETRIEVAL_FAILURE,
                diagnosis_failures=["Model abstained: insufficient grounded evidence"],
            )
        # No claims verified — treat as retrieval failure
        return VerdictResult(
            verdict_status=VerdictStatus.FAIL,
            reliability_status=ReliabilityStatus.FAILED,
            reliability_score=0.0,
            diagnosis_type=DiagnosisType.RETRIEVAL_FAILURE,
            diagnosis_failures=["No claims extracted for verification"],
        )

    coverage = supported / total
    contradiction_rate = contradicted / total

    # Determine PASS/FAIL verdict based on thresholds
    passes_coverage = coverage >= thresholds.minimum_evidence_coverage
    passes_contradiction = contradiction_rate <= thresholds.maximum_contradiction_rate

    if passes_coverage and passes_contradiction:
        verdict_status = VerdictStatus.PASS
    else:
        verdict_status = VerdictStatus.FAIL

    # Compute reliability score: coverage discounted by contradiction rate
    reliability_score = max(0.0, min(1.0, coverage * (1 - contradiction_rate)))

    # Determine diagnosis
    failures: list[str] = []
    if not passes_contradiction:
        failures.append(f"{contradicted}/{total} claims contradicted by evidence")
    if not passes_coverage:
        failures.append(f"Only {supported}/{total} claims supported by evidence")

    if not failures:
        diagnosis_type = DiagnosisType.NONE
    elif not passes_contradiction:
        diagnosis_type = DiagnosisType.EVIDENCE_CONFLICT
    else:
        diagnosis_type = DiagnosisType.LOW_COVERAGE

    # Map to user-facing reliability status
    if is_refusal_answer(answer):
        reliability_status = ReliabilityStatus.ABSTAINED
    elif verdict_status == VerdictStatus.PASS:
        reliability_status = ReliabilityStatus.TRUSTED
    elif reliability_score >= thresholds.abstain_below:
        reliability_status = ReliabilityStatus.UNCERTAIN
    else:
        reliability_status = ReliabilityStatus.FAILED

    return VerdictResult(
        verdict_status=verdict_status,
        reliability_status=reliability_status,
        reliability_score=reliability_score,
        diagnosis_type=diagnosis_type,
        diagnosis_failures=failures,
    )


def verdict_from_state(
    state: dict,
    thresholds: Thresholds,
) -> VerdictResult:
    """
    Compute verdict from graph state dict.

    Extracts claim counts and answer from LangGraph state.
    """
    claims = state.get("claims", [])
    supported = sum(1 for c in claims if c.get("state") == "SUPPORTED")
    contradicted = sum(1 for c in claims if c.get("state") == "CONTRADICTED")
    neutral = sum(1 for c in claims if c.get("state") == "NEUTRAL")
    total = len(claims)
    answer = state.get("answer")

    return compute_verdict(
        supported=supported,
        contradicted=contradicted,
        neutral=neutral,
        total=total,
        thresholds=thresholds,
        answer=answer,
    )
