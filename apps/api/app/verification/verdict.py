"""
TRUSTRAG — Unified Trust Verdict Module.

Single source of truth for reliability verdict computation.
Eliminates split-brain between graph.py and analysis_service.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VerdictStatus(str, Enum):
    """Normalized verdict outcomes from the reliability engine."""

    PASS = "PASS"
    FAIL = "FAIL"


class ReliabilityStatus(str, Enum):
    """Final user-facing reliability statuses."""

    TRUSTED = "TRUSTED"
    UNCERTAIN = "UNCERTAIN"
    FAILED = "FAILED"
    ABSTAINED = "ABSTAINED"


class DiagnosisType(str, Enum):
    """Diagnosis categories for failed/abstained analyses."""

    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
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
    if answer == "ABSTAIN":
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