"""
Unit tests for text preprocessing, lexical analysis, and Porter Stemmer.
"""

from __future__ import annotations

from app.ingestion.preprocessor import (
    PorterStemmer,
    lexical_analyze,
    normalize_text,
    stem_word,
)


def test_normalize_text_bullets_and_artifacts():
    # Tests stripping of PDF bullet artifacts (\uf0d8, \u2022)
    raw = "Introduction \uf0d8 To \u2022 DataStructures"
    normalized = normalize_text(raw)
    assert "\uf0d8" not in normalized
    assert "\u2022" not in normalized
    assert "introduction" in normalized
    assert "datastructures" in normalized


def test_normalize_text_dehyphenation():
    # Tests repairing hyphenated line breaks
    raw = "Information docu-\nmentation and retriev-\n   al."
    normalized = normalize_text(raw)
    assert "documentation" in normalized
    assert "retrieval" in normalized
    assert "docu-" not in normalized


def test_normalize_text_contractions():
    raw = "They aren't able to search because it's cannot be found."
    normalized = normalize_text(raw)
    assert "are not" in normalized
    assert "is" in normalized
    assert "can not" in normalized


def test_porter_stemmer():
    stemmer = PorterStemmer()

    # Standard IR terms
    assert stemmer.stem("indexing") == "index"
    assert stemmer.stem("indexes") == "index"
    assert stemmer.stem("indexed") == "index"
    assert stemmer.stem("retrieval") == "retriev"
    assert stemmer.stem("retrieved") == "retriev"
    assert stemmer.stem("algorithms") == "algorithm"
    assert stemmer.stem("algorithmic") == "algorithm"
    assert stemmer.stem("structures") == "structur"
    assert stemmer.stem("structured") == "structur"
    assert stemmer.stem("stemming") == "stem"
    assert stemmer.stem("summarization") == "summar"


def test_stem_word_helper():
    assert stem_word("categories") == "categori"
    assert stem_word("connected") == "connect"


def test_lexical_analyze_pipeline():
    text = "The automatic indexing and inverted file structures aren't simple."
    tokens = lexical_analyze(text, stem=True)

    # Stopwords like "the", "and", "aren't" (are not) are removed
    assert "the" not in tokens
    assert "and" not in tokens

    # Morphological roots
    assert "automat" in tokens  # automatic -> automat
    assert "index" in tokens    # indexing -> index
    assert "invert" in tokens   # inverted -> invert
    assert "file" in tokens     # file -> file
    assert "structur" in tokens # structures -> structur
    assert "simpl" in tokens    # simple -> simpl


def test_lexical_analyze_without_stemming():
    text = "Automatic indexing systems"
    tokens = lexical_analyze(text, stem=False)
    assert "automatic" in tokens
    assert "indexing" in tokens
    assert "systems" in tokens


def test_document_zoning():
    from app.ingestion.preprocessor import detect_chunk_zone

    # Title zone
    title_chunk = "Information Retrieval Systems\nUNIT-2 Syllabus\nCataloging and Indexing"
    assert detect_chunk_zone(title_chunk, page=1) == "title"

    # Header zone
    header_chunk = "DATA STRUCTURES\nIntroduction to DataStructures"
    assert detect_chunk_zone(header_chunk, page=2) == "header"

    # Metadata zone
    meta_chunk = "Effective from: 2026-08-01\nAuthor: John Doe"
    assert detect_chunk_zone(meta_chunk, page=1) == "metadata"

    # Summary zone
    summary_chunk = "Summary: This document describes automatic indexing."
    assert detect_chunk_zone(summary_chunk, page=2) == "summary"

    # Body zone
    body_chunk = "In trying to determine specific facts, the goal of document summarization is..."
    assert detect_chunk_zone(body_chunk, page=3) == "body"


def test_query_noise_stopwords():
    from app.ingestion.preprocessor import lexical_analyze

    # Query with conversational filler
    query = "Please explain the details regarding automatic indexing"
    # When is_query=True, "please", "explain", "details", "regarding" are filtered out
    tokens = lexical_analyze(query, stem=True, is_query=True)
    assert "automat" in tokens
    assert "index" in tokens
    assert "pleas" not in tokens
    assert "explain" not in tokens
    assert "detail" not in tokens


def test_extract_ngrams():
    from app.ingestion.preprocessor import extract_ngrams

    tokens = ["data", "structur", "index"]
    bigrams = extract_ngrams(tokens, n=2)
    assert bigrams == ["data_structur", "structur_index"]


def test_zone_weighted_sparse_vector():
    from app.ingestion.sparse_vector import generate_sparse_vector

    text = "automatic indexing"
    vec_body = generate_sparse_vector(text, zone="body")
    vec_header = generate_sparse_vector(text, zone="header")
    vec_title = generate_sparse_vector(text, zone="title")

    # Header and title zones receive boosted weights (1.5x and 2.0x) compared to body (1.0x)
    assert vec_title["values"][0] > vec_header["values"][0]
    assert vec_header["values"][0] > vec_body["values"][0]
