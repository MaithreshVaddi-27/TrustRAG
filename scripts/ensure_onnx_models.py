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
  MODEL_CACHE_DIR           # preferred override (default: apps/api/.model_cache)
  CACHE_DIR                 # legacy fallback (MODEL_CACHE_DIR wins)
  EMBEDDING_MODEL           # override embedding model (default: BAAI/bge-small-en-v1.5)
  RERANKER_MODEL            # override reranker model (default: cross-encoder/...MiniLM-L-6-v2)
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
    # MODEL_CACHE_DIR is preferred; CACHE_DIR kept as legacy fallback.
    # (CACHE_DIR is also the runtime SQLite disk-cache var — for model
    # weights prefer MODEL_CACHE_DIR to avoid collisions.)
    env_dir = os.getenv("MODEL_CACHE_DIR") or os.getenv("CACHE_DIR")
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
    rnk_base = cfg.reranker_model.split("/")[-1].replace(".", "_")

    # Embedding: canonical <base>.onnx (dots preserved, e.g. bge-small-en-v1.5.onnx)
    emb_path = cache / f"{emb_base}.onnx"

    # Reranker: canonical reranker-<base>_int8.onnx — must match
    # app/core/model_registry.py get_reranker() auto-generated path.
    rnk_path = cache / f"reranker-{rnk_base}_int8.onnx"

    return (emb_path, rnk_path)


def _find_existing_model(cache: Path, base_name: str, kind: str) -> Path | None:
    """Find an existing model file (canonical first, legacy names accepted).

    Legacy files are reused as-is (never re-downloaded); new exports always
    use the canonical names from _model_paths().

    `kind` keeps the two model slots strictly separate: an embedding lookup
    must NEVER match a reranker file (and vice versa) — their tensors are
    incompatible and booting with the wrong one corrupts all vectors.
    """
    underscored = base_name.replace(".", "_")
    if kind == "embedding":
        candidates = [
            cache / f"{base_name}.onnx",
            cache / f"{underscored}.onnx",
        ]
    else:
        candidates = [
            cache / f"reranker-{underscored}_int8.onnx",  # canonical
            cache / f"{underscored}_int8.onnx",  # legacy, no reranker- prefix
            cache / f"reranker-{base_name}.onnx",  # legacy, no int8 suffix
            cache / f"reranker-{underscored}.onnx",
        ]
        # Also match the registry's old auto-path (model with org, -- separator).
        for extra in sorted(cache.glob("reranker-*.onnx")):
            if extra not in candidates:
                candidates.append(extra)
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _export_embedding_onnx(cfg, emb_path: Path) -> bool:
    """Export embedding model to ONNX (canonical .model_cache path).

    Delegates to scripts/export_bge_onnx.py, whose graph contains transformer
    + CLS pooling + L2 normalization — exactly what app/core/onnx_embeddings.py
    expects. A bare backbone export does NOT satisfy this contract.
    """
    print(f"[ensure_onnx] Exporting embedding model: {cfg.embedding_model} -> {emb_path}")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from export_bge_onnx import export_bge_to_onnx

        export_bge_to_onnx(emb_path, model_name=cfg.embedding_model)
        print(f"[ensure_onnx] Embedding export OK: {emb_path}")
        return True
    except ImportError as e:
        print(f"[ensure_onnx] Missing dependencies for embedding export: {e}", file=sys.stderr)
        print(
            '[ensure_onnx] Install with: pip install -e apps/api/".[local-models]"',
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f"[ensure_onnx] Embedding export failed: {e}", file=sys.stderr)
        return False


def _export_reranker_onnx(cfg, rnk_path: Path) -> bool:
    """Export reranker model to ONNX with int8 quantization.

    Delegates to app/core/onnx_reranker.export_crossencoder_to_onnx — the same
    implementation the backend uses at runtime — instead of a duplicate exporter.
    """
    print(f"[ensure_onnx] Exporting reranker model: {cfg.reranker_model} -> {rnk_path}")
    try:
        from sentence_transformers import CrossEncoder

        from app.core.onnx_reranker import export_crossencoder_to_onnx

        model = CrossEncoder(cfg.reranker_model)
        export_crossencoder_to_onnx(model, str(rnk_path), tokenizer_name=cfg.reranker_model)
        print(f"[ensure_onnx] Reranker export + quant OK: {rnk_path}")
        return True
    except ImportError as e:
        print(f"[ensure_onnx] Missing dependencies for reranker export: {e}", file=sys.stderr)
        print(
            '[ensure_onnx] Install with: pip install -e apps/api/".[local-models]"',
            file=sys.stderr,
        )
        return False
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
            print(f"[ensure_onnx] WARNING: dim mismatch: got {emb.shape[-1]}, want {expected_dim}")
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
    parser.add_argument("--docker", action="store_true", help="Docker mode (fail on missing)")
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

    # Check existing (canonical first, all legacy names accepted)
    emb_existing = _find_existing_model(cache, cfg.embedding_model.split("/")[-1], "embedding")
    rnk_existing = _find_existing_model(cache, cfg.reranker_model.split("/")[-1], "reranker")
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
            return 0
        else:
            missing = []
            if not emb_exists:
                missing.append("embedding")
            if not rnk_exists:
                missing.append("reranker")
            print(f"[ensure_onnx] Missing: {', '.join(missing)}", file=sys.stderr)
            return 1

    # Export missing
    if not emb_exists or args.force:
        if not _export_embedding_onnx(cfg, emb_path):
            return 1
        if not _verify_l2_norm(emb_path, cfg.embedding_dimensionality):
            print("[ensure_onnx] Exported embedding FAILED verification", file=sys.stderr)
            return 1
    else:
        print(f"[ensure_onnx] Embedding already present: {emb_path}")
        if not _verify_l2_norm(emb_path, cfg.embedding_dimensionality):
            print(
                f"[ensure_onnx] Cached embedding FAILED verification: {emb_path}. "
                "Delete it and re-run (or use --force).",
                file=sys.stderr,
            )
            return 1

    if not rnk_exists or args.force:
        if not _export_reranker_onnx(cfg, rnk_path):
            # Reranker is optional at runtime (get_reranker() falls back to
            # PyTorch, then to RRF order) — warn, don't block the backend.
            # Only --docker (bake-into-image) treats this as fatal.
            print(
                "[ensure_onnx] WARNING: reranker export failed; backend will "
                "fall back to RRF order. The export needs torch + "
                "sentence-transformers + onnxruntime: from apps/api run "
                "'pip install -e \".[local-models]\"' (onnxruntime ships "
                "with the base requirements), then re-run.",
                file=sys.stderr,
            )
            if args.docker:
                return 1
    else:
        print(f"[ensure_onnx] Reranker already present: {rnk_path}")

    print("[ensure_onnx] All models ready ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
