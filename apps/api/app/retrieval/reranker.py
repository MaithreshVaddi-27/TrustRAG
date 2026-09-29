"""
TRUSTRAG — Reranking engine.

Uses CrossEncoder from sentence-transformers to re-evaluate candidate
relevance before slicing the generation context.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.core.model_registry import get_reranker

logger = get_logger(__name__)

def _rerank_sync(
    query: str,
    chunks: list[dict[str, Any]],
    max_context_override: int | None = None,
) -> list[dict[str, Any]]:
    """Rerank candidates with the configured CrossEncoder."""
    cfg = get_model_config()

    max_context = (
        max_context_override
        if max_context_override is not None
        else cfg.max_context_chunks
    )

    if not chunks:
        return []

    if not cfg.reranker_enabled:
        return chunks[:max_context]

    depth_cap = max(
        cfg.reranker_top_k,
        cfg.fusion_top_k,
        max_context,
    )
    candidates = [dict(chunk) for chunk in chunks[:depth_cap]]

    try:
        model = get_reranker()
        if model is None:
            raise RuntimeError("Reranker model is unavailable")

        logger.info(
            "Running cross-encoder reranking",
            model=cfg.reranker_model,
            count=len(candidates),
        )

        pairs = [(query, chunk["text"]) for chunk in candidates]
        scores = model.predict(pairs)

        for chunk, score in zip(candidates, scores):
            chunk["rerank_score"] = float(score)

        ranked = sorted(
            candidates,
            key=lambda chunk: chunk["rerank_score"],
            reverse=True,
        )

        return ranked[:max_context]

    except Exception as exc:
        logger.error(
            "Reranking execution failed",
            error=str(exc),
        )
        raise
    
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
