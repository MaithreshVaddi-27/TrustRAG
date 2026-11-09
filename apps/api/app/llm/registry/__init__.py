"""
TRUSTRAG — Model Registry factory sub-modules.

Each factory has a single responsibility:

- ``factories/onnx_paths.py`` — ONNX weight path resolution + status reporting
- ``factories/llm.py`` — LLM + verification model factory (_create_llm, get_llm,
  get_verification_model)
- ``factories/embedding.py`` — ONNX BGE embedding model factory (get_embedding_model)
- ``factories/reranker.py`` — reranker factory (get_reranker)
- ``factories/status.py`` — registry_status summary

``get_llm``, ``get_verification_model``, ``get_embedding_model``,
``get_reranker``, ``registry_status``, ``clear_onnx_caches``, and
``onnx_model_status`` are re-exported from this package.
"""

from __future__ import annotations

from app.llm.registry.factories.embedding import get_embedding_model
from app.llm.registry.factories.llm import get_llm, get_verification_model
from app.llm.registry.factories.onnx_paths import (
    clear_onnx_caches,
    onnx_model_status,
)
from app.llm.registry.factories.reranker import get_reranker
from app.llm.registry.factories.status import registry_status

__all__ = [
    "clear_onnx_caches",
    "get_embedding_model",
    "get_llm",
    "get_reranker",
    "get_verification_model",
    "onnx_model_status",
    "registry_status",
]
