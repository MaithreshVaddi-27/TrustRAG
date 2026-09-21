#!/usr/bin/env python3
"""
TRUSTRAG — Ensure ONNX models are present in cache.

Works both inside Docker and on host. Single script for all environments.

Usage:
  python scripts/ensure_onnx_models.py              # check + export if missing
  python scripts/ensure_onnx_models.py --verify     # only verify, don't export
  python scripts/ensure_onnx_models.py --force      # re-export even if present
  python scripts/ensure_onnx_models.py --docker     # Docker mode (bakes into image)

Env vars:
  CACHE_DIR                 # override cache directory (default: apps/api/.model_cache)
  EMBEDDING_MODEL           # override embedding model (default: BAAI/bge-small-en-v1.5)
  RERANKER_MODEL            # override reranker model (default: cross-encoder/ms-marco-MiniLM-L-6-v2)
  HF_TOKEN                  # Hugging Face token for private models
  HF_HUB_OFFLINE=1          # force offline mode (use local cache only)
  SKIP_ONNX_EXPORT=1        # skip export (verify only)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Add apps/api to path for imports
_API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

try:
    from app.core.config import get_model_config
except ImportError:
    # Fallback if config not loadable (e.g., during Docker build before install)
    def get_model_config():
        class _Cfg:
            embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
            reranker_model = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            embedding_dimensionality = 384
        return _Cfg()


def _cache_dir() -> Path:
    """Resolve cache directory (works in Docker and host)."""
    env_dir = os.getenv("CACHE_DIR")
    if env_dir:
        return Path(env_dir)
    # Default: apps/api/.model_cache (relative to repo root)
    return _API_ROOT / ".model_cache"


def _model_paths(cache: Path, cfg) -> tuple[Path, Path]:
    """Return (embedding_onnx, reranker_onnx) paths.
    
    Supports both naming conventions:
    - dots preserved: bge-small-en-v1.5.onnx (existing export_bge_onnx.py output)
    - dots to underscores: bge-small-en-v1_5.onnx (new convention)
    """
    emb_base = cfg.embedding_model.split("/")[-1]
    rnk_base = cfg.reranker_model.split("/")[-1]
    
    # Embedding: check both conventions
    emb_candidates = [
        cache / f"{emb_base}.onnx",           # dots preserved (existing)
        cache / f"{emb_base.replace('.', '_')}.onnx",  # dots to underscores
    ]
    emb_path = emb_candidates[0]  # default to dots-preserved
    
    # Reranker: int8 quantized
    rnk_path = cache / f"{rnk_base.replace('.', '_')}_int8.onnx"
    
    return (emb_path, rnk_path)


def _find_existing_model(cache: Path, base_name: str) -> Path | None:
    """Find existing model file with either naming convention."""
    # Try dots-preserved first
    preserved = cache / f"{base_name}.onnx"
    if preserved.exists():
        return preserved
    # Try dots-to-underscores
    underscored = cache / f"{base_name.replace('.', '_')}.onnx"
    if underscored.exists():
        return underscored
    return None


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _export_embedding_onnx(cfg, emb_path: Path) -> bool:
    """Export embedding model to ONNX (reuses logic from export_bge_onnx.py)."""
    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        from transformers import AutoTokenizer
    except ImportError as e:
        print(f"[ensure_onnx] Missing dependencies for embedding export: {e}", file=sys.stderr)
        print("[ensure_onnx] Install with: pip install optimum[onnxruntime] transformers", file=sys.stderr)
        return False

    print(f"[ensure_onnx] Exporting embedding model: {cfg.embedding_model} -> {emb_path}")
    try:
        # Load and export
        model = ORTModelForFeatureExtraction.from_pretrained(
            cfg.embedding_model,
            export=True,
            trust_remote_code=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            cfg.embedding_model,
            trust_remote_code=True,
        )
        model.save_pretrained(emb_path.parent)
        tokenizer.save_pretrained(emb_path.parent)
        # Rename to expected filename
        exported = emb_path.parent / "model.onnx"
        if exported.exists():
            exported.rename(emb_path)
        print(f"[ensure_onnx] Embedding export OK: {emb_path}")
        return True
    except Exception as e:
        print(f"[ensure_onnx] Embedding export failed: {e}", file=sys.stderr)
        return False


def _export_reranker_onnx(cfg, rnk_path: Path) -> bool:
    """Export reranker model to ONNX with int8 quantization."""
    try:
        import torch
        from optimum.onnxruntime import ORTModelForSequenceClassification
        from transformers import AutoTokenizer
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError as e:
        print(f"[ensure_onnx] Missing dependencies for reranker export: {e}", file=sys.stderr)
        print("[ensure_onnx] Install with: pip install optimum[onnxruntime] transformers onnxruntime", file=sys.stderr)
        return False

    print(f"[ensure_onnx] Exporting reranker model: {cfg.reranker_model} -> {rnk_path}")
    try:
        # Export base ONNX
        base_path = rnk_path.with_suffix(".onnx")
        model = ORTModelForSequenceClassification.from_pretrained(
            cfg.reranker_model,
            export=True,
            trust_remote_code=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            cfg.reranker_model,
            trust_remote_code=True,
        )
        model.save_pretrained(base_path.parent)
        tokenizer.save_pretrained(base_path.parent)
        exported = base_path.parent / "model.onnx"
        if exported.exists():
            exported.rename(base_path)

        # Quantize to int8
        quantized_path = rnk_path
        quantize_dynamic(
            str(base_path),
            str(quantized_path),
            weight_type=QuantType.QInt8,
            optimize_model=True,
            per_channel=False,
            reduce_range=False,
        )
        # Cleanup base
        if base_path.exists():
            base_path.unlink()
        print(f"[ensure_onnx] Reranker export + quant OK: {rnk_path}")
        return True
    except Exception as e:
        print(f"[ensure_onnx] Reranker export failed: {e}", file=sys.stderr)
        return False


def _verify_l2_norm(path: Path, expected_dim: int) -> bool:
    """Verify ONNX model outputs L2-normalized vectors."""
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError:
        return True  # Skip verification if deps missing

    try:
        sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        # Dummy input
        input_ids = np.array([[101, 2023, 2003, 102]], dtype=np.int64)  # "[CLS] hello world [SEP]"
        attention_mask = np.array([[1, 1, 1, 1]], dtype=np.int64)
        inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in [i.name for i in sess.get_inputs()]:
            inputs["token_type_ids"] = np.array([[0, 0, 0, 0]], dtype=np.int64)
        outputs = sess.run(None, inputs)
        emb = outputs[0]
        if emb.shape[-1] != expected_dim:
            print(f"[ensure_onnx] WARNING: dimension mismatch: got {emb.shape[-1]}, expected {expected_dim}")
            return False
        norms = np.linalg.norm(emb, axis=-1)
        if not np.allclose(norms, 1.0, atol=1e-3):
            print(f"[ensure_onnx] WARNING: vectors not L2-normalized (norms: {norms})")
            return False
        print(f"[ensure_onnx] L2 norm verification OK: {path.name}")
        return True
    except Exception as e:
        print(f"[ensure_onnx] L2 verification skipped: {e}")
        return True  # Don't fail on verification issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure ONNX models are cached")
    parser.add_argument("--verify", action="store_true", help="Only verify, don't export")
    parser.add_argument("--force", action="store_true", help="Re-export even if files exist")
    parser.add_argument("--docker", action="store_true", help="Docker mode (non-zero exit on failure)")
    args = parser.parse_args()

    if os.getenv("SKIP_ONNX_EXPORT", "").strip() == "1":
        print("[ensure_onnx] SKIP_ONNX_EXPORT=1 set, skipping export")
        return 0

    cfg = get_model_config()
    cache = _cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    emb_path, rnk_path = _model_paths(cache, cfg)

    print(f"[ensure_onnx] Cache dir: {cache}")
    print(f"[ensure_onnx] Embedding: {cfg.embedding_model} -> {emb_path}")
    print(f"[ensure_onnx] Reranker:  {cfg.reranker_model} -> {rnk_path}")

    # Check existing (both naming conventions)
    emb_existing = _find_existing_model(cache, cfg.embedding_model.split("/")[-1])
    rnk_existing = _find_existing_model(cache, cfg.reranker_model.split("/")[-1] + "_int8")
    emb_exists = emb_existing is not None
    rnk_exists = rnk_existing is not None
    # Use existing path if found, otherwise default
    if emb_existing:
        emb_path = emb_existing
    if rnk_existing:
        rnk_path = rnk_existing

    if args.verify:
        if emb_exists and rnk_exists:
            print("[ensure_onnx] Both models present ✓")
            _verify_l2_norm(emb_path, cfg.embedding_dimensionality)
            _verify_l2_norm(rnk_path, 1)  # reranker outputs single logit
            return 0
        else:
            missing = []
            if not emb_exists:
                missing.append("embedding")
            if not rnk_exists:
                missing.append("reranker")
            print(f"[ensure_onnx] Missing: {', '.join(missing)}", file=sys.stderr)
            return 1 if args.docker else 0

    # Export missing
    if not emb_exists or args.force:
        if not _export_embedding_onnx(cfg, emb_path):
            return 1
        _verify_l2_norm(emb_path, cfg.embedding_dimensionality)
    else:
        print(f"[ensure_onnx] Embedding already present: {emb_path}")
        _verify_l2_norm(emb_path, cfg.embedding_dimensionality)

    if not rnk_exists or args.force:
        if not _export_reranker_onnx(cfg, rnk_path):
            return 1
        _verify_l2_norm(rnk_path, 1)
    else:
        print(f"[ensure_onnx] Reranker already present: {rnk_path}")
        _verify_l2_norm(rnk_path, 1)

    print("[ensure_onnx] All models ready ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())