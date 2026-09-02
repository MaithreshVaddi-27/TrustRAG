"""
TRUSTRAG — Reranking engine.

Uses CrossEncoder from sentence-transformers to re-evaluate the relevance
of candidates before slicing generation context.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.core.model_registry import get_reranker

logger = get_logger(__name__)


def rerank_candidate_chunks(
    query: str, chunks: list[dict[str, Any]], max_context_override: int | None = None
) -> list[dict[str, Any]]:
    """
    Rerank candidate chunks using the CrossEncoder model configured in models.yaml.

    If reranking is disabled or candidates list is empty, returns original candidates list
    sliced by maximum context limits.
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
            return chunks[:min(max_context, 4)]
        return chunks[:max_context]

    try:
        model = get_reranker()
        if model is None:
            logger.warning("Reranker model factory returned None, skipping rerank")
            if len(chunks) > 3 and chunks[0].get("dense_score", 0.0) >= 0.78:
                return chunks[:min(max_context, 4)]
            return chunks[:max_context]

        logger.info("Running cross-encoder reranking", model=cfg.reranker_model, count=len(chunks))

        # Build query-document input pairs
        pairs = [(query, c["text"]) for c in chunks]

        # Predict scores
        scores = model.predict(pairs)

        # Update scores inside chunks
        for i, score in enumerate(scores):
            chunks[i]["rerank_score"] = float(score)

        # Sort descending by rerank score
        chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

        # Adaptive Top-K: If top chunks are confident, bound to top 4
        effective_limit = min(max_context, 4) if (len(chunks) > 3 and chunks[0].get("rerank_score", 0.0) >= 0.80) else max_context
        sliced = chunks[:effective_limit]
        logger.debug("Reranking completed", top_score=sliced[0]["rerank_score"] if sliced else 0.0, count=len(sliced))
        return sliced

    except Exception as exc:
        logger.error("Reranking execution failed, falling back to RRF rankings", error=str(exc))
        return chunks[:max_context]
