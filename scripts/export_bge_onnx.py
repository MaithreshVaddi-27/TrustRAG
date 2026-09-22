#!/usr/bin/env python3
"""
DEPRECATED — thin shim over scripts/ensure_onnx_models.py.

The original torch-based exporter (~150 lines, writing to
apps/api/data/models/bge-small-en-v1.5.onnx with a sidecar .onnx.data file)
duplicated the optimum-based exporter in ensure_onnx_models.py and wrote to a
*different* directory than the one the backend reads
(apps/api/.model_cache/ — see app/core/model_registry.py).

Kept so existing docs/commands don't break; new code should call:
    python scripts/bootstrap.py
    python scripts/ensure_onnx_models.py

Usage (unchanged):
    python scripts/export_bge_onnx.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ensure_onnx_models import (  # noqa: E402, I001 — sys.path anchored above
    _API_ROOT as _ENSURE_API_ROOT,
    _cache_dir,
    _export_embedding_onnx,
    _model_paths,
    _verify_l2_norm,
    get_model_config,
)


def export_bge_to_onnx() -> None:
    """Export the embedding model to the canonical .model_cache location."""
    print("[export_bge_onnx] DEPRECATED: use 'python scripts/bootstrap.py' instead.")
    cfg = get_model_config()
    cache = _cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    emb_path, _ = _model_paths(cache, cfg)
    assert _ENSURE_API_ROOT == _API_ROOT  # both scripts share one repo-root anchor
    print(f"[export_bge_onnx] Exporting {cfg.embedding_model} -> {emb_path}")
    if not _export_embedding_onnx(cfg, emb_path):
        raise SystemExit(1)
    _verify_l2_norm(emb_path, cfg.embedding_dimensionality)


if __name__ == "__main__":
    export_bge_to_onnx()
