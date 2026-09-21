#!/usr/bin/env bash
# TRUSTRAG — hardware-aware local LLM launcher (router server mode).
#
# Starts llama-server in router mode to serve multiple models from cache.
# Models are loaded on-demand when selected from UI.
#
# Usage:
#   ./scripts/start_local_llm.sh [--max N] [--port PORT]
#   --max N : maximum concurrent loaded models (default: 4)
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
MAX_MODELS=4
PORT=8080
while [ $# -gt 0 ]; do
  case "$1" in
    --max) MAX_MODELS="${2:-4}"; shift 2 ;;
    --port) PORT="${2:-8080}"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Models directory (HuggingFace cache where GGUF models are stored).
MODELS_DIR="$HOME/.cache/huggingface/hub"
if [ ! -d "$MODELS_DIR" ]; then
  echo "ERROR: Models directory not found: $MODELS_DIR" >&2
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