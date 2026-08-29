"""
TRUSTRAG — character-based text chunker.

Chunks document pages using sliding windows with configured size and overlap.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def chunk_text(
    pages: list[dict[str, Any]], chunk_size: int = 512, chunk_overlap: int = 64
) -> list[dict[str, Any]]:
    """
    Split page texts into overlapping character chunks.

    Each chunk records:
      - text: string content of the chunk
      - page: page number it belongs to
      - chunk_index: integer index of chunk in document
      - character_offset: start character index in page
    """
    chunks = []
    chunk_index = 0

    # Guard against a misconfigured chunk_overlap >= chunk_size, which would make
    # the step size zero or negative and hang the loop below forever.
    step = chunk_size - chunk_overlap
    if step <= 0:
        logger.warning(
            "chunk_overlap >= chunk_size, forcing minimum step to avoid infinite loop",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        step = max(1, chunk_size)

    from app.ingestion.preprocessor import detect_chunk_zone, normalize_text

    for page_obj in pages:
        page_num = page_obj["page"]
        raw_text = page_obj.get("text", "")
        text = normalize_text(raw_text)

        if not text.strip():
            continue

        length = len(text)
        start = 0

        # Slide character window
        while start < length:
            end = min(start + chunk_size, length)
            chunk_content = text[start:end].strip()

            if chunk_content:
                zone = detect_chunk_zone(chunk_content, page=page_num)
                chunks.append(
                    {
                        "text": chunk_content,
                        "page": page_num,
                        "chunk_index": chunk_index,
                        "character_offset": start,
                        "zone": zone,
                    }
                )
                chunk_index += 1

            # Check termination
            if end >= length:
                break

            # Slide by step size (size - overlap)
            start += step

    return chunks
