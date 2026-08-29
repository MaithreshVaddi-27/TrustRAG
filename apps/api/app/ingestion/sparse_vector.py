"""
TRUSTRAG — client-side token-frequency sparse vectorizer.

Generates consistent integer indices and weight values for text chunks.
Used directly for Qdrant's sparse vector queries (BM25 fallback).
"""

from __future__ import annotations

from typing import Any

import xxhash

from app.ingestion.preprocessor import ZONE_WEIGHT_BOOSTS, lexical_analyze

# Minimal list of common English stopwords to filter out from sparse queries
STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "aren't",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "can't",
    "cannot",
    "could",
    "couldn't",
    "did",
    "didn't",
    "do",
    "does",
    "doesn't",
    "doing",
    "don't",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "hadn't",
    "has",
    "hasn't",
    "have",
    "haven't",
    "having",
    "he",
    "he'd",
    "he'll",
    "he's",
    "her",
    "here",
    "here's",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "how's",
    "i",
    "i'd",
    "i'll",
    "i'm",
    "i've",
    "if",
    "in",
    "into",
    "is",
    "isn't",
    "it",
    "it's",
    "its",
    "itself",
    "let's",
    "me",
    "more",
    "most",
    "mustn't",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "ought",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "shan't",
    "she",
    "she'd",
    "she'll",
    "she's",
    "should",
    "shouldn't",
    "so",
    "some",
    "such",
    "than",
    "that",
    "that's",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "there's",
    "these",
    "they",
    "they'd",
    "they'll",
    "they're",
    "they've",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "wasn't",
    "we",
    "we'd",
    "we'll",
    "we're",
    "we've",
    "were",
    "weren't",
    "what",
    "what's",
    "when",
    "when's",
    "where",
    "where's",
    "which",
    "while",
    "who",
    "who's",
    "whom",
    "why",
    "why's",
    "with",
    "won't",
    "would",
    "wouldn't",
    "you",
    "you'd",
    "you'll",
    "you're",
    "you've",
    "your",
    "yours",
    "yourself",
    "yourselves",
}

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
