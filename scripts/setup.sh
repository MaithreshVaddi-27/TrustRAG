#!/usr/bin/env bash
# TRUSTRAG — new-machine setup verifier (local-first, zero API keys required).
#
# Checks every local prerequisite and prints copy-paste fixes for whatever is
# missing. Idempotent and non-destructive: it never installs, overwrites, or
# starts anything — run it as often as you like.
#
# Usage:
#   ./scripts/setup.sh
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0

ok()   { PASS=$((PASS + 1)); echo "  ✓ $1"; }
warn() { FAIL=$((FAIL + 1)); echo "  ✗ $1"; echo "    → $2"; }

echo "[setup] TRUSTRAG local prerequisites — $ROOT_DIR"
echo
if [ "${OS:-}" = "Windows_NT" ]; then
  echo "  NOTE: native Windows shell detected — run this script under Git Bash or WSL:"
  echo "         Git Bash:  bash scripts/setup.sh    WSL:  wsl ./scripts/setup.sh"
fi
echo

echo "─ Toolchain ─"
if command -v python3 >/dev/null 2>&1; then
  PYV="$(python3 --version 2>&1 | cut -d' ' -f2)"
  case "$PYV" in 3.11.*|3.12.*) ok "python3 $PYV";; *) warn "python3 $PYV unsupported (need 3.11–3.12)" "Install Python 3.11 or 3.12 (3.13+ breaks torch/onnxscript export); Windows: winget install Python.Python.3.11";; esac
else warn "python3 not found" "Install Python 3.11 or 3.12 (https://python.org)"; fi
if command -v node >/dev/null 2>&1; then ok "node $(node --version)"; else warn "node not found" "Install Node.js 22+ (https://nodejs.org)"; fi
if command -v npm >/dev/null 2>&1; then ok "npm $(npm --version)"; else warn "npm not found" "Ships with Node.js 22+"; fi
if command -v curl >/dev/null 2>&1; then ok "curl present"; else warn "curl not found" "Install curl (Windows: winget install cURL.cURL) — needed for LLM probes below"; fi

echo "─ Environment file ─"
if [ -f "$ROOT_DIR/.env" ]; then
  ok ".env exists"
  if grep -q "REPLACE_WITH_LONG_RANDOM_SECRET" "$ROOT_DIR/.env" 2>/dev/null; then
    warn "JWT_SECRET is still the placeholder" 'Run: python3 -c "import secrets; print(secrets.token_hex(64))" and paste it as JWT_SECRET in .env'
  else
    ok "JWT_SECRET looks configured"
  fi
else
  warn ".env missing" "Run: cp .env.example .env  (then set JWT_SECRET, see above)"
fi

echo "─ Backend venv ─"
if [ -x "$ROOT_DIR/apps/api/.venv/bin/python" ]; then
  ok "apps/api/.venv present"
else
  warn "apps/api/.venv missing" "Run: cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -e \".[dev,local-models]\""
fi

echo "─ Embeddings (default provider: onnx, torch-free) ─"
VPY="$ROOT_DIR/apps/api/.venv/bin/python"
if [ -f "$ROOT_DIR/apps/api/.model_cache/bge-small-en-v1.5.onnx" ]; then
  ok "ONNX embedding model present (onnx provider ready, torch-free)"
elif [ -x "$VPY" ] && "$VPY" -c "import sentence_transformers" 2>/dev/null; then
  ok "torch embedding stack present (huggingface provider ready; run python scripts/bootstrap.py for the default onnx path)"
elif [ ! -x "$VPY" ]; then
  warn "backend venv missing — embedding checks skipped" "Run: cd apps/api && python3 -m venv .venv && . .venv/bin/activate (Windows: .venv\\Scripts\\Activate.ps1) && pip install -e \".[dev,local-models]\""
else
  warn "no embedding stack" "Run: apps/api/.venv/bin/python scripts/bootstrap.py  (downloads/exports ONNX weights into apps/api/.model_cache/; needs network once)"
fi
if [ -x "$VPY" ] && "$VPY" "$ROOT_DIR/scripts/ensure_onnx_models.py" --verify >/dev/null 2>&1; then
  ok "ONNX cache verified (embedding + reranker)"
elif [ ! -x "$VPY" ]; then
  echo "  • ONNX verify skipped (no venv yet — see above)"
else
  warn "ONNX cache incomplete" "Run: apps/api/.venv/bin/python scripts/bootstrap.py"
fi

echo "─ Frontend deps ─"
if [ -d "$ROOT_DIR/apps/web/node_modules" ]; then
  ok "apps/web/node_modules present"
else
  warn "apps/web/node_modules missing" "Run: cd apps/web && npm install"
fi

echo "─ Services ─"
if (echo > /dev/tcp/localhost/27017) 2>/dev/null; then
  ok "MongoDB reachable on :27017"
else
  warn "MongoDB not reachable on :27017" "macOS: brew tap mongodb/brew && brew services start mongodb-community  |  Linux: sudo systemctl enable --now mongod (no systemd/WSL: sudo service mongod start)  |  Windows: net start MongoDB"
fi
if (echo > /dev/tcp/localhost/11434) 2>/dev/null; then
  echo "  • Ollama detected on :11434 (optional)"
fi
if (echo > /dev/tcp/127.0.0.1/8080) 2>/dev/null; then
  if curl -sf http://127.0.0.1:8080/v1/models 2>/dev/null | grep -qi "mlx"; then
    echo "  • MLX server detected on :8080 (should run on :8090 instead)"
  else
    echo "  • llama-server detected on :8080 (optional)"
  fi
else
  echo "  • No local LLM on :8080"
fi
if (echo > /dev/tcp/127.0.0.1/8090) 2>/dev/null; then
  if curl -sf http://127.0.0.1:8090/v1/models 2>/dev/null | grep -qi "mlx"; then
    echo "  • MLX server detected on :8090 (Apple Silicon, optional)"
  else
    echo "  • Unknown server on :8090"
  fi
else
  echo "  • No MLX server on :8090 — start it with:"
  echo "      mlx_lm.server --model mlx-community/Llama-3.2-1B-Instruct-4bit --port 8090"
fi
if command -v mlx_lm.server >/dev/null 2>&1; then
  ok "mlx_lm.server installed (Apple Silicon local inference)"
elif python3 -c "import sys,platform; sys.exit(0 if sys.platform=='darwin' and platform.machine()=='arm64' else 1)" 2>/dev/null; then
  echo "  • mlx_lm.server not installed (Apple Silicon only, optional: pip install mlx-lm)"
else
  echo "  • mlx_lm.server not applicable here (Apple Silicon only — this host can't run it)"
fi

echo "─ Ports ─"
for port in 8000 5173 8080 8090; do
  if (echo > /dev/tcp/localhost/$port) 2>/dev/null; then
    echo "  • :$port already in use (stop the other service or adjust config/ports.yaml)"
  else
    ok "port :$port free"
  fi
done

echo
echo "[setup] $PASS checks passed, $FAIL need attention."
if [ "$FAIL" -eq 0 ]; then
  echo "Next:"
  echo "  1. ./scripts/start_local_llm.sh        # boot the local model server"
  echo "  2. cd apps/api && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
  echo "  3. cd apps/web && npm run dev          # open http://localhost:5173"
  echo "  Model weights live in apps/api/.model_cache/ (via scripts/bootstrap.py) — never committed."
fi
exit "$FAIL"
