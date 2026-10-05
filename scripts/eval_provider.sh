#!/usr/bin/env bash
# TRUSTRAG — compare a provider against the frozen baseline.
#
# One script per invocation keeps small-model and large-model runs
# reproducible and separate: each provider gets its own results file and its
# own recorded experiment, so "does the 1.2B local model actually work?"
# is answered by numbers rather than by eyeballing a screenshot.
#
# The pipeline adapts to model size on its own (compact CRAFT prompt + the
# two-step verification path for ≤3B; full prompt + fused path otherwise), so
# this script does not switch behaviour — it only boots the provider, checks
# it answers, and runs the shared dataset.
#
# Usage:
#   ./scripts/eval_provider.sh <provider> [model] --email X --password Y --kb-id Z
#
#   provider : ollama | llama_cpp | mlx | gemini
#   model    : optional id override (defaults to models.yaml for that provider)
#
# Examples:
#   # small local model (auto-picks models.yaml default, uses :8080)
#   ./scripts/eval_provider.sh llama_cpp --email ops@example.com --password '...' --kb-id $ID
#   # large local model on a different port
#   ./scripts/eval_provider.sh mlx mlx-community/Llama-3.2-3B-Instruct-4bit --email ... --kb-id $ID
#   # cloud
#   ./scripts/eval_provider.sh gemini --email ... --kb-id $ID
#
# Prereqs: API + MongoDB + Qdrant up, a KB holding tests/eval/fixtures/corpus/*,
# and the provider already serving (start_local_llm.sh / start_mlx_server.sh).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT_DIR/apps/api/.venv/bin/python"

if [ -z "${PY:-}" ] || [ ! -x "$PY" ]; then
  echo "ERROR: API venv not found at $PY" >&2
  exit 1
fi

PROVIDER="${1:-}"
[ -n "$PROVIDER" ] || {
  echo "usage: $0 <ollama|llama_cpp|mlx|gemini> [model] --email X --password Y --kb-id Z" >&2
  exit 1
}
shift
MODEL="${1:-}"
if [ -n "$MODEL" ] && [ "${MODEL#--}" = "$MODEL" ]; then shift; fi

case "$PROVIDER" in
  ollama|llama_cpp|llamacpp|mlx|gemini) ;;
  *) echo "ERROR: unsupported provider '$PROVIDER'" >&2; exit 1 ;;
esac

# Resolve the effective base URL + default model the same way the app does, so
# a "provider is down" verdict here means the same thing it would in the API.
read -r BASE_URL DEFAULT_MODEL <<<"$(cd "$ROOT_DIR/apps/api" && "$PY" -c "
from app.core.config.model_config import get_model_config
from app.core.config.settings import get_settings
s = get_settings()
cfg = get_model_config()
p = '$PROVIDER'
# Cloud providers (gemini) have no base_url — they go through the SDK.
url = ''
if p == 'mlx':
    url = s.mlx_base_url
elif p == 'ollama':
    url = s.ollama_base_url
elif p != 'gemini':
    url = s.llamacpp_base_url
try:
    model = cfg.llm_model_for(p) or ''
except Exception:
    model = ''
# '-' sentinel: an empty url would word-split into the model field.
print(url or '-', model or '-')
" | tail -n 1)"
[ "$BASE_URL" = "-" ] && BASE_URL=""
[ "$DEFAULT_MODEL" = "-" ] && DEFAULT_MODEL=""
EFFECTIVE_MODEL="${MODEL:-$DEFAULT_MODEL}"

echo "provider   : $PROVIDER"
echo "model      : ${EFFECTIVE_MODEL:-<server default>}"
echo "base url   : ${BASE_URL:-<cloud / n/a>}"

# Preflight: a provider that cannot answer will burn the whole dataset at
# --delay-seconds per query and produce an all-error report.
if [ "$PROVIDER" != "gemini" ] && [ -n "$BASE_URL" ]; then
  if curl -sf --max-time 5 "${BASE_URL%/}/models" >/dev/null 2>&1; then
    echo "preflight  : OK"
  else
    echo "WARNING: no server answering at $BASE_URL — start it first:" >&2
    case "$PROVIDER" in
      mlx)        echo "  ./scripts/start_mlx_server.sh" >&2 ;;
      llama_cpp)  echo "  ./scripts/start_local_llm.sh" >&2 ;;
      ollama)     echo "  ollama serve && ollama pull <model>" >&2 ;;
    esac
  fi
fi

OUT_DIR="$ROOT_DIR/docs/evaluation/results/$PROVIDER"
mkdir -p "$OUT_DIR"

# Small models need a leaner tier (models.yaml lean_tier) — already automatic.
# The only thing the caller must supply is credentials and the KB id.
exec "$PY" "$ROOT_DIR/scripts/run_baseline_eval.py" \
  --out-dir "$OUT_DIR" \
  --config-name "trustrag_baseline_${PROVIDER}" \
  --description "Frozen baseline (baseline_v1) on ${PROVIDER}: ${EFFECTIVE_MODEL:-server default}" \
  "$@"