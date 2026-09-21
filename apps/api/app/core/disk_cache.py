"""
Persistent on-disk SQLite embedding cache.
Eliminates redundant embedding passes for identical chunks or queries across runs,
saving 100% of compute load on repeat or revision embeddings.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import struct
import time
from collections.abc import Sequence

import structlog

logger = structlog.get_logger(__name__)

CACHE_DIR = os.getenv(
    "CACHE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache"),
)
DB_PATH = os.path.join(CACHE_DIR, "embedding_cache.db")

# TTL for cache entries (default: 30 days). Set to 0 to disable TTL.
CACHE_TTL_SECONDS = int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", str(30 * 24 * 3600)))


def _get_connection() -> sqlite3.Connection:
    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embedding_cache (
            key TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            vector BLOB NOT NULL,
            dim INTEGER NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    # Add created_at index for TTL cleanup if not exists
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_embedding_cache_created_at ON embedding_cache(created_at)"
    )
    conn.commit()
    return conn


def _cleanup_expired_entries() -> int:
    """Delete cache entries older than CACHE_TTL_SECONDS. Returns count deleted."""
    if CACHE_TTL_SECONDS <= 0:
        return 0
    conn = None
    try:
        conn = _get_connection()
        cutoff = time.time() - CACHE_TTL_SECONDS
        cur = conn.cursor()
        cur.execute("DELETE FROM embedding_cache WHERE created_at < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            # Run VACUUM periodically to reclaim space (cheap when few deletions)
            # Use a simple heuristic: VACUUM every 100 deletions
            if deleted >= 100:
                conn.execute("VACUUM")
        logger.debug("Embedding cache TTL cleanup", deleted=deleted, ttl_seconds=CACHE_TTL_SECONDS)
        return deleted
    except Exception as exc:
        logger.debug("Cache TTL cleanup error", error=str(exc))
        return 0
    finally:
        if conn:
            conn.close()


def _make_key(text: str, model: str) -> str:
    # Normalized key avoids repeat embeddings for case/whitespace variants
    # (OPT: local-LLM/embedding load).
    h = hashlib.sha256(f"{model.strip().lower()}:{text.strip().lower()}".encode()).hexdigest()
    return h


def get_cached_embedding(text: str, model: str) -> list[float] | None:
    """Retrieve embedding vector from SQLite cache if present."""
    key = _make_key(text, model)
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT vector, dim FROM embedding_cache WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        blob, dim = row[0], row[1]
        return list(struct.unpack(f"{dim}f", blob))
    except Exception as exc:
        logger.debug("Disk cache lookup error", error=str(exc))
        return None
    finally:
        if conn:
            conn.close()


def set_cached_embedding(text: str, model: str, vector: Sequence[float]) -> None:
    """Store embedding vector as packed float32 in SQLite cache."""
    if not vector:
        return
    key = _make_key(text, model)
    dim = len(vector)
    blob = struct.pack(f"{dim}f", *vector)
    conn = None
    try:
        conn = _get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO embedding_cache "
            "(key, model, vector, dim, created_at) VALUES (?, ?, ?, ?, ?)",
            (key, model, blob, dim, time.time()),
        )
        conn.commit()
    except Exception as exc:
        logger.debug("Disk cache store error", error=str(exc))
    finally:
        if conn:
            conn.close()


def get_cached_embeddings_batch(
    texts: Sequence[str], model: str
) -> tuple[dict[int, list[float]], list[int]]:
    """
    Check cache for a batch of texts.
    Returns:
      cached: dict mapping index -> embedding vector
      missing_indices: list of indices that need to be computed
    """
    cached: dict[int, list[float]] = {}
    missing_indices: list[int] = []

    if not texts:
        return cached, missing_indices

    conn = None
    try:
        conn = _get_connection()
        keys = [_make_key(text, model) for text in texts]
        indices_by_key: dict[str, list[int]] = {}
        for idx, key in enumerate(keys):
            indices_by_key.setdefault(key, []).append(idx)

        placeholders = ",".join("?" for _ in indices_by_key)
        cur = conn.cursor()
        # Placeholders are generated solely from the number of internal hashes;
        # every key remains bound as a parameter, so no SQL text is user data.
        sql = f"SELECT key,vector,dim FROM embedding_cache WHERE key IN ({placeholders})"  # noqa: S608
        cur.execute(sql, tuple(indices_by_key))
        for key, blob, dim in cur.fetchall():
            vector = list(struct.unpack(f"{dim}f", blob))
            for idx in indices_by_key[key]:
                cached[idx] = vector
        missing_indices = [idx for idx in range(len(texts)) if idx not in cached]
    except Exception as exc:
        logger.debug("Batch disk cache error", error=str(exc))
        missing_indices = list(range(len(texts)))
    finally:
        if conn:
            conn.close()

    return cached, missing_indices


def set_cached_embeddings_batch(
    texts: Sequence[str], model: str, vectors: Sequence[Sequence[float]]
) -> None:
    """
    Batch store embedding vectors in a single transaction.
    Replaces N+1 single-row writes with one executemany call.
    """
    if not texts or not vectors:
        return
    if len(texts) != len(vectors):
        raise ValueError("texts and vectors must have same length")

    conn = None
    try:
        conn = _get_connection()
        # Prepare batch data
        batch_data = []
        for text, vector in zip(texts, vectors, strict=True):
            if not vector:
                continue
            key = _make_key(text, model)
            dim = len(vector)
            blob = struct.pack(f"{dim}f", *vector)
            batch_data.append((key, model, blob, dim, time.time()))

        if batch_data:
            conn.executemany(
                "INSERT OR REPLACE INTO embedding_cache "
                "(key, model, vector, dim, created_at) VALUES (?, ?, ?, ?, ?)",
                batch_data,
            )
            conn.commit()
    except Exception as exc:
        logger.debug("Batch disk cache store error", error=str(exc))
    finally:
        if conn:
            conn.close()


# Module-level cleanup trigger (called from main.py startup or periodically)
_last_cleanup_ts: float = 0.0
CLEANUP_INTERVAL_SECONDS = int(
    os.getenv("EMBEDDING_CACHE_CLEANUP_INTERVAL", str(6 * 3600))
)  # default 6 hours


def maybe_cleanup_cache() -> None:
    """Call periodically (e.g., on startup or via background task) to expire old entries."""
    global _last_cleanup_ts
    now = time.time()
    if now - _last_cleanup_ts >= CLEANUP_INTERVAL_SECONDS:
        _last_cleanup_ts = now
        _cleanup_expired_entries()


__all__ = [
    "get_cached_embedding",
    "set_cached_embedding",
    "get_cached_embeddings_batch",
    "set_cached_embeddings_batch",
    "maybe_cleanup_cache",
    "_cleanup_expired_entries",
]
