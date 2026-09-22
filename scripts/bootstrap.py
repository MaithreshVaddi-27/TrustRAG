#!/usr/bin/env python3
"""
TRUSTRAG — Pre-backend bootstrap (run before uvicorn / docker compose).

What it does:
  1. Ensures ONNX embedding + reranker weights are cached locally
     (downloads/exports on first run; no-op in ~1s when cached).
  2. Best-effort local-LLM discovery snapshot (ollama / llama.cpp / mlx)
     so the backend serves the right models from the first request.
  3. Prints actionable next steps (never auto-downloads multi-GB LLM blobs).

Models are NEVER committed to git (.gitignore: *.onnx, .model_cache/, *.gguf,
*.safetensors). Every user — new clone or fresh `git pull` — runs this once;
a model-ID change in apps/api/config/models.yaml is detected automatically
(the old cache file simply stops matching and only the new model is fetched).

Usage:
  python scripts/bootstrap.py              # ensure everything, then start backend
  python scripts/bootstrap.py --verify     # check only, no downloads (CI / setup.sh)
  python scripts/bootstrap.py --force      # re-export even if cached
  python scripts/bootstrap.py --skip-discovery  # skip LLM discovery snapshot

Typical flow:
  python scripts/bootstrap.py
  cd apps/api && .venv/bin/uvicorn app.main:app --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))


def _ensure_onnx(argv: list[str]) -> int:
    """Run the ONNX ensure phase with forwarded flags. Returns exit code."""
    import ensure_onnx_models as e

    old_argv = sys.argv
    sys.argv = ["ensure_onnx_models.py", *argv]
    try:
        return int(e.main())
    finally:
        sys.argv = old_argv


def _seed_discovery() -> int:
    """Best-effort local-LLM discovery snapshot. Never fails the bootstrap."""
    try:
        from app.core.local_llm import seed_local_model_discovery
    except Exception as exc:
        print(f"[bootstrap] discovery skipped (import failed: {exc})")
        return 0
    try:
        result = asyncio.run(seed_local_model_discovery())
        total = len(result.get("ollama", [])) + len(result.get("llama_cpp", []))
        print(f"[bootstrap] discovery: {total} local generative model(s) snapshotted")
        return 0
    except Exception as exc:
        print(f"[bootstrap] discovery skipped (no local LLM running?: {exc})")
        return 0


def main() -> int:
    args = set(sys.argv[1:])
    verify = "--verify" in args
    force = "--force" in args
    skip_discovery = "--skip-discovery" in args

    print("[bootstrap] TRUSTRAG pre-backend bootstrap")

    # ── Phase 1: ONNX weights (the slow part on first run, ~1s when cached) ──
    forward = []
    if verify:
        forward.append("--verify")
    if force:
        forward.append("--force")
    if "--docker" in args:
        forward.append("--docker")
    rc = _ensure_onnx(forward)
    if rc != 0:
        if verify:
            print(
                "[bootstrap] NOT READY — run without --verify to download/export", file=sys.stderr
            )
            return 1
        print("[bootstrap] ONNX ensure failed", file=sys.stderr)
        return 1
    if verify:
        print("[bootstrap] READY ✓ (verify only, nothing downloaded)")

    # ── Phase 2: LLM discovery snapshot (fast, best-effort) ──
    if not skip_discovery and not verify:
        _seed_discovery()

    if not verify:
        print("[bootstrap] READY ✓ — start the backend:")
        print("  cd apps/api && .venv/bin/uvicorn app.main:app --port 8000 --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
