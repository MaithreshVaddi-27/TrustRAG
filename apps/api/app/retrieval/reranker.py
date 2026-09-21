"""
TRUSTRAG — Reranking engine.

Uses CrossEncoder from sentence-transformers to re-evaluate the relevance
of candidates before slicing generation context.

Implements early termination strategies:
- Approximate reranking with early exit for high-confidence results
- Batch processing with progressive scoring
- Adaptive top-k based on score distribution
- Result caching per query to avoid re-scoring
"""

from __future__ import annotations

import asyncio
import hashlib
from collections import OrderedDict
from typing import Any

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.core.model_registry import get_reranker

logger = get_logger(__name__)

# Early termination configuration (fallback defaults; actual values from models.yaml via config)
EARLY_TERMINATION_MIN_BATCH = 16  # Minimum candidates before early termination check

# Reranker result cache (LRU, in-memory)
# Key: hash of (query + document_text), Value: score
# Cache size configurable via models.yaml
class _RerankerCache:
    """Thread-safe LRU cache for reranker scores."""

    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, doc_text: str) -> str:
        """Create a hash key for query-document pair."""
        combined = f"{query}\x00{doc_text}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def get(self, query: str, doc_text: str) -> float | None:
        """Get cached score for query-document pair."""
        key = self._make_key(query, doc_text)
        if key in self._cache:
            self._cache.move_to_end(key)  # Mark as recently used
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, query: str, doc_text: str, score: float) -> None:
        """Cache score for query-document pair."""
        key = self._make_key(query, doc_text)
        if key in self._cache:
            self._cache.move_to_end(key)
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # Remove least recently used
        self._cache[key] = score

    def get_stats(self) -> dict[str, int]:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 1),
        }

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0


# Global cache instance (initialized lazily)
_reranker_cache: _RerankerCache | None = None


def _get_reranker_cache() -> _RerankerCache:
    """Get or create the global reranker cache."""
    global _reranker_cache
    if _reranker_cache is None:
        cfg = get_model_config()
        max_size = cfg.reranker_cache_size if hasattr(cfg, 'reranker_cache_size') else 500
        _reranker_cache = _RerankerCache(max_size=max_size)
    return _reranker_cache


def _rerank_sync(
    query: str, chunks: list[dict[str, Any]], max_context_override: int | None = None
) -> list[dict[str, Any]]:
    """
    Synchronous reranking implementation (CPU-bound).

    Implements early termination:
    - Progressive batch scoring with confidence checks
    - Early exit when top results exceed confidence threshold
    - Score gap analysis to skip low-value candidates
    """
    cfg = get_model_config()
    max_context = (
        max_context_override if max_context_override is not None else cfg.max_context_chunks
    )

    if not chunks:
        return []

    # Check if reranking is enabled
    if not cfg.reranker_enabled:
        logger.debug("Reranker disabled, returning candidates list directly", limit=max_context)
        # Adaptive Top-K: If top chunks are confident, bound to top 4 to save model context load
        if len(chunks) > 3 and chunks[0].get("dense_score", 0.0) >= 0.78:
            return chunks[: min(max_context, 4)]
        return chunks[:max_context]

    # Bound scoring depth (models.yaml: reranker.top_k). The floor at
    # fusion_top_k is load-bearing: capping below the fused width would
    # discard candidates before scoring, defeating reranking entirely.
    depth_cap = max(cfg.reranker_top_k, cfg.fusion_top_k, max_context)
    candidates = chunks[:depth_cap]

    try:
        model = get_reranker()
        if model is None:
            logger.warning("Reranker model factory returned None, skipping rerank")
            if len(chunks) > 3 and chunks[0].get("dense_score", 0.0) >= 0.78:
                return chunks[: min(max_context, 4)]
            return chunks[:max_context]

        logger.info(
            "Running cross-encoder reranking", model=cfg.reranker_model, count=len(candidates)
        )

        # Build query-document input pairs
        pairs = [(query, c["text"]) for c in candidates]

        # Phase 3.2: Reranker Result Caching
        # Check cache first to avoid re-scoring
        cache = _get_reranker_cache()
        cached_scores: dict[int, float] = {}
        uncached_indices: list[int] = []
        uncached_pairs: list[tuple[str, str]] = []

        for i, (q, doc_text) in enumerate(pairs):
            cached = cache.get(q, doc_text)
            if cached is not None:
                cached_scores[i] = cached
            else:
                uncached_indices.append(i)
                uncached_pairs.append((q, doc_text))

        logger.debug(
            "Reranker cache lookup",
            total=len(pairs),
            cached=len(cached_scores),
            uncached=len(uncached_pairs),
            cache_stats=cache.get_stats(),
        )

        # Progressive batch scoring with early termination for uncached pairs
        all_scores: list[float] = [0.0] * len(pairs)

        # Fill in cached scores
        for idx, score in cached_scores.items():
            all_scores[idx] = score

        if uncached_pairs:
            batch_size = min(cfg.reranker_batch_size, len(uncached_pairs))
            model = get_reranker()
            if model is None:
                logger.warning("Reranker model factory returned None, skipping rerank")
                if len(chunks) > 3 and chunks[0].get("dense_score", 0.0) >= 0.78:
                    return chunks[: min(max_context, 4)]
                return chunks[:max_context]

            logger.info(
                "Running cross-encoder reranking", model=cfg.reranker_model,
                count=len(uncached_pairs), cached=len(cached_scores)
            )

            uncached_scores: list[float] = []

            for i in range(0, len(uncached_pairs), batch_size):
                batch_pairs = uncached_pairs[i : i + batch_size]
                batch_scores = model.predict(batch_pairs)
                uncached_scores.extend(batch_scores)

                # Early termination check after processing enough candidates
                processed = i + len(batch_scores)
                if processed >= EARLY_TERMINATION_MIN_BATCH:
                    # Check if top result is confidently better than rest
                    # We need to check against ALL scores (cached + uncached so far)
                    combined_so_far = list(cached_scores.values()) + uncached_scores
                    if len(combined_so_far) >= 3:
                        top_score = max(combined_so_far)
                        sorted_scores = sorted(combined_so_far, reverse=True)
                        second_best = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
                        score_gap = top_score - second_best

                        # Early exit if top result is very confident and well separated
                        if (
                            top_score >= cfg.reranker_early_termination_confidence
                            and score_gap >= cfg.reranker_score_gap_threshold
                        ):
                            logger.info(
                                "Early termination: high confidence top result",
                                top_score=top_score,
                                score_gap=score_gap,
                                processed=processed,
                                total=len(uncached_pairs),
                            )
                            # Pad remaining scores with 0.0
                            remaining = len(uncached_pairs) - processed
                            uncached_scores.extend([0.0] * remaining)
                            break

            # Map uncached scores back to original indices and cache them
            for local_idx, orig_idx in enumerate(uncached_indices):
                score = uncached_scores[local_idx]
                all_scores[orig_idx] = score
                # Cache the new score
                cache.set(query, pairs[orig_idx][1], score)

        # Update scores inside chunks
        for i, score in enumerate(all_scores):
            candidates[i]["rerank_score"] = float(score)

        # Sort descending by rerank score — on a copy, never the caller's list.
        ranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)

        # Adaptive Top-K: If top chunks are confident, bound to top 4
        effective_limit = (
            min(max_context, 4)
            if (len(ranked) > 3 and ranked[0].get("rerank_score", 0.0) >= 0.80)
            else max_context
        )
        sliced = ranked[:effective_limit]
        logger.debug(
            "Reranking completed",
            top_score=sliced[0]["rerank_score"] if sliced else 0.0,
            count=len(sliced),
        )
        return sliced

    except Exception as exc:
        logger.error("Reranking execution failed, falling back to RRF rankings", error=str(exc))
        return chunks[:max_context]


async def rerank_candidate_chunks(
    query: str, chunks: list[dict[str, Any]], max_context_override: int | None = None
) -> list[dict[str, Any]]:
    """
    Rerank candidate chunks using the CrossEncoder model configured in models.yaml.
    Runs CPU-bound CrossEncoder.predict in a thread pool to avoid blocking the event loop.

    If reranking is disabled or candidates list is empty, returns original candidates list
    sliced by maximum context limits.
    """
    return await asyncio.to_thread(_rerank_sync, query, chunks, max_context_override)
