"""
TRUSTRAG — Meta-claim filtering and degenerate claim heuristics.

Small local models often "verify" the prompt instead of the subject matter,
emitting claims like "The user asks for X" or "This is a single-part
question". Such claims can score SUPPORTED (the query text IS in context via
the prompt) and launder a degenerate answer into TRUSTED. These helpers drop
them before verification so echo outputs collapse to zero claims → honest
FAIL/abstain.
"""

from __future__ import annotations

import re

from app.observability.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "_PREDICATE_VERBS",
    "_filter_degenerate_claims",
    "_fused_claims_cover_answer",
    "_is_meta_claim",
]

# Evidence-layout references only when digit-anchored ("Segment 2 states…",
# "Page 8 lists…", "Path A (…"), so subject-matter uses of these words
# ("network segment", "landing page", "career path") pass through.
# The segment pattern excludes bracketed inline citations ("[Segment 1]"),
# which are legitimate provenance markers, not scaffold echo.
_META_CLAIM_PATTERNS = (
    "the user asks",
    "the user is asking",
    "the user's query",
    "the users query",
    "the user query",
    "user query is",
    "user asks for",
    "user prompt",
    "original user",
    "asks to identify",
    "missing facts",
    "reasoning process",
    "single-part question",
    "multi-part question",
    "sub-question",
    "the question asks",
    "the answer must be",
    "provided text",
    "let me re-evaluate",
    "let me re-read",
    "re-evaluate",
    "re-read",
    "critical_path",
    "lets look at",
    "let's look at",
    "let us look at",
)

_META_CLAIM_REGEXES = (
    re.compile(r"(?<!\[)\bsegments?\s+\d"),
    re.compile(r"\bpage\s+\d"),
    re.compile(r"\bpath\s+[a-c0-9]\b"),
)


def _is_meta_claim(text: str) -> bool:
    """True when a claim is about the QA process, not the subject matter."""
    lowered = text.lower().strip()
    if lowered.startswith("#"):
        return True
    if "<context>" in lowered or "answering_criteria" in lowered or "final_section" in lowered:
        return True
    if any(p in lowered for p in _META_CLAIM_PATTERNS):
        return True
    return any(rx.search(lowered) for rx in _META_CLAIM_REGEXES)


def _filter_degenerate_claims(claims: list[str]) -> list[str]:
    """Drop degenerate claims that small models emit instead of facts:
    - questions (end with "?" — usually the model echoed the query)
    - single-word heading-like claims (< 15 chars, title case, no period)
    - label fragments that end mid-thought with a colon
    - title-case heading lines (2-6 words, no terminal punctuation,
      capitalised-initial, no predicate verb)
    - section-numbered lines ("1. Eligibility")
    Returns stripped, non-empty claim texts.
    """
    filtered: list[str] = []
    for c in claims:
        c_stripped = c.strip()
        if not c_stripped:
            continue
        if c_stripped.endswith("?"):
            logger.debug("Dropping question-like claim", claim=c_stripped[:60])
            continue
        if re.match(r"^\d+\.\s+", c_stripped):
            logger.debug("Dropping section-numbered claim", claim=c_stripped[:60])
            continue
        words = c_stripped.split()
        if (
            len(words) == 1
            and len(c_stripped) < 15
            and not c_stripped.endswith((".", "!", "?"))
            and c_stripped[0].isupper()
            and c_stripped == c_stripped.capitalize()
        ):
            logger.debug("Dropping heading-like claim", claim=c_stripped[:60])
            continue
        if len(words) == 1 and not c_stripped.endswith((".", "!", "?")):
            logger.debug("Dropping single-token claim", claim=c_stripped[:60])
            continue
        if c_stripped.endswith(":") and len(words) <= 8:
            logger.debug("Dropping label-fragment claim", claim=c_stripped[:60])
            continue
        if (
            2 <= len(words) <= 6
            and not c_stripped.endswith((".", "!", "?", ";"))
            and all(w[0].isupper() or not w[0].isalpha() for w in words)
            and not any(w.lower().strip(",;:") in _PREDICATE_VERBS for w in words)
        ):
            logger.debug("Dropping title-case heading claim", claim=c_stripped[:60])
            continue
        filtered.append(c_stripped)
    return filtered


def _fused_claims_cover_answer(answer: str, claims: list[str]) -> bool:
    """Conservatively reject fused output that drops answer content."""
    answer_sentences = [
        re.sub(r"\[Segment\s+\d+\]", "", sentence).strip(" #	")
        for sentence in re.split(r"(?<=[.!?])\s+", answer)
        if len(sentence.strip()) > 40
    ]
    claim_tokens = {token for claim in claims for token in re.findall(r"\w+", claim.lower())}
    return bool(claims) and all(
        set(re.findall(r"\w+", sentence.lower())) <= claim_tokens for sentence in answer_sentences
    )


# Relational verbs used to split a claim into subject-predicate-object.
# Deliberately cross-domain: code ("returns", "raises", "imports"), contracts
# ("obliges", "terminates"), science ("correlates", "yields"), prose ("denotes",
# "means").
_PREDICATE_VERBS = frozenset(
    {
        # copula / modality
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "can",
        "cannot",
        "must",
        "should",
        "may",
        "will",
        "would",
        "shall",
        # generic relational
        "allows",
        "requires",
        "provides",
        "contains",
        "includes",
        "excludes",
        "supports",
        "guarantees",
        "specifies",
        "covers",
        "defines",
        "describes",
        "enables",
        "disables",
        "limits",
        "denotes",
        "means",
        "refers",
        "corresponds",
        "implies",
        "depends",
        "extends",
        "implements",
        "correlates",
        "quantifies",
        "regulates",
        # code / api
        "returns",
        "raises",
        "throws",
        "emits",
        "yields",
        "calls",
        "imports",
        "accepts",
        "rejects",
        "reads",
        "writes",
        "creates",
        "updates",
        "removes",
        "validates",
        "executes",
        "resolves",
        "consumes",
        "produces",
        # documents / process
        "obliges",
        "terminates",
        "supersedes",
        "authorizes",
        "governs",
        "applies",
        "expires",
        "establishes",
        "prohibits",
    }
)
