"""
TRUSTRAG — client-side token-frequency sparse vectorizer.

Generates consistent integer indices and weight values for text chunks.
Used directly for Qdrant's sparse vector queries (BM25 fallback).
"""

from __future__ import annotations

import re
from typing import Any

import xxhash

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
    """Clean, lowercase, and tokenize text into words, removing stopwords."""
    text_clean = text.lower()
    # Replace punctuation with spaces
    words = re.findall(r"\b[a-z0-9]{2,}\b", text_clean)
    return [w for w in words if w not in STOPWORDS]


def generate_sparse_vector(text: str) -> dict[str, list[Any]]:
    """
    Generate sparse vector indices and values for the input text.

    Uses xxhash to deterministically map words to consistent 32-bit indices
    within a VOCAB_SIZE_LIMIT range, ensuring stateless alignment.
    Values represent simple term frequency (TF) weights.
    """
    tokens = tokenize(text)
    if not tokens:
        return {"indices": [], "values": []}

    freqs: dict[int, int] = {}
    for token in tokens:
        # Generate consistent 32-bit hash index
        idx = xxhash.xxh32(token.encode("utf-8")).intdigest() % VOCAB_SIZE_LIMIT
        freqs[idx] = freqs.get(idx, 0) + 1

    total_tokens = len(tokens)

    # Sort indices for predictability
    sorted_indices = sorted(freqs.keys())
    # Values normalized by document length (Term Frequency)
    values = [float(freqs[idx]) / total_tokens for idx in sorted_indices]

    return {"indices": sorted_indices, "values": values}
