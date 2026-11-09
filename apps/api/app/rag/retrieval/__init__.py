"""
TRUSTRAG — Retrieval Capability.

Hybrid dense + sparse retrieval with RRF fusion, reranking, and temporal filtering.
"""

from app.rag.retrieval.retriever import (
    dense_search,
    sparse_search,
    reciprocal_rank_fusion,
    apply_temporal_filtering,
    retrieve_hybrid_chunks,
)
from app.rag.retrieval.reranker import (
    rerank_candidate_chunks,
)

__all__ = [
    "dense_search",
    "sparse_search",
    "reciprocal_rank_fusion",
    "apply_temporal_filtering",
    "retrieve_hybrid_chunks",
    "rerank_candidate_chunks",
]