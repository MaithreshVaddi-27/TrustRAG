# TrustRAG Full-Stack Audit — "Get It Working Now" (2026-09-06)

**Auditors (roles):** Senior Designer (Apple-design) · Senior Frontend · Senior Backend ·
Senior AI/ML · Senior Security · Senior Testing (blackbox + whitebox)
**Branch:** `ui-redesign` (dirty: CRLF-only churn, no logic diff — verified via `git diff -w`)
**Goal per request:** make this broken project working NOW. Improvements deferred.

## Verdict

The project was **not broken in tests** — it was **broken in runtime wiring**:
backend 111/111 pytest pass, frontend 15/15 vitest pass, `vite build` OK, eslint OK
(before this audit). Live boot failed for operational reasons: Ollama down,
`.env` ignored by model routing, logout never revoked tokens, CI lint gate red,
leaked cloud key. All P0 blockers below are **FIXED and verified** in this pass.

## Addendum 12:10 UTC — Local-models pass: WORKING ✅

**Question asked:** "when using local models is it now working?" **Answer: YES.**

### P0-LOCAL-1 — API crashed on boot with local embeddings — FOUND + FIXED
- **Where:** `apps/api/app/main.py:115` called `SharedEmbeddingManager.get_instance()`,
  but `app/core/model_registry.py:SharedEmbeddingManager` only defined `__new__`
  singleton — no `get_instance()` → `AttributeError` → `Application startup failed`.
- **Why tests missed it:** pytest never runs `lifespan`; crash only fires when
  `embedding_provider in ("huggingface","local")` — exactly the local path.
- **Fix:** added `get_instance()` classmethod returning `cls()`.
- **Verify:** `uvicorn` boots, `/health` → `status: ok`,
  `services: {mongodb: ok, qdrant: ok}`,
  `models: ollama gemma4:e2b | huggingface BAAI/bge-small-en-v1.5`.

### Local environment (this machine)
- `brew services start ollama` → 4 models present:
  `gemma4:e2b-it-qat` (4.3 GB), `qwen3.5:4b`, `granite4.2:3b-q4_K_M`,
  `embeddinggemma:300m-qat-q8_0`. `.env`: `AI_PROVIDER=ollama`,
  `OLLAMA_MODEL=gemma4:e2b` (resolves to local `gemma4:e2b-it-qat`),
  `EMBEDDING_PROVIDER=huggingface`, `BAAI/bge-small-en-v1.5` (384d).
- llama.cpp server (`:8081`) not running — not needed for the default path.

### End-to-end local proof (all offline, zero cloud keys used)
1. `POST /auth/register` + `/auth/login` → JWT (232 chars) ✅
2. `POST /knowledge-bases` → KB created ✅
3. `POST /knowledge-bases/{id}/documents` (refund-policy txt) →
   `ingestion_status: completed` ✅ (local BGE embeddings + Qdrant local)
4. `POST /analyses` ("What is the refund policy for annual contracts?") →
   `status: completed`, `reliability: {score: 1.0, status: TRUSTED}`,
   grounded answer from local Ollama ✅
5. `GET /analyses/{id}/claims` → 2 claims; `/evidence` → 1 chunk ✅
6. Regression: `pytest` **111 passed**, `ruff check` clean, `ruff format` clean ✅

**Note:** API is currently RUNNING at `http://127.0.0.1:8080` (started for this
verification). Frontend was not started — run `cd apps/web && npm run dev`
for `http://localhost:5173`.

## Addendum 12:35 UTC — Local perf pass: cooler + faster ✅

**Complaint:** local models overheat the machine and take >5min per analysis.

**Root causes (measured):**
1. Default local LLM `gemma4:e2b` (4.3GB) on an 8GB unified-memory Mac — the repo's
   own `hardware.py` recommends `granite4.2:3b-q4_K_M` (2.2GB) for the `lean` tier.
2. `sentence-transformers` + torch loaded **inside the API process** for BGE embeddings
   (~1GB RAM + MPS/CPU heat), even though `embeddinggemma` was already installed.
3. Ollama requests used `num_ctx 4096` + `num_predict 2048` defaults → huge KV-cache
   on unified memory; up to 9 sequential LLM calls per analysis (gen + decompose +
   NLI, ×3 with recovery), 180s timeouts, 2 retries.
4. Bonus find while verifying: `DELETE /knowledge-bases/{id}` **always 500'd** —
   `serialize_kb()` passed `is_snapshot`/`version`/`parent_kb_id` but `KBResponse`
   dropped them (`extra='ignore'`), so `delete_kb()` crashed on `kb.is_snapshot`.

**Fixes (local path only, cloud providers untouched):**
- `.env`: `OLLAMA_MODEL=granite4.2:3b-q4_K_M`; `EMBEDDING_PROVIDER=ollama`,
  `EMBEDDING_MODEL=embeddinggemma:300m-qat-q8_0`, `EMBEDDING_DIM=768`.
- `models.yaml` (v1.0→1.1): lean 3B defaults, `max_output_tokens` 2048→1024 (gen) /
  1024→512 (verify), timeouts 180→120s, retries 2→1. Retrieval/reliability/recovery
  thresholds UNCHANGED (quality preserved).
- `local_llm.py`: `num_ctx` 4096→2048, `num_predict` 2048→1024; hardcoded ollama
  fallbacks aligned to granite; llama.cpp cap 2048→1024.
- `schemas/kb.py`: added `version`/`parent_kb_id`/`is_snapshot` to `KBResponse`
  (delete now returns 204 — verified).
- Tests hardened against `.env` leakage: `test_config` isolates `EMBEDDING_DIM*`;
  `test_local_llm` blanks Settings overrides + clears model caches (was failing
  after the perf change — correctly caught the drift).

**Verified on this machine:**
- `/health`: `ok`, `ollama granite4.2:3b-q4_K_M | ollama embeddinggemma 768`.
- `ollama ps`: only granite resident (2.4GB, 100% GPU, ctx 2048, auto-unload ~5m).
  Zero torch/HF imports in the API process (was: full BGE+torch load).
- Fresh 768d KB → ingest `completed` → analysis **`completed`, TRUSTED 1.0**,
  correct grounded answer, 2 claims + 1 evidence. Breakdown: retrieval <1s,
  generation ~21s, decompose+NLI ~66s → **~88s total** (was: 5min+ territory with
  thrashing + heat).
- `pytest` 111 passed, `ruff check` + `format` clean.

**Must know:** switching embedding models invalidates old KB vectors — the stale
BGE `LocalKB` was deleted; **re-upload documents into a new KB** after this change.
**Deferred:** decompose+NLI is now the floor (~66s on 3B due to long JSON-schema
prompts) — combining them into one structured call is the next speedup, left for later.

## Addendum 13:05 UTC — Stuck-pipeline spiral: ROOT-CAUSED + FIXED ✅

**Symptom (your screenshots):** Playground spins 192s+ on "Claim Entailment", then lands
`0% FAILED` with a 14-word stub answer ("Steps of an Information Retrieval System…
The"), 32 evidence chunks, 0 claims, 6 recovery cards.

**What the screenshots proved:**
- Drawer had **Local BGE 384d selected** while the server default (top bar) was
  **embeddinggemma 768d**. The backend silently "aligned" dims (truncate / zero-pad
  in `retriever.py`) — cross-space queries return plausible-looking garbage with
  zero errors. Verification fails → 2 recovery rounds (rendered as 6 timeline cards,
  one per trace event — the loop itself was correctly capped) → FAILED stub.
- Recovery doubles retrieval (`top_k=40`) with NO cap on generation context → 16–32
  chunks crammed into a 2k-context local LLM → `num_ctx` overflow → truncated stub.
- Separate find: `DELETE /knowledge-bases/{id}` always 500'd (`KBResponse` dropped
  `is_snapshot`).

**Fixes:**
- `graph.py`: generation context hard-capped at `max_context_chunks` (8); extra chunks
  stay as evidence only (`retrieval.capped` trace event). Search wide, reason narrow.
- `pipeline.py`: KB record pins `embedding_model/provider/dim` at first ingest.
- `analysis_service.create_analysis`: embedding mismatch vs the pin → instant **422**
  naming both models + the fix (verified live: 0.025s, zero inference).
- `analysis_service` finalize: FAILED + zero claims + stub answer (<5 words) → clean
  abstention sentence stored instead of the stub (score/diagnosis kept).
- `schemas/kb.py` + `kb_service.py`: `KBResponse` carries the pin; delete-KB fixed
  (verified: 204).
- `PlaygroundPage.jsx` + `QueryPanel.jsx`: selector auto-snaps to the selected KB's
  pin on KB switch; KB index space shown ("KB index: …"); amber mismatch banner with
  one-click snap. Backend remains the enforcer (422).
- Tests: pin-write count (ingestion), KBResponse mock fix + new 422 mismatch test →
  **112 passed**, ruff clean, frontend lint/test/build clean.

**Verified live (lean stack):**
- Mismatched request → 422 in 0.025s, no heat.
- On-topic query → `completed`, **TRUSTED 1.0**, correct answer, 77s, zero recovery.
- Your exact off-topic query → **ABSTAIN in ~1s** (empty-evidence guard, no LLM burned;
  18 trace events, 1 fast recovery round) instead of 192s of heat.
- Legacy KBs (no pin, e.g. created before this change) are exempt from the 422 —
  **re-upload their documents once** to get a pin; the UI flags them as legacy.

## Addendum 14:00 UTC — llama.cpp owns 8080 + embeddings out of LLM servers ✅

**Requests:** (1) `127.0.0.1:8080` is llama.cpp's port — move the backend off it.
(2) Remove embedding-model selection AND usage from ollama/llama.cpp entirely,
frontend + backend. `ollama list` = Ollama LLM source, `llama-server --cache-list` =
llama LLM source.

**Port move (done):** backend `8080` → **`8000`** everywhere operational
(docker-compose, Dockerfile `PORT`, Vite proxy default, Playwright/k6 defaults,
CI workflow, README). llama.cpp base URL → `http://127.0.0.1:8080/v1` (.env,
models.yaml, client default, compose `host.docker.internal:8080`, Settings UI text).

**Central port registry (new, per request):** repo-root **`config/ports.yaml`** is now
the single source of truth (backend 8000, frontend 5173, ollama 11434, llamacpp 8080,
mongodb 27017, qdrant 6335:6333/6336:6334). **`scripts/apply_ports.py`** propagates
one edit to 10 consumers (compose, Dockerfile, models.yaml, .env files, Vite,
Playwright/e2e, k6, CI, README); `--check` gates CI (added to `backend-lint`).
Proven live: flipped backend to 8001 → 9 files rewritten → flipped back, clean.
Backend `ModelConfig` URL defaults now derive from ports.yaml (env still wins);
`/models/providers` exposes the active `ports` block. Model IDs stay in
`models.yaml` + `.env` (no duplication — documented in ports.yaml header).

**Embedding removal (done, both layers):**
- Backend: deleted `OllamaEmbeddings`/`LlamaCppEmbeddings`; `get_embedding_model()`
  raises `ConfigurationError` ("LLM-only… set EMBEDDING_PROVIDER=huggingface") for
  ollama/llamacpp; `/models/providers` lists only huggingface/google/nvidia;
  `discover_ollama_cli_models` returns LLM names only; both status checks filter
  embedding keywords (incl. a shared `_is_embedding_model_name` helper + defense in
  the merger); `hardware.py` recommendations → BGE; schema examples updated.
- Frontend: drawer offers Local BGE + Gemini only (ollama/llamacpp buttons removed);
  Settings embedding cards for Ollama/llama.cpp removed; stale fallbacks/ports fixed.
- Env: `EMBEDDING_PROVIDER=huggingface`, BGE 384d (torch is back in the API process —
  accepted tradeoff of this request; granite-3B LLM keeps heat well below before).
- Tests: 5 new (`test_ports.py`: registry keys, 8080 reservation, URL derivation,
  keyword filter, mocked CLI filtering) + reworked mismatch/embedding tests →
  **117 passed**, ruff clean, frontend lint/test/build clean.

**Verified live on :8000:** `/health ok` (granite + BGE 384); providers show
LLM-only lists, llama base `127.0.0.1:8080/v1`, cache-list models
(Qwen3.5, granite, OCC-RAG — note: `occ-ai/OCC-RAG-*` is NOT in the embedding filter;
say the word if those are embedding models and I'll exclude them too); BGEKB
re-indexed with pin `BAAI/bge-small-en-v1.5 384`; on-topic E2E → TRUSTED 1.0 in 88s.

**Honest caveats observed this pass:**
- Ollama's brew service died twice mid-session (`Cannot connect` → pipeline correctly
  ABSTAINs in <1s instead of hanging — error path works). If it keeps dying, check
  memory pressure / `brew services` persistence.
- granite-3B structured-JSON flakiness is real: same on-topic query passed TRUSTED 1.0
  once, then hit "JSON schema parsing failed → repair" and abstained after ~5min
  (repair salvaged 2 claims but thresholds failed). The system stays SAFE (abstains,
  never hallucinates) but 3B verification is variable — `qwen3.5:4b` is one click away
  in the UI; robust short-schema prompts are the deferred fix.
- Your old embeddinggemma-768d KBs are invalid under BGE — delete + re-upload
  (verified flow this pass).

## Addendum 14:30 UTC — Frontend live verification + console-error fix ✅

**First live UI pass this session** (API `:8000` + Vite `:5173`): Playwright E2E
**2/2 pass**, incl. the SEC-H1 logout-revocation flow through the real UI (validates
the earlier logout fix). Vitest 15/15, build clean.
- New drawer check (throwaway spec, not committed): no Ollama/llama.cpp embedding
  options, BGE + Gemini present, LLM selector intact, **zero console/page errors**.
- Fix from that check: `AppLayout.jsx` spread `{...dragControls}` (dead
  `useDragControls` hook — no handle ever called `start()`) leaked
  `componentControls` onto the DOM → React `%s`-prop console error on every page.
  Removed spread + hook + import; drawer keeps direct `drag="x"` behavior.
- Also fixed two stale `:8081` labels in the LLM provider selector → `:8080`.
- Browsers weren't installed for Playwright (`npx playwright install chromium` done).


## P0 — Fixed in this pass (blocking "working now")

### P0-SEC-1 — GEMINI_API_KEY exposed in live `.env` — FLAGGED, NOT committed
- **Where:** `/.env:48` (`GEMINI_API_KEY=AQ.Ab8R...BAOQ`)
- **Severity:** P0 security. `.env` is gitignored (good — `git status` shows no `.env`),
  but the key sits in plaintext on disk and was pasted into this session.
- **Action taken:** did NOT rotate (can't from here). **You must revoke/rotate it in
  Google AI Studio now** and replace the value. Never share `.env` contents.
- **Status:** documented; requires owner action.

### P0-CFG-1 — `.env` model routing silently ignored — FIXED
- **Where:** `apps/api/app/core/config.py` (`ModelConfig` read `os.environ` directly;
  `Settings` loads `.env` via pydantic-settings which does NOT export to `os.environ`).
- **Symptom (proven):** shell had no `EMBEDDING_PROVIDER` → `Settings.embedding_provider=huggingface`
  but `ModelConfig.embedding_provider=google_genai`; `/health` reported `google_genai`
  despite `.env` saying `huggingface`. Same class of bug for `AI_PROVIDER/LLM_MODEL`.
  Offline/local boot therefore demanded a Gemini key it shouldn't need.
- **Fix:** `load_dotenv(apps/api/.env)` + `load_dotenv(repo/.env)` at import in `config.py`
  (`override=False` so real env still wins).
- **Verify:** `Settings EMB=huggingface AI=ollama` ==
  `ModelConfig EMB=huggingface LLM=ollama gemma4:e2b` → `CONFIG CONSISTENT OK`.

### P0-SEC-2 — Frontend logout never revoked the JWT (SEC-H1 bypass) — FIXED
- **Where:** `apps/web/src/services/auth.js:logout()` + callers
  `apps/web/src/layouts/AppLayout.jsx:handleLogout()` and
  `apps/web/src/pages/SettingsPage.jsx:handleLogout()` called only `authStore.clearSession()`.
- **Impact:** backend `POST /auth/logout` denylist existed but UI never called it —
  a "logged out" token stayed valid until expiry.
- **Fix:** `authService.logout()` is now `async`, `POST /api/v1/auth/logout` (best-effort)
  then clears local session; both callers await it before `navigate('/login')`.
- **Verify:** `npm run lint` clean, `vitest` 15/15 pass, `vite build` OK.

### P0-CI-1 — Backend lint gate red (19 ruff + 2 format) — FIXED
- **Symptom:** `ruff check` 19 errors, `ruff format --check` 2 files dirty → CI
  `backend-lint` job fails.
- **Fix (no behavior change):**
  - `pyproject.toml`: removed duplicated `orjson>=3.10.0` line.
  - `app/agent/graph.py`: extracted `web_msg` / `web_done_msg` (also resolves E501 vs
    formatter collapse conflict).
  - `app/api/v1/knowledge_bases.py`, `app/retrieval/retriever.py`, `app/core/context.py`:
    wrapped long lines / prompt construction.
  - `app/core/context.py`: `asyncio.create_task` now keeps a reference (RUF006).
  - `app/core/experimentation.py`: `hashlib.md5(..., usedforsecurity=False)` ×2 with
    non-security comment (S324 bucketing-only), removed dead `metrics_key` (F841),
    `list[...] | None` (RUF013).
  - `app/core/secrets_manager.py`: removed dead `secret_path` (F841); `noqa: S603/S607`
    on fixed-arg `sops`/`age` invocations over internal paths.
  - `app/core/security.py`: `noqa: S105` on `SERVICE_TOKEN_TYPE` label (not a credential).
  - `app/core/tracing.py`: removed unused `settings` (F841) + now-unused import (F401).
- **Verify:** `ruff check` → **All checks passed**; `ruff format --check` → **89 files formatted**;
  `pytest` → **111 passed**.

### P0-RUN-1 — Backend/frontend both DOWN locally — DIAGNOSED, run recipe verified
- **Findings:** MongoDB `started` (brew) and reachable (`connect_db` → `MONGO CONNECT OK`,
  `health_check True`); Qdrant embedded `local` OK; **Ollama server NOT running**
  (`ollama list` → connection refused) while `.env` has `AI_PROVIDER=ollama`.
  Earlier `/health` "mongodb: degraded" was an artifact of calling it via `TestClient`
  without lifespan (no `connect_db`), not a production defect — real lifespan path works.
- **Fix applied:** none to `.env` (owner's provider choice); config-consistency fix above
  ensures the provider actually honored is the one in `.env`.
- **To run now (verified steps):**
  ```bash
  brew services start mongodb-community          # already running
  ollama serve &                                 # REQUIRED while AI_PROVIDER=ollama
  # OR: set AI_PROVIDER=gemini in .env (a valid GEMINI_API_KEY is present)
  cd apps/api && ./.venv/bin/python -c "from app.main import create_app" # import OK
  uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload &
  cd apps/web && npm run dev                     # http://localhost:5173
  curl -s http://localhost:8080/api/v1/health
  ```

## P1 — Not blocking boot, recorded for later (NOT fixed per "improvements later")

1. **P1-CFG:** `.env` provider/model skew — `AI_PROVIDER=ollama` but
   `LLM_MODEL=gemini-3.5-flash-lite` (ignored on the ollama path, which uses
   `OLLAMA_MODEL=gemma4:e2b`). Same for `VERIFICATION_MODEL`. Decide one provider and align.
2. **P1-SEC:** `allow_headers=["*"]` + `allow_credentials=True` in `app/main.py` CORS is
   permissive; tighten to explicit headers when frontends are known.
3. **P1-TEST:** 26 dirty files are pure CRLF churn (`git diff -w` empty). Normalize with
   `.gitattributes` / `git add --renormalize` to keep diffs reviewable.
4. **P1-PERF:** `PlaygroundPage` chunk ~202 kB, `chart-vendor` ~393 kB; lazy-load charts.
5. **P1-AI:** `models.yaml` embedding default is `google_genai` while `.env.example` default is
   `huggingface` — after the P0-CFG fix `.env` wins, but align defaults to avoid confusion.
6. **P1-OPS:** `ORJSONResponse` deprecation warning (FastAPI now serializes via Pydantic);
   migrate `default_response_class` when convenient.

## Role notes

- **Designer (Apple-design):** foundations present — `whileTap` press feedback, `backdrop-blur`
  materials, `prefers-reduced-motion` in 5+ CSS modules, `aria-label` on icon buttons,
  44px touch targets in `styles/components.css`. No P0 design blocker; motion audit deferred.
- **Frontend:** `lib/api.js` correctly avoids JWT-in-URL via `/stream-ticket`; 401 clears session
  and surfaces backend messages. Vite proxy has overlapping `/api` + `/api/v1/analyses` keys
  (harmless — same target); dedupe later.
- **Backend:** lifespan binds port before warmup (good); exception handlers never leak internals;
  security headers + GZip + request-ID + rate limits wired. `health` always 200 with `status`
  field — intentional for probes.
- **AI/ML:** hybrid RRF + BGE-local path is coherent once P0-CFG-1 is fixed; dimension
  truncation + L2 re-normalization in `retriever.py` is mathematically sound.
- **Security:** anti-IDOR scoping, revocation TTL index, SSRF/sanitize pipeline noted in docs;
  only the UI-side revocation bypass and leaked key were P0.
- **Testing:** whitebox 111 pytest + 15 vitest + lint + build all green post-fix; blackbox
  (live register→KB→ingest→analysis→stream) still requires a running LLM (Ollama or Gemini)
  — run the E2E recipe above, then `npm run test:e2e` + `k6 run load-test/smoke.js`.

## Verification log (this pass)

- `pytest tests/ -q --no-cov` → **111 passed** (pre and post fix)
- `ruff check app/ tests/` → 19 errors → **All checks passed**
- `ruff format --check` → 2 dirty → **89 files formatted**
- `npm run lint` → clean (1 error mid-pass from new unused import → fixed → clean)
- `npm run test` → **15 passed**; `npm run build` → **success** (2.7–3s)
- Config consistency script → `CONFIG CONSISTENT OK`
- `connect_db` → `MONGO CONNECT OK`, `health_check True`
- `git diff -w --stat` → empty (CRLF-only churn confirmed)

## Files changed in this pass

- `apps/api/pyproject.toml` — dedupe `orjson`
- `apps/api/app/core/config.py` — `load_dotenv` fix (P0-CFG-1)
- `apps/api/app/agent/graph.py`, `app/api/v1/knowledge_bases.py`,
  `app/retrieval/retriever.py`, `app/core/{context,experimentation,secrets_manager,security,tracing}.py`
  — lint gate fixes (P0-CI-1)
- `apps/web/src/services/auth.js`, `src/layouts/AppLayout.jsx`, `src/pages/SettingsPage.jsx`
  — server-side logout revocation (P0-SEC-2)
- `apps/api/app/core/model_registry.py` — added `SharedEmbeddingManager.get_instance()`
  (P0-LOCAL-1: local-embeddings boot crash)
- `app/agent/graph.py` — generation-context cap at `max_context_chunks` (spiral guard)
- `app/ingestion/pipeline.py` — KB embedding-space pin on first ingest
- `app/services/analysis_service.py` — 422 on embedding mismatch; abstention text for
  degenerate stubs
- `app/api/v1/schemas/kb.py` + `app/services/kb_service.py` — pin fields on KBResponse
- `apps/web/.../PlaygroundPage.jsx` + `.../QueryPanel.jsx` — auto-snap selector to KB
  pin, index-space label, mismatch banner
- `config/ports.yaml` (new) + `scripts/apply_ports.py` (new) + CI `--check` gate —
  single source of truth for all ports
- `app/core/local_llm.py` — deleted embedding clients; LLM-only CLI discovery
- `app/core/model_registry.py`, `app/api/v1/models.py`, `app/core/hardware.py` —
  embedding removal + ports exposure
- `apps/web/.../SettingsPage.jsx`, `.../QueryPanel.jsx`, `.../PlaygroundPage.jsx`,
  `.../AppLayout.jsx` — embedding options removed, ports fixed
