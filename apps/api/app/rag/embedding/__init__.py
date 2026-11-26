"""
TRUSTRAG — Embedding engine and cache wrapper (canonical).

This package owns the embedding implementation. The engine (``ONNXBGEEmbeddings``)
and the cache wrapper (``ONNXBGEEmbeddingsWrapper``) are defined here and
nowhere else; ``app.llm.onnx_embeddings`` re-exports them as the stable
historical import path.

ONNX Runtime is patched through ``app.llm.onnx_embeddings`` — the engine
consults that module at call time, so a patch applied there affects this
implementation. See ``app.rag.embedding.engine._ort_shim``.
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
