"""
TRUSTRAG — Claim verification coercion helpers.

Tolerant normalization of NLI verdict aliases, segment lists, claim ids, and
batch verdict items. Small local models routinely emit near-miss JSON; these
helpers coerce instead of raising so valid claims still get verified.
"""

from __future__ import annotations

import re
from typing import Any

from app.observability.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "_coerce_claim_id",
    "_coerce_segment_list",
    "_normalize_verdict_value",
    "_usable_batch_verdict_item",
]

# Canonical verdict vocabulary.
_CANONICAL_VERDICTS = frozenset({"SUPPORTED", "CONTRADICTED", "NEUTRAL"})

# Aliases small models emit instead of canonical verdict words.
# → SUPPORTED (12 entries) / → CONTRADICTED (12 entries): symmetric by design.
# Unknown strings default NEUTRAL.
_VERDICT_ALIASES: dict[str, str] = {
    # → SUPPORTED
    "VERIFIED": "SUPPORTED",
    "PROVEN": "SUPPORTED",
    "TRUE": "SUPPORTED",
    "CORRECT": "SUPPORTED",
    "YES": "SUPPORTED",
    "ENTAILMENT": "SUPPORTED",
    "ENTAILED": "SUPPORTED",
    "CONFIRMED": "SUPPORTED",
    "VALID": "SUPPORTED",
    # Verb/noun forms and single-letter shorthands reasoning models emit
    # (observed live: verdict "S" for a supported claim).
    "SUPPORT": "SUPPORTED",
    "SUPPORTS": "SUPPORTED",
    "S": "SUPPORTED",
    # Small-model misspelling observed 8/8 with gemma3:1b.
    "VERICITS": "SUPPORTED",
    # → CONTRADICTED
    "REFUTED": "CONTRADICTED",
    "FALSE": "CONTRADICTED",
    "WRONG": "CONTRADICTED",
    "NO": "CONTRADICTED",
    "DISPROVEN": "CONTRADICTED",
    "CONTRADICTS": "CONTRADICTED",
    "REFUTES": "CONTRADICTED",
    "DENIED": "CONTRADICTED",
    "CONTRADICT": "CONTRADICTED",
    "REFUTE": "CONTRADICTED",
    "DISPROVE": "CONTRADICTED",
    "C": "CONTRADICTED",
    # → NEUTRAL
    "UNCERTAIN": "NEUTRAL",
    "UNKNOWN": "NEUTRAL",
    "UNVERIFIED": "NEUTRAL",
    "UNCLEAR": "NEUTRAL",
    "UNRELATED": "NEUTRAL",
    "N/A": "NEUTRAL",
    "NA": "NEUTRAL",
    "NONE": "NEUTRAL",
    "N": "NEUTRAL",
}


def _normalize_verdict_value(value: Any) -> Any:
    """Normalize a raw verdict string to one of SUPPORTED/CONTRADICTED/NEUTRAL."""
    if value is None:
        return value
    if isinstance(value, str):
        upper = value.strip().upper().rstrip(".:;!,")
        if upper in _CANONICAL_VERDICTS:
            return upper
        mapped = _VERDICT_ALIASES.get(upper)
        if mapped is not None:
            logger.debug("Coerced NLI verdict alias", raw=value, mapped=mapped)
            return mapped
        logger.debug("Unknown NLI verdict string; defaulting to NEUTRAL", raw=value)
        return "NEUTRAL"
    return value


def _coerce_segment_list(value: Any) -> list[int]:
    """Coerce mixed supporting_segments into a list of ints.

    Ints pass through; numeric strings and digit runs inside prose
    ("Segment 2 states…") yield their numbers; pure-evidence prose yields
    nothing. Out-of-range numbers are dropped downstream by bounds checks.
    """
    if value is None:
        return []
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, str)):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    out: list[int] = []
    for item in value:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            out.append(item)
        elif isinstance(item, str):
            for match in re.findall(r"-?\d+", item):
                try:
                    out.append(int(match))
                except ValueError:
                    continue
    deduped = list(dict.fromkeys(out))
    if isinstance(value, list) and deduped != list(value):
        logger.debug("Coerced NLI supporting_segments", raw=value, coerced=deduped)
    return deduped


def _coerce_claim_id(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            match = re.search(r"-?\d+", value)
            if match:
                try:
                    return int(match.group(0))
                except ValueError:
                    pass
    return 0


def _usable_batch_verdict_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Return the row only if it maps to a real claim with a real verdict.

    Template echoes ("VERDICT_1", "<array>") and rows with no claim id are
    dropped rather than coerced: coercing them would mark a claim NEUTRAL and
    suppress the individual fallback that would otherwise verify it, which is
    exactly how a malformed batch response became a false abstention.
    """
    if not isinstance(item, dict):
        return None
    claim_id = _coerce_claim_id(item.get("claim_id", item.get("id")))
    if claim_id <= 0:
        logger.debug("Dropped batch NLI row without a claim id", row=str(item)[:80])
        return None
    raw_verdict = item.get("verdict")
    if not isinstance(raw_verdict, str):
        logger.debug("Dropped batch NLI row without a verdict", claim_id=claim_id)
        return None
    bare = raw_verdict.strip().upper().rstrip(".:;!,")
    if bare in _CANONICAL_VERDICTS or bare in _VERDICT_ALIASES:
        return item
    return None
