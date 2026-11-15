"""
TRUSTRAG — ONNX Runtime BGE embedding wrapper (backward-compatible shim).

This is the single stable import path for the embedding engine and its cache
wrapper. The implementation lives in ``app.rag.embedding``:

- ``app.rag.embedding.engine`` -> ``ONNXBGEEmbeddings``,
  ``EMBEDDING_MODE_QUERY``, ``EMBEDDING_MODE_DOCUMENT``
- ``app.rag.embedding.cache``  -> ``ONNXBGEEmbeddingsWrapper``

It also re-exports ``_ORT_AVAILABLE`` and ``ort``: the engine consults this
module at call time (``app.rag.embedding.engine._ort_shim``), so patching
ONNX Runtime availability or the session factory *here* affects the single
canonical implementation. That is the one supported patch point.

Existing imports (``from app.llm.onnx_embeddings import ...``) continue to
work.
"""

from __future__ import annotations

from app.rag.embedding import (
    EMBEDDING_MODE_DOCUMENT,
    EMBEDDING_MODE_QUERY,
    ONNXBGEEmbeddings,
    ONNXBGEEmbeddingsWrapper,
)
from app.rag.embedding.engine import (
    _ORT_AVAILABLE,
    ort,
)

__all__ = [
    "EMBEDDING_MODE_DOCUMENT",
    "EMBEDDING_MODE_QUERY",
    "_ORT_AVAILABLE",
    "ONNXBGEEmbeddings",
    "ONNXBGEEmbeddingsWrapper",
    "ort",
]
