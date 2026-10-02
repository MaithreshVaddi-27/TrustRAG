"""
TRUSTRAG — Pluggable Chunking Strategies.

Provides multiple chunking strategies that can be selected at runtime
via models.yaml configuration. All strategies produce consistent output
format compatible with the ingestion pipeline.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.rag.ingestion.chunker import chunk_text
from app.rag.ingestion.preprocessor import detect_chunk_zone, normalize_text

logger = get_logger(__name__)


class ChunkingStrategy:
    """Abstract base class for chunking strategies."""

    def chunk(
        self,
        pages: list[dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Execute chunking according to this strategy."""
        raise NotImplementedError()


class SlidingWindowStrategy(ChunkingStrategy):
    """Standard sliding window chunking (default behavior)."""

    def chunk(
        self,
        pages: list[dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return chunk_text(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


class SemanticChunkingStrategy(ChunkingStrategy):
    """Semantic-aware chunking that respects document structure.

    Attempts to keep related content together based on detected headings,
    sections, or semantic boundaries.
    """

    def chunk(
        self,
        pages: list[dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        chunk_index = 0

        for page_obj in pages:
            page_num = page_obj["page"]
            raw_text = page_obj.get("text", "")
            text = normalize_text(raw_text)

            if not text.strip():
                continue

            ocr_used = bool(page_obj.get("ocr_used", False))
            ocr_confidence = page_obj.get("ocr_confidence")
            page_image_png = page_obj.get("page_image_png")

            # Detect potential section boundaries (headings, etc.)
            lines = text.split("\n")
            sections: list[str] = []
            current_section: list[str] = []

            for line in lines:
                # Heuristic: lines that look like headings (all caps, short, start with #)
                # NOTE: normalize_text lowercases, so the isupper() branch only fires
                # for digit/symbol lines; '#' markdown headings are the live signal.
                is_heading = (
                    line.strip().startswith("#")
                    or (len(line.strip()) < 100 and line.strip().isupper())
                    or line.strip().startswith(("##", "###", "####"))
                )
                if is_heading and current_section:
                    sections.append("\n".join(current_section))
                    current_section = [line]
                elif is_heading:
                    current_section = [line]
                else:
                    current_section.append(line)

            if current_section:
                sections.append("\n".join(current_section))

            # Chunk each section independently, keeping TRUE page offsets so
            # evidence citations (character_offset) stay traceable.
            cursor = 0
            for section in sections:
                if not section.strip():
                    continue
                offset = text.find(section, cursor)
                if offset < 0:
                    offset = cursor
                # Use the standard chunker on each section
                section_result = chunk_text(
                    [
                        {
                            "page": page_num,
                            "text": section,
                            "ocr_used": ocr_used,
                            "ocr_confidence": ocr_confidence,
                            "page_image_png": page_image_png,
                        }
                    ],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                for c in section_result:
                    c["chunk_index"] = chunk_index
                    chunk_index += 1
                    c["page"] = page_num
                    c["character_offset"] = offset + c["character_offset"]
                    c["zone"] = detect_chunk_zone(c["text"], page=page_num)
                chunks.extend(section_result)
                cursor = offset + len(section)

        return chunks


class ProgressiveChunkingStrategy(ChunkingStrategy):
    """Progressive chunking that starts small and grows.

    Useful for documents where initial context is sufficient, but deeper
    content may need larger chunks for coherence.
    """

    def chunk(
        self,
        pages: list[dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        # Use standard chunking but with progressive size adjustment
        all_chunks: list[dict[str, Any]] = []
        chunk_index = 0

        for page_obj in pages:
            page_num = page_obj["page"]
            raw_text = page_obj.get("text", "")
            text = normalize_text(raw_text)

            if not text.strip():
                continue

            ocr_used = bool(page_obj.get("ocr_used", False))
            ocr_confidence = page_obj.get("ocr_confidence")
            page_image_png = page_obj.get("page_image_png")

            length = len(text)
            start = 0

            # Degenerate-config check, warned ONCE per page (M3): the smallest
            # progressive window is 0.5 * chunk_size, so an overlap at/above
            # that collapses the step toward 1 char (507x chunk blowup).
            # Startup validation (_validate_chunk_windows) rejects overlap >=
            # chunk_size; this covers direct calls with in-between values.
            min_window = int(chunk_size * 0.5)
            if chunk_overlap >= min_window:
                logger.warning(
                    "chunk_overlap >= progressive min-window, using full-window steps",
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    min_window=min_window,
                )

            while start < length:
                # Use progressively larger chunks near the beginning
                progress = start / max(length, 1)
                effective_chunk_size = int(chunk_size * (0.5 + 0.5 * progress))
                end = min(start + effective_chunk_size, length)
                raw_slice = text[start:end]
                chunk_content = raw_slice.strip()

                if chunk_content:
                    # Same M4 rule as chunker.py: offset indexes the first
                    # real character, not stripped whitespace.
                    leading_ws = len(raw_slice) - len(raw_slice.lstrip())
                    zone = detect_chunk_zone(chunk_content, page=page_num)
                    all_chunks.append(
                        {
                            "text": chunk_content,
                            "page": page_num,
                            "chunk_index": chunk_index,
                            "character_offset": start + leading_ws,
                            "zone": zone,
                            "ocr_used": ocr_used,
                            "ocr_confidence": ocr_confidence,
                            "page_image_png": page_image_png,
                        }
                    )
                    chunk_index += 1

                if end >= length:
                    break
                # Step scales with the effective window: a fixed full-size step
                # would skip text while windows are still small (silent gaps).
                # Guarded like chunker.py: fall back to a full-window step
                # instead of degrading toward 1 char.
                step = effective_chunk_size - chunk_overlap
                if step <= 0:
                    step = max(1, effective_chunk_size)
                start += step

        return all_chunks


def lines_of(text: str) -> list[str]:
    """Split normalized page text into lines (newlines are preserved by normalize_text)."""
    return text.split("\n")


def is_table_line(line: str) -> bool:
    """Heuristic: pipe-separated or wide multi-space lines look like table rows."""
    stripped = line.strip()
    return (
        "|" in line or stripped.startswith("|") or (len(stripped) > 20 and stripped.count(" ") > 3)
    )


class LayoutAwareChunkingStrategy(ChunkingStrategy):
    """Layout-aware chunking that respects document structure like tables,
    figures, and formatted sections.

    Preserves table boundaries and keeps related visual/text content together.
    """

    def chunk(
        self,
        pages: list[dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        chunk_index = 0

        for page_obj in pages:
            page_num = page_obj["page"]
            raw_text = page_obj.get("text", "")
            text = normalize_text(raw_text)

            if not text.strip():
                continue

            ocr_used = bool(page_obj.get("ocr_used", False))
            ocr_confidence = page_obj.get("ocr_confidence")
            page_image_png = page_obj.get("page_image_png")

            # Group consecutive lines into table vs prose blocks, preserving
            # page order. Tables are chunked as whole blocks (never split
            # row-by-row); prose blocks go through the standard chunker.
            # Blocks are recorded as raw-line spans so the exact page
            # substring (including blank lines) is chunked and every
            # character_offset rebases to true page coordinates (M2) — the
            # old code chunked a re-joined sub-string and never rebased, so
            # every layout chunk after the first pointed at the wrong span
            # (and chunks from different blocks collided on offset 0).
            raw_lines = lines_of(text)
            line_starts: list[int] = []
            pos = 0
            for ln in raw_lines:
                line_starts.append(pos)
                pos += len(ln) + 1  # +1 for the "\n" that split() removed
            blocks: list[tuple[str, int, int]] = []  # (kind, start_idx, end_excl)
            for idx, line in enumerate(raw_lines):
                if not line.strip():
                    if blocks:
                        kind, s, _ = blocks[-1]
                        blocks[-1] = (kind, s, idx + 1)
                    continue
                kind = "table" if is_table_line(line) else "text"
                if blocks and blocks[-1][0] == kind:
                    k, s, _ = blocks[-1]
                    blocks[-1] = (k, s, idx + 1)
                else:
                    blocks.append((kind, idx, idx + 1))

            for kind, start_idx, end_idx in blocks:
                block_text = "\n".join(raw_lines[start_idx:end_idx])
                if not block_text.strip():
                    continue
                block_base = line_starts[start_idx]
                if kind == "table":
                    table_chunks = self._chunk_table_content(
                        block_text,
                        block_base,
                        page_num,
                        chunk_index,
                        chunk_size,
                        chunk_overlap,
                        ocr_used,
                        ocr_confidence,
                        page_image_png,
                    )
                    chunks.extend(table_chunks)
                    chunk_index += len(table_chunks)
                else:
                    section_result = chunk_text(
                        [
                            {
                                "page": page_num,
                                "text": block_text,
                                "ocr_used": ocr_used,
                                "ocr_confidence": ocr_confidence,
                                "page_image_png": page_image_png,
                            }
                        ],
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                    for c in section_result:
                        c["chunk_index"] = chunk_index
                        chunk_index += 1
                        c["page"] = page_num
                        c["character_offset"] = block_base + c["character_offset"]
                    chunks.extend(section_result)

        return chunks

    def _chunk_table_content(
        self,
        combined: str,
        block_base: int,
        page_num: int,
        chunk_index: int,
        chunk_size: int,
        chunk_overlap: int,
        ocr_used: bool = False,
        ocr_confidence: float | None = None,
        page_image_png: bytes | None = None,
    ) -> list[dict[str, Any]]:
        """Chunk table-related content while preserving row structure.

        `combined` is the block's exact page substring (rows joined with
        "\\n", never " ": space-joining glued markdown rows together into
        fabricated rows like `| val 3 | | val 4 |`). Offsets rebase to page
        coordinates via `block_base` (M2).
        """
        if not combined.strip():
            return []

        result = chunk_text(
            [
                {
                    "page": page_num,
                    "text": combined,
                    "ocr_used": ocr_used,
                    "ocr_confidence": ocr_confidence,
                    "page_image_png": page_image_png,
                }
            ],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for i, c in enumerate(result):
            c["chunk_index"] = chunk_index + i
            c["page"] = page_num
            c["zone"] = "table"
            c["character_offset"] = block_base + c["character_offset"]

        return result


# Global strategy instance
_chunking_strategy: ChunkingStrategy | None = None


def get_chunking_strategy() -> ChunkingStrategy:
    """Get the global chunking strategy instance from models.yaml config."""
    global _chunking_strategy
    if _chunking_strategy is None:
        strategy_name = _get_strategy_from_config()
        _chunking_strategy = _create_strategy(strategy_name)
    return _chunking_strategy


def _get_strategy_from_config() -> str:
    """Retrieve the chunking strategy name from models.yaml config."""
    return get_model_config().chunking_strategy


def _create_strategy(strategy_name: str) -> ChunkingStrategy:
    """Create a chunking strategy instance based on the config name."""
    strategies: dict[str, type[ChunkingStrategy]] = {
        "sliding_window": SlidingWindowStrategy,
        "semantic": SemanticChunkingStrategy,
        "progressive": ProgressiveChunkingStrategy,
        "layout_aware": LayoutAwareChunkingStrategy,
    }
    strategy_class = strategies.get(strategy_name.lower(), SlidingWindowStrategy)
    logger.info("Using chunking strategy", strategy=strategy_name)
    return strategy_class()


def clear_chunking_strategy() -> None:
    """Clear the cached chunking strategy (useful for config reloads)."""
    global _chunking_strategy
    _chunking_strategy = None
