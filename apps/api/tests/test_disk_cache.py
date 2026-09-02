"""
Unit tests for persistent SQLite embedding cache.
"""

import os
from app.core.disk_cache import (
    get_cached_embedding,
    set_cached_embedding,
    get_cached_embeddings_batch,
    _make_key,
)


def test_make_key():
    k1 = _make_key("Sample text", "model-a")
    k2 = _make_key("Sample text", "model-a")
    k3 = _make_key("Sample text", "model-b")
    assert k1 == k2
    assert k1 != k3


def test_disk_cache_set_and_get(tmp_path, monkeypatch):
    test_db_dir = str(tmp_path / "cache")
    monkeypatch.setenv("CACHE_DIR", test_db_dir)
    monkeypatch.setattr("app.core.disk_cache.CACHE_DIR", test_db_dir)
    monkeypatch.setattr("app.core.disk_cache.DB_PATH", os.path.join(test_db_dir, "test_cache.db"))

    text = "Artificial intelligence and retrieval augmented generation."
    model = "test-embed-v1"
    vec = [0.1234, 0.5678, -0.9876, 0.0]

    # Initially empty
    assert get_cached_embedding(text, model) is None

    # Store
    set_cached_embedding(text, model, vec)

    # Retrieve
    retrieved = get_cached_embedding(text, model)
    assert retrieved is not None
    assert len(retrieved) == len(vec)
    for a, b in zip(retrieved, vec):
        assert abs(a - b) < 1e-4

    # Miss on different model
    assert get_cached_embedding(text, "other-model") is None


def test_disk_cache_batch(tmp_path, monkeypatch):
    test_db_dir = str(tmp_path / "cache_batch")
    monkeypatch.setenv("CACHE_DIR", test_db_dir)
    monkeypatch.setattr("app.core.disk_cache.CACHE_DIR", test_db_dir)
    monkeypatch.setattr("app.core.disk_cache.DB_PATH", os.path.join(test_db_dir, "batch_cache.db"))

    model = "batch-model"
    texts = [
        "First document paragraph",
        "Second document paragraph",
        "Third document paragraph",
    ]
    vecs = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]

    # Pre-cache only item 0 and item 2
    set_cached_embedding(texts[0], model, vecs[0])
    set_cached_embedding(texts[2], model, vecs[2])

    cached_map, missing = get_cached_embeddings_batch(texts, model)

    assert 0 in cached_map
    assert 2 in cached_map
    assert 1 not in cached_map
    assert missing == [1]

    # Verify vector precision
    assert abs(cached_map[0][0] - 1.0) < 1e-4
    assert abs(cached_map[2][2] - 1.0) < 1e-4
