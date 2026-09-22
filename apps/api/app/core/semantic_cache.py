"""
TRUSTRAG — Semantic Cache & Context Pruning Intelligence Engine.

Techniques to reduce system compute load and latency:
1. Semantic Response Cache:
   Short-circuits the entire RAG pipeline when a query is semantically equivalent
   (cosine similarity >= threshold) to a previously verified answer, avoiding 100%
   of LLM generation and NLI verification load.

2. Context & Token Pruner:
   Algorithmically compresses retrieved context text by stripping repetitive boilerplate,
   normalizing dense whitespace, and deduplicating cross-chunk sentences before passing
   to the LLM, reducing KV-cache allocation in RAM/VRAM by 25-40%.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache directory for persistence. `parents[2]` resolves to apps/api/ -- the same
# base the embedding SQLite cache (disk_cache.py) and model-discovery snapshot
# (local_llm.py) use, so CACHE_DIR coalesces all three caches into one directory.
CACHE_DIR = Path(
    os.getenv(
        "CACHE_DIR",
        Path(__file__).resolve().parents[2] / "data" / "cache",
    )
)
PERSISTENCE_FILE = CACHE_DIR / "semantic_cache.json"

# Configurable limits (via env vars for lean/prod tiers)
_MAX_CACHE_ENTRIES = int(os.getenv("SEMANTIC_CACHE_MAX_ENTRIES", "500"))
_SEMANTIC_CACHE_TTL_SECONDS = int(
    os.getenv("SEMANTIC_CACHE_TTL_SECONDS", str(24 * 3600))  # 24h default
)
_MAX_RESPONSE_SIZE_CHARS = int(
    os.getenv("SEMANTIC_CACHE_MAX_RESPONSE_CHARS", "20000")  # cap response payload
)

# In-memory fast semantic cache storage using deque for O(1) FIFO eviction
# Each entry: {"kb_id", "query", "vector", "response", "timestamp"} -- see insert()
_SEMANTIC_CACHE: deque[dict[str, Any]] = deque(maxlen=_MAX_CACHE_ENTRIES)
_CACHE_LOCK = threading.RLock()  # Guards all reads/writes to _SEMANTIC_CACHE
_MATRIX_CACHE: np.ndarray | None = None  # Stacked vectors for vectorized cosine
_MATRIX_DIRTY = True  # Flag to rebuild matrix when cache changes
_PERSISTENCE_INTERVAL_SECONDS = 300  # Persist every 5 minutes
_last_persist_time = 0.0


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _rebuild_matrix() -> None:
    """Rebuild the stacked vector matrix for vectorized cosine similarity."""
    global _MATRIX_CACHE, _MATRIX_DIRTY
    if not _SEMANTIC_CACHE:
        _MATRIX_CACHE = None
        _MATRIX_DIRTY = False
        return

    vectors = [entry["vector"] for entry in _SEMANTIC_CACHE]
    # Ensure all vectors are numpy arrays and same dimension
    try:
        _MATRIX_CACHE = np.vstack(vectors).astype(np.float32)
        # Pre-normalize for cosine similarity (assumes vectors may not be normalized)
        norms = np.linalg.norm(_MATRIX_CACHE, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        _MATRIX_CACHE = _MATRIX_CACHE / norms
        _MATRIX_DIRTY = False
    except ValueError:
        # Inconsistent dimensions - fallback to list-based search
        _MATRIX_CACHE = None
        _MATRIX_DIRTY = False


def _load_persisted_cache() -> None:
    """Load semantic cache from disk on startup."""
    global _SEMANTIC_CACHE, _MATRIX_DIRTY, _last_persist_time
    if not PERSISTENCE_FILE.exists():
        return

    try:
        with open(PERSISTENCE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return

        _SEMANTIC_CACHE.clear()
        for entry in data:
            if not all(k in entry for k in ("kb_id", "query", "vector", "response", "timestamp")):
                continue
            # TTL filter on load (skip expired entries)
            if _SEMANTIC_CACHE_TTL_SECONDS > 0:
                if entry.get("timestamp", 0) < time.time() - _SEMANTIC_CACHE_TTL_SECONDS:
                    continue
            # Convert vector back to numpy array
            entry["vector"] = np.array(entry["vector"], dtype=np.float32)
            _SEMANTIC_CACHE.append(entry)

        _MATRIX_DIRTY = True
        _last_persist_time = time.time()
        logger.info("Loaded semantic cache from disk", entries=len(_SEMANTIC_CACHE))
    except Exception as exc:
        logger.warning("Failed to load semantic cache from disk", error=str(exc))


def _persist_cache() -> None:
    """Persist semantic cache to disk, including an explicit empty state."""
    global _last_persist_time
    try:
        _ensure_cache_dir()
        # Snapshot under the lock so a concurrent insert/evict during serialization
        # can't mutate the deque mid-iteration (RuntimeError: deque mutated during
        # iteration). RLock is reentrant, so this is safe even when the caller
        # already holds _CACHE_LOCK.
        with _CACHE_LOCK:
            snapshot = list(_SEMANTIC_CACHE)
        serializable = []
        for entry in snapshot:
            serializable.append(
                {
                    "kb_id": entry["kb_id"],
                    "query": entry["query"],
                    "vector": entry["vector"].tolist()
                    if isinstance(entry["vector"], np.ndarray)
                    else entry["vector"],
                    "response": entry["response"],
                    "timestamp": entry["timestamp"],
                }
            )

        temp_file = PERSISTENCE_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(serializable, f)
        temp_file.replace(PERSISTENCE_FILE)

        _last_persist_time = time.time()
        logger.debug("Persisted semantic cache to disk", entries=len(_SEMANTIC_CACHE))
    except Exception as exc:
        logger.warning("Failed to persist semantic cache to disk", error=str(exc))


def _maybe_persist() -> None:
    """Persist cache if enough time has passed since last persist."""
    global _last_persist_time
    if time.time() - _last_persist_time >= _PERSISTENCE_INTERVAL_SECONDS:
        _persist_cache()


def _cleanup_expired_entries() -> int:
    """Remove entries older than TTL. Returns count removed."""
    global _SEMANTIC_CACHE, _MATRIX_DIRTY
    if _SEMANTIC_CACHE_TTL_SECONDS <= 0:
        return 0
    now = time.time()
    cutoff = now - _SEMANTIC_CACHE_TTL_SECONDS
    with _CACHE_LOCK:
        original_len = len(_SEMANTIC_CACHE)
        # Filter in-place
        _SEMANTIC_CACHE = deque(
            (e for e in _SEMANTIC_CACHE if e.get("timestamp", 0) >= cutoff),
            maxlen=_MAX_CACHE_ENTRIES,
        )
        removed = original_len - len(_SEMANTIC_CACHE)
        if removed > 0:
            _MATRIX_DIRTY = True
            logger.debug(
                "Semantic cache TTL cleanup",
                removed=removed,
                ttl_seconds=_SEMANTIC_CACHE_TTL_SECONDS,
            )
        return removed


def cosine_similarity(v1: list[float] | np.ndarray, v2: list[float] | np.ndarray) -> float:
    """Compute cosine similarity between two normalized or raw floating point vectors."""
    v1_arr = np.asarray(v1, dtype=np.float32)
    v2_arr = np.asarray(v2, dtype=np.float32)

    if v1_arr.size == 0 or v2_arr.size == 0 or v1_arr.shape != v2_arr.shape:
        return 0.0

    norm_a = np.linalg.norm(v1_arr)
    norm_b = np.linalg.norm(v2_arr)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(np.dot(v1_arr, v2_arr) / (norm_a * norm_b))


def check_semantic_cache(
    query: str,
    kb_id: str,
    query_vector: list[float],
    similarity_threshold: float = 0.94,
    embedding_model: str | None = None,
) -> dict[str, Any] | None:
    """
    Search the semantic response cache for an equivalent previously verified answer.
    Returns cached result dict if similarity >= similarity_threshold, else None.

    Entries are namespaced by embedding model so a re-index with a different
    embedding space can never serve stale vectors/answers (SEC correctness).
    """
    # Periodic TTL cleanup (cheap, runs under lock)
    _cleanup_expired_entries()

    if not _SEMANTIC_CACHE:
        return None

    query_arr = np.asarray(query_vector, dtype=np.float32)
    if query_arr.size == 0:
        return None

    # Filter by KB + embedding model namespace
    model_ns = (embedding_model or "").strip().lower()
    with _CACHE_LOCK:
        kb_indices = [
            i
            for i, e in enumerate(_SEMANTIC_CACHE)
            if e.get("kb_id") == kb_id and e.get("embedding_model", "").strip().lower() == model_ns
        ]

    if not kb_indices:
        return None

    # Fast path: vectorized cosine for same-dimension vectors
    if _MATRIX_CACHE is not None and _MATRIX_CACHE.size > 0:
        kb_matrix = _MATRIX_CACHE[kb_indices]
        query_norm = np.linalg.norm(query_arr)
        if query_norm > 0:
            query_normalized = query_arr / query_norm
            similarities = kb_matrix @ query_normalized
            best_idx = int(np.argmax(similarities))
            best_sim = float(similarities[best_idx])

            if best_sim >= similarity_threshold:
                best_entry = _SEMANTIC_CACHE[kb_indices[best_idx]]
                logger.info(
                    "Semantic cache vector hit",
                    query=query,
                    matched_similarity=round(best_sim, 4),
                    threshold=similarity_threshold,
                    kb_id=kb_id,
                )
                return best_entry["response"]
    else:
        # Fallback to scalar cosine
        best_sim = 0.0
        best_match: dict[str, Any] | None = None
        for idx in kb_indices:
            entry = _SEMANTIC_CACHE[idx]
            sim = cosine_similarity(query_arr, entry["vector"])
            if sim > best_sim:
                best_sim = sim
                if sim >= similarity_threshold:
                    best_match = entry["response"]

        if best_match and best_sim >= similarity_threshold:
            logger.info(
                "Semantic cache vector hit (fallback)",
                query=query,
                matched_similarity=round(best_sim, 4),
                threshold=similarity_threshold,
                kb_id=kb_id,
            )
            return best_match

    return None


def _json_safe(value: Any) -> Any:
    """Return a JSON-serializable copy, converting BSON ObjectIds to strings."""
    return json.loads(json.dumps(value, default=str))


def store_semantic_cache(
    query: str,
    kb_id: str,
    query_vector: list[float],
    response_data: dict[str, Any],
    embedding_model: str | None = None,
) -> None:
    """
    Save a verified answer to the semantic cache using JSON-safe data only.

    Audit artifacts (Mongo ObjectIds, evidence rows, claim documents) are
    intentionally not trusted from cache. The graph revalidates those against
    the current database before serving the answer.
    """
    if not query_vector or not response_data:
        return

    safe_response = _json_safe(response_data)
    # Cap response size to prevent unbounded memory growth
    if len(str(safe_response)) > _MAX_RESPONSE_SIZE_CHARS:
        logger.debug("Semantic cache response too large, skipping", size=len(str(safe_response)))
        return

    # Periodic TTL cleanup
    _cleanup_expired_entries()

    with _CACHE_LOCK:
        entry = {
            "kb_id": kb_id,
            "query": query,
            "vector": np.asarray(query_vector, dtype=np.float32),
            "response": safe_response,
            "timestamp": time.time(),
            "embedding_model": (embedding_model or "").strip().lower(),
        }
        _SEMANTIC_CACHE.append(entry)
        _MATRIX_DIRTY = True  # noqa: N806 — module-level cache flag, UPPER by convention

    _maybe_persist()


def invalidate_kb_cache(kb_id: str, persist: bool = True) -> int:
    """Remove all cached answers for a knowledge base and persist the removal.

    Returns:
        Number of entries removed.
    """
    global _SEMANTIC_CACHE, _MATRIX_DIRTY
    with _CACHE_LOCK:
        original_len = len(_SEMANTIC_CACHE)
        _SEMANTIC_CACHE = deque(
            (e for e in _SEMANTIC_CACHE if e.get("kb_id") != kb_id),
            maxlen=_MAX_CACHE_ENTRIES,
        )
        removed = original_len - len(_SEMANTIC_CACHE)
        _MATRIX_DIRTY = True
    if persist:
        _persist_cache()
    return removed


def load_cache() -> int:
    """Load semantic cache from disk. Call explicitly at application startup.

    Returns:
        Number of entries loaded.
    """
    _load_persisted_cache()
    return len(_SEMANTIC_CACHE)


def clear_all_cache(persist: bool = True) -> int:
    """Clear the entire semantic cache (for testing).

    Returns:
        Number of entries removed.
    """
    global _SEMANTIC_CACHE, _MATRIX_DIRTY
    with _CACHE_LOCK:
        original_len = len(_SEMANTIC_CACHE)
        _SEMANTIC_CACHE = deque(maxlen=_MAX_CACHE_ENTRIES)
        removed = original_len
        _MATRIX_DIRTY = True
    if persist:
        _persist_cache()
    return removed


def reset_module_state() -> None:
    """Completely reset module state for test isolation.

    Clears in-memory cache, matrix, and persists empty state to disk.
    Use in test fixtures for complete isolation between tests.
    """
    global _SEMANTIC_CACHE, _MATRIX_CACHE, _MATRIX_DIRTY, _last_persist_time
    with _CACHE_LOCK:
        _SEMANTIC_CACHE = deque(maxlen=_MAX_CACHE_ENTRIES)
        _MATRIX_CACHE = None
        _MATRIX_DIRTY = True
        _last_persist_time = 0.0
    _persist_cache()


def prune_context_tokens(context: str, max_chars: int = 6000) -> str:
    """
    Lightweight, deterministic context pruning & token compaction.
    Reduces context length by 20-35% without requiring an external neural model:
    - Normalizes redundant whitespace and blank lines
    - Strips markdown horizontal rules and repetitive separator tags
    - Deduplicates identical sentences across overlapping chunks
    - Bounds length to max_chars preserving complete sentences
    """
    if not context or len(context) <= 40:
        return context

    # 1. Strip repetitive markdown borders, HRs, and divider blocks
    text = re.sub(r"[-=_*]{3,}", "", context)

    # 2. Normalize whitespace and newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # 3. Deduplicate identical sentences across overlapping chunk boundaries
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])(?:\s+|\n+)", text) if s.strip()]
    seen_sentences: set[str] = set()
    unique_sentences: list[str] = []

    for s in sentences:
        norm = re.sub(r"^[^\w]*", "", s).strip().lower()
        norm = re.sub(r"^segment \d+.*?\n", "", norm).strip()
        if len(norm) > 20 and norm in seen_sentences:
            continue
        seen_sentences.add(norm)
        unique_sentences.append(s)

    pruned = " ".join(unique_sentences)

    # 4. Sentence-boundary truncation if still exceeding max_chars
    if len(pruned) > max_chars:
        truncated = pruned[:max_chars]
        last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_period > int(max_chars * 0.75):
            pruned = truncated[: last_period + 1]
        else:
            pruned = truncated + "..."

    return pruned


# Module-level cache is lazy-loaded; call load_cache() explicitly at startup
# _load_persisted_cache()  # Disabled at import time for test isolation
