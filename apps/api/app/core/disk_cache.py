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
    conn.commit()
    return conn


def _make_key(text: str, model: str) -> str:
    h = hashlib.sha256(f"{model}:{text.strip()}".encode()).hexdigest()
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
            "INSERT OR REPLACE INTO embedding_cache (key, model, vector, dim, created_at) VALUES (?, ?, ?, ?, ?)",
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
        cur = conn.cursor()
        for idx, text in enumerate(texts):
            key = _make_key(text, model)
            cur.execute("SELECT vector, dim FROM embedding_cache WHERE key = ?", (key,))
            row = cur.fetchone()
            if row:
                blob, dim = row[0], row[1]
                cached[idx] = list(struct.unpack(f"{dim}f", blob))
            else:
                missing_indices.append(idx)
    except Exception as exc:
        logger.debug("Batch disk cache error", error=str(exc))
        missing_indices = list(range(len(texts)))
    finally:
        if conn:
            conn.close()

    return cached, missing_indices
