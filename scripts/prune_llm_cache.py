#!/usr/bin/env python3
"""TRUSTRAG — Prune generative-LLM weights, keep embedding + reranker.

Removes downloaded GENERATIVE models (GGUF / MLX / Ollama blobs) while
preserving:
  - embedding model  (models.yaml `embedding.model`, default BAAI/bge-small-en-v1.5)
  - reranker model   (models.yaml `reranker.model`, default cross-encoder/ms-marco-MiniLM-L-6-v2)
  - ONNX exports in apps/api/.model_cache (bge + reranker .onnx)

Usage:
  python scripts/prune_llm_cache.py          # prune HF hub generative models
  python scripts/prune_llm_cache.py --dry-run  # list only
  python scripts/prune_llm_cache.py --ollama   # also print `ollama rm` commands (server must run)

Re-download pruned weights any time via:
  scripts/start_local_llm.sh  (llama-server)  /  ollama pull <model>
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

try:
    from app.core.config import get_model_config

    _cfg = get_model_config()
    KEEP_IDS = {str(_cfg.embedding_model).lower(), str(_cfg.reranker_model).lower()}
except Exception:
    KEEP_IDS = {"baai/bge-small-en-v1.5", "cross-encoder/ms-marco-miniLM-l-6-v2"}

# Substring hints that always mark a GENERATIVE (non-embedding/reranker) weight.
_GENERATIVE_HINTS = ("gguf", "mlx", "smollm", "granite", "lfm", "qwen", "minicpm", "exaone")


def _hub_dir() -> Path:
    return Path.home() / ".cache" / "huggingface" / "hub"


def _repo_id(dir_name: str) -> str:
    return dir_name.replace("models--", "").replace("--", "/")


def prune_hf_hub(dry_run: bool = False) -> tuple[int, int]:
    hub = _hub_dir()
    if not hub.exists():
        print(f"[prune] HF hub not found: {hub}")
        return 0, 0
    removed, freed = 0, 0
    for d in sorted(hub.glob("models--*")):
        repo = _repo_id(d.name)
        if repo.lower() in KEEP_IDS:
            print(f"[prune] KEEP (embedding/reranker): {repo}")
            continue
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        if dry_run:
            print(f"[prune] WOULD REMOVE {repo} ({size / 1e9:.2f} GB)")
        else:
            shutil.rmtree(d, ignore_errors=True)
            print(f"[prune] REMOVED {repo} ({size / 1e9:.2f} GB)")
        removed += 1
        freed += size
    print(f"[prune] {removed} generative model(s), {freed / 1e9:.2f} GB {'(dry-run)' if dry_run else 'freed'}")
    return removed, freed


def ollama_hints() -> None:
    print("[prune] Ollama blobs live in ~/.ollama (server-managed).")
    print("[prune] With `ollama serve` running, remove unneeded models via:")
    print("  ollama list                 # see what's installed")
    print("  ollama rm <model>           # drop one generative model")
    print("[prune] Embedding/reranker run torch-free via ONNX — no Ollama copy needed.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Prune generative LLM weights, keep embedding+reranker")
    ap.add_argument("--dry-run", action="store_true", help="List only, delete nothing")
    ap.add_argument("--ollama", action="store_true", help="Print Ollama prune hints")
    args = ap.parse_args()
    prune_hf_hub(dry_run=args.dry_run)
    if args.ollama:
        ollama_hints()
    return 0


if __name__ == "__main__":
    sys.exit(main())
