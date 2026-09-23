#!/usr/bin/env bash
# TRUSTRAG — hardware-aware local LLM launcher (router server mode).
#
# Starts llama-server in router mode to serve multiple models from cache.
# Models are loaded on-demand when selected from UI.
#
# Usage:
#   ./scripts/start_local_llm.sh [--max N] [--port PORT]
#   --max N : maximum concurrent loaded models (default: RAM-aware — 1 on
#             ≤8 GB hosts, 2 on ≤16 GB, 4 above; an explicit --max always wins)
#   --port PORT : port to serve on (default: 8080)
#   Default: serves all cached GGUF models from HuggingFace cache.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
PY="$API_DIR/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "ERROR: API venv not found at $PY — run 'cd apps/api && python -m venv .venv && pip install -e .' first." >&2
  exit 1
fi

# Resolve hardware-specific launch flags.
LAUNCH_FLAGS=($(cd "$API_DIR" && "$PY" -c "
from app.core.hardware import get_llamacpp_launch_args
print(' '.join(get_llamacpp_launch_args()))
"))

# Parse args.
MAX_MODELS=""
PORT=8080
while [ $# -gt 0 ]; do
  case "$1" in
    --max) MAX_MODELS="${2:-4}"; shift 2 ;;
    --port) PORT="${2:-8080}"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Default --max follows host RAM (each resident GGUF + its KV cache is GBs;
# on 8 GB hosts a second model means swap). Matches the -c/-np tiers in
# app/core/hardware.py:get_llamacpp_launch_args.
if [ -z "$MAX_MODELS" ]; then
  MAX_MODELS=$(cd "$API_DIR" && "$PY" -c "
from app.core.hardware import get_system_memory_info
total = get_system_memory_info()['total_gb']
print(1 if total <= 8.5 else (2 if total <= 16.5 else 4))
")
fi

# Models directory (HuggingFace cache where GGUF models are stored).
# Created on demand: a fresh machine has no GGUFs yet, and the router
# autoloads models as they arrive — so start anyway and tell the user how
# to fetch one instead of hard-failing.
MODELS_DIR="${HF_HUB_CACHE:-$HOME/.cache/huggingface/hub}"
if [ ! -d "$MODELS_DIR" ]; then
  echo "[start_local_llm] creating empty models dir: $MODELS_DIR"
  mkdir -p "$MODELS_DIR"
  echo "[start_local_llm] no GGUF models cached yet — fetch one, e.g.:"
  echo "    hf download LiquidAI/LFM2.5-1.2B-Instruct-GGUF --include '*Q4_K_M*' --local-dir '$MODELS_DIR'"
  echo "  (needs 'pip install -U \"huggingface_hub[cli]\"'; router picks it up on select)"
fi

if ! command -v llama-server >/dev/null 2>&1; then
  echo "ERROR: 'llama-server' not found on PATH." >&2
  echo "  macOS:  brew install llama.cpp" >&2
  echo "  Linux:  download a release from https://github.com/ggerganov/llama.cpp/releases" >&2
  echo "  Windows: run this script under WSL (native .cmd wrapper is not shipped)." >&2
  exit 1
fi

echo "[start_local_llm] router mode: serving from $MODELS_DIR"
echo "[start_local_llm] max concurrent models: $MAX_MODELS"
echo "[start_local_llm] port : $PORT"

exec llama-server \
  --models-dir "$MODELS_DIR" \
  --models-max "$MAX_MODELS" \
  --models-autoload \
  --port "$PORT" \
  "${LAUNCH_FLAGS[@]}"