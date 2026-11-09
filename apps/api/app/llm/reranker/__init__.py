"""
TRUSTRAG — Reranker Re-export (Backward Compatibility).

Thin re-export pointing to rag.retrieval for backward compatibility.
"""

from __future__ import annotations

from app.rag.retrieval.onnx_reranker import ONNXCrossEncoder

__all__ = [
    "ONNXCrossEncoder",
]
