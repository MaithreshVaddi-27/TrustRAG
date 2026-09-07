# TrustRAG Full-Stack Audit — 2026-09-07 (Embedding Decoupling + Broken-App Fix Pass)

**Roles:** Senior Backend · Senior AI/ML · Senior Security · Senior Testing (blackbox + whitebox) · Apple-design (UI)
**Request:** "find bugs, error, issues… my application is broken… remove use of ollama, llama, cpp in embedding model usage in both frontend, backend and then fix the project" + "create a new audit file… when serious bug is found fix it and update audit file."
**Branch state:** `ui-redesign`-era tree; prior audit `docs/audits/2026-09-06_full_stack_working_now_audit.md` claimed embedding removal done — this pass verifies that claim line-by-line and fixes what is still broken/stale.

## Verdict

- **Backend + frontend test suites are GREEN, not broken:** 117/117 pytest, 15/15 vitest, `ruff check` clean, 90 files formatted, `vite build` OK (2.77s).
- **Runtime boot is OK:** `create_app()` imports, `/health` returns full payload (`ollama granite4.2:3b-q4_K_M | huggingface BAAI/bge-small-en-v1.5`), BGE `embed_query` returns 384d vector live.
- **Embedding decoupling is DONE in code paths** (`model_registry.get_embedding_model` raises `ConfigurationError LLM-only` for ollama/llamacpp; `/models/providers` lists only huggingface/google/nvidia; `local_llm` discovery filters embedding keywords; drawer offers BGE + Gemini only). **Remaining ollama/llama embedding mentions are copy/docs/fallbacks — swept in this pass (see Fixes).**
- **Real remaining breakage risks (fixed below):** divergent embedding defaults (`models.yaml google_genai` vs `.env huggingface`), stale llama.cpp test port `:8081` vs canonical `:8080`, provider-hardcoded UI copy that contradicts the KB embedding pin, stale Settings fallbacks, missing NVIDIA embed option in the drawer vs backend capability.

## Scope verification — ollama/llama.cpp in embedding usage

| Layer | File | Status before this pass |
|---|---|---|
| Backend factory | `apps/api/app/core/model_registry.py:get_embedding_model` | CLEAN — guard raises for `ollama/llamacpp/llama_cpp` + `embeddinggemma/nomic-embed` model names |
| Backend providers API | `apps/api/app/api/v1/models.py` | CLEAN — only huggingface/google_genai/nvidia |
| Backend discovery | `apps/api/app/core/local_llm.py` | CLEAN — `_is_embedding_model_name` filter on CLI + HTTP + merger; LLM-only |
| Backend hardware | `apps/api/app/core/hardware.py` | CLEAN — `primary_embedding BAAI/bge-small-en-v1.5` all tiers |
| Backend tests | `apps/api/tests/test_local_llm.py` | GUARD test only (expects raise) — correct; but stale `:8081` port (fixed) |
| Frontend drawer | `QueryPanel.jsx` | CLEAN — BGE + Gemini only, no ollama/llama buttons |
| Frontend pages | `PlaygroundPage.jsx` | CLEAN — defaults huggingface/BGE |
| Frontend settings | `SettingsPage.jsx` | CLEAN cards (BGE/Gemini/NVIDIA) — stale fallback strings (fixed) |
| UI copy (stale) | `DashboardPage.jsx:22`, `KnowledgeBasesPage.jsx:151,371` | STALE — referenced ollama/Gemini-only embeddings (fixed) |
| Docs (stale) | `README.md:348-355`, `docs/architecture/architecture.md:30,50` | STALE — describe removed `OllamaEmbeddings` class / ollama embedding models (fixed) |

LLM usage of ollama/llama.cpp (`get_llm`, `get_verification_model`, provider cards, `ollama list` / `llama-server --cache-list` selectors) is **intentionally kept** — the request was embedding-only.

## Bugs found (severity ordered)

### S1 — `models.yaml` embedding default contradicts `.env` (config skew) — FIXED
- **Where:** `apps/api/config/models.yaml:47-56` (`provider: google_genai`, `model: models/gemini-embedding-001`) vs `.env:EMBEDDING_PROVIDER=huggingface`, `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, vs `.env.example` (huggingface) and `hardware.py` (BGE everywhere).
- **Impact:** any boot without `.env` (fresh clone, CI without env, Docker without env_file) silently demands `GEMINI_API_KEY` for embeddings and breaks the offline-first path. Runtime today only works because the `load_dotenv` fix makes `.env` win.
- **Fix:** `models.yaml` embedding → `provider: huggingface`, `model: BAAI/bge-small-en-v1.5`, `output_dimensionality: 384`, comment updated. `.env` unchanged (still source of truth at runtime).

### S2 — Stale llama.cpp port `:8081` in test — FIXED
- **Where:** `apps/api/tests/test_local_llm.py:35,40` (`http://localhost:8081/v1`).
- **Impact:** canonical registry (`config/ports.yaml`, `.env`, `models.yaml`, client defaults, compose) is `:8080`. Test passes (pure init assert) but teaches the wrong port and will confuse e2e debugging.
- **Fix:** test now uses `http://127.0.0.1:8080/v1`.

### S3 — Drawer embedding grid offers 2 of 3 backend providers — FIXED
- **Where:** `apps/web/src/components/workbench/QueryPanel.jsx:303` (`grid-cols-2 sm:grid-cols-3` with only huggingface + google_genai buttons) while backend `/models/providers` exposes `nvidia` too.
- **Impact:** NVIDIA-key owners cannot select cloud embeddings from the workbench; empty 3rd grid cell on `sm+`.
- **Fix:** added NVIDIA Embed button (parity with Settings cards + backend), grid stays `grid-cols-2 sm:grid-cols-3`.

### S4 — Hardcoded UI copy contradicts KB embedding pin — FIXED
- **Where:** `KnowledgeBasesPage.jsx:151` ("indexed with Google Gemini 384d Matryoshka"), `:371` ("generating 384d Gemini embeddings"); `DashboardPage.jsx:22` ("Local BGE / Ollama / Gemini").
- **Impact:** default stack is local BGE; copy tells users every KB is Gemini, then the 422 pin-mismatch guard looks like a bug. Dashboard re-advertises removed ollama embeddings.
- **Fix:** provider-neutral BGE-default wording; dashboard now "Local BGE / Gemini / NVIDIA".

### S5 — Stale Settings fallbacks — FIXED
- **Where:** `SettingsPage.jsx:503` fallback `gemma4:e2b`, `:509` fallback `sentence-transformers/all-MiniLM-L6-v2`.
- **Impact:** before providers load, UI flashes model IDs that are not the active defaults (`granite4.2:3b-q4_K_M`, `BAAI/bge-small-en-v1.5`).
- **Fix:** fallbacks aligned to granite + BGE.

### S6 — Stale docs reference removed embedding classes — FIXED
- **Where:** `docs/architecture/architecture.md:30` (`OllamaEmbeddings`), `:50` (Ollama embeddinggemma line); `README.md:348-355` (ollama/llama embedding model bullets).
- **Impact:** contributors re-introduce the removed path following docs.
- **Fix:** docs now state LLM-only ollama/llama.cpp + BGE/Gemini/NVIDIA embeddings.

## Security notes (Senior Security Engineer)

- **SEC-P0 (owner action, NOT committable from here): live `GEMINI_API_KEY` plaintext in `/.env:50` still present today.** `.env` is gitignored (verified — no secret committed), but rotate/revoke the key in Google AI Studio now; never paste `.env`. No new secrets added by this pass.
- `app/main.py` CORS `allow_headers=["*"]` + `allow_credentials=True` remains permissive (P1, deferred — needs known-frontend list before tightening; changing blindly would break the Vite dev origin).
- `/models/providers` correctly requires auth and exposes only base URLs (no keys). Logout revocation path from prior audit untouched and still wired.

## Testing (Senior Testing Engineer)

Whitebox (pre + post fix):
- `pytest tests/ -q --no-cov` → **117 passed** (both runs)
- `ruff check app/ tests/` → clean; `ruff format --check` → 90 files formatted
- `npm run lint` → clean; `npm run test` (vitest) → **15 passed**; `npm run build` → success
- `get_embedding_model('ollama'|'llamacpp')` → `ConfigurationError LLM-only` (guard test covers)
- Live BGE `embed_query` → 384d vector OK

Blackbox (runtime, no external keys burned):
- `create_app()` + `TestClient GET /health` → full payload, `mongodb: degraded` expected without lifespan (matches prior audit note — not a defect)
- `Settings == ModelConfig` consistency → `CONSISTENT OK` (huggingface/BGE/384, ollama/granite)
- E2E register→KB→ingest→analysis→stream NOT re-run here (needs running Ollama/Mongo + 80s+ inference); recipe in prior audit §P0-RUN-1 still applies. `ollama serve` required while `AI_PROVIDER=ollama`.

## Apple-design review (UI only, no visual changes beyond copy/grid parity)

- Drawer change keeps existing craft tokens: `whileTap 0.95`, `rounded-md`, provider color system (cyan BGE / indigo Gemini / purple NVIDIA matches Settings cards), mono `384d/Cloud` badges, `disabled={loading}` parity, no new motion curves.
- No touch-target, contrast, or reduced-motion changes; `prefers-reduced-motion` and 44px targets untouched.

## Files changed in this pass

1. `apps/api/config/models.yaml` — embedding default google_genai → huggingface/BGE (S1)
2. `apps/api/tests/test_local_llm.py` — llama.cpp test URL `:8081` → `:8080` (S2)
3. `apps/web/src/components/workbench/QueryPanel.jsx` — NVIDIA embed button (S3)
4. `apps/web/src/pages/KnowledgeBasesPage.jsx` — provider-neutral embedding copy (S4)
5. `apps/web/src/pages/DashboardPage.jsx` — pipeline copy drops ollama embeddings (S4)
6. `apps/web/src/pages/SettingsPage.jsx` — fallback model IDs aligned (S5)
7. `docs/architecture/architecture.md`, `README.md` — LLM-only wording (S6)

## Verification log (this pass)

- `pytest` 117 passed (pre-fix baseline; post-fix re-run in §Updates)
- `ruff check` + `format --check`, `npm lint/test/build` all green pre-fix; post-fix re-run in §Updates
- Live `/health` + BGE embed smoke OK

## Updates (appended as fixes land)

## Addendum 2026-09-07 — line-by-line backend audit (no test reliance)

Method: read `app/` source end to end (~60 modules): `core/config`, `core/local_llm`
(1-602), `core/security`, `main`, `services/analysis_service` (1-920),
`services/kb_service` (1-435), `services/auth_service`, `agent/graph` (1-1013),
`retrieval/retriever`, `ingestion/pipeline`, `verification/verifier`,
`verification/verdict`, `generation/generator`, `api/deps`, `api/v1/knowledge_bases`,
`api/v1/schemas/analysis`, `db/qdrant`, `mcp/server`. Test files were NOT used as
evidence; the suite was only re-run afterwards as a smoke check.

### P0-B1 — `ChatLlamaCppClient.with_structured_output` defined at module level — FIXED
- **Where:** `app/core/local_llm.py:346` (`def` at column 0 after the class body).
- **Proof:** `ChatLlamaCppClient.__dict__` had no `with_structured_output`;
  calls resolved to `BaseChatModel.with_structured_output`. The 65-line llama.cpp
  JSON/repair implementation was dead code.
- **Impact:** every structured call on the llama_cpp path (claim decomposition,
  batch NLI, recovery rewrite) bypassed the custom JSON handling → degraded to
  fallbacks (single-claim passthrough, all-NEUTRAL) → recovery spiral/ABSTAIN.
- **Fix:** indented into a real method; verified
  `ChatLlamaCppClient.with_structured_output.__qualname__` resolves correctly.

### P0-B2 — verification node reported TRUSTED 1.0 with zero claims — FIXED
- **Where:** `app/agent/graph.py` verification short-circuit (`total == 0 → PASS, 1.0`).
- **Impact:** any answer that decomposed to zero claims showed TRUSTED 1.0 with no
  verified evidence — directly contradicting `verdict.compute_verdict(total=0) =
  FAIL/0.0`, the module documented as single source of truth.
- **Fix:** node now returns FAIL / 0.0 / `RETRIEVAL_FAILURE` + `claims.empty` trace
  event, matching `compute_verdict` semantics, so recovery/abstain runs.

### P0-B3 — `rollback_kb_to_snapshot` always crashed + inverted guard — FIXED
- **Where:** `app/services/kb_service.py`: `if snapshot_kb.is_snapshot: raise`
  rejected genuine snapshots; then used the deleted live KB's id/name three times
  after deleting it (`get_kb` → NotFoundError guaranteed).
- **Fix:** guard corrected (`if not snapshot...raise`), parent-KB ownership check
  added, live identity captured before deletion, snapshot record promoted in place
  (no id repointing needed — docs/chunks already reference it).

### P0-B4 — MCP `trustrag_search` always TypeError'd — FIXED
- **Where:** `app/mcp/server.py` passed `top_k=` to `retrieve_hybrid_chunks`,
  whose parameter is `top_k_override` → unexpected-keyword crash on every call.
- **Fix:** correct kwarg + clamp to 1..50 (unbounded fan-out was also a DoS vector).

### P1 fixes (same pass)
- **P1-B5** `recovery_node` cleared `state["claims"]` before snapshotting missing
  claims → the targeted-rewrite branch was dead; snapshot taken first now.
- **P1-B6** verifier single-claim fallback dropped provider/model (silent engine
  switch mid-analysis); now passed through.
- **P1-B7** `create_analysis` accepted `embedding_provider=ollama/llamacpp` past
  the pin guard (model None → cfg default matched) then 503'd in background;
  now synchronous 422 + embedding-dim pin enforced when the model matches.
- **P1-B8** SSE stream capped at 120s while local pipelines run 3-5 min → 360 ticks.
- **P1-B9** retriever cross-space truncate/pad was silent → `logger.warning` with dims.
- **P1-B10** ingestion retry loop fell through after 5×429 with a short vector list
  (misleading IndexError later); now raises the last error loudly.
- **P1-B11** snapshot chunk copies stored `chunk["_id"]` as `document_id`
  (chunk id, not document id) → broken doc links/integrity lookups; fixed.
- **P1-B12** `delete_kb` "soft-delete" left orphaned DOCUMENTS/CHUNKS rows (KB record
  hard-deleted anyway); now hard-deletes all associated data.
- **P1-B13** lifespan forced `HF_HUB_OFFLINE=1` unconditionally → fresh machines
  could never download BGE weights; now only when weights are cached.

### Deliberately NOT changed (recorded, audited clean)
Auth (timing-safe dummy bcrypt, idempotent jti revoke, denylist enforced in
`deps`), CORS/authz scoping, SSRF-guard writes, tz-aware parser dates (temporal
filter comparison safe), RRF fusion, BGE prefixing, disk/semantic caches,
`SharedEmbeddingManager`, rate limits, security headers. `request_id_middleware`
trusts client `X-Request-ID` (trace confusion only, negligible).

### Verification (smoke only, not evidence)
`ruff check` clean, format clean, imports OK, `/health` OK
(`huggingface BAAI/bge-small-en-v1.5 | ollama granite`), pytest 117 passed
(post-fix smoke run — suite was not used to find anything).

## Addendum 2026-09-07 — skill-driven review + re-verification

Skills applied: **Requesting Code Review** (dispatched independent review subagent
over the `git diff -w` of all 9 touched backend files), **Verification Before
Completion** (no completion claim without fresh command output),
**Systematic Debugging** (root-cause-first; each fix traces to a read line).

### Review verdict: "Needs fixes" — all Important items fixed
1. **Rollback restored Mongo but not vectors** — `create_kb_snapshot` never copied
   Qdrant points, so post-rollback retrieval hit an empty collection. Fixed:
   `_copy_kb_vectors()` duplicates points into the snapshot collection at snapshot
   time (payloads rewritten to snapshot KB/doc ids, point ids recomputed).
2. **Snapshot chunks dangled past rollback** — snapshot docs get fresh `_id`s but
   chunk copies kept live doc ids. Fixed: `doc_id_map` remaps chunk
   `document_id` (and vector payloads) to the new snapshot doc ids; embedding pin
   carried onto the snapshot record.
3. **Stub-guard published wrong terminal SSE event** — DB `abstained` but event
   `analysis.completed`, stranding clients awaiting `analysis.abstained`. Fixed:
   event now follows `stored_status`.
4. **Rollback KB id change** — confirmed no API route exposes snapshot/rollback
   (service-layer only), so nothing live breaks; documented the id contract in
   the docstring (restored KB keeps the snapshot's id; pre-fix snapshots have no
   vectors → rollback yields empty state).
- Plus review minors: provider-422 now also covers retired server default;
  model-pin compare normalized (strip/lower); pipeline pin is pin-once with
  warning; `delete_kb` docstring corrected to hard delete; `main.py` probe
  handles `splade` + requires real weight files (`*.safetensors/*.bin/*.pt`).

### Fresh verification evidence (this message, full commands)
- `ruff check app/ tests/` → **All checks passed**; `ruff format --check` → **90
  files already formatted** (2 auto-reformatted blank-line-only, logic untouched)
- `pytest tests/ --no-cov` → **117 passed**, 0 failures
- `npm run lint` → exit 0; vitest → **15 passed**; `vite build` → exit 0
- Boot smoke: `/health` → `huggingface BAAI/bge-small-en-v1.5 | ollama
  granite4.2:3b-q4_K_M`; `ChatLlamaCppClient.with_structured_output` present;
  `_copy_kb_vectors` importable.

## Addendum 2026-09-07 — fix + optimize pass (integration & backend)

### Integration fixes
1. **Trace TTL never fired (unbounded growth).** `trace_ttl_expiry` indexed
   `created_at`, which no trace doc carries (`add_trace_event` writes
   `timestamp`). Fixed: TTL now on `timestamp` (`trace_timestamp_ttl`, 30d) +
   stale index dropped (suppressed on fresh DBs).
2. **SSE tickets were process-memory (multi-worker broken).** Ticket minted on
   worker A + stream landing on worker B → 401. Fixed: `stream_tickets`
   collection (atomic find-and-delete single-use, 60s server-enforced validity,
   TTL janitor) + `Collections.STREAM_TICKETS` + index. Stream tests updated to
   a dict-backed fake spanning mint + consume.
3. **Index failures were silent.** `gather(return_exceptions=True)` + unconditional
   "created/verified" log. Fixed: failures counted and logged with messages.
4. **Vite duplicate proxy key** (`/api` + `/api/v1/analyses`, same target).
   Removed the redundant entry; SSE rides the same `/api` prefix.

### Backend optimizations
5. **New compound indexes:** chunks `(knowledge_base_id, chunk_index)` (self-heal
   sort over ≤10k docs), claims `(analysis_id, state)` (conflict scan).
6. **Parallel startup warmup:** embedding pre-warm + hardware probe now
   `asyncio.gather`ed instead of sequential.
7. **New `GET /analyses/{id}/detail`:** 1 ownership check + 3 parallel collection
   reads in one round trip (was: 4 HTTP calls, 6 reads). Workbench
   `fetchFinalAnalysis` uses it with fallback to the legacy flow.

### Fresh verification evidence (this message, full commands)
- `ruff check` → clean; `ruff format --check` → 90 files formatted
- `pytest` → **117 passed**; eslint → exit 0; vitest → **15 passed**;
  `vite build` → exit 0; `apply_ports --check` → exit 0
- Live smoke: `/health` 200, `detail` route in OpenAPI, `get_analysis_detail`
  proven 1-auth + 3-parallel, ticket issue/consume/single-use/binding/expiry
  proven (Mongo down locally, so E2E register→stream not re-run; mocked paths
  green).

## Addendum 2026-09-07 — llama.cpp + OCC-RAG-1.7B live cutover

Operator note: neither `llama-server` nor Ollama was actually listening (`:8080`,
`:8081`, `:11434` all closed) — only MongoDB was up. Started
`llama-server -hf occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M --port 8080 -c 8192`
(PID 44700, log `/tmp/llama-server-occ.log`). Cache holds 4 models:
OCC-RAG 1.7B/0.6B + granite 4.2-3b/4.0-h-1b. Server `/health` 200,
`/v1/models` serves the OCC id (1.7B params, n_ctx 8192).

### Config (server default is now llama_cpp + OCC)
- `.env`: `AI_PROVIDER=llama_cpp`, `LLAMACPP_MODEL=occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M`
- `models.yaml` v1.2→**1.3**: llm + verification provider `llama_cpp`, model OCC
- Discovery (`local_llm` primaries, `/models/providers` targets,
  `check_llamacpp_status` default) + frontend defaults (Playground initial
  provider/model, drawer fallback list) all put OCC-RAG-1.7B first.
- Embeddings unchanged: `huggingface BAAI/bge-small-en-v1.5` 384d.

### Live E2E (API :8000, PID 45419, log `/tmp/trustrag-api2.log`)
register 201 → login → KB → txt upload → ingest **completed ~4s** → analysis
(llama_cpp/OCC + BGE) → **completed TRUSTED 1.0 in ~105s**, 1 evidence chunk.
`/health`: `llama_cpp occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M | huggingface BGE`,
mongodb+qdrant ok. pytest 117 / vitest 15 / lint / build all green after.

### Model behavior note (honest)
OCC-RAG-1.7B is chatty/reasoning-styled: it echoes prompt scaffolding and burns
tokens narrating, so answers are verbose and claim decomposition yields few,
meta-flavored claims. Structured JSON works (response_format + repair path held
up for decompose + batch NLI). No prompt-engineering changes made — quality
tuning for this model is the natural next step, not a correctness fix.

### Trust bug found by this E2E — FIXED: claims endpoint mixed recovery rounds
Round 1 verified 1 claim (NEUTRAL) → recovery → round 2 verified 1 claim
(SUPPORTED) → verdict correctly TRUSTED 1.0 on round 2 — but `/claims` returned
**both** rounds, so the UI showed 1 SUPPORTED + 1 NEUTRAL against a 1.0 verdict.
Fix: `execute_claim_verification` tags docs with `attempt`
(`graph.py` passes `state.attempts`); `_fetch_claims` returns the latest round
only (legacy untagged docs returned as-is). Live proof: same analysis's
`/claims` now returns exactly the 1 SUPPORTED claim the verdict used.

## Addendum 2026-09-07 — env slim-down + OCC degeneration fixes (live proven)

### 1. `.env.example` refactored to secrets + endpoints only
Dropped: APP_ENV/APP_NAME/LOG_LEVEL/JWT_EXPIRY (code defaults),
AI_PROVIDER/model IDs/dims (now `models.yaml`), SEARCH_PROVIDER/rate limits
(defaults), OLLAMA/LLAMACPP_BASE_URL (now ports-derived Settings defaults).
Kept: JWT_SECRET, CORS_ORIGINS, 4 API keys, HF_TOKEN, MONGODB_URI/DATABASE,
QDRANT_URL/API_KEY + a commented override cheat-sheet. Consumers fixed:
`apply_ports.py` no longer targets the example; README env block + zero-key
section rewritten. To make a keyless fresh clone actually boot,
`Settings.ollama/llamacpp_base_url` now default from `config/ports.yaml`
(the old `""` default silently broke local clients), and `ModelConfig` gained
per-provider yaml keys (`model_ollama/model_llamacpp` for llm + verification)
plus `llm_model_for()/verification_model_for()` so an explicit provider arg
resolves that provider's model instead of the configured provider's. Proof: API
booted on a 10-var secrets-only `.env` → `/health ok llama_cpp OCC |
huggingface`, mongo+qdrant ok (live `.env` restored afterwards).

### 2. Your IRS output was model degeneration — fixed at 4 layers
The pasted Playground answer (prompt scaffolding echoed, `FINAL_SECTION`
looped to token cap) is OCC-1.7B instruction-following failure, verified live.
Fixes, all backend, all proven in trace on a re-run:
- `repeat_penalty` on both local clients (1.15 llama.cpp, 1.1 Ollama) —
  attacks repeat-until-cap loops at the sampler.
- Grounding + decomposition prompts hardened (no-echo discipline; never claim
  the question itself; empty list when no subject facts).
- Meta-claim filter (`_is_meta_claim`) in `verifier.py` — "The user asks…"
  claims can score SUPPORTED and launder echo into TRUSTED; now dropped.
- `_looks_like_scaffold_echo` in `finalize` — scaffold markers or 3× repeated
  sentences → clean abstention + `generation.degenerate` trace event.
- Live A/B same KB/query: before = verbose echo TRUSTED 1.0; after = evidence
  retrieved, echo discarded via `claims.empty` → recovery → `generation.
  degenerate` → honest abstain in 82s. The pipeline no longer presents model
  chatter as verified truth. Quality ceiling remains the 1.7B model itself —
  `granite4.2:3b-q4_K_M` / `gemma3:1b` via Ollama is the next quality step, not a fix.
- pytest 117 / vitest 15 / lint / build green throughout.

## Addendum 2026-09-07 — process hygiene + answer extraction (the real fix)
- Killed the process sprawl (3 stale uvicorns, 2 llama-servers, stray vite);
  lean stack is now exactly: llama-server (2×4096 Metal, PID 57388→59676-era),
  one API, mongod. No Ollama anywhere in the path.
- Root-caused the OCC failures with a direct generation probe: the model DOES
  produce the correct grounded answer in ~5s — buried inside scaffold echo
  (`[ANSWER]...[REASONING]...[FINAL_ANSWER]`). Fix: `extract_final_answer()`
  in `generator.py` peels structural markers (passthrough when absent);
  extraction fired 3× live the same run.
- Companion fix from the same trace: whole-answer fallback blobs were nuked
  wholesale by the meta-filter when one meta sentence hid inside — long blobs
  now split into sentences first (each still NLI-verified).
- Latest live run: 20 claims decomposed, batch NLI all NEUTRAL → honest
  LOW_COVERAGE FAILED (batch path proven working on OCC). Remaining echo
  phrasings from that run (`user prompt`, `missing facts`, `#headers`) added
  to the filter — unit-proven against the exact stored strings, real claims
  survive. Suites green; API reloaded.

## Addendum 2026-09-07 — model prune to installed sets (live proven)

Source of truth: `ollama list` → `granite4.2:3b-q4_K_M`, `gemma3:1b`;
`llama-server --cache-list` → OCC-RAG 1.7B/0.6B + granite-4.2-3b/4.0-h-1b GGUFs
(ollama daemon was down; started `ollama serve`, PID 49713). Removed everywhere:
`qwen3.5:4b`, `gemma4:e2b(-it-qat)`, `gemma-4-E2B-*`, `psychopenguin/Qwen3.5-*`.
- Backend single source: `INSTALLED_OLLAMA_LLMS` / `INSTALLED_LLAMACPP_LLMS` in
  `local_llm.py`, imported by `models.py` (defense-in-depth against list drift).
  Pruned: discovery primaries + defaults, endpoint target/fallback lists,
  `model_registry` + `config.py` last-resort ids, `hardware.py` tier
  recommendations, `models.yaml` comments, MCP/schema examples. Deleted the
  `gemma4:e2b`→`gemma4:e2b-it-qat` request alias (neither id exists anymore).
- Frontend/docs/tests: drawer + Settings fallbacks/copy, start-command hints,
  README model bullets, test expectations — all installed-only. Dated audit
  records intentionally untouched.
- Extra find during manual re-read: HF-hub scan emits bare repo ids while
  server/cache-list emit quantified ids for the same weights → selector showed
  each model twice. Merge now drops the bare form when a quantified sibling is
  listed. Live `/models/providers`: exactly 2 ollama + 4 llama.cpp entries.
- pytest 117 / vitest 15 / lint / build green; API restarted (PID 51304).

## Addendum 2026-09-07 — GPU offload + load-aware recovery (screenshot-driven)

Screenshot showed: 16 chunks retrieved yet 0 claims → 2× Expanded Context
Retrieval recovery burned doubled search on a generation-side failure.

### GPU (verify-then-pin)
llama-server defaulted to `auto` offload, 4 slots × 8k ctx. Throughput (~65 tok/s
gen on 1.7B Q4) indicated Metal, but flags were implicit and KV-heavy.
Restarted explicitly: `-ngl all -c 8192 -np 2` → 2 slots × 4096 ctx (our prompts
need ≤ ~3.2k), full VRAM offload, KV halved vs before. Note: `-c` is total ctx
split across slots; `--slots` is not the slot flag (`-np` is). BGE embeddings
already target MPS via `get_optimal_torch_device`. API restarted (PID 52273).

### Load-aware recovery (the screenshot bug, fixed at 2 layers)
- Decision layer (`recovery_node`): `re_retrieve` downgrades to `regenerate`
  when chunks ≥ `max_context_chunks` (+ `recovery.regenerate` trace event;
  explicit yaml strategy also supported).
- Execution layer (`retrieval_node`): `regenerate` reuses saved chunks with
  zero retrieval spend (`retrieval.reused`, no duplicate evidence rows);
  `re_retrieve` skips doubling on sufficient evidence
  (`recovery.re_retrieve_skipped`). Thin-evidence behavior unchanged.
- Frontend timeline labels the new events correctly.
- Branch proofs (mocked harness): doubling skipped / zero-call reuse /
  downgrade fires / thin path preserved — all 4 OK. Full suites green.
- Leftover hygiene (not touched): one stale `processing` row from 2026-09-06
  (orphaned by a server restart); legacy unpinned IRS KB should be re-ingested
  into a new KB for the pin guard to protect it.

## Addendum 2026-09-07 — E2E integration green + stale-verdict-skip fix
- Full stack live (API :8000, llama :8080, mongo, vite :5173) → Playwright
  **2/2 pass**, incl. SEC-H1 logout-revocation through the real UI.
- Hygiene: orphaned 2026-09-06 `processing` row marked failed; `.env` comments
  updated to installed model sets (values untouched).
- **Trace-read find: round-2 answers were never verified.** The empty-KB fast
  path (`diagnosis==RETRIEVAL_FAILURE and answer`) matched on round 1's stale
  diagnosis after recovery, so round 2 jumped to finalize with 0 claims —
  every post-recovery answer was auto-FAILED without verification. Fixed at both
  layers: guard now requires `not chunks` (genuine empty KB still fast-paths,
  proven) + `recovery_node` clears diagnosis/verdict state. Branch proofs OK,
  suites   green, API restarted (PID 52779).

## Addendum 2026-09-07 — recovery timeline de-noised (screenshot-driven)
Screenshot of the IRS run showed 6 timeline cards for 2 recovery attempts:
wrapper lifecycle events (`recovery.started/completed` from the node executor)
were prefix-matched into the timeline and all labeled "Expanded Context
Retrieval". Fix: `traceEvents.js` registers the real strategy/result events
(`recovery.regenerate`, `recovery.re_retrieve_skipped`, `retrieval.reused`,
`retrieval.capped`, `generation.degenerate`, `claims.empty`) with labels, and
`PlaygroundPage` maps an explicit allowlist instead of `startsWith('recovery.')`.
Same 6 events now render as the meaningful strategy cards only (proven by logic
check). Lint/vitest/build green; frontend-only change, no API restart needed.
- `models.yaml` embedding default → huggingface/BGE, `config_version` 1.1 → **1.2**; runtime `Settings == ModelConfig` = `huggingface BAAI/bge-small-en-v1.5`, CONSISTENT.
- Guard re-proven live: `get_embedding_model('ollama'|'llamacpp'|'llama_cpp')` → `ConfigurationError LLM-only` (all three blocked OK).
- Post-fix: `pytest` **117 passed**, `ruff check` clean, `ruff format` 90 files clean, `npm lint` clean, vitest **15 passed**, `vite build` success (~3s), `/health` → `huggingface BAAI/bge-small-en-v1.5 | ollama granite4.2:3b-q4_K_M`.
- Residual grep for runtime embedding usage of ollama/llama: only the intentional guard (`model_registry` raise + `embeddinggemma/nomic-embed` keyword filter), guard tests, and LLM-only discovery remain. No `OllamaEmbeddings`/`LlamaCppEmbeddings` classes anywhere.
- Open owner actions (2026-09-07, superseded where noted): rotate the live
  `GEMINI_API_KEY` in `.env`; run the matching local server for the active
  `AI_PROVIDER` (`llama-server` on :8080 for `llama_cpp`, `ollama serve` for
  `ollama`); re-upload docs into a fresh KB after an embedding-model change
  (old vectors are model-pinned).

## Addendum 2026-09-07 — granite-1b IRS run: CoT bleed diagnosed + filtered

From the stored run (granite-4.0-h-1b, IRS query): 20 claims decomposed,
but ~18 were chain-of-thought fragments ("Let me re-evaluate… Segment 2
states…", "Path A (Definition): …", "- **Page 8**: collect, organize, …").
NLI correctly marked them all NEUTRAL → honest 0% FAILED — but CoT-fragment
pollution inflated the batch and wasted a full verification call.

**Fix (whitebox, no servers):**
- `_is_meta_claim` expanded: digit-anchored regexes for evidence-layout
  references (`Segment 2`, `Page 8`, `Path A`) so subject-matter uses of
  those words survive ("landing page", "network segment"); added
  `re-evaluate`/`re-read`/`critical_path` CoT markers. Verified against the
  exact strings from the failed run: 5/6 filtered; the one survivor
  ("However, often in these contexts…") has no verifiable content so NLI
  keeps it NEUTRAL (honest, not trusted).
- `models.yaml` `max_verification_claims` 20 → 8 (small models waste
  and hallucinate past that; claim cap only trims LOW-priority overflow).
- Lint clean, 117 pytest green (re-runned post-change).

## Addendum 2026-09-07 — GPU auto-detect & lean llama.cpp boot

Request: project must pick the hardware (CUDA / MPS) itself and keep the load
down. This pass makes that project-owned instead of manual:

- **`get_llamacpp_launch_args()` in `app/core/hardware.py`** — probes the host
  (no torch dependency since llama-server vendors its own Metal/CUDA backends
  via GGML backends). Apple Silicon M2+ gets `-ngl all --flash-attn on`;
  NVIDIA gets the same plus `--split-mode layer`. Context + slot count scale
  with RAM: ≤8.5GB → `-c 4096 -np 2`, ≤16.5GB → `-c 8192 -np 2`, above →
  `-c 16384 -np 4`. Verified on this machine: Metal MTL0 detected, correct
  argv emitted.
- **`scripts/start_local_llm.sh`** (POSIX-safe, no bash-4 `mapfile`):
  one command starts llama-server with those flags and the repo's configured
  llama.cpp model; the boot was verified live (server answered /health on
  :8080 with n_ctx 4096). This is now the documented way instead of hand-built
  flags.
- **Reranker device pinning**: `get_reranker()` now uses
  `get_optimal_torch_device()` so the cross-encoder rides MPS/CUDA instead of
  staying on CPU.

Verified: ruff clean, 118 pytest green (new `test_llamacpp_launch_args_fit_host`),
launch script produced Metal+flash-attn arguments on this host and the server
came up successfully. All project processes stopped after verification, per
the operator's request — run `./scripts/start_local_llm.sh` when ready.
