#!/usr/bin/env bash
# TRUSTRAG — hardware-aware local LLM launcher.
#
# Detects the host GPU (Metal on Apple Silicon, CUDA on NVIDIA) and boots
# llama-server with full GPU offload plus memory-tier context/concurrency
# budgets, so the model runs on the GPU without saturating unified memory.
#
# Usage:
#   ./scripts/start_local_llm.sh [model_repo[:quant]]
#   Default model: repo's llama_cpp config default (see models.yaml).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
PY="$API_DIR/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "ERROR: API venv not found at $PY — run 'cd apps/api && python -m venv .venv && pip install -e .' first." >&2
  exit 1
fi

# Resolve flags + default model via the API's hardware/config layer.
# Two-line output: line 1 = flags (space-separated), line 2 = default model id.
OUT="$(cd "$API_DIR" && "$PY" - <<'PYEOF'
from app.core.config import get_model_config
from app.core.hardware import get_llamacpp_launch_args

print(" ".join(get_llamacpp_launch_args()))
print(get_model_config().llm_model_for("llama_cpp"))
PYEOF
)"
LAUNCH_FLAGS=$(echo "$OUT" | sed -n '1p')
DEFAULT_MODEL=$(echo "$OUT" | sed -n '2p')
MODEL="${1:-$DEFAULT_MODEL}"

echo "[start_local_llm] model : $MODEL"
echo "[start_local_llm] flags : $LAUNCH_FLAGS"
echo "[start_local_llm] port  : 8080"

# Split flags on whitespace into argv (words only, no globbing).
# shellcheck disable=SC2086
exec llama-server -hf "$MODEL" --port 8080 $LAUNCH_FLAGS
