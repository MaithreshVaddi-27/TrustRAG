"""
TRUSTRAG — Claim triple extraction heuristic.

Splits a claim assertion into subject-predicate-object using relational verbs.
Sentence order is the natural reading order, so the first relational verb
wins — this avoids the old bug where a low-priority verb occurring late beat
a high-priority one occurring early.
"""

from __future__ import annotations

from app.rag.verification.meta import _PREDICATE_VERBS

__all__ = ["extract_claim_triple_heuristic"]


def extract_claim_triple_heuristic(
    text: str,
) -> tuple[str | None, str | None, str | None]:
    """
    Extract basic subject-predicate-object heuristics from a claim assertion.

    Scans the sentence LEFT TO RIGHT and splits at the first relational verb.
    """
    if not text or not text.strip():
        return None, None, None

    words = text.strip().rstrip(".").split()
    for i, w in enumerate(words):
        if i == 0 or i == len(words) - 1:
            continue  # need something on both sides
        if w.lower().strip(",;:") in _PREDICATE_VERBS:
            return " ".join(words[:i]), w, " ".join(words[i + 1 :])

    # No known verb: fall back to a positional split.
    if len(words) >= 4:
        return " ".join(words[:2]), words[2], " ".join(words[3:])
    return (words[0] if words else None), None, None
