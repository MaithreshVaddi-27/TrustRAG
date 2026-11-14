#!/usr/bin/env bash
# Start the local services the backend benchmark needs, and wait until the API
# answers. Safe to re-run: it only starts what is not already listening.
set -u

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="/opt/homebrew/opt/python@3.12/libexec/bin/python3"
MONGODB_DIR="${MONGODB_DIR:-/tmp/mongodata}"

wait_for_http() {
  local url="$1" tries="${2:-60}" i=0
  while [ "$i" -lt "$tries" ]; do
    if curl -s -o /dev/null --max-time 2 "$url"; then return 0; fi
    i=$((i + 1)); sleep 1
  done
  return 1
}

if ! curl -s -o /dev/null --max-time 2 http://127.0.0.1:27017 2>/dev/null; then
  if ! mongosh --quiet --eval 'db.runCommand({ping:1}).ok' mongodb://localhost:27017 >/dev/null 2>&1; then
    mkdir -p "$MONGODB_DIR"
    nohup mongod --dbpath "$MONGODB_DIR" --port 27017 --logpath /tmp/mongod.log >/dev/null 2>&1 &
    echo "started mongod"
  fi
fi

if ! curl -s -o /dev/null --max-time 2 http://127.0.0.1:11434/api/tags; then
  nohup ollama serve >/tmp/ollama.log 2>&1 &
  echo "started ollama"
fi

if ! curl -s -o /dev/null --max-time 2 http://127.0.0.1:8000/api/v1/health; then
  cd "$API_DIR" || exit 1
  nohup "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning \
    >/tmp/trustrag_api.log 2>&1 &
  echo "started api"
fi

for _ in $(seq 1 60); do
  if wait_for_http http://127.0.0.1:8000/api/v1/health 1; then
    echo "api is up"
    exit 0
  fi
done

echo "api did not come up — see /tmp/trustrag_api.log" >&2
tail -20 /tmp/trustrag_api.log >&2
exit 1
