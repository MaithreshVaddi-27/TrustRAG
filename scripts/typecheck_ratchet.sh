#!/usr/bin/env bash
# mypy ratchet (N-94): mypy was configured but never run, so its error backlog
# was invisible. This runs mypy and fails only when the error count EXCEEDS the
# committed ceiling — the ceiling ratchets down as errors are fixed.
#
# Usage: scripts/typecheck_ratchet.sh [ceiling]
set -uo pipefail
cd "$(dirname "$0")/../apps/api"

CEILING_FILE="mypy-error-ceiling.txt"
if [ $# -ge 1 ]; then
  CEILING="$1"
else
  CEILING="$(cat "$CEILING_FILE" 2>/dev/null || echo 0)"
fi

PY="${PYTHON:-.venv/bin/python}"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

OUTPUT="$("$PY" -m mypy --python-version 3.12 app/ 2>&1)"
COUNT="$(printf '%s\n' "$OUTPUT" | grep -cE '^(app|apps)/.*: error:' || true)"

echo "$OUTPUT" | tail -1
echo "mypy errors: ${COUNT} (ceiling ${CEILING})"

if [ "$COUNT" -gt "$CEILING" ]; then
  echo "FAIL: mypy error count exceeds the committed ceiling."
  echo "Fix errors, or (deliberately) raise $CEILING_FILE."
  exit 1
fi
echo "PASS: no new type errors."
