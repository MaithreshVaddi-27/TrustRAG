"""
TRUSTRAG — RAG Pipeline Capability.

Main entry point for RAG functionality organized into sub-capabilities:
- embedding: ONNX BGE embeddings with caching
- retrieval: Hybrid dense/sparse search with RRF and reranking
- ingestion: Document parsing, chunking, OCR, indexing
- verification: Claim decomposition, NLI, verdicts
- generation: Grounded answer generation
- agent: LangGraph agent orchestration
"""

from __future__ import annotations

__all__ = [
    "embedding",
    "retrieval",
    "ingestion",
    "verification",
    "generation",
    "agent",
]