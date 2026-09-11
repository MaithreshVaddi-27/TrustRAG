"""
TRUSTRAG — client-side token-frequency sparse vectorizer.

Generates consistent integer indices and weight values for text chunks.
Used directly for Qdrant's sparse vector queries (BM25 fallback).
"""

from __future__ import annotations

from typing import Any

import xxhash

from app.ingestion.preprocessor import ZONE_WEIGHT_BOOSTS, lexical_analyze

VOCAB_SIZE_LIMIT = 1_000_000


def tokenize(text: str) -> list[str]:
    """
    Clean, normalize, tokenize, filter stopwords, and stem words using Porter Stemmer.

    Ensures consistent morphological root alignment between document indexing and query retrieval.
    """
    return lexical_analyze(text, stem=True)


def generate_sparse_vector(
    text: str,
    zone: str = "body",
    is_query: bool = False,
) -> dict[str, list[Any]]:
    """
    Generate sparse vector indices and values for the input text.

    Incorporates:
      - Text normalization, de-hyphenation, and contraction expansion
      - Conversational query noise filtering when is_query=True
      - Porter Stemming
      - Document Zoning boost: terms appearing in TITLE or HEADER zones receive
        amplified weights (e.g. 2.0x for Title, 1.5x for Header)
    """
    tokens = lexical_analyze(text, stem=True, is_query=is_query)
    if not tokens:
        return {"indices": [], "values": []}

    # Apply document zone weight multiplier
    zone_boost = ZONE_WEIGHT_BOOSTS.get(zone, 1.0)

    freqs: dict[int, float] = {}
    for token in tokens:
        idx = xxhash.xxh32(token.encode("utf-8")).intdigest() % VOCAB_SIZE_LIMIT
        freqs[idx] = freqs.get(idx, 0.0) + zone_boost

    total_tokens = len(tokens)

    # Sort indices for predictability
    sorted_indices = sorted(freqs.keys())
    # Normalized by token count, reflecting zone-weighted term frequency
    values = [float(freqs[idx]) / total_tokens for idx in sorted_indices]

    return {"indices": sorted_indices, "values": values}
