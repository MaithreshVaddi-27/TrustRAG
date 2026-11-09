"""
TRUSTRAG — Analysis service: degenerate output detection.

Detects prompt-echo / repetition-loop generations from small local models so
such text is never stored as a synthesis.
"""

from __future__ import annotations

__all__ = [
    "_SCAFFOLD_MARKERS",
    "_UNVERIFIED_ANSWER",
    "_looks_like_scaffold_echo",
]

_SCAFFOLD_MARKERS = (
    # Verbatim CRAFT/TOON fence tokens from the grounding prompts.
    "<context>",
    "<premise>",
    "<craft",
    "<role>",
    "<action>",
    "<format>",
    "<tone>",
    "<loop>",
    "answering_criteria",
    "final_section",
    "final_answer",
    "final_output",
    # Rendered section headings the prompt itself uses.
    "### context",
    "### role",
    "### action",
    "### format",
    "### tone",
    "segment 1 [source:",
)

# A short sentence repeated this many times is a decoding loop, not prose.
_LOOP_REPEAT_THRESHOLD = 3
# Phrases below this length are ignored by the loop detector.
_LOOP_MIN_PHRASE_LEN = 20

# Single user-facing refusal used for every non-TRUSTED terminal state.
_UNVERIFIED_ANSWER = (
    "I couldn't verify an answer from this knowledge base: the retrieved "
    "evidence did not support a grounded response, so I am abstaining rather "
    "than guessing. Try a more specific query or add documents covering this "
    "topic."
)


def _looks_like_scaffold_echo(answer: str | None) -> bool:
    """Detect prompt-echo / repetition-loop generations."""
    if not answer:
        return False
    lowered = answer.lower()
    if any(m in lowered for m in _SCAFFOLD_MARKERS):
        return True

    flattened = lowered.replace("\n", " ")

    # Same substantive sentence 3+ times = repetition loop.
    seen: dict[str, int] = {}
    for sentence in flattened.split(". "):
        s = sentence.strip()
        if len(s) < _LOOP_MIN_PHRASE_LEN:
            continue
        seen[s] = seen.get(s, 0) + 1
        if seen[s] >= _LOOP_REPEAT_THRESHOLD:
            return True

    # One phrase repeated to fill the token cap.
    words = flattened.split()
    if len(words) >= 24:
        for size in (4, 6, 8):
            if len(words) % size:
                continue
            phrases = {" ".join(words[i : i + size]) for i in range(0, len(words), size)}
            if len(phrases) == 1:
                return True
    return False
