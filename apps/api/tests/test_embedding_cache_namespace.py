"""
Embedding-cache namespace tests (audit finding: query/document key collision).

`embed_query` prepends the BGE retrieval instruction; `embed_documents` does
not. For the same input string those are *different vectors*. The two-tier cache
keyed both paths on (model, text) with no discriminator, so whichever call ran
first won the slot and the other silently received the wrong vector — a
retrieval-quality bug with no error surface anywhere, persisted in SQLite for
the life of the cache.

These tests use a delegate that returns a distinguishable vector per mode, so a
collision is observable rather than theoretical.
"""

from __future__ import annotations

import pytest

from app.core.disk_cache import (
    EMBEDDING_MODE_DOCUMENT,
    EMBEDDING_MODE_QUERY,
    _make_key,
    get_cached_embedding,
    get_cached_embeddings_batch,
    set_cached_embedding,
    set_cached_embeddings_batch,
)


@pytest.fixture(autouse=True)
def _isolated_disk_cache(tmp_path, monkeypatch):
    """Point the SQLite cache at a per-test file so nothing leaks between tests
    or into the developer's real cache."""
    import sqlite3

    import app.core.disk_cache as dc

    db = str(tmp_path / "emb_cache.db")
    monkeypatch.setattr(dc, "DB_PATH", db, raising=False)
    monkeypatch.setattr(
        dc, "_get_connection", lambda: sqlite3.connect(db, timeout=10.0), raising=False
    )
    # The schema is created on first connect; mirror _get_connection's setup.
    original = dc._get_connection

    def _conn():
        conn = original()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS embedding_cache "
            "(key TEXT PRIMARY KEY, model TEXT, vector BLOB, dim INTEGER, created_at REAL)"
        )
        conn.commit()
        return conn

    monkeypatch.setattr(dc, "_get_connection", _conn)
    yield


QUERY_VEC = [0.11, 0.22, 0.33]
DOC_VEC = [0.99, 0.88, 0.77]


class _ModeAwareBase:
    """Returns a different vector for query vs document, like the real BGE
    instruction path does."""

    def __init__(self) -> None:
        self.query_calls = 0
        self.doc_calls = 0

    def embed_query(self, text: str) -> list[float]:
        self.query_calls += 1
        return list(QUERY_VEC)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.doc_calls += 1
        return [list(DOC_VEC) for _ in texts]

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)


def _wrapper():
    from app.llm.onnx_embeddings import ONNXBGEEmbeddingsWrapper

    return ONNXBGEEmbeddingsWrapper(_ModeAwareBase(), max_cache_size=16)


# ─── Key namespacing ─────────────────────────────────────────────────────────


def test_query_and_document_keys_differ():
    """The core invariant: one string, two namespaces, two different keys."""
    q = _make_key("retention policy", "bge", EMBEDDING_MODE_QUERY)
    d = _make_key("retention policy", "bge", EMBEDDING_MODE_DOCUMENT)
    assert q != d, "query and document share a cache key — vectors will cross over"


def test_key_is_stable_within_a_mode():
    """Repeated lookups of the same (text, model, mode) must hit, or the cache
    is useless."""
    a = _make_key("retention policy", "bge", EMBEDDING_MODE_QUERY)
    b = _make_key("  Retention Policy  ", "BGE", EMBEDDING_MODE_QUERY)
    assert a == b, "cache key is not normalised for case/whitespace"


def test_cache_version_invalidates_pre_existing_rows():
    """Rows written before the mode discriminator carry no mode, so they cannot be
    trusted. The version prefix must keep them from being read back."""
    import hashlib

    legacy = hashlib.sha256(b"bge:retention policy").hexdigest()
    current = _make_key("retention policy", "bge", EMBEDDING_MODE_DOCUMENT)
    assert current != legacy, (
        "a pre-fix row would still be reachable — legacy rows may hold a query "
        "vector and must not be served as a document vector"
    )


# ─── Disk cache ──────────────────────────────────────────────────────────────


def test_disk_cache_keeps_query_and_document_apart():
    set_cached_embedding("retention policy", "bge", QUERY_VEC, EMBEDDING_MODE_QUERY)
    set_cached_embedding("retention policy", "bge", DOC_VEC, EMBEDDING_MODE_DOCUMENT)

    # The cache packs float32, so a disk round-trip is lossy by design.
    assert get_cached_embedding("retention policy", "bge", EMBEDDING_MODE_QUERY) == pytest.approx(
        QUERY_VEC, abs=1e-6
    )
    assert get_cached_embedding(
        "retention policy", "bge", EMBEDDING_MODE_DOCUMENT
    ) == pytest.approx(DOC_VEC, abs=1e-6)


def test_disk_batch_cache_keeps_document_mode_separate():
    set_cached_embedding("p", "bge", QUERY_VEC, EMBEDDING_MODE_QUERY)
    cached, missing = get_cached_embeddings_batch(["p"], "bge", EMBEDDING_MODE_DOCUMENT)
    assert missing == [0], "a query row was served as a document vector"

    set_cached_embeddings_batch(["p"], "bge", [DOC_VEC], EMBEDDING_MODE_DOCUMENT)
    cached, missing = get_cached_embeddings_batch(["p"], "bge", EMBEDDING_MODE_DOCUMENT)
    assert missing == []
    assert cached[0] == pytest.approx(DOC_VEC, abs=1e-6)


# ─── Wrapper: the end-to-end bug ─────────────────────────────────────────────


def test_wrapper_does_not_serve_a_document_vector_to_a_query():
    """Document first, then query the same text — the exact ordering that used to
    corrupt retrieval."""
    w = _wrapper()
    doc_vec = w.embed_documents(["retention policy"])[0]
    query_vec = w.embed_query("retention policy")

    assert doc_vec == DOC_VEC
    assert query_vec == QUERY_VEC, "query got the cached document vector"
    assert w._base.query_calls == 1, "query was served from cache, not computed"


def test_wrapper_does_not_serve_a_query_vector_to_a_document():
    """The reverse ordering must also be safe."""
    w = _wrapper()
    query_vec = w.embed_query("retention policy")
    doc_vec = w.embed_documents(["retention policy"])[0]

    assert query_vec == QUERY_VEC
    assert doc_vec == DOC_VEC, "document got the cached query vector"
    assert w._base.doc_calls == 1, "document was served from cache, not computed"


@pytest.mark.asyncio
async def test_async_paths_are_namespaced_too():
    """aembed_* is what the graph actually calls; an unsplit async path would
    reintroduce the bug on the hot route while the sync tests still passed."""
    w = _wrapper()
    await w.aembed_documents(["retention policy"])
    q = await w.aembed_query("retention policy")
    assert q == QUERY_VEC, "async query got the cached document vector"

    w2 = _wrapper()
    await w2.aembed_query("retention policy")
    d = (await w2.aembed_documents(["retention policy"]))[0]
    assert d == pytest.approx(DOC_VEC, abs=1e-6), "async document got the cached query vector"


def test_second_identical_query_still_hits_the_cache():
    """The split must not break caching within a mode."""
    w = _wrapper()
    first = w.embed_query("retention policy")
    second = w.embed_query("retention policy")
    assert first == second
    assert w._base.query_calls == 1, "cache never hit for a repeated query"


def test_case_and_whitespace_variants_share_a_slot():
    w = _wrapper()
    w.embed_query("Retention Policy")
    w.embed_query("  retention policy  ")
    assert w._base.query_calls == 1, "normalisation regressed"
