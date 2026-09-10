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

echo "─ Toolchain ─"
if command -v python3 >/dev/null 2>&1; then ok "python3 $(python3 --version 2>&1 | cut -d' ' -f2)"; else warn "python3 not found" "Install Python 3.11+ (https://python.org)"; fi
if command -v node >/dev/null 2>&1; then ok "node $(node --version)"; else warn "node not found" "Install Node.js 20+ (https://nodejs.org)"; fi
if command -v npm >/dev/null 2>&1; then ok "npm $(npm --version)"; else warn "npm not found" "Ships with Node.js 20+"; fi

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
  warn "apps/api/.venv missing" "Run: cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\""
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
  warn "MongoDB not reachable on :27017" "macOS: brew services start mongodb-community  |  Linux: sudo systemctl enable --now mongod"
fi
if (echo > /dev/tcp/localhost/11434) 2>/dev/null; then
  echo "  • Ollama detected on :11434 (optional)"
fi
if (echo > /dev/tcp/127.0.0.1/8080) 2>/dev/null; then
  echo "  • llama-server detected on :8080 (optional)"
else
  echo "  • llama-server not running — start it before analyses: ./scripts/start_local_llm.sh"
fi

echo "─ Ports ─"
for port in 8000 5173; do
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
  echo "  Embeddings (BAAI/bge-small-en-v1.5, ~120MB) download automatically on first boot."
fi
exit "$FAIL"
