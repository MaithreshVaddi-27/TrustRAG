"""
TRUSTRAG — Model Registry: ONNX weight path resolution + status.

Resolves ONNX weight file paths for embedding and reranker models, and
reports their presence so startup can fail loudly on a missing bake.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.config import ModelConfig, get_model_config
from app.observability.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "clear_onnx_caches",
    "onnx_model_status",
    "_resolve_embedding_onnx_path",
    "_resolve_reranker_onnx_path",
]

# ─── ONNX singleton caches (P1-3) ────────────────────────────────────────────
# ORT InferenceSession + tokenizer construction (~130MB mmap + graph opt)
# must not run per query. Lock-guarded singletons keyed on resolved paths.
_embedding_lock = threading.Lock()
_embedding_cache: dict[tuple, Any] = {}
_reranker_lock = threading.Lock()
_reranker_cache: dict[tuple, Any] = {}


def clear_onnx_caches() -> None:
    """Clear cached ONNX singletons (tests only)."""
    with _embedding_lock:
        _embedding_cache.clear()
    with _reranker_lock:
        _reranker_cache.clear()


def _resolve_embedding_onnx_path(cache_dir: Path) -> Path | None:
    """Resolve the ONNX embedding weights for the configured model.

    Single-model install: the id comes from ``embedding.model`` in
    models.yaml (default ``BAAI/bge-small-en-v1.5``). Canonical file is
    ``<base>.onnx`` (e.g. ``bge-small-en-v1.5.onnx``); the legacy
    underscored variant (``bge-small-en-v1_5.onnx``) is accepted.
    Returns None when neither exists so callers fail with one message.
    """
    active_model = get_model_config().embedding_model
    base = active_model.split("/")[-1]
    for candidate in (cache_dir / f"{base}.onnx", cache_dir / f"{base.replace('.', '_')}.onnx"):
        if candidate.exists():
            return candidate
    return None


def _resolve_reranker_onnx_path(cache_dir: Path, reranker_model: str) -> Path:
    """Canonical reranker ONNX path (mirrors get_reranker auto-generation)."""
    base = reranker_model.split("/")[-1].replace(".", "_")
    return cache_dir / f"reranker-{base}_int8.onnx"


def onnx_model_status() -> dict[str, Any]:
    """Report presence of the ONNX weight files required by the configuration.

    Startup calls this so a missing bake fails loudly in logs (with the exact
    bootstrap command) instead of surfacing as per-query ConfigurationError
    or silent RRF-only reranking.
    """
    cfg: ModelConfig = get_model_config()
    api_base = Path(__file__).parent.parent.parent.parent.parent
    cache_dir = (api_base / cfg.embedding_cache_dir).resolve()
    emb = _resolve_embedding_onnx_path(cache_dir)
    rnk_path = (
        Path(cfg.reranker_onnx_model_path)
        if cfg.reranker_onnx_model_path
        else _resolve_reranker_onnx_path(cache_dir, cfg.reranker_model)
    )
    return {
        "embedding_provider": "onnx",
        "embedding_model": cfg.embedding_model,
        "embedding_onnx_present": emb is not None,
        "embedding_onnx_path": str(emb) if emb else str(cache_dir),
        "reranker_enabled": cfg.reranker_enabled,
        "reranker_use_onnx": cfg.reranker_use_onnx,
        "reranker_onnx_present": rnk_path.exists(),
        "reranker_onnx_path": str(rnk_path),
    }
