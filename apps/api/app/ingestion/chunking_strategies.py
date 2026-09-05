"""
TRUSTRAG — Pluggable Chunking Strategies.

Provides multiple chunking strategies that can be selected at runtime
via models.yaml configuration. All strategies produce consistent output
format compatible with the ingestion pipeline.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.ingestion.chunker import chunk_text
from app.ingestion.preprocessor import detect_chunk_zone, normalize_text

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

            # Detect potential section boundaries (headings, etc.)
            lines = text.split("\n")
            sections: list[str] = []
            current_section: list[str] = []

            for line in lines:
                # Heuristic: lines that look like headings (all caps, short, start with #)
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

            # Chunk each section independently, then merge adjacent chunks
            section_chunks: list[dict[str, Any]] = []
            for section in sections:
                if not section.strip():
                    continue
                # Use the standard chunker on each section
                section_result = chunk_text(
                    [{"page": page_num, "text": section}],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                section_chunks.extend(section_result)

            # If we have multiple sections, merge first/last chunks to preserve
            # document flow at boundaries
            if len(section_chunks) > 1:
                # Adjust chunk indices
                for i, c in enumerate(section_chunks):
                    c["chunk_index"] = chunk_index + i
                    c["page"] = page_num
                    c["character_offset"] = 0  # Reset for section-based chunking
                    c["zone"] = detect_chunk_zone(c["text"], page=page_num)
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            elif section_chunks:
                c = section_chunks[0]
                c["chunk_index"] = chunk_index
                c["page"] = page_num
                c["character_offset"] = 0
                c["zone"] = detect_chunk_zone(c["text"], page=page_num)
                chunks.append(c)
                chunk_index += 1

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

            length = len(text)
            start = 0
            step = max(1, chunk_size - chunk_overlap)

            while start < length:
                # Use progressively larger chunks near the beginning
                progress = start / max(length, 1)
                effective_chunk_size = int(chunk_size * (0.5 + 0.5 * progress))
                end = min(start + effective_chunk_size, length)
                chunk_content = text[start:end].strip()

                if chunk_content:
                    zone = detect_chunk_zone(chunk_content, page=page_num)
                    all_chunks.append(
                        {
                            "text": chunk_content,
                            "page": page_num,
                            "chunk_index": chunk_index,
                            "character_offset": start,
                            "zone": zone,
                        }
                    )
                    chunk_index += 1

                if end >= length:
                    break
                start += step

        return all_chunks


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

            # Check for table markers or structured content
            lines = text.split("\n")
            table_rows: list[str] = []
            content_lines: list[str] = []

            for line in lines:
                # Detect table-like content (multiple columns, pipe-separated, etc.)
                is_table_line = (
                    "|" in line
                    or line.strip().startswith("|")
                    or (len(line.strip()) > 20 and line.strip().count(" ") > 3)
                )
                if is_table_line and table_rows:
                    # Process accumulated table rows
                    table_chunks = self._chunk_table_content(
                        table_rows, page_num, chunk_index, chunk_size, chunk_overlap
                    )
                    chunks.extend(table_chunks)
                    chunk_index += len(table_chunks)
                    table_rows = [line]
                elif is_table_line:
                    table_rows.append(line)
                else:
                    content_lines.append(line)

            # Process remaining table rows
            if table_rows:
                table_chunks = self._chunk_table_content(
                    table_rows, page_num, chunk_index, chunk_size, chunk_overlap
                )
                chunks.extend(table_chunks)
                chunk_index += len(table_chunks)

            # Chunk remaining content lines
            if content_lines:
                content_text = "\n".join(content_lines)
                if content_text.strip():
                    section_result = chunk_text(
                        [{"page": page_num, "text": content_text}],
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                    for c in section_result:
                        c["chunk_index"] = chunk_index
                        c["page"] = page_num
                        c["zone"] = detect_chunk_zone(c["text"], page=page_num)
                    chunks.extend(section_result)
                    chunk_index += len(section_chunks) if (section_chunks := section_result) else 0

        return chunks

    def _chunk_table_content(
        self,
        table_rows: list[str],
        page_num: int,
        chunk_index: int,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[dict[str, Any]]:
        """Chunk table-related content while preserving row structure."""
        if not table_rows:
            return []

        combined = " ".join(table_rows)
        result = chunk_text(
            [{"page": page_num, "text": combined}],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for c in result:
            c["chunk_index"] = chunk_index
            c["page"] = page_num
            c["zone"] = "table"

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
    from app.core.config import get_model_config

    cfg = get_model_config()
    strategy = getattr(cfg, "_chunking_strategy", None)
    if strategy is None:
        raw = cfg._data.get("ingestion", {})
        strategy = raw.get("chunking_strategy", "sliding_window")
    return strategy


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
