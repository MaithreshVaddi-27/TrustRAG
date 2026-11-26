"""
TRUSTRAG — Retrieval Capability.

Hybrid dense + sparse retrieval with RRF fusion, reranking, and temporal filtering.
"""

from app.rag.retrieval.reranker import (
    rerank_candidate_chunks,
)
from app.rag.retrieval.retriever import (
    apply_temporal_filtering,
    dense_search,
    reciprocal_rank_fusion,
    retrieve_hybrid_chunks,
    sparse_search,
)

__all__ = [
    "apply_temporal_filtering",
    "dense_search",
    "reciprocal_rank_fusion",
    "rerank_candidate_chunks",
    "retrieve_hybrid_chunks",
    "sparse_search",
]
