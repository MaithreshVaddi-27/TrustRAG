#!/usr/bin/env bash
# TRUSTRAG — the full accuracy evaluation matrix.
#
# Runs the 33-probe ground truth (27 answerable + 6 unanswerable) against
# every model configuration the project has measured, with the same corpus,
# the same harness and the same scoring. Each run gets a fresh knowledge
# base so nothing leaks between configurations.
#
# The shipped configuration is restored at the end, whatever happens.
#
# Usage:
#   bash scripts/eval/run_matrix.sh            # all six configurations
#   bash scripts/eval/run_matrix.sh gemma3     # only the gemma3 runs
#
# Artifacts: eval_accuracy_<label>.json, one per configuration.

set -uo pipefail

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Same venv discovery as start_local_llm.sh / typecheck_ratchet.sh: the venv
# layout differs on Windows, and a Homebrew-only absolute path broke Linux and
# Windows outright.
if [ -x "$API_DIR/.venv/bin/python" ]; then
  PY="$API_DIR/.venv/bin/python"
elif [ -x "$API_DIR/.venv/Scripts/python.exe" ]; then
  PY="$API_DIR/.venv/Scripts/python.exe"
elif [ -x "$API_DIR/.venv/Scripts/python" ]; then
  PY="$API_DIR/.venv/Scripts/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "ERROR: no Python 3.11/3.12 found — create apps/api/.venv first." >&2
  exit 1
fi
MODELS_YAML="$API_DIR/config/models.yaml"
API_URL="http://127.0.0.1:8000"

# The shipped models.yaml, restored on exit however this script ends.
MODELS_YAML_BACKUP="$(mktemp)"
cp "$MODELS_YAML" "$MODELS_YAML_BACKUP"

restore() {
  cp "$MODELS_YAML_BACKUP" "$MODELS_YAML"
  rm -f "$MODELS_YAML_BACKUP"
}
trap restore EXIT INT TERM

ONLY="${1:-all}"

stop_api() {
  # `pkill -f` is not available on Windows; the health probe below is the
  # authority anyway. Prefer a recorded PID, then a best-effort pkill.
  if [ -n "${API_PID:-}" ]; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
    API_PID=""
  fi
  if command -v pkill >/dev/null 2>&1; then
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
  elif command -v taskkill >/dev/null 2>&1; then
    taskkill //F //IM python.exe 2>/dev/null || true
  fi
  sleep 3
}

start_api() {
  # start_api <extra env assignments...>
  stop_api
  # Background the subshell itself and exec uvicorn inside it, so $! is the
  # process we later need to stop (nested `&` would lose that PID).
  ( cd "$API_DIR" && exec env "$@" "$PY" -m uvicorn app.main:app \
      --host 127.0.0.1 --port 8000 --log-level warning >"$API_DIR/eval_api.log" 2>&1 ) &
  API_PID=$!
  for _ in $(seq 1 60); do
    if curl -sf -o /dev/null --max-time 2 "$API_URL/api/v1/health"; then return 0; fi
    sleep 1
  done
  echo "api did not come up" >&2
  return 1
}

set_temperature() {
  "$PY" - "$MODELS_YAML" "$1" <<'PYEOF'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); value = sys.argv[2]
s = p.read_text()
s = re.sub(r"^  temperature: .*$", f"  temperature: {value}", s, count=1, flags=re.M)
p.write_text(s)
PYEOF
}

set_context_chunks() {
  # The cap that retrieval and recovery actually use is the *tier* cap
  # (cost_controls.lean_tier.max_context_chunks), not the top-level
  # retrieval.max_context_chunks - the tier is chosen from the model's
  # context window, and gemma3:1b lands on lean_tier.
  "$PY" - "$MODELS_YAML" "$1" <<'PYEOF'
import pathlib, re, sys

p = pathlib.Path(sys.argv[1])
value = sys.argv[2]
s = p.read_text()

m = re.search(r"^(\s*)lean_tier:\s*$", s, flags=re.M)
if not m:
    raise SystemExit("lean_tier block not found in models.yaml")
indent = m.group(1)
block_re = re.compile(
    rf"^(?P<ind>{indent}  )max_context_chunks: \d+.*$", flags=re.M
)
after = s[m.end():]
new_after, n = block_re.subn(
    f"    max_context_chunks: {value}", after, count=1
)
if n != 1:
    raise SystemExit("lean_tier.max_context_chunks not found")
p.write_text(s[:m.end()] + new_after)
PYEOF
}

run() {
  local label="$1"; shift
  local provider="$1"; shift
  local model="$1"; shift
  echo "── $label"
  ( cd "$API_DIR" && "$PY" scripts/eval/eval_accuracy.py \
      --out "eval_accuracy_${label}.json" \
      --label "$label" \
      --provider "$provider" \
      --model "$model" ) 2>&1 | grep -E '"(label|answer_accuracy|abstention_accuracy|answerable_answered|unanswerable_abstained|recall_at_k|precision_at_k|mrr|mean_latency_ms)"' || echo "  RUN FAILED: $label"
}

want() {
  [ "$ONLY" = "all" ] && return 0
  case "$1" in *"$ONLY"*) return 0;; *) return 1;; esac
}

# ── 1. gemma3:1b, the shipped default ───────────────────────────────────────
if want gemma3_1b; then
  start_api && run gemma3_1b ollama gemma3:1b
fi

# ── 2. gemma3:1b with the cross-encoder reranker ────────────────────────────
if want gemma3_rerank; then
  start_api RERANKER_ENABLED=true && run gemma3_rerank ollama gemma3:1b
fi

# ── 3. gemma3:1b with greedy decoding ───────────────────────────────────────
if want gemma3_temp0; then
  set_temperature 0.0
  start_api && run gemma3_temp0 ollama gemma3:1b
  cp "$MODELS_YAML_BACKUP" "$MODELS_YAML"
fi

# ── 4. gemma3:1b with three context chunks instead of five ──────────────────
if want gemma3_ctx3; then
  set_context_chunks 3
  start_api && run gemma3_ctx3 ollama gemma3:1b
  cp "$MODELS_YAML_BACKUP" "$MODELS_YAML"
fi

# ── 5. qwen3:1.7b — deep-reasoning mode, verifier thinking on ────────────────
if want qwen3_1_7b; then
  start_api DEEP_REASONING_MODE=true LLM_VERIFICATION_THINKING=true \
    && run qwen3_1_7b ollama qwen3:1.7b
fi

# ── 6. qwen3:1.7b with the thinking control (the shipped setting) ────────────
if want qwen3_nothink; then
  start_api DEEP_REASONING_MODE=true LLM_VERIFICATION_THINKING=false \
    && run qwen3_nothink ollama qwen3:1.7b
fi

# Restore the shipped configuration and leave the API running on it.
cp "$MODELS_YAML_BACKUP" "$MODELS_YAML"
start_api DEEP_REASONING_MODE=true LLM_VERIFICATION_THINKING=false
echo
echo "artifacts: $API_DIR/eval_accuracy_*.json"
