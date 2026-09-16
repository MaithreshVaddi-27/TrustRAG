"""
Tests for semantic caching and context pruning.
"""

import json

from bson import ObjectId

import app.core.semantic_cache as semantic_cache
from app.core.semantic_cache import (
    check_semantic_cache,
    clear_semantic_cache,
    cosine_similarity,
    invalidate_semantic_cache,
    prune_context_tokens,
    store_semantic_cache,
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
    assert (
        check_semantic_cache("Unrelated question", kb, vec_dissimilar, similarity_threshold=0.90)
        is None
    )


def test_semantic_cache_sanitizes_object_ids_for_persistence(tmp_path, monkeypatch):
    """BSON values must not make periodic disk persistence fail silently."""
    cache_file = tmp_path / "semantic_cache.json"
    monkeypatch.setattr(semantic_cache, "PERSISTENCE_FILE", cache_file)
    clear_semantic_cache()
    try:
        store_semantic_cache(
            "cached audit question",
            "kb_json_safe",
            [1.0, 0.0],
            {"answer": "Verified answer.", "legacy_object_id": ObjectId()},
        )
        semantic_cache._persist_cache()

        persisted = json.loads(cache_file.read_text(encoding="utf-8"))
        assert persisted[0]["response"]["answer"] == "Verified answer."
        assert isinstance(persisted[0]["response"]["legacy_object_id"], str)
    finally:
        clear_semantic_cache()


def test_semantic_cache_invalidates_only_target_kb_and_persists(tmp_path, monkeypatch):
    cache_file = tmp_path / "semantic_cache.json"
    monkeypatch.setattr(semantic_cache, "PERSISTENCE_FILE", cache_file)
    clear_semantic_cache()
    try:
        store_semantic_cache("target question", "kb_to_remove", [1.0, 0.0], {"answer": "old"})
        store_semantic_cache("other question", "kb_to_keep", [0.0, 1.0], {"answer": "keep"})

        removed = invalidate_semantic_cache("kb_to_remove")

        assert removed == 1
        assert check_semantic_cache("target question", "kb_to_remove", [1.0, 0.0]) is None
        assert check_semantic_cache("other question", "kb_to_keep", [0.0, 1.0]) is not None
        persisted = json.loads(cache_file.read_text(encoding="utf-8"))
        assert [entry["kb_id"] for entry in persisted] == ["kb_to_keep"]
    finally:
        clear_semantic_cache()


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


def test_cache_directories_coalesce(monkeypatch):
    """All on-disk caches must share the same apps/api/data base directory."""
    # Isolate CACHE_DIR env so a developer override can't flip the assertion.
    monkeypatch.delenv("CACHE_DIR", raising=False)

    from pathlib import Path

    import app.core.disk_cache as disk_cache
    import app.core.local_llm as local_llm

    api_root = Path(semantic_cache.__file__).resolve().parents[2]
    assert str(api_root).endswith("apps/api")

    assert Path(semantic_cache.CACHE_DIR).resolve() == api_root / "data" / "cache"
    assert Path(disk_cache.CACHE_DIR).resolve() == api_root / "data" / "cache"
    # Discovery snapshot sits in the data root (sibling of cache/), same API base.
    assert local_llm._DISCOVERY_SNAPSHOT_PATH.resolve().parent == api_root / "data"
