"""
TRUSTRAG — ONNX Runtime BGE embedding wrapper (backward-compatible shim).

The implementation has been split into the ``app.llm.embedding`` sub-package:

- ``app.llm.embedding.engine`` -> ``ONNXBGEEmbeddings``,
  ``EMBEDDING_MODE_QUERY``, ``EMBEDDING_MODE_DOCUMENT``
- ``app.llm.embedding.cache`` -> ``ONNXBGEEmbeddingsWrapper``

Existing imports (``from app.llm.onnx_embeddings import ...``) continue to work.
"""

from __future__ import annotations

from app.llm.embedding import (
    EMBEDDING_MODE_DOCUMENT,
    EMBEDDING_MODE_QUERY,
    ONNXBGEEmbeddings,
    ONNXBGEEmbeddingsWrapper,
)
from app.llm.embedding.engine import (
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
