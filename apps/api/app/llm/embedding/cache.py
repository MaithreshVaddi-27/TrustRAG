"""
TRUSTRAG — Embedding cache re-export (backward compatibility).

The implementation lives in ``app.rag.embedding.cache``. This module used to
hold a byte-identical copy that only differed in its import line, so the same
wrapper class existed twice. This shim keeps every historic import path
working while there is now exactly one implementation.
"""

from __future__ import annotations

from app.rag.embedding.cache import ONNXBGEEmbeddingsWrapper

__all__ = ["ONNXBGEEmbeddingsWrapper"]
