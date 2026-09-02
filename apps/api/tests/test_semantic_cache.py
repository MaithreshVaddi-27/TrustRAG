"""
Tests for semantic caching and context pruning.
"""

from app.core.semantic_cache import (
    cosine_similarity,
    check_semantic_cache,
    store_semantic_cache,
    prune_context_tokens,
)


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-5

    v3 = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(v1, v3) - 0.0) < 1e-5

    # Zero vector safety
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_semantic_cache_lifecycle():
    kb = "kb_test_001"
    q1 = "What are the core risk factors of Company X?"
    vec1 = [0.95, 0.05, 0.0]
    data1 = {"answer": "Company X faces operational and currency risks.", "reliability_score": 0.96}

    store_semantic_cache(q1, kb, vec1, data1)

    # Exact query hit
    hit_exact = check_semantic_cache(q1, kb, vec1)
    assert hit_exact is not None
    assert hit_exact["answer"] == data1["answer"]

    # Semantic similarity hit with slightly varied vector
    vec_similar = [0.94, 0.06, 0.01]
    hit_similar = check_semantic_cache(
        "What are the main risks for Company X?", kb, vec_similar, similarity_threshold=0.90
    )
    assert hit_similar is not None
    assert hit_similar["answer"] == data1["answer"]

    # Different KB miss
    assert check_semantic_cache(q1, "kb_other", vec1) is None

    # Dissimilar query miss
    vec_dissimilar = [0.0, 1.0, 0.0]
    assert check_semantic_cache("Unrelated question", kb, vec_dissimilar, similarity_threshold=0.90) is None


def test_prune_context_tokens():
    short = "Short text stays as is."
    assert prune_context_tokens(short) == short

    # Long text with repetitive markdown and duplicate sentences
    content = (
        "--- Segment 1 ---\n"
        "Revenue increased by 14% year over year due to cloud growth. "
        "Revenue increased by 14% year over year due to cloud growth. "
        "Operating expenses remained stable throughout Q3. "
        "=====================\n"
        "Operating expenses remained stable throughout Q3. "
        "The overall outlook remains positive."
    )
    pruned = prune_context_tokens(content, max_chars=2000)
    assert "Revenue increased by 14% year over year due to cloud growth." in pruned
    # Duplicate sentence should appear only once
    assert pruned.count("Revenue increased by 14% year over year due to cloud growth.") == 1
    assert pruned.count("Operating expenses remained stable throughout Q3.") == 1
    # Markdown borders stripped
    assert "===" not in pruned
