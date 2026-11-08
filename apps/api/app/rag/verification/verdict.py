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


def is_refusal_answer(answer: str | None) -> bool:
    """True for ABSTAIN and hedged-refusal prose no verifier can use."""
    if not answer:
        return False
    if answer.strip() == "ABSTAIN":
        return True
    lowered = answer.lower()
    return any(rx.search(lowered) for rx in _REFUSAL_REGEXES)


# Stopwords that frequently appear in questions but carry no topical content
_QUESTION_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "long",
        "many",
        "may",
        "me",
        "might",
        "more",
        "most",
        "much",
        "must",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "shall",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
        # Generic query verbs
        "confirm",
        "state",
        "find",
        "tell",
        "show",
        "describe",
        "explain",
        "give",
        "list",
    }
)


def extract_content_tokens(text: str) -> set[str]:
    """Extract lowercased alphanumeric content tokens (len >= 2 or numbers),
    excluding stopwords."""
    if not text:
        return set()
    tokens = set(re.findall(r"\b[a-z0-9_-]{2,}\b", text.lower()))
    return {t for t in tokens if t not in _QUESTION_STOPWORDS}


def is_responsive_answer(query: str | None, answer: str | None) -> bool:
    """Determine whether an answer responds to the topic of the query.

    Gemma 3 1B and other small models sometimes emit an unrelated fact from a
    served document (e.g. answering 'Backups expire after 7 days' when asked
    'How long are bearer tokens valid?'). Because that fact appears in the
    served document, NLI verifies it as SUPPORTED, which would otherwise
    produce a 100% reliability score for a completely wrong answer.

    Returns True if:
    - Query is absent or contains no substantive content words.
    - Answer is an explicit refusal/abstention.
    - Answer shares at least one content token (or simple stem) with the query.
    """
    if not query or not query.strip():
        return True
    if not answer or not answer.strip():
        return False
    if is_refusal_answer(answer):
        return True

    query_tokens = extract_content_tokens(query)
    if not query_tokens:
        return True

    answer_lower = answer.lower()
    answer_tokens = set(re.findall(r"\b[a-z0-9_-]{2,}\b", answer_lower))

    # Direct token intersection
    if query_tokens & answer_tokens:
        return True

    # Stem / substring match: e.g. "tokens" in query vs "token" in answer,
    # "retention" vs "retained"
    for q_tok in query_tokens:
        if len(q_tok) >= 4:
            if q_tok.endswith("s") and q_tok[:-1] in answer_tokens:
                return True
            stem = q_tok[:4]
            if any(a_tok.startswith(stem) for a_tok in answer_tokens if len(a_tok) >= 4):
                return True
        elif q_tok in answer_tokens:
            return True

    return False


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
    # Verification itself could not run (structured batch call unusable AND the
    # per-claim fallback budget exhausted). Kept separate from LOW_COVERAGE so a
    # verifier outage is never reported as "the evidence was insufficient" —
    # that false attribution is what produced the Phase-1 false abstentions
    # (q022/q024: 12 claims stored with "Verification skipped" explanations were
    # scored as unsupported evidence).
    VERIFICATION_UNAVAILABLE = "VERIFICATION_UNAVAILABLE"
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
    unchecked: int = 0,
    query: str | None = None,
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
        unchecked: Number of claims that could NOT be verified (batch call
            unusable and the per-claim fallback budget exhausted). Excluded from
            the coverage ratio, but a run with any unchecked claim can never be
            TRUSTED: an unverified sentence is an unknown, not trust. Reported as
            VERIFICATION_UNAVAILABLE, never LOW_COVERAGE, so a verifier outage is
            never misattributed to insufficient evidence.
        query: Optional user query string. If provided, answers that are completely
            non-responsive to the query topic (e.g. answering about backups when
            asked about deletion requests) are downgraded to UNCERTAIN / LOW_COVERAGE
            so the grounding gate withholds them.

    Returns:
        VerdictResult with all computed fields
    """
    if query and answer and not is_responsive_answer(query, answer):
        return VerdictResult(
            verdict_status=VerdictStatus.FAIL,
            reliability_status=ReliabilityStatus.UNCERTAIN,
            reliability_score=0.0,
            diagnosis_type=DiagnosisType.LOW_COVERAGE,
            diagnosis_failures=[
                "Answer is non-responsive: addresses an unrelated fact from the "
                "context rather than the question asked"
            ],
        )

    if unchecked > 0:
        # Never TRUSTED while any claim is unverified, however good the
        # verified subset looks. The unchecked sentence may be the hallucination.
        return VerdictResult(
            verdict_status=VerdictStatus.FAIL,
            reliability_status=(
                ReliabilityStatus.ABSTAINED
                if is_refusal_answer(answer)
                else ReliabilityStatus.FAILED
            ),
            reliability_score=0.0,
            diagnosis_type=DiagnosisType.VERIFICATION_UNAVAILABLE,
            diagnosis_failures=[
                f"{unchecked} claim(s) could not be verified against evidence "
                "(verification unavailable); answer withheld"
            ],
        )

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

    Extracts claim counts and answer from LangGraph state. Claims persisted as
    UNCHECKED (batch call unusable and per-claim fallback exhausted) are counted
    separately and force VERIFICATION_UNAVAILABLE, so the trust decision and the
    diagnosis stay honest about what was actually verified.
    """
    claims = state.get("claims", [])
    supported = sum(1 for c in claims if c.get("state") == "SUPPORTED")
    contradicted = sum(1 for c in claims if c.get("state") == "CONTRADICTED")
    neutral = sum(1 for c in claims if c.get("state") == "NEUTRAL")
    unchecked = sum(1 for c in claims if c.get("state") == "UNCHECKED")
    total = supported + contradicted + neutral
    answer = state.get("answer")
    query = state.get("query")

    return compute_verdict(
        supported=supported,
        contradicted=contradicted,
        neutral=neutral,
        total=total,
        thresholds=thresholds,
        answer=answer,
        unchecked=unchecked,
        query=query,
    )
