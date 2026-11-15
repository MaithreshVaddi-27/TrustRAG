#!/usr/bin/env bash
# Start the local services the backend benchmark needs, and wait until the API
# answers. Safe to re-run: it only starts what is not already listening.
#
# The children are started in their own session (see start_daemon). A plain
# `nohup cmd &` leaves the daemon in the caller's process group, so whatever
# cleans up that group when the launching shell exits takes the service with
# it — which is how the API disappeared mid-run during the B5 resilience
# check. A new session is immune to both.
set -u

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="/opt/homebrew/opt/python@3.12/libexec/bin/python3"
MONGODB_DIR="${MONGODB_DIR:-/tmp/mongodata}"

# start_daemon <logfile> <command...>
# Runs the command detached: its own session, no controlling terminal, stdout
# and stderr redirected to the log file. The child's pid is printed so the
# caller can record it.
start_daemon() {
  local log="$1"; shift
  "$PY" - "$log" "$@" <<'PYEOF'
import os
import subprocess
import sys

log_path, *cmd = sys.argv[1:]
with open(log_path, "ab", buffering=0) as log:
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,  # setsid(): own session + process group
        cwd=os.getcwd(),
    )
print(proc.pid)
PYEOF
}

# wait_for_http <url> [tries] — succeeds only on a 2xx/3xx answer.
# A bare `curl` without --fail also succeeds on a 500, which would report a
# broken API as healthy.
wait_for_http() {
  local url="$1" tries="${2:-60}" i=0
  while [ "$i" -lt "$tries" ]; do
    if curl -sf -o /dev/null --max-time 2 "$url"; then return 0; fi
    i=$((i + 1)); sleep 1
  done
  return 1
}

if ! mongosh --quiet --eval 'db.runCommand({ping:1}).ok' mongodb://localhost:27017 >/dev/null 2>&1; then
  mkdir -p "$MONGODB_DIR"
  start_daemon /tmp/mongod.log mongod --dbpath "$MONGODB_DIR" --port 27017 --logpath /tmp/mongod.log >/dev/null
  echo "started mongod"
  for _ in $(seq 1 30); do
    mongosh --quiet --eval 'db.runCommand({ping:1}).ok' mongodb://localhost:27017 >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! curl -sf -o /dev/null --max-time 2 http://127.0.0.1:11434/api/tags; then
  start_daemon /tmp/ollama.log ollama serve >/dev/null
  echo "started ollama"
fi

API_PID_FILE=/tmp/trustrag_api.pid

# A stale process can be holding the port while answering nothing (it was
# killed mid-request, or it is a leftover from a previous session). Health is
# the test that matters — if /health does not answer, the port is not serving.
if ! curl -sf -o /dev/null --max-time 2 http://127.0.0.1:8000/api/v1/health; then
  if [ -f "$API_PID_FILE" ]; then
    OLD_PID="$(cat "$API_PID_FILE" 2>/dev/null || true)"
    if [ -n "${OLD_PID}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
      echo "stopping the unresponsive api (pid $OLD_PID)"
      kill -TERM "$OLD_PID" 2>/dev/null || true
      sleep 2
      kill -KILL "$OLD_PID" 2>/dev/null || true
    fi
    rm -f "$API_PID_FILE"
  fi
  cd "$API_DIR" || exit 1
  API_PID="$(start_daemon /tmp/trustrag_api.log \
    "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning)"
  echo "$API_PID" > "$API_PID_FILE"
  echo "started api (pid $API_PID)"
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
