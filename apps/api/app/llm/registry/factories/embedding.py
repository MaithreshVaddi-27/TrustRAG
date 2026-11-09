"""
TRUSTRAG — Model Registry: ONNX BGE embedding model factory.

Single embedding engine: ONNX Runtime BGE (torch-free).
``embedding.model`` in models.yaml is the sole source of truth — no provider
choice, no per-request override.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.config import ModelConfig, get_model_config
from app.llm.onnx_embeddings import ONNXBGEEmbeddings, ONNXBGEEmbeddingsWrapper
from app.llm.registry.factories.onnx_paths import (
    _embedding_cache,
    _embedding_lock,
    _resolve_embedding_onnx_path,
)
from app.observability.logging import get_logger
from app.security.exceptions import ConfigurationError

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

logger = get_logger(__name__)

__all__ = ["get_embedding_model"]


def get_embedding_model() -> Embeddings:
    """
    Return the single ONNX embedding model wrapped with persistent disk cache.

    The model id comes from models.yaml ``embedding.model`` (default
    ``BAAI/bge-small-en-v1.5``). There is no provider choice and no
    per-request override — the engine is always ONNX Runtime BGE.

    Cloud embeddings (google_genai) were removed: embeddings are a
    local-only concern now, so ingestion and retrieval work fully offline.
    """
    cfg: ModelConfig = get_model_config()

    active_model = cfg.embedding_model

    # Use the API directory as base for relative cache_dir to ensure consistency
    # (Path.resolve() alone is CWD-dependent: repo-root vs apps/api runs
    # would split the cache in two. Always anchor to api_base.)
    api_base = Path(__file__).parent.parent.parent.parent.parent
    cache_dir = (api_base / cfg.embedding_cache_dir).resolve()
    onnx_model_path = _resolve_embedding_onnx_path(cache_dir)
    if onnx_model_path is None:
        raise ConfigurationError(
            f"ONNX embedding model not found in {cache_dir} "
            f"(looked for '{active_model.split('/')[-1]}.onnx' and legacy "
            "underscored variant). "
            "Run 'python scripts/bootstrap.py' (or "
            "'python scripts/ensure_onnx_models.py') to download/export it.",
        )

    logger.info(
        "Initializing ONNX Runtime BGE embedding model",
        model=active_model,
        onnx_path=str(onnx_model_path),
    )


    cache_key = (active_model, str(onnx_model_path), int(cfg.embedding_max_seq_length))
    with _embedding_lock:
        cached = _embedding_cache.get(cache_key)
        if isinstance(cached, Embeddings):
            return cached

    try:
        base_emb = ONNXBGEEmbeddings(
            model_path=str(onnx_model_path),
            tokenizer_name=active_model,
            max_seq_length=cfg.embedding_max_seq_length,
        )
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to load ONNX embedding model from {onnx_model_path}. "
            "Re-run 'python scripts/bootstrap.py --force' to re-export it.",
            detail=str(exc)[:300],
        ) from exc
    wrapped = ONNXBGEEmbeddingsWrapper(base_emb, model_name=f"onnx::{active_model}")
    with _embedding_lock:
        _embedding_cache[cache_key] = wrapped
    return wrapped
