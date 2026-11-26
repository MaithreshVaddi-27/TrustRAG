"""
TRUSTRAG — grounded answer generation: context formatting & pruning.

Context formatting (indexed segments for citation mapping), token pruning,
and citation extraction/stripping utilities.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "extract_citations",
    "extract_final_answer",
    "format_context",
    "format_context_with_chunk_indices",
    "prune_context_tokens",
    "strip_citation_markers",
    "strip_invalid_citations",
    "strip_scaffold_tags",
    "strip_stray_abstain",
    "strip_think_blocks",
]


def prune_context_tokens(context: str, max_chars: int = 6000) -> str:
    """Lightweight, deterministic context pruning & token compaction."""
    if not context or len(context) <= 40:
        return context

    text = re.sub(r"[-=_*]{3,}", "", context)
    text = re.sub(r"[ 	]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])(?:\s+|\n+)", text) if s.strip()]
    seen_sentences: set[str] = set()
    unique_sentences: list[str] = []

    for s in sentences:
        norm = re.sub(r"^[^\w]*", "", s).strip().lower()
        norm = re.sub(r"^segment \d+.*?\n", "", norm).strip()
        if len(norm) > 20 and norm in seen_sentences:
            continue
        seen_sentences.add(norm)
        unique_sentences.append(s)

    pruned = " ".join(unique_sentences)

    if len(pruned) > max_chars:
        truncated = pruned[:max_chars]
        last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_period > int(max_chars * 0.75):
            pruned = truncated[: last_period + 1]
        else:
            pruned = truncated + "..."

    return pruned


# Inline provenance markers the generator is instructed to emit: "[Segment N]" or "[N]".
# Both formats must be supported for backward compatibility with existing outputs.
_CITATION_RE = re.compile(r"\[(?:Segment\s+)?(\d+)\]")


def extract_citations(answer: str) -> list[int]:
    """Return the 1-indexed segment numbers cited as [Segment N], in order."""
    if not answer:
        return []
    return [int(match.group(1)) for match in _CITATION_RE.finditer(answer)]


def strip_citation_markers(answer: str) -> str:
    """Strip [Segment N] / [N] citation markers from answer text.

    Removes dangling spaces before punctuation and collapses double spaces
    so prose flows naturally after marker removal.
    """
    if not answer:
        return answer
    cleaned = _CITATION_RE.sub("", answer)
    cleaned = re.sub(r" ([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ 	]{2,}", " ", cleaned)
    return cleaned.strip()


def strip_stray_abstain(answer: str) -> str:
    """Remove a trailing standalone ABSTAIN token from a substantive answer."""
    if not answer:
        return answer
    text = answer.strip()
    if text == "ABSTAIN":
        return "ABSTAIN"
    while True:
        stripped = text.rstrip()
        if not stripped:
            return "ABSTAIN"
        parts = stripped.rsplit(None, 1)
        last = parts[-1].rstrip(".") if parts else ""
        if last == "ABSTAIN":
            text = stripped[: len(stripped) - len(parts[-1])].rstrip()
            continue
        break
    text = text.strip()
    if len(text) < 20:
        return "ABSTAIN"
    return text


def strip_invalid_citations(
    answer: str,
    valid_segments: int,
    context_chunks: list[str] | None = None,
) -> tuple[str, list[int]]:
    """Remove [Segment N] refs with N outside 1..valid_segments or where segment lacks claim text.

    A cited segment that was never served or that lacks supporting content from
    the cited clause is hallucinated provenance: the ref is stripped (never the
    sentence — entailment is the verifier's job) and reported in the returned
    dropped list. Answers without refs, and fully valid answers, return byte-identical.
    """
    if not answer:
        return answer, []
    dropped: list[int] = []

    _filler_words = {
        "this",
        "that",
        "these",
        "those",
        "from",
        "with",
        "have",
        "been",
        "under",
        "after",
        "before",
        "shall",
        "will",
        "would",
        "could",
        "should",
        "their",
        "there",
        "which",
        "where",
        "about",
        "above",
        "below",
        "between",
        "into",
        "through",
        "during",
        "other",
        "some",
        "such",
        "only",
        "also",
    }

    def _clause_matches_segment(clause: str, segment_text: str) -> bool:
        if not clause or not segment_text:
            return True
        seg_lower = segment_text.lower()
        words = re.findall(r"\b[a-z0-9_-]{3,}\b", clause.lower())
        content = [w for w in words if w not in _filler_words and not w.startswith("segment")]
        if not content:
            return True
        for w in content:
            if w in seg_lower:
                return True
            if w.endswith("s") and len(w) > 4 and w[:-1] in seg_lower:
                return True
            if w.endswith("ed") and len(w) > 5 and w[:-2] in seg_lower:
                return True
        return False

    def _replace(match: re.Match[str]) -> str:
        number = int(match.group(1))
        if not (1 <= number <= valid_segments):
            dropped.append(number)
            return ""

        if context_chunks is not None and 1 <= number <= len(context_chunks):
            prefix = answer[: match.start()]
            last_boundary = max(
                prefix.rfind("\n"),
                prefix.rfind(". "),
                prefix.rfind("; "),
                prefix.rfind("- "),
                0,
            )
            clause = prefix[last_boundary:].strip().lstrip("-*# ")
            seg_text = context_chunks[number - 1]
            if not _clause_matches_segment(clause, seg_text):
                dropped.append(number)
                return ""

        return match.group(0)

    cleaned = _CITATION_RE.sub(_replace, answer)
    if dropped:
        cleaned = re.sub(r"[ 	]{2,}", " ", cleaned)
        cleaned = re.sub(r" ([.,;:!?])", r"\1", cleaned)
    return cleaned, dropped


_THINK_BLOCK_RE = re.compile(
    r"<\s*(think|thinking|thought|reasoning)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_THINK_OPEN_RE = re.compile(r"<\s*(think|thinking|thought|reasoning)\b[^>]*>", re.IGNORECASE)


def strip_think_blocks(answer: str) -> str:
    """Remove thinking-model reasoning traces from model output.

    Handles closed blocks anywhere, plus a trailing unclosed opener (the
    model was cut mid-thought — everything from the opener on is trace).
    Returns the input unchanged when no markers exist.
    """
    if not answer or "<" not in answer:
        return answer
    cleaned = _THINK_BLOCK_RE.sub("", answer)
    match = _THINK_OPEN_RE.search(cleaned)
    if match:
        cleaned = cleaned[: match.start()]
    return cleaned


_SCAFFOLD_TAG_RE = re.compile(
    r"(?:\[Query\]|\[Query:\]|<CONTEXT>|</CONTEXT>|\[CONTEXT\]|\[/CONTEXT\])",
    re.IGNORECASE,
)
_SCAFFOLD_XML_RE = re.compile(
    r"</?(?:Query|Context|Premise|Role|Action|Format|Tone|Loop)[^>]*>", re.IGNORECASE
)


def strip_scaffold_tags(answer: str) -> str:
    """Remove echoed prompt scaffold tags ([Query], <CONTEXT>, etc.) from the final answer."""
    if not answer:
        return answer
    cleaned = _SCAFFOLD_TAG_RE.sub("", answer)
    cleaned = _SCAFFOLD_XML_RE.sub("", cleaned)
    if cleaned != answer:
        cleaned = re.sub(r"[ 	]{2,}", " ", cleaned)
        cleaned = re.sub(r" ([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


_ANSWER_SECTION_MARKERS = ("[FINAL_ANSWER]", "[ANSWER]")
_SCAFFOLD_BLOCK_MARKERS = (
    "[CONTEXT]",
    "[QUERY]",
    "[RELEVANCE]",
    "[REASONING]",
    "[VALIDATION]",
    "ANSWERING_CRITERIA",
    "FINAL_SECTION",
    "FINAL_OUTPUT",
    "<CONTEXT>",
    "<QUERY>",
)


def _strip_leading_fenced_echo(text: str) -> str:
    """Drop scaffold blocks the model emitted BEFORE the real answer.

    Removes any number of leading fenced/bracket blocks, with or without a
    closing tag. Bounded so a malformed unclosed tag cannot loop forever.
    A tag only counts as scaffolding if it starts a block (followed by a
    newline or its close tag); prose mentions of tags survive intact.
    """
    closing = {
        "<CONTEXT>": "</CONTEXT>",
        "<QUERY>": "</QUERY>",
        "[CONTEXT]": None,
        "[QUERY]": None,
    }
    for _ in range(4):  # bounded: a runaway tag cannot loop forever
        stripped = text.lstrip()
        if not stripped:
            return ""
        upper = stripped.upper()
        matched = False
        for open_tag, close_tag in closing.items():
            if not upper.startswith(open_tag):
                continue
            tail = stripped[len(open_tag) :]
            is_block = tail[:1] in ("\n", "\r", "") or (
                close_tag is not None and tail.upper().lstrip().startswith(close_tag)
            )
            if not is_block:
                continue
            matched = True
            rest = tail
            if close_tag is not None:
                close_idx = rest.upper().find(close_tag)
                if close_idx != -1:
                    rest = rest[close_idx + len(close_tag) :]
            else:
                rest = rest.split("\n\n", 1)[-1]
            text = rest
            break
        if not matched:
            break
    return text


def extract_final_answer(answer: str) -> str:
    """Return the model's final answer with prompt-echo scaffolding removed."""
    if not answer:
        return answer

    text = answer
    for marker in _ANSWER_SECTION_MARKERS:
        idx = text.rfind(marker)
        if idx != -1:
            text = text[idx + len(marker) :]
            break

    text = _strip_leading_fenced_echo(text)

    cut_at = len(text)
    for marker in _SCAFFOLD_BLOCK_MARKERS:
        if marker == "[ANSWER]":
            continue
        start = 0
        while True:
            idx = text.upper().find(marker, start)
            if idx == -1:
                break
            at_line_start = idx == 0 or text[idx - 1] in "\n\r"
            if at_line_start:
                cut_at = min(cut_at, idx)
                break
            start = idx + 1
    text = text[:cut_at]

    stripped = text.strip()
    if stripped.lower().startswith("answer:"):
        stripped = stripped[len("answer:") :].strip()

    if len(stripped) < 20:
        return answer.strip()
    return stripped


def _chunk_order_key(chunk: dict[str, Any]) -> tuple[float, str]:
    """Deterministic, provider-independent ordering key for evidence chunks."""
    score = chunk.get("rrf_score")
    if score is None:
        score = chunk.get("rerank_score")
    if score is None:
        score = chunk.get("dense_score")
    text = chunk.get("text", "").strip()
    return (-float(score or 0.0), text.lower()[:120])


def _sanitize_label(value: str, max_len: int = 80) -> str:
    """Strip control characters and truncate label to prevent context boundary injection."""
    sanitized = "".join(ch for ch in value if ch.isprintable() and ch not in "\n\r	")
    return sanitized[:max_len]


def format_context_with_chunk_indices(
    chunks: list[dict[str, Any]],
    max_chars: int | None = None,
    provider: str | None = None,
) -> tuple[str, list[int]]:
    """Format chunks and return the original index represented by each segment.

    Segments are sorted by score (descending) then text, deduped by punctuation-
    insensitive prefix, and numbered sequentially starting at Segment 1. Segment
    numbering stays aligned with ``chunk_indices``.
    """
    if max_chars is None:
        try:
            from app.config import get_model_config

            max_chars = get_model_config().evidence_budget_chars(provider)
        except Exception:
            max_chars = 3000
    if not chunks:
        return "", []

    formatted: list[str] = []
    chunk_indices: list[int] = []
    seen_prefixes: set[str] = set()
    indexed_chunks = sorted(enumerate(chunks), key=lambda item: _chunk_order_key(item[1]))
    total_chars = 0
    display_idx = 0
    for chunk_idx, c in indexed_chunks:
        text = c.get("text", "").strip()
        if not text:
            continue
        # Deduplicate identical or near-identical text snippets.
        prefix = re.sub(r"[^a-z0-9\s]", "", text.lower())
        prefix = " ".join(prefix.split()[:20])
        if prefix in seen_prefixes:
            continue
        seen_prefixes.add(prefix)
        display_idx += 1

        filename = _sanitize_label(c.get("filename") or "unknown_doc")
        page = int(c.get("page") or 1)
        body = prune_context_tokens(text)
        segment = f"--- Segment {display_idx} [Source: {filename}, Page {page}] ---\n{body}"
        segment_len = len(segment) + (2 if formatted else 0)

        if formatted and total_chars + segment_len > max_chars:
            break
        if not formatted and segment_len > max_chars:
            formatted.append(segment)
            chunk_indices.append(chunk_idx)
            total_chars += segment_len
            break

        formatted.append(segment)
        chunk_indices.append(chunk_idx)
        total_chars += segment_len

    return "\n\n".join(formatted), chunk_indices


def format_context(chunks: list[dict[str, Any]]) -> str:
    """Format evidence segments into a clean structured block with deduplication."""
    context, _ = format_context_with_chunk_indices(chunks)
    return context
