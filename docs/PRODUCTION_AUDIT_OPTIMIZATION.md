# TRUSTRAG — Production Audit: Bugs, Errors, Issues, Optimization & Low-RAM Upgrades

Date: 2026-10-02 · Scope: full repo (backend / frontend / AI-ML / security / DevOps / QA)
Method: read code → grep for hardcoded IDs/secrets → verify call paths → fix root cause → test.

Config doctrine (CONTRIBUTING.md): **no model IDs in code** (`apps/api/config/models.yaml`
is the single source of truth), **no secrets in code or YAML** (`.env` only).

---

## 1. Critical (fixed in this pass)

| ID | Severity | Finding | Root cause | Fix |
|----|----------|---------|------------|-----|
| C-1 | HIGH | Hardcoded model-ID fallbacks in `app/core/config.py` (12× `or "…"` literals: `gemma3:1b`, `LiquidAI/LFM2…:Q4_K_M`, `mlx-community/…`, `gemini-3.5-flash-lite`, `BAAI/bge-small-en-v1.5`). Editing `models.yaml` did **not** update everywhere — the literal won whenever a yaml key was absent. | Defensive `or "literal"` tails on every resolver. | Removed all literal tails; resolvers now do required `models.yaml` lookups and fail fast (`KeyError`) when a key is missing. Env overrides (`OLLAMA_MODEL`, `LLM_MODEL`, `VERIFICATION_MODEL`, …) unchanged — env still wins. |
| C-2 | HIGH | `ONNXBGEEmbeddings.__init__` defaulted `tokenizer_name="BAAI/bge-small-en-v1.5"`, `max_seq_length=512`. A caller omitting args silently pinned the old model regardless of `models.yaml`. | Duplicated IDs at the engine layer. | Defaults → `None`; when `None`, resolved from `get_model_config().embedding_model` / `.embedding_max_seq_length`. Production caller (`model_registry.py`) already passes both explicitly — behavior unchanged. |
| C-3 | MEDIUM | `ONNXCrossEncoder` last-resort literal `tokenizer_name or "cross-encoder/…"` + `max_seq_length or 512` fired when config was broken, silently embedding the wrong model. | Same duplication pattern. | Fail fast: raise `RuntimeError` naming the missing `models.yaml` key instead of silently pinning a stale model. Normal path (config present, or explicit args) untouched. |
| C-4 | MEDIUM | Test helper `_make_embedder` hardcoded `tokenizer_name="BAAI/bge-small-en-v1.5"`; mock API keys (`"tvly-test-12345"`, `"test-gemini-api-key"`) read as hardcoded secrets. | Test doubles looked like real credentials / real config. | Helper default now resolves from `get_model_config().embedding_model`. All test keys marked `SYNTHETIC` in comments; `conftest.py` uses `os.environ.setdefault` so a real env value (CI secret) always wins over the dummy. No real secret ever committed (verified: `git log -S` pattern scan clean). |

## 2. Secrets & config — audit result

- Runtime: **clean**. All secrets (`JWT_SECRET`, `GEMINI_API_KEY`, `TAVILY_API_KEY`, `HF_TOKEN`, `MONGODB_URI`, `QDRANT_API_KEY`, …) flow `.env` → `Settings` → services. No `os.getenv("…_KEY")` outside `config.py`; no key literals in `app/`.
- Tests: **clean after C-4**. Remaining key-like strings are redaction test vectors (`test_wave2_cloud_resilience.py`, fake `AIza…`/`sk-…`) and mocks — all synthetic, all labeled.
- Known accepted duplication (documented, not fixed): `local_llm.py` Pydantic `Field(default=…)` mirrors `models.yaml` by design (schema defaults for standalone clients); `hardware.py` model names are advisory recommendation strings, never used for loading. Both carry comments pointing at `models.yaml`.

## 3. RAM & inference speed — what already exists (verified, not churned)

Single ONNX Runtime engine (torch-free, ~500–1000 MB RSS saved vs torch): shared session
factory `app/llm/onnx_runtime.py` (sequential exec, `ORT_ENABLE_ALL`, intra-op auto→min(cpu,4),
inter-op 1, CPU arena+mem-pattern on; every knob overridable via `ONNX_*` env).
Tier-aware micro-batching (lean 32 / std 64 / high 128, `ONNX_EMBED_MICRO_BATCH` to pin),
two-tier embedding cache (LRU + SQLite, model-namespaced), query-vector LRU shared with the
semantic cache, reranker result cache (500), adaptive Top-K cap (4 on RRF ≥ 0.02),
fused decompose+verify (1 NLI call instead of 2), claim caps per hardware tier,
`TOKENIZERS_PARALLELISM=false` + `MALLOC_ARENA_MAX=1`, local-LLM q8_0 KV cache + flash-attn
(`scripts/start_local_llm.sh`), model auto-unload after 5 m idle, `LOCAL_LLM_MAX_CONCURRENCY=1`.
Measured baseline (see git history for the 2026-10-03 pass; current status in docs/AUDIT_2026-10-04.md): API-ready ~4 s, RSS 178 MB → ~700 MB resident.

## 4. Bloat removed / modernization (this pass)

- **NVIDIA NIM provider removed** (user request): the provider was already half-dead —
  `settings.nvidia_api_key`, `cfg.supported_nvidia_models`, `cfg.nvidia_base_url` did not
  exist, `_create_llm` had no NIM branch (requests fell through to Gemini), and
  `GET /api/v1/models` + the analysis allowlist validator crashed on the dangling
  references. Removed end-to-end: `/models` entry, request-validator allowlist/override
  entries, ledger cloud-tuple entry, `langchain-nvidia-ai-endpoints` dep (+ `uv lock`
  resync, which also dropped 4 other stale lock entries nothing imports), all NIM/NIM-alias
  test paths, README/spec/guide mentions. Providers now: `ollama | llama_cpp | mlx | gemini`
  (+ `google_genai` env alias in ledger/verifier/kwargs paths).
- **DuckDuckGo search removed** (Tavily-only): the 4e47b72 commit deleted the function
  but left MCP tools, graph dispatch, the frontend selector, and 10+ tests dangling
  (selecting DDG 500'd at runtime). Removed `duckduckgo_search` + `hybrid_web_search`
  tools, graph always grounds via `tavily_search`, frontend shows a single Tavily badge.
  `sanitize_url` regained lightweight SSRF teeth (private/loopback/reserved IP literals
  + metadata hostnames, no DNS on the hot path).
- **URL document ingestion removed** (completing 4e47b72): the machinery was deleted but
  two endpoints (`documents/from-url`, `internal/ingest/url`), their schemas, the
  `URL_INGEST_ALLOWLIST_EXTRA` env, and 4 test files still referenced it (app would not
  even import). Endpoints + schemas + env + tests removed; uploads are the only intake.
- **Page-image chain implemented (TDD GREEN)**: `app/rag/ingestion/page_images.py` did not
  exist (RED tests specified it) and `kb_service` imported it, so **the app did not boot**.
  Implemented traversal-safe store (`PAGE_IMAGES_DIR` env-first), `GET
  /documents/{id}/pages/{page}/image` route, parser render-bytes handoff (gated on
  `ocr.store_page_images`), chunker propagation (already present), pipeline
  save-once-per-page + ref (bytes never leak into Mongo/Qdrant), snapshot copies owning
  COPIES, delete purges. (Note: commits 430eec1/4df200d deleted this feature; the
  operator chose RESTORE for a premium evidence-auditable product — history in git.)
- **Reranker restored** (reversing a3897b2): batching, early termination, adaptive
  Top-4, result cache, RRF fallback all test-pinned but deleted. Restored verbatim from
  git; the 8 reranker tests pass unmodified.
- **Query-vector LRU restored** (`retriever._query_cache`, bounded, capacity from
  `retrieval.query_cache_capacity`): feeds both `dense_search` and the graph's semantic
  prefetch — one ONNX embed per distinct query instead of per leg × round.
- **Strict bounded retrieval**: per-branch + hybrid timeouts restored
  (`RETRIEVAL_*_TIMEOUT` globals, env > yaml > 45s/60s fallbacks) with fail-loud
  `RetrievalOutageError` (partial evidence is never served silently); empty sparse
  vectors short-circuit to [] (stopword-only queries are valid empty, not outage).
  Dead `adaptive_top_k_*` knobs removed (yaml + config + env + tests); `config_version`
  bumped 1.23 → 1.24.
- **DOCX/HTML parsers restored** (stdlib + defusedxml, zero new deps): zip-bomb ratio
  guard, XXE-safe (entities raise, never resolve), PK magic check; HTML tag stripper
  dropping script/style. `supported_formats` promise (8 formats) holds again.
- **EICAR self-test restored** inside `scan_for_malware` (chunked, split-boundary safe):
  ClamAV-fail-open alone was theater on hosts without a daemon. `_detect_encoding`
  (head-sampled chardet) restored as the non-UTF-8 fallback path.
- **Dead-credential classification restored** in `_execute_with_fallback`: bare 401/403s
  and key-worded vendor errors terminate as `LLM_UNAVAILABLE` (shared helper, no more
  duplicated terminal block) instead of burning recovery rounds; current vocabulary
  kept (`LLM_OUTAGE` is gone everywhere).
- **Stale test module repaired**: `test_wave2_cloud_resilience.py` could not even be
  collected (imported `app.core.llm_outage`, deleted in the centralize-exceptions refactor;
  suite red at HEAD). Removed the 4 obsolete `classify_llm_exception` unit tests (outage
  behavior stays covered at graph level), aligned `google_genai` alias handling in
  `generator.py`/`local_llm.py` (`_invoke_kwargs_for_provider`, `calculate_dynamic_num_ctx`,
  `verification_cap_kwargs` now treat it as Gemini instead of raising/falling to local
  defaults), and fixed the NIM-era expectations. File collects and passes again.
- Frontend: no removable deps — `motion` (`motion/react`, 11 files) and `recharts`
  (DashboardPage) are both load-bearing (an early grep for `from 'motion'` missed
  subpath imports; the mistaken removal was reverted and versions re-pinned
  inside their original majors). Real frontend win: the dead 3-way search-provider
  selector is now a single Tavily badge (fewer states, honest UI).
- Backend: `tavily-python` retained (sole search provider). No other dead deps found.

## 5. Frontend production design (Apple-design + ui-ux-pro-max lens)

Verified already in place: centralized Axios client with JWT interceptor + 401 session clear,
SSE via short-lived stream tickets (JWT never in URL), `ErrorBoundary`, skeleton/empty/error
states on workbench components, `ReliabilityBadge` / `ClaimInspector` / `EvidenceViewer` with
distinct SUPPORTED / CONTRADICTED / NEUTRAL visuals, translucent toolbar material +
system-font stack, `prefers-reduced-motion` handling in `motionConfig.js`.
Next premium step (scheduled, §7 U-3): interruptible spring micro-interactions on the
Playground pipeline (response ≤100 ms on pointer-down, animate from presentation value).

## 6. Remaining issues (open, ranked)

| ID | Severity | Issue |
|----|----------|-------|
| O-1 | MEDIUM | `analysis_service.py` ~54% coverage — create/finalize branches need integration tests (plan exists: `ANALYSIS_SERVICE_TEST_GAPS.md`). |
| O-2 | MEDIUM | In-memory rate limiter multiplies its ceiling by worker count; wire Redis (`SLOWAPI_STORAGE_URI`) in the deploy template for multi-worker prod. |
| O-3 | LOW | `AnalysisResponse` hand-rolled `serialize_*` helpers (~80 lines) could use `model_validate` — deferred to avoid behavior risk. |
| O-4 | LOW | `hardware.py` recommendation strings + `local_llm.py` Field defaults still mirror `models.yaml` (accepted, commented). A `_DEFAULTS` sync test would lock them together. |

## 7. Upgrade queue (later, in order)

- **U-1 — Pinned ONNX env (speed + RAM):** run models under an `ONNX_*`-tuned env profile per
  host class. Lean ≤8 GB: `ONNX_INTRA_OP_THREADS=1|2`, `ONNX_CPU_MEM_ARENA=false`,
  `ONNX_MEM_PATTERN=false`, `ONNX_EMBED_MICRO_BATCH=32`, `RETRIEVAL_QUERY_CACHE_CAPACITY=256`,
  `RERANKER_BATCH_SIZE=8`; plus shell `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_FLASH_ATTENTION=1`,
  `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=5m`. Standard 16 GB:
  yaml defaults. GPU hosts: `ONNX_PROVIDERS=CUDAExecutionProvider,CPUExecutionProvider` (needs
  `onnxruntime-gpu`). All vars already honored — this is ops config, not code.
- **U-2 — Fewer LLM round-trips:** keep fused decompose+verify on; raise `max_verification_claims`
  only on cloud tier; never re-search CONTRADICTED claims (already policy).
- **U-3 — Playground premium motion:** spring-based pipeline transitions per Apple-design §4
  (critically damped default, bounce only on flick-driven sheets), token-stream rendering over
  existing SSE plumbing.
- **U-4 — Nightly live E2E:** promote `scripts/e2e_manual_verify.sh` to scheduled CI with a
  MongoDB service container.
- **U-5 — `_DEFAULTS` sync test:** one test asserting `local_llm.py` Field defaults and
  `hardware.py` recommendation IDs equal their `models.yaml` counterparts (kills O-4 drift).

---
*Single live tracker: this file (optimization/RAM/config) + `docs/AUDIT_2026-10-04.md` (current full pass)
+ `docs/EXECUTION_PLAN.md` (sequencing). Older point-in-time reports removed; history in git.*
