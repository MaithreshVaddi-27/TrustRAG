"""
TRUSTRAG — Embedding Re-export (Backward Compatibility).

Thin re-export pointing to rag.embedding for backward compatibility.
"""

from __future__ import annotations

from app.rag.embedding.cache import ONNXBGEEmbeddingsWrapper
from app.rag.embedding.engine import (
    EMBEDDING_MODE_DOCUMENT,
    EMBEDDING_MODE_QUERY,
    ONNXBGEEmbeddings,
)

__all__ = [
    "EMBEDDING_MODE_DOCUMENT",
    "EMBEDDING_MODE_QUERY",
    "ONNXBGEEmbeddings",
    "ONNXBGEEmbeddingsWrapper",
]
