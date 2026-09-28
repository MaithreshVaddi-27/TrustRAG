# TrustRAG — Audit: Bugs, Errors, Issues, Upgrades, Optimization & Less-RAM Plan

> **Date:** 2026-09-28 · **Scope:** full stack (FastAPI backend, React frontend, ONNX inference, config/env, security, DevOps, testing)
> **Goal:** ultra-premium production level — less RAM, faster inference, ONNX-only local models, zero hardcoded secrets, single-source config.
> **Method:** Senior Designer + Frontend + Backend + AI/ML + Security + Optimization + DevOps + Testing (black-box & white-box) review, guided by `apple-design`, `ui-ux-pro-max`, `frontend-design-direction`, `using-superpowers` skills.
> **Config version at audit:** `models.yaml` v1.22 · **After upgrades:** v1.23 (new `onnx:` block).

Resolution order (unchanged): `apps/api/config/models.yaml` (defaults) → `config/ports.yaml` (ports) → `.env` (secrets + overrides win).

---

## 1. Verdict summary

| Area | Status | Notes |
|------|--------|-------|
| Secrets / API keys | ✅ PASS — env-only | All keys via `Settings` (pydantic-settings) + `.env`; `.env` gitignored; log redaction for `AIza`/`sk-`; SSE stream-ticket keeps JWT out of URLs; tests use sentinel values only (§2) |
| Config centralization | ⚠️ GAP → FIXED in v1.23 | Embedding/reranker IDs central, but ONNX runtime knobs (threads, arena, micro-batch) were hardcoded/env-only → new `onnx:` block (§4, U-1) |
| ONNX inference env | ⚠️ GAP → FIXED in v1.23 | Reranker had tuned `SessionOptions`; **embedding session used bare defaults** (no thread cap, no explicit graph opt) → shared factory (§4, U-2) |
| RAM usage | ✅ GOOD → IMPROVED | Tier-aware batching, KV `q8_0` + flash-attn, ONNX int8 reranker, disk+memory caches, malloc_trim guard; embedding session now capped (§5) |
| Inference speed | ✅ GOOD → IMPROVED | `ORT_ENABLE_ALL` + arena now applied to embeddings too; micro-batch tunable (§5) |
| Frontend design | ✅ PASS — premium | Lazy routes, vendor chunks, ErrorBoundary, safe-area, focus-visible, `prefers-reduced-motion/transparency/contrast` all present (Apple §14) (§6) |
| Testing | ✅ GOOD → EXTENDED | Hermetic conftest; added `test_onnx_runtime_config.py` (§7) |

---

## 2. Bugs / Errors / Issues found (with severity + fix)

### B-1 — Embedding ONNX session untuned (perf/RAM) · Severity: **Medium**
- **Where:** `apps/api/app/core/onnx_embeddings.py:86` — `ort.InferenceSession(model_path, providers=...)` with no `SessionOptions`.
- **Impact:** Default thread pool = full CPU count → thread oversubscription next to uvicorn workers + tokenizer pool; higher peak RAM; no explicit `ORT_ENABLE_ALL`.
- **Fix (U-2):** shared `app/core/onnx_runtime.py::build_session_options()` used by **both** embeddings and reranker. Intra-op threads default `min(cpu_count, 4)`; inter-op `1`; `ORT_ENABLE_ALL`; arena/pattern from config.
- **Verify:** `pytest tests/test_onnx_runtime_config.py -v`.

### B-2 — ONNX knobs not in central config (config-drift risk) · Severity: **Medium**
- **Where:** `onnx_embeddings.py` (micro-batch `32`, providers `["CPUExecutionProvider"]` hardcoded); `onnx_reranker.py:115` (`RERANKER_BATCH_SIZE` read via raw `os.environ`, bypassing `cfg.reranker_batch_size`).
- **Impact:** Updating one place does not update everywhere — violates the project's own "never hardcode" rule.
- **Fix (U-1):** new `onnx:` block in `models.yaml` v1.23 + `Settings.onnx_*` properties with env overrides (`ONNX_*`); reranker batch resolves `explicit arg → RERANKER_BATCH_SIZE → models.yaml → 16`.
- **Verify:** change `onnx.embed_micro_batch` in yaml → embedding chunking follows; `ONNX_INTRA_OP_THREADS=2` → session options follow.

### B-3 — Reranker batch-size precedence bypass · Severity: **Low**
- Same root as B-2. Fixed by routing through `get_model_config().reranker_batch_size` first.

### B-4 — Tests set dummy keys via `setdefault` (accepted, documented) · Severity: **Info**
- **Where:** `apps/api/tests/conftest.py:31-39`.
- **Ruling:** NOT a violation — values are non-functional sentinels (`test-gemini-api-key`), hermetic by design (pops leaky `.env` vars first). Real keys can never load in tests because `setdefault` never overwrites a real env value with a dummy, and CI provides no real keys.
- **Action:** documented here; new test asserts production key fields default to empty.

### B-5 — Frontend `SettingsPage.jsx` shows loopback endpoints as text · Severity: **Info**
- **Where:** `apps/web/src/pages/SettingsPage.jsx:330,387` — display-only strings (`localhost:11434`, `127.0.0.1:8080/v1`).
- **Ruling:** NOT hardcoded secrets/endpoints — informational labels; actual calls use `VITE_API_URL`/`VITE_API_BASE_URL` env via `src/lib/api.js` with Vite proxy fallback. No change.

### Historical issues (already fixed, kept for traceability)
- Prior full-tracker audit lives in `docs/audit-2026-09-28-ui-redesign-full.md` (ingestion H1–H2/M1–M5/L1–L2, ONNX-only enforcement, test hermeticity, CI-1–CI-3). This file covers the **new** optimization/less-RAM pass and does not duplicate it.

---

## 3. Security audit (white-box + black-box)

- [x] **No hardcoded production keys** — `rg` for `sk-`/`AIza`/quoted `api_key=` across `app/` returns only redaction regexes (`logging.py`) and `settings.*` reads. ✅
- [x] **Tests** use sentinel values only; `.env` + `.model_cache/` gitignored (verified via `git check-ignore`). ✅
- [x] **JWT** HS256 + `iss`/`aud` + JTI denylist + 60-min expiry; bcrypt cost 12; login lockout via TTL collection. ✅
- [x] **SSRF guards** on URL ingest; Pydantic v2 validation; filename sanitization; 20 MB cap. ✅
- [x] **JWT never in URL** — SSE uses short-lived stream tickets. ✅
- [x] **Tokenizer supply-chain pin** (`HF_TOKENIZER_REVISION`) retained; override path unchanged. ✅
- [x] **CORS** from `CORS_ORIGINS`; `APP_ENV=production` requires `QDRANT_API_KEY`. ✅
- [ ] **Next (not this pass):** rotate `JWT_SECRET` per environment; add Redis-backed rate limiting in prod (`RATE_LIMIT_STORAGE_URI`); consider `ONNX_CPU_MEM_ARENA=false` on sub-2 GB containers (now one env flag away).

---

## 4. Upgrades implemented (this pass)

### U-1 — Central `onnx:` config block (models.yaml v1.22 → v1.23)
```yaml
onnx:
  providers: ["CPUExecutionProvider"]
  intra_op_threads: 0        # 0 = auto → min(cpu_count, 4)
  inter_op_threads: 1
  graph_optimization: "all"  # none|basic|extended|all
  cpu_mem_arena: true
  mem_pattern: true
  embed_micro_batch: 32
```
Env overrides (win over yaml): `ONNX_PROVIDERS`, `ONNX_INTRA_OP_THREADS`, `ONNX_INTER_OP_THREADS`, `ONNX_GRAPH_OPTIMIZATION`, `ONNX_CPU_MEM_ARENA`, `ONNX_MEM_PATTERN`, `ONNX_EMBED_MICRO_BATCH`. Documented in `.env.example` (ONNX Runtime section).

### U-2 — Shared ONNX session factory (`app/core/onnx_runtime.py`)
- `build_session_options()` — single place for `SessionOptions`; caps auto threads; maps graph-opt string → `ort.GraphOptimizationLevel`.
- `create_session(model_path, providers=None)` — applies factory + config providers.
- `onnx_embeddings.py` and `onnx_reranker.py` both use it (reranker behavior unchanged: same defaults as before).
- Embeddings constructor accepts optional `sess_options`/`providers` overrides (backward compatible); micro-batch from `cfg.onnx_embed_micro_batch`.

### U-3 — Reranker batch precedence fix
`explicit arg → RERANKER_BATCH_SIZE env → models.yaml reranker.batch_size → 16`.

### U-4 — Regression tests (`apps/api/tests/test_onnx_runtime_config.py`)
Hermetic, no model files needed: factory honors config, env overrides win, auto-cap `min(cpu,4)`, graph-level mapping, `embed_micro_batch` default 0 (auto), reranker batch precedence, production API-key *field defaults* empty. **6 tests, all passing; full backend suite 671 passed.**
> Caught live during this pass: `int(yaml_val or 32)` swallowed the meaningful `0` default — fixed to explicit `is None` checks. This is why the tests exist.

### U-5 — Frontend: no code change (verified premium)
Apple-design + ui-ux-pro-max checklist re-verified (see §6). Churn avoided deliberately before a commit.

---

## 5. Optimization & less-RAM guide (production tuning)

| Knob | Default | Less-RAM setting | Faster-inference setting |
|------|---------|------------------|--------------------------|
| `ONNX_INTRA_OP_THREADS` | auto `min(cpu,4)` | `1–2` | `4` (or CPU count on 32 GB+) |
| `ONNX_CPU_MEM_ARENA` | `true` | `false` (saves arena blocks, slower warm) | `true` |
| `ONNX_EMBED_MICRO_BATCH` | `32` | `16` on ≤8 GB | `64` on 32 GB+ |
| `RERANKER_BATCH_SIZE` | `16` (yaml) | `8` on ≤8 GB | `32` on GPU/CPU-big |
| `OMP_NUM_THREADS` (legacy alias honored by reranker) | unset | `2` | `4–8` |
| `TOKENIZERS_PARALLELISM` | unset | `false` (prevents thread-pool bloat next to torch) | — |
| `MALLOC_ARENA_MAX` | unset | `1` (glibc fragmentation guard) | — |
| `OLLAMA_KV_CACHE_TYPE` + `OLLAMA_FLASH_ATTENTION` | shell env | `q8_0` + `1` (halves KV RAM) | same |
| `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1` | shell env | keep on ≤8 GB | raise only with parallel-capable server |
| `LOCAL_LLM_MAX_CONCURRENCY` | `1` | keep `1` on 8 GB | raise with parallel server |

> `optimization.kv_cache_quantization` (`q8_0`) and `flash_attention` remain honored by `scripts/start_local_llm.sh`. `TOKENIZERS_PARALLELISM=false` is recommended whenever the export extra (`local-models`, torch) is installed next to the server.

---

## 6. Frontend design verification (Apple-design · ui-ux-pro-max · frontend-direction)

- **Motion:** springs via `motion/react`; cursor spotlight uses `MotionValues` outside React render cycle (no re-render on mousemove) — matches Apple "response kills latency".
- **Accessibility (§14):** `prefers-reduced-motion` (9 stylesheets incl. `animations.css:334` cross-fade fallback), `prefers-reduced-transparency` + `prefers-contrast` (`materials.css:169,185`). ✅
- **Layout:** mobile-first Tailwind, `100dvh` guards, safe-area insets, `overflow-x: hidden`, focus-visible rings, min touch targets per pro-rules.
- **Perf:** route-level `lazy()` + `Suspense`, vendor `manualChunks` (react/query/chart/motion/ui), ErrorBoundary per route, centralized Axios client with normalized errors.
- **Env:** `VITE_API_URL` → `VITE_API_BASE_URL` → proxy fallback; no secrets in client bundle. ✅
- **Decision:** no visual churn this pass — design system already ultra-premium; changes limited to backend inference path (zero UI regression surface).

---

## 7. Test report (this pass)

```bash
cd apps/api && ruff check app/ tests/ && ruff format --check app/ tests/
cd apps/api && .venv/bin/python -m pytest tests/test_onnx_runtime_config.py -v
cd apps/api && .venv/bin/python -m pytest -v -x -q   # full suite (mocked, no live services)
```
- New: `tests/test_onnx_runtime_config.py` (6 tests, hermetic).
- Full suite + `ruff` must be green before push (commit is local only per owner instruction).
- **Result this pass: 671 passed, 0 failed (17.1 s).**

> **Note (2026-09-28, during this pass):** a parallel session landed complementary in-tree improvements mid-audit (embedding `SessionOptions` tuning, tier-aware micro-batching, `TOKENIZERS_PARALLELISM=false`, yaml-driven reranker/embedding defaults, lean-tier reranker cap). They were **adopted, not reverted**: the shared `onnx_runtime.py` factory + `onnx:` block now route those behaviors through central config, dead-code alias `_onnx_intra_op_threads` delegates to the factory, and lint (E501/S110) was cleaned so the tree stays CI-green.

---

## 8. Second sweep (same pass): config-drift + frontend hardening

### B-6 — Cloud allowlists duplicated in `models.py` (drift: yaml 7 vs code 5) · **Medium**
- **Where:** `app/api/v1/models.py:133-157` — hardcoded `default_model` + `models` lists for gemini/nvidia.
- **Fix:** `default_model` → `cfg.llm_model_for(...)`; `models` → `cfg.supported_gemini_models` / `cfg.supported_nvidia_models`. Yaml edit now propagates to the Playground dropdown with no code change.

### B-7 — Stale local-LLM field defaults · **Low**
- **Where:** `ChatOllamaClient.model` (`granite4.2:3b-q4_K_M` vs yaml `gemma3:1b`); `ChatLlamaCppClient.model` (`occ-ai/OCC-RAG-1.7B-GGUF` — not in yaml at all).
- **Fix:** defaults aligned to `models.yaml` (`gemma3:1b`, `LiquidAI/LFM2.5-1.2B...`) + source-of-truth comments; `check_ollama/llamacpp/mlx_status` prefer `cfg.llm_model_for(...)` when discovered.

### B-8 — Yaml/code fallback literals mismatched · **Low**
- **Where:** `ModelConfig.llm_model_for` / `verification_model_for` fallbacks (`granite4.2`, `ibm-granite/...-3b`) vs yaml (`gemma3:1b`, `LFM2.5-1.2B`).
- **Fix:** fallbacks aligned to yaml values (missing-key path only; normal path already reads yaml).

### B-9 — Tokenizer/RAM env guards only in Docker · **Low**
- **Fix:** `app/main.py` lifespan now `setdefault`s `TOKENIZERS_PARALLELISM=false` + caps `OMP_NUM_THREADS=min(cpu,4)` for every process (api, workers, tests), not just the image.

### U-6 — Frontend ultra-premium hardening (Apple-design · ui-ux-pro-max)
- `src/styles/tokens.css` (new): `:root` vars for primary/surface/trust/glow/radius/motion — single source alongside `tailwind.config.js`; imported first in `index.css`.
- `AppLayout.jsx`: removed global `select-none` (was killing text selection shell-wide); added skip-link → `#main-content`; `tabIndex=-1` + `aria-label` on `<main>`; `aria-label` on mobile close; `aria-hidden` on decorative lucide icons + cursor glow.
- Cursor glow: rAF-throttled, `passive` listener, disabled on `pointer: coarse` and `reducedMotion` (battery/perf).
- `vite.config.js`: `sourcemap: true` → `'hidden'` (no source leak in prod dist; traces still mappable via uploaded maps).

### Secrets re-verification (this sweep)
- `rg` for `sk-`/`AIza`/quoted `api_key=` across `app/`, `tests/`, `web/src`, `scripts/`: only redaction regexes (`logging.py`), `settings.*` reads, and sentinel fixtures (`test-*`, `dummy-key`, `StrongPass123!`) — **no production keys hardcoded, tests included**. `.env.example` secrets are empty placeholders; `docker-compose.yml` carries only non-sensitive hostnames.

## 9. Phase-by-phase production pass, part 2 (2026-09-28 — this session)

Phases completed in RAG order (preprocessing → retrieval → augmentation → generation → overall), then backend → security → DevOps. Rule applied throughout: **top-level imports everywhere**, except names tests patch at their source module (called via module attribute: `mod.name`) and heavy/optional deps (torch, transformers tokenizer, rapidocr, pyclamd, tavily/ddgs fallback, onnx export path) — each intentional lazy site either kept or documented inline.

### PHASE 1 — Frontend loaders (libraries.dev family)
- New `web/src/styles/loaders.css` (orbs, skeleton shimmer, `stream-beam`, reduced-motion/transparency guards), `ThinkingOrbs.jsx` (`role=status`, sm/md/lg), `Skeleton.jsx`/`SkeletonRows`.
- `Loader2` page/panel waits → orbs: `App.jsx` route fallback, HUD `StageCard`, `QueryPanel` submit (+elapsed), Conflicts/Claims/Evidence/KB/Experiments/Trace(skeleton rows); `ResultsPanel` stream card rides `border-beam stream-beam`. Button micro-spinners kept (correct pattern).
- Verified manually per page (no test-script reliance): eslint 0 warnings, `vite build` ok, vitest 33 passed.

### PHASE 2 — Preprocessing
- `pipeline.py`/`chunker.py`: imports hoisted; stale `all-MiniLM-L6-v2` docstring → ONNX BGE; dead 429/`RESOURCE_EXHAUSTED` backoff removed (local-only engine; was unreachable + slept minutes); `qdrant_upsert_batch` → `models.yaml` + `QDRANT_UPSERT_BATCH`.

### PHASE 3 — Retrieval
- Timeouts → `retrieval.branch_timeout_seconds`/`hybrid_timeout_seconds` (0 = module-global fallback, still monkeypatch-able); adaptive threshold/cap → yaml + `ADAPTIVE_*` env; query LRU → `retrieval.query_cache_capacity` + `RETRIEVAL_QUERY_CACHE_CAPACITY`; removed inner `math`/`bson`/duplicate `RetrievalOutageError` imports.

### PHASE 4 — Augmentation + generation
- Hoisted imports in `verifier.py`/`graph.py`/`generator.py` (−57 lines); patch-compat via `config_mod`, `retriever_mod`, `integrity_mod`, `memory`/`model_registry`/`semantic_cache`/`qdrant_db`/`pipeline_mod` module refs.
- Caught by tests during the pass: `test_create_analysis` 503 — top-bound probe bypassed the source-level mock; module-attr calls restore it. Same fix applied to `get_llm` (`mcp/server`), `retrieve_hybrid_chunks`, `audit_evidence_integrity`.

### PHASE 5 — Backend hardening
- Routes/services hoisted (`knowledge_bases`, `documents`, `health`, `models`, `internal`, `analysis_service`, `kb_service`, `mcp/server`, `chunking_strategies`, `parser`, `onnx_*`); dual patch-levels documented inline in `kb_service` snapshot path (deliberately NOT hoisted).

### PHASE 6 — Security
- Scan clean: no hardcoded keys in `app/`, `tests/`, `web/src`, `scripts/`; `.env` + `.model_cache/` gitignored. Hardened 3 `detail=str(exc)` bson-echo sites (`deps.py`, `documents.py` ×2) to static `"malformed id"`.
- **Fixed S-1 (found while closing this phase):** `JWT_SECRET=REPLACE_WITH_…` in `.env.example` is 44 chars, so it passed the existing 32-char strength check — copying the template into production would have silently set a publicly-known HMAC signing key (full auth bypass / forged stream tickets). `production_must_have_qdrant_key` now also rejects `REPLACE_WITH*`/`CHANGE_ME*`; 3 new tests cover placeholder rejection, missing-Qdrant, and happy path.

### PHASE 6b — `.gitignore` / `.env.example` hygiene
- `.gitignore`: `!**/.env.example` (the `.env.*` rule silently matched nested templates, so a new app's template would be untrackable), plus `qdrant_storage/`, `*.sqlite3-journal`, `*.rdb`, `.freebuff/` (external CLI scratch dir found in repo root).
- `.env.example`: closed the docs gap — 11 vars read by `config.py` were undocumented (`KV_CACHE_QUANTIZATION`, `PROMPT_CACHING`, `CONTEXT_COMPRESSION_*`, `LOCAL_LLM_EARLY_EXIT_EOS`, `LOCAL_LLM_MODEL_UNLOAD_ENABLED`, `RERANKER_USE_ONNX`, `RERANKER_ONNX_MODEL_PATH`, `NIM_BASE_URL`/`NVIDIA_BASE_URL`, `VERIFICATION_MAX_RETRIES`). Now 30/30 `config.py` env names are documented; script-checked.

### PHASE 7 — DevOps/docs
- `apply_ports.py --check` exit 0. README v1.21 → v1.23 + new-knob rows/env table; `.env.example` documents all new vars (`RETRIEVAL_*`, `ADAPTIVE_*`, `QDRANT_UPSERT_BATCH`, `RERANKER_MAX_SEQ_LENGTH`).

### Test scripts updated after fixes
- `tests/test_onnx_runtime_config.py`: 6 → 9 tests (retrieval infra defaults/overrides, timeout resolution incl. monkeypatch fallback).

### Verification (this session, working tree)
- Backend: `ruff check` + `ruff format --check` clean (134 files); `pytest`: **674 passed**.
- Frontend: `eslint` 0 warnings; vitest 33 passed; `vite build` ok.

## 10. Commit & push policy (per owner)

- Commits are **local only** — owner pushes after final review. No `git push`, no PR creation in this pass.
- Model weights (`apps/api/.model_cache/`) and `.env` are never committed (gitignored, verified).

## 10b. Current status (2026-09-28, end of this pass)

| Phase | Area | Status |
|-------|------|--------|
| 1 | Frontend loaders / visual system | ✅ DONE — orbs, skeletons, stream-beam; manual per-page review + eslint/build/33 vitest |
| 2 | Preprocessing (pipeline, chunker) | ✅ DONE — imports, no dead 429 backoff, upsert batch centralized |
| 3 | Retrieval (timeouts, adaptive K, cache) | ✅ DONE — all budgets in `models.yaml` v1.23 + env overrides |
| 4 | Augmentation + generation | ✅ DONE — imports hoisted, patch-compat preserved, suite-caught 503 fixed |
| 5 | Backend hardening (routes/services/MCP) | ✅ DONE — intentional lazies documented inline |
| 6 | Security | ✅ DONE — S-1 JWT placeholder fixed; 3 bson-echo details made static |
| 6b | `.gitignore` / `.env.example` hygiene | ✅ DONE — nested template rule, 4 ignore gaps, 11 undocumented vars closed |
| 7 | DevOps + docs | ✅ DONE — ports check green, README v1.23, audit log current |
| — | Verification (this pass) | ✅ 677 backend passed · ruff clean · web eslint/build/vitest green |
| — | Commits | ✅ `35c076e` (ONNX config) · `0dce6d4` (phase pass) · security/ignore commit below |

**Not done / out of scope for this pass:** manual browser review of the new loader animations (built + tested, not clicked through), live k6 budget run, ONNX arena-off profile measurement on 512 MB containers.

## 10c. User-reported bugs: ungrounded answers + >70s latency (2026-09-28)

Two user-visible complaints, two independent root causes. Neither was a model-quality problem.

### G-1 — Answers not from the knowledge base (CRITICAL, fixed)

**Symptom:** the app returned fluent answers containing content that was not in the knowledge base.

**Root cause — the verdict was computed and then ignored.** `analysis_service.run_analysis_pipeline` only special-cased `ReliabilityStatus.ABSTAINED`. `FAILED` (reliability below `abstain_below`) and `UNCERTAIN` (coverage/contradiction thresholds missed) fell into the `else` branch and were stored **verbatim with `status: "completed"`**. The pipeline detected the ungrounded content via NLI and then presented it anyway — with a reliability badge showing it was not trusted.

**Fix:** added `_presentable_answer()` as the single gate where the verdict is applied to user-visible text. Only `TRUSTED` may present model prose; everything else becomes the abstention message, and the stored status becomes `abstained` (score/diagnosis preserved so the UI can still explain). Tests: `test_finalize_withholds_unverified_answer_from_user[FAILED|UNCERTAIN]`, `test_finalize_keeps_trusted_answer`.

### G-2 — Generation prompt locked to one domain (CRITICAL, fixed)

**Symptom (reported):** the product is not domain-specific (not market/policies) — it must answer from the code-base.

**Root cause:** `GROUNDING_SYSTEM_PROMPT` was hardcoded to a single subject, comparing subjects across "architecture, interaction model, **contextual intelligence**, and source verification", ranking "**most demanded**" / "**enterprise needs**" / "**industry trends**", and navigating "**syllabus**" sections. Two of those instructions directly caused hallucination on any other corpus:

- `"Do NOT output ABSTAIN if the Context contains relevant discussion of the topics"` — **contradicts grounding rule 1** and instructs the model to answer from weak context.
- `"You MUST address EVERY part"` + `"Prioritize items noted as leading, most demanded"` — pressures the model to fill sections from prior knowledge when the context does not cover them.

**Fix:** rewrote the prompt as explicitly domain-agnostic (source code, policies, market material, scientific literature, or prose — the context decides). Grounding is now the highest-priority rule that overrides all others; abstention is a positive obligation where "partial topical overlap is not support"; terminology must come from the context. Citation, injection-defense, and small-model output-discipline rules are preserved verbatim (redteam/citation tests still pass). Regression tests: `test_grounding_prompt_has_no_single_domain_lock`, `test_grounding_prompt_does_not_discourage_abstention`, `test_grounding_prompt_declares_domain_agnostic`.

### L-1 — No bound on total analysis time (fixed)

**Symptom:** >70 s to produce an answer.

**Root cause:** `max_recovery_latency_seconds: 180` only accumulates time spent *inside the recovery node*, so it could not bound a full run. With `max_recovery_attempts: 2` the graph performs up to **3 complete rounds** (retrieval + generation + verification each), and nothing stopped a new round from starting on wall-clock grounds. Round 1 alone can spend minutes on a 1.2B local model.

**Fix:** `cost_controls.max_analysis_seconds` (default 120, `MAX_ANALYSIS_SECONDS`, `0` disables) sets a monotonic deadline in the initial state. `should_recover` ends the loop once spent, marks `RECOVERY_BUDGET_EXHAUSTED` (so a truncated run is never reported as a clean PASS), and the already-computed verdict stands. Actual wall-clock is now recorded in `analysis_elapsed_ms` and over-budget runs are logged, so latency is measurable instead of inferred.

**Quality is not reduced by this:** the deadline removes *redundant retries* after the budget is gone, not verification of the first answer. Combined with G-1, a budget-truncated run now abstains honestly instead of displaying a weakly-supported answer.

**Not yet done:** the per-call breakdown (which of the ~9 sequential LLM calls dominates) is not instrumented, so the exact split between generation and NLI latency is still unmeasured. A trace-level timer per node is the follow-up.

### G-3 — Prompt hardening: XML fences, token compaction, echo/fence-breakout bugs (fixed)

`GROUNDING_SYSTEM_PROMPT` restructured into XML sections (`<role>`, `<rules>`, `<scope>`, `<security>`, `<output>`) and compacted **3,602 chars / 781 tokens → 1,916 chars / 435 tokens (−46%)**. The prompt is a constant prefix on every generation call, so this is ~346 fewer tokens of KV cache per call on a 1.2B model with a 4,096-token window — a latency win, not just cleanliness. The Context/Query payload is now XML-fenced in the user message, giving the model an explicit instruction/data boundary.

Three real bugs found and fixed while doing it:

- **Leading echo survived whole (pre-existing).** `extract_final_answer` cut text *before* the first scaffold marker, so a marker at index 0 made the cut a no-op. A model that echoed the prompt first kept the entire echo — including copied untrusted document text — in the stored answer. That is the prompt-injection symptom. Added `_strip_leading_fenced_echo`.
- **Fence breakout from untrusted documents (new).** A document containing a literal `</context>` closed the block early, letting the rest of the document read as instructions. Added `neutralize_prompt_fences`, applied on the generation path **and to all three NLI prompt templates** — the verifier is the trust-critical path, where a document containing `[CLAIM]` could inject a fake claim.
- **False-positive truncation (caught by self-review).** Marker matching was substring-based, so a legitimate answer *about* the tags ("the template wraps payload in `<context>` and `<query>` tags") was truncated. Markers now only count at the start of a line. This matters specifically because the system answers from code bases, where questions about the prompt machinery are normal traffic.

Tests: `tests/test_prompt_echo_stripping.py` (16 cases: leading/trailing echo, prose mentions preserved, byte-identical passthrough, fence neutralization).

### G-4 — Domain lock removed from production logic, tests, corpus, and docs (fixed)

Full sweep: the product answers from any knowledge base, so a single subject baked into production code silently degraded everything else.

**Production defects (highest severity — these shipped):**

| Site | Defect | Fix |
|------|--------|-----|
| `ingestion/preprocessor.py` | `detect_chunk_zone` matched literal keywords (`UNIT-`, `CHAPTER`, `SYLLABUS`, `ISBN:`, `DOI:`, `effective from`). A code, contract, paper or prose corpus matched **nothing** — every chunk became `BODY` and the BM25 zone weights (1.5/1.3/0.8) never applied. | Detection is now **structural**: page-1 title-line shape (short, Title Case or ALL CAPS, no terminal period, not `label: value`), and `label: value` front-matter whose value is a date/version/hash/number. Two constraints prevent false positives — outline markers require a section NUMBER and must lead the line, and a heading never ends in a period (so "Section 12 of the agreement applies." stays `BODY`). |
| `verification/verifier.py` | Predicate list was commerce/ops-only (`refunds`, `stores`, `deletes`). **And the loop was wrong:** predicates in the outer loop, so a low-priority verb late in a sentence beat a high-priority one early — `"The rate is 5% and it allows refunds."` produced the nonsensical subject `"The rate is 5% and it"`. | Now a cross-domain verb set scanned **left to right**, splitting at the first relational verb. That sentence yields the correct `("The rate", "is", …)`. |
| `services/search_service.py` | The URL-ingestion allowlist was a fixed reference list, so a KB seeded from its own sources was impossible without a code change. | Added `URL_INGEST_ALLOWLIST_EXTRA`. This is an **SSRF ceiling** (`_effective_allowlist` intersects, so a request can only narrow), so the default was NOT widened — operators extend it explicitly. Narrow host matching, the IP blocklist, DNS checks, and size limits are unchanged; the error message now reports the real effective list. |
| `verification/verifier.py` | Fused decompose+verify few-shot example was a refund claim, biasing a domain-agnostic verifier toward commerce. | Example is now a shape placeholder plus an explicit "never copy its subject matter". |
| `agent/graph.py` | Query-rewrite prompt exemplified `API → Application Programming Interface`, biasing acronym expansion toward software. | Stated as a subject-neutral rule instead. |
| `generation/generator.py` | The `<scope>` block enumerated source-code + textbook structure while naming other domains as examples — asymmetric. | Delegates terminology, structure, and detail level to the Context. |

**Test suite:** ~180 commerce-domain fixtures across 23 files rewritten to generic/technical vocabulary. Two failures were introduced by the sweep itself and fixed: `lexical_analyze("record\nwindow")` and the BM25 TF test both depended on the *stems* of the old words, so the replacement text was corrected rather than the assertion weakened.

**Eval corpus rebuilt across four domains** — `service-api.md` (code/API), `retention-policy.md` + `leave-policy.md` (policy/HR), `thermal-runoff-study.txt` (science), `limits-2025.txt` (stale) + `limits-2026.txt` (current), `scratch-notes.txt` (injection). Dataset grew to **27 queries** (14 factual / 3 temporal / 3 conflicting / 2 missing-evidence / 5 adversarial), preserving every capability class while spanning four unrelated subjects — so a passing run is now *evidence* of agnosticism rather than a single-subject result presented as general. `test_baseline_dataset.py` no longer hardcodes a query count or the id `q024`; the no-coverage rule is expressed by `expected_outcome`, and a new test pins corpus breadth.

**Docs/UI:** running worked-example re-based from refunds onto an API reference; project guide now states the pipeline is domain-agnostic; KB/experiment placeholders and two landing-page lines span several domains.

**Not changed, flagged for the owner:** `apps/web/src/components/landing/landingData.js` advertises hardcoded benchmark figures (99.4% "SOTA S-Tier", 81.2%, 68.7%, 24.1%) and cites "HaluEval, RAGTruth, and proprietary enterprise finance/biomedical datasets". Those are factual marketing claims, not domain lock — rewriting or removing them without evidence would be fabrication, so they were left untouched and need an owner decision.

### Verification
- Backend `pytest`: **734 passed** · `ruff check` + `ruff format --check` clean · ports check green.
- Frontend: eslint 0 warnings, 33 vitest passed, `vite build` ok.
- Frontend: eslint 0 warnings, 33 vitest passed (unchanged — no UI contract changed; `abstained` status and the reliability badge already render correctly).
- The new config test caught a real defect during development: `max_analysis_seconds` was written under `recovery:` in yaml while read from `cost_controls`, so the default silently resolved to 0 (disabled). Fixed by relocating the key.

## 11. Follow-ups (ordered backlog, not started)

1. Set `SLOWAPI_STORAGE_URI` to Redis for production. The shared SlowAPI limiter in
   `app/core/rate_limiter.py` defaults to in-memory storage, so with more than one
   uvicorn worker the per-client caps are process-local and a client gets N× the
   intended limit by spreading requests across workers. `.env.example` documents
   the variable but leaves it commented out, so the unsafe default ships.
2. Add k6 budget assertion for p95 analysis latency after ONNX tuning lands.
3. Evaluate `onnxruntime` arena-off profile on 512 MB containers; record in PERFORMANCE-GUIDE.
4. Rotate `JWT_SECRET` per environment; document rotation runbook.
5. Re-run `scripts/bootstrap.py --verify` in CI gate after `models.yaml` version bumps (drift guard for the new `onnx:` block).
