#!/usr/bin/env bash
# TRUSTRAG — MLX local LLM launcher (Apple Silicon).
#
# Starts mlx_lm.server on the port reserved for MLX in config/ports.yaml
# (currently 8090). MLX serves ONE model per process, so run additional
# instances on consecutive ports (8091, 8092, …) to offer more models;
# check_mlx_status() scans a range and aggregates what it finds.
#
# Usage:
#   ./scripts/start_mlx_server.sh [MODEL] [--port PORT] [--dry-run] [--check]
#   MODEL : HF repo id (default: models.yaml `llm.model_mlx`)
#   --port PORT  : override (default: ports.yaml `mlx`, currently 8090)
#   --dry-run     : print the command, don't start
#   --check       : report status of the MLX port range, then exit
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
PY="$API_DIR/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "ERROR: API venv not found at $PY — run 'cd apps/api && python -m venv .venv && pip install -e .' first." >&2
  exit 1
fi

# Model default + port both come from config so there is one source of truth.
read -r DEFAULT_MODEL DEFAULT_PORT <<<"$(cd "$API_DIR" && "$PY" -c "
from app.core.config.model_config import get_model_config
from app.core.config.settings import get_ports
cfg = get_model_config()
model = 'mlx-community/Llama-3.2-1B-Instruct-4bit'
try:
    model = cfg.llm_model_for('mlx') or model
except Exception:
    pass
print(model, get_ports().get('mlx', 8090))
" | tail -n 1)"

MODEL="$DEFAULT_MODEL"
PORT="$DEFAULT_PORT"
DRY_RUN=0
CHECK_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:-$DEFAULT_PORT}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --check) CHECK_ONLY=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    -*) echo "Unknown arg: $1" >&2; exit 1 ;;
    *) MODEL="$1"; shift ;;
  esac
done

if [ "$CHECK_ONLY" = "1" ]; then
  echo "[mlx] scanning :$PORT-$((PORT + 4)) for MLX servers"
  found=0
  for offset in 0 1 2 3 4; do
    p=$((PORT + offset))
    if models=$(curl -sf --max-time 2 "http://127.0.0.1:$p/v1/models" 2>/dev/null); then
      echo "[mlx] :$p UP"
      echo "$models" | sed 's/^/         /'
      found=1
    else
      echo "[mlx] :$p down"
    fi
  done
  [ "$found" = "1" ] || echo "[mlx] no MLX server responding — start one with: $0 $MODEL"
  exit 0
fi

# Architecture gate: mlx_lm only runs on Apple Silicon.
if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo "ERROR: MLX requires Apple Silicon (macOS arm64); this host is $(uname -s)/$(uname -m)." >&2
  echo "  The 'llama_cpp' provider is the portable fallback: ./scripts/start_local_llm.sh" >&2
  exit 1
fi

# Resolve the server entry point. mlx-lm exposes a console script, but a
# `python -m` fallback keeps this working when it is only installed as a lib.
if command -v mlx_lm.server >/dev/null 2>&1; then
  SERVER_CMD=(mlx_lm.server)
elif "$PY" -c "import mlx_lm.server" >/dev/null 2>&1; then
  SERVER_CMD=("$PY" -m mlx_lm.server)
else
  echo "ERROR: 'mlx_lm' is not installed." >&2
  echo "  Install:  $PY -m pip install mlx-lm" >&2
  echo "  (or:      pip install -e 'apps/api[mlx]')" >&2
  exit 1
fi

if [ "$DRY_RUN" = "1" ]; then
  echo "[mlx] would run: ${SERVER_CMD[*]} --model $MODEL --port $PORT"
  exit 0
fi

if curl -sf --max-time 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
  echo "ERROR: something is already serving on :$PORT." >&2
  echo "  Stop it, or pass --port \$((PORT + 1)) to run another instance." >&2
  exit 1
fi

echo "[mlx] model: $MODEL"
echo "[mlx] port : $PORT  (base URL http://127.0.0.1:$PORT/v1)"
echo "[mlx] first request pays the load cost; weights stream from the HF cache on demand."

exec "${SERVER_CMD[@]}" --model "$MODEL" --port "$PORT"