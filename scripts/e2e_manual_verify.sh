#!/usr/bin/env bash
# One-shot E2E manual verification: boots API+web, exercises the live flow,
# and prints PASS/FAIL per step. Servers are torn down at the end.
set -u
cd "$(dirname "$0")/.."   # repo root

PASS=0; FAIL=0
ok()  { echo "  PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

cleanup() {
  [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null
  [ -n "${WEB_PID:-}" ] && kill "$WEB_PID" 2>/dev/null
  wait 2>/dev/null
  echo ""
  echo "════════════════════════════════════════"
  echo "RESULT: $PASS passed, $FAIL failed"
}
trap cleanup EXIT

echo "── 1. Boot stack ──────────────────────────"
( cd apps/api && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning \
    > /tmp/trustrag_api.log 2>&1 ) &
API_PID=$!

( cd apps/web && npx vite --port 5173 --strictPort > /tmp/trustrag_vite.log 2>&1 ) &
WEB_PID=$!

for i in $(seq 1 40); do
  curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1 && break
  sleep 1
done
curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1 \
  && ok "API healthy on :8000" || { bad "API failed to start"; exit 1; }

for i in $(seq 1 20); do
  curl -sf http://localhost:5173/ >/dev/null 2>&1 && break
  sleep 1
done
curl -sf http://localhost:5173/ >/dev/null 2>&1 \
  && ok "Vite serving on :5173" || bad "Vite failed to start"

echo "── 2. Auth flow ───────────────────────────"
EMAIL="e2e-$(date +%s)@trustrag.dev"
REG=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Str0ng!Passphrase2026\",\"full_name\":\"E2E\"}")
echo "$REG" | grep -q '"email"' && ok "register returns profile (no token)" || bad "register: $REG"

LOGIN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Str0ng!Passphrase2026\"}")
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
[ -n "$TOKEN" ] && ok "login returns JWT (${#TOKEN} chars)" || bad "login failed: $LOGIN"

ME=$(curl -s http://127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN")
echo "$ME" | grep -q '"email"' && ok "auth/me resolves user" || bad "auth/me: $ME"

BADLOGIN=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" -d "{\"email\":\"$EMAIL\",\"password\":\"wrongpass\"}")
[ "$BADLOGIN" = "401" ] && ok "wrong password → 401" || bad "wrong password → $BADLOGIN"

echo "── 3. Knowledge base + document ───────────"
KB=$(curl -s -X POST http://127.0.0.1:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"E2E KB","description":"live verification"}')
KB_ID=$(echo "$KB" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
[ -n "$KB_ID" ] && ok "KB created: $KB_ID" || bad "KB create: $KB"

printf 'TrustRAG verification pipeline splits answers into atomic claims and checks each against retrieved evidence using natural language inference. Sources are audited with SHA-256 hashes. The system self-heals with bounded recovery attempts or safely abstains.' > /tmp/trustrag_e2e_doc.md
DOC=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/trustrag_e2e_doc.md")
DOC_ID=$(echo "$DOC" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
[ -n "$DOC_ID" ] && ok "document ingested: $DOC_ID" || bad "ingest: $DOC"

# Wait for async indexing (chunk count on the KB document record)
INDEXED=""
for i in $(seq 1 30); do
  DOC_STATUS=$(curl -s "http://127.0.0.1:8000/api/v1/documents/$DOC_ID" -H "Authorization: Bearer $TOKEN" \
    | python3 -c "import sys,json;print(json.load(sys.stdin).get('ingestion_status',''))" 2>/dev/null)
  [ "$DOC_STATUS" = "completed" ] && { INDEXED=yes; break; }
  sleep 1
done
[ -n "$INDEXED" ] && ok "document indexed" || bad "document never indexed (last=$DOC_STATUS)"

echo "── 4. Analysis run (no LLM required: abstains or answers) ──"
AN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/analyses \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"How does TrustRAG verify answers?\"}")
AN_ID=$(echo "$AN" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
[ -n "$AN_ID" ] && ok "analysis created: $AN_ID" || bad "analysis create: $AN"

FINAL=""
for i in $(seq 1 90); do
  STATUS=$(curl -s "http://127.0.0.1:8000/api/v1/analyses/$AN_ID" -H "Authorization: Bearer $TOKEN" \
    | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
  case "$STATUS" in
    completed|abstained|failed) FINAL=$STATUS; break ;;
  esac
  sleep 1
done
[ -n "$FINAL" ] && [ "$FINAL" != "failed" ] \
  && ok "analysis reached terminal state: $FINAL" \
  || bad "analysis did not settle (last=$STATUS)"

if [ -n "$FINAL" ] && [ "$FINAL" != "failed" ]; then
  CLAIMS=$(curl -s "http://127.0.0.1:8000/api/v1/analyses/$AN_ID/claims" -H "Authorization: Bearer $TOKEN")
  echo "$CLAIMS" | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'  claims persisted: {len(d)}')" \
    && ok "claims endpoint responds" || bad "claims: $CLAIMS"
  TRACE=$(curl -s "http://127.0.0.1:8000/api/v1/analyses/$AN_ID/trace" -H "Authorization: Bearer $TOKEN")
  echo "$TRACE" | grep -q '"event"' && ok "execution trace populated" || bad "trace: $(echo $TRACE | head -c 120)"
fi

echo "── 5. Ownership / authz ───────────────────"
OTHER_EMAIL="e2e-other-$(date +%s)@trustrag.dev"
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$OTHER_EMAIL\",\"password\":\"Str0ng!Passphrase2026\",\"full_name\":\"Other\"}" >/dev/null
TOKEN2=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$OTHER_EMAIL\",\"password\":\"Str0ng!Passphrase2026\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
CROSS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/v1/knowledge-bases/$KB_ID" \
  -H "Authorization: Bearer $TOKEN2")
[ "$CROSS" = "403" ] || [ "$CROSS" = "404" ] \
  && ok "cross-user KB access rejected ($CROSS)" \
  || bad "cross-user access returned $CROSS"

echo "── 6. UI smoke (Vite serves app shell) ────"
HTML=$(curl -s http://localhost:5173/)
echo "$HTML" | grep -qi '<div id="root">' && ok "SPA shell served" || bad "unexpected shell: $(echo "$HTML" | head -c 120)"
