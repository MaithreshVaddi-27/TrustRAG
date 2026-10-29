"""
TRUSTRAG — Reranking engine.

Uses CrossEncoder from sentence-transformers to re-evaluate the relevance
of candidates before slicing generation context.

Implements early termination strategies:
- Approximate reranking with early exit for high-confidence results
- Batch processing with progressive scoring
- Adaptive top-k based on score distribution
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config.model_config import get_model_config
from app.core.observability.logging import get_logger
from app.llm.model_registry import get_reranker

logger = get_logger(__name__)

# Early termination configuration (fallback defaults; actual values from models.yaml via config)
EARLY_TERMINATION_MIN_BATCH = 16  # Minimum candidates before early termination check


def _is_high_confidence(top_chunk: dict[str, Any]) -> bool:
    """Single confidence signal for adaptive Top-K, in RRF units first.

    Fused rows carry `rrf_score` (with rrf_k=60 the max for a result ranked #1
    in both legs is 2/61 ≈ 0.033, so >= 0.02 means near-top in both legs).
    Dense cosine (>= 0.78) and cross-encoder logit (>= 0.80) thresholds are
    legacy fallbacks for rows that never went through RRF fusion.
    """
    rrf = top_chunk.get("rrf_score")
    if isinstance(rrf, (int, float)):
        return rrf >= 0.02
    if "rerank_score" in top_chunk:
        return float(top_chunk.get("rerank_score", 0.0)) >= 0.80
    return float(top_chunk.get("dense_score", 0.0)) >= 0.78


def _adaptive_top_k_slice(chunks: list[dict[str, Any]], max_context: int) -> list[dict[str, Any]]:
    """Adaptive Top-K: confident top chunks bound the window to 4.

    Single home for the slice so the threshold can't drift between call sites.
    """
    if len(chunks) > 3 and _is_high_confidence(chunks[0]):
        return chunks[: min(max_context, 4)]
    return chunks[:max_context]


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
        return _adaptive_top_k_slice(chunks, max_context)

    # Bound scoring depth (models.yaml: reranker.top_k). The floor at
    # fusion_top_k is load-bearing: capping below the fused width would
    # discard candidates before scoring, defeating reranking entirely.
    # Copy each dict: rerank_score assignment below must not leak into the
    # caller's chunks (a list slice alone shares the dicts).
    # L-6: scale depth by tier — lean keeps 5, scoring 20 is 4x waste.
    depth_cap = min(cfg.reranker_top_k, max(cfg.fusion_top_k, max_context * 2))
    candidates = [dict(c) for c in chunks[:depth_cap]]

    try:
        model = get_reranker()
        if model is None:
            logger.warning("Reranker model factory returned None, skipping rerank")
            return _adaptive_top_k_slice(chunks, max_context)

        logger.info(
            "Running cross-encoder reranking", model=cfg.reranker_model, count=len(candidates)
        )

        # Build query-document input pairs
        pairs = [(query, c["text"]) for c in candidates]

        # Progressive batch scoring with early termination.
        # No result cache: every call scores fresh (stale scores after
        # re-ingest were worse than the re-scoring cost).
        all_scores: list[float] = [0.0] * len(pairs)
        # Tracks which candidates actually received a cross-encoder score.
        # Early termination can leave later candidates unscored; those must not
        # masquerade as scored (a fabricated 0.0 ranks above genuine negative
        # relevance and can evict real evidence from the generation/verification
        # context window — which then turns supported claims into NEUTRAL).
        scored_mask: list[bool] = [False] * len(pairs)

        if pairs:
            _batch = getattr(cfg, "reranker_batch_size_effective", None) or cfg.reranker_batch_size
            batch_size = min(_batch, len(pairs))
            # NOTE: no second `model is None` check here — None already
            # returned above, so it is unreachable.

            for i in range(0, len(pairs), batch_size):
                batch_pairs = pairs[i : i + batch_size]
                batch_scores = model.predict(batch_pairs)
                for j, score in enumerate(batch_scores):
                    idx = i + j
                    all_scores[idx] = float(score)
                    scored_mask[idx] = True

                # Early termination check after processing enough candidates
                processed = i + len(batch_scores)
                if processed >= EARLY_TERMINATION_MIN_BATCH:
                    scored_so_far = [all_scores[k] for k in range(processed) if scored_mask[k]]
                    if len(scored_so_far) >= 3:
                        top_score = max(scored_so_far)
                        sorted_scores = sorted(scored_so_far, reverse=True)
                        second_best = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
                        score_gap = top_score - second_best

                        # Early exit if top result is very confident and well separated.
                        # Remaining candidates stay unscored (no fabricated 0.0).
                        if (
                            top_score >= cfg.reranker_early_termination_confidence
                            and score_gap >= cfg.reranker_score_gap_threshold
                        ):
                            logger.info(
                                "Early termination: high confidence top result",
                                top_score=top_score,
                                score_gap=score_gap,
                                processed=processed,
                                total=len(pairs),
                                unscored=len(pairs) - processed,
                            )
                            break

        # Update scores inside chunks — only actually-scored candidates get a
        # rerank_score; unscored ones keep none (never a fake 0.0).
        for i, score in enumerate(all_scores):
            if scored_mask[i]:
                candidates[i]["rerank_score"] = float(score)

        # Rank scored candidates first (by score desc), then unscored. Unscored
        # candidates never outrank a genuinely-scored chunk, so early termination
        # cannot push real evidence out of the top slice.
        scored = [c for c, m in zip(candidates, scored_mask, strict=False) if m]
        unscored = [c for c, m in zip(candidates, scored_mask, strict=False) if not m]
        scored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        ranked = scored + unscored

        # Adaptive Top-K: If top scored chunks are confident, bound to top 4.
        # Unscored candidates rank after all scored ones, so a confident head
        # of real signal bounds the window instead of a fabricated 0.0.
        confident = len(scored) > 3 and _is_high_confidence(scored[0])
        effective_limit = min(max_context, 4) if confident else max_context
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
