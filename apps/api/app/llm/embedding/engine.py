"""
TRUSTRAG — Embedding engine re-export (backward compatibility).

The implementation lives in ``app.rag.embedding.engine``. This module used to
hold a second, near-identical copy of the engine — which meant two distinct
``ONNXBGEEmbeddings`` classes existed in the codebase and only one of them was
ever used. This shim keeps every historic import path working while there is
now exactly one implementation.
"""

from __future__ import annotations

from app.rag.embedding.engine import (
    _ORT_AVAILABLE,
    EMBEDDING_MODE_DOCUMENT,
    EMBEDDING_MODE_QUERY,
    ONNXBGEEmbeddings,
    _get_ort,
    _is_ort_available,
    ort,
)

__all__ = [
    "EMBEDDING_MODE_DOCUMENT",
    "EMBEDDING_MODE_QUERY",
    "_ORT_AVAILABLE",
    "ONNXBGEEmbeddings",
    "_get_ort",
    "_is_ort_available",
    "ort",
]
