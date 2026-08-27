"""
TRUSTRAG — character-based text chunker.

Chunks document pages using sliding windows with configured size and overlap.
"""

from __future__ import annotations

from typing import Any


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

    for page_obj in pages:
        page_num = page_obj["page"]
        text = page_obj["text"]

        if not text.strip():
            continue

        length = len(text)
        start = 0

        # Slide character window
        while start < length:
            end = min(start + chunk_size, length)
            chunk_content = text[start:end].strip()

            if chunk_content:
                chunks.append({
                    "text": chunk_content,
                    "page": page_num,
                    "chunk_index": chunk_index,
                    "character_offset": start
                })
                chunk_index += 1

            # Check termination
            if end >= length:
                break

            # Slide by step size (size - overlap)
            start += (chunk_size - chunk_overlap)

    return chunks
