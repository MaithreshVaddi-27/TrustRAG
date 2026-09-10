# TrustRAG Senior Audit — Backend, AI/ML, Security, Optimization, Testing

**Date**: 2026-09-10 (Round 2 appended same day — live Playground trace diagnosis)
**Roles**: Senior Backend · Senior AI/ML · Senior Security · Senior Optimization · Senior Testing (blackbox + whitebox)
**Scope**: `apps/api` backend with emphasis on the RAG pipeline and local-LLM load (Ollama + llama.cpp); Round 2 adds Playground trace forensics + scoped Apple-design UI polish
**Status**: AUDITED · CRITICAL BUGS FIXED · RAG/LLM OPTIMIZATIONS APPLIED · 169/169 TESTS PASSING · RUFF CLEAN · FRONTEND LINT+15 TESTS+BUILD GREEN

> Note: the working tree contained uncommitted changes before this audit (config retunes,
> model-discovery hardening, ticket-based SSE auth). Findings below are against that working
> tree. One pre-existing failure caused by those changes (stale router test vs
> `max_recovery_attempts: 1`) is recorded as PRE-EXISTING and fixed here.

---

## 1. Executive summary

| Category | Critical | High | Medium | Low | Fixed in this audit |
|---|---|---|---|---|---|
| Backend correctness | 1 | 6 | 8 | 2 | 5 (+1 test) |
| AI/ML + local-LLM load | 1 | 4 | 5 | 1 | 6 opts |
| Security | 0 | 1 | 5 | 3 | 1 (+1 test) |
| Testing (whitebox/blackbox) | 0 | 1 | 1 | 0 | 2 tests fixed + 1 added |
| **TOTAL** | **2** | **12** | **19** | **6** | **15 code + 3 test changes** |

The single most serious finding was **CRIT-1**: `app/agent/graph.py` did not compile
(`IndentationError` in `recovery_node`), so the entire LangGraph recovery workflow — the
product's core differentiator — could not even be imported. Fixed and compile-verified.

---

## 2. Critical findings (fixed)

### CRIT-1 — `app/agent/graph.py:890-892` — recovery_node did not compile (FIXED)
- **Severity**: Critical. **Evidence**: `python3 -m py_compile` →
  `IndentationError: expected an indented block after 'except' statement on line 890`.
- **Root cause**: the `except` body (`logger.error`, `state[...] = None`) was dedented to the
  `except` level. Any import of the graph module raised.
- **Fix**: re-indented the `except` body; compile now passes (`ALL_COMPILE_OK`).

### CRIT-2 — `app/agent/graph.py:817-855` — dead `query_rewrite` branch, wasted recovery round (FIXED)
- **Severity**: Critical (correctness + LLM load). **Evidence**: the `try/model.ainvoke` block
  was nested inside the `else:` (abstain/insufficient-context) branch, so whenever
  `missing_claims` was non-empty — the common failure case — the rewrite prompt was built
  and then **never invoked**; the graph looped `recovery → retrieval → generation →
  verification` on the identical query, burning one full ~9-call pipeline per failed analysis.
- **Fix**: dedented the `try/except` so both prompt variants invoke the model, and set
  `current_query` / `recovery_strategy` / trace event on success with fallback to the
  original query on failure.

---

## 3. High findings (fixed or mitigated)

| ID | Location | Issue | Action |
|---|---|---|---|
| HIGH-1 | `retriever.py:425-430` | Naive vs aware `datetime` comparison (`datetime.now(UTC)` vs legacy naive Mongo dates) raised `TypeError` → retrieval 500 | FIXED: normalize naive bounds to UTC-aware before comparing |
| HIGH-2 | `generator.py:250-264` | `response.content=None` became the literal answer `"None"`, stored and verified as a claim | FIXED: return `ABSTAIN` on `None` content |
| HIGH-3 | `generator.py:283-286` | All exceptions (auth/config/outage) masked as `ABSTAIN`, corrupting verdicts | RECORDED: left as-is intentionally (reliability-first abstention is spec §32); outage paths (`RetrievalOutageError`) already bypass it. Revisit only with an error-taxonomy change |
| HIGH-4 | `local_llm.py:39-51` | Pooled `AsyncClient` keyed on recyclable `id(loop)`; unbounded per-timeout entries | RECORDED: mitigated by shutdown hook + single local concurrency (OPT-4); full key redesign deferred (risk > benefit this round) |
| HIGH-5 | `local_llm.py:594-651` | `asyncio.wait_for(proc.communicate(), 4s)` timeout left zombie `ollama`/`llama-server` procs | FIXED: `proc.kill()` + `await proc.wait()` on `TimeoutError` in both discovery functions |
| HIGH-6 | `local_llm.py:71-105` | Unknown message types silently dropped → empty prompts to local models | FIXED: `str` passthrough, warning on unsupported types, `ConfigurationError` on empty prompt |
| HIGH-7 | `retriever.py:462-471` | Unbounded `asyncio.gather` (dense+sparse) could pin a worker forever | FIXED: 60s `wait_for` budget, raises `RetrievalOutageError` on timeout |
| HIGH-8 | `semantic_cache.py:197-276` | Cache key `(query, kb_id)` ignored embedding space; stale answers served after re-index; mixed dims could break matmul | FIXED: `embedding_model` namespacing on check+store, dim-equality filter on both fast and vector paths; graph passes `provider:model` |
| HIGH-9 | `analyses.py:165-183` | `POST /{id}/stream-ticket` issued tickets without ownership/existence check → ticket/Mongo spam for foreign IDs | FIXED: `get_analysis(id, user_id)` ownership check before issuance; added `test_stream_ticket_requires_ownership` (404 on foreign ID) |

---

## 4. Medium findings

- **MED-1** `retriever.py:191` cache key unnormalized → repeat embeddings. FIXED (lower/strip).
- **MED-2** `disk_cache.py:45-47` key case-sensitive → repeat embeddings. FIXED (lower/strip).
- **MED-3** `graph.py:205-206` recovery doubled `top_k` (20→40) then generation capped at 8. FIXED — see OPT-3.
- **MED-4** `verifier.py:485-498` sequential per-claim fallback, no early-exit. FIXED — see OPT-2.
- **MED-5** `local_llm.py:641-650` blocking sync `glob` in async status path. RECORDED (4s-budgeted startup/diagnostic path only; `to_thread` refactor deferred).
- **MED-6** CORS credentialed + wildcard `vercel.app/pages.dev` regex (`main.py:364-372`). RECORDED, not changed (deployment choice; recommend explicit origins).
- **MED-7** Suffix-only upload validation, no decompression-bomb caps (`knowledge_bases.py`, `parser.py`). RECORDED, not changed (20 MB compressed cap exists; per-entry inflation caps recommended next).
- **MED-8** Prompt-injection defense is instruction-only, markers unescaped (`generator.py`). RECORDED (spec §12 architecture; output-policy filter recommended next).
- **MED-9** In-memory rate-limiter counters are per-worker (`rate_limiter.py:67`). RECORDED (correct for local-first single worker; Redis needed only for multi-worker prod).
- **MED-10** `X-Request-ID` reflected/logged unsanitized (`main.py:330-334`). RECORDED (validate + truncate recommended).

Checked and PASS (no change): bcrypt-12 + 72B cap + complexity rules; IDOR ownership on
documents/KB/analyses reads; SSRF allowlist-intersection + DNS re-resolve + IP pin;
path traversal (`Path().name` + null-byte strip); XXE (`defusedxml`); secret leakage
(boolean flags only); `.env` untracked + ignored; `models.yaml` secret-free.

---

## 5. Local-LLM load optimizations (RAG backend)

Per-analysis fan-out before this audit: up to **9 sequential LLM calls**
(generate → decompose → batch NLI → batch retry → up to 5 full-context fallbacks),
plus a wasted recovery round (CRIT-2) and 2× retrieval on recovery.

| ID | Change | Location | Expected effect |
|---|---|---|---|
| OPT-1 | Generation context budget `5500 → 3000` chars | `generator.py:137-140` | Fits local `num_ctx`; kills truncated-stub degenerations that triggered retries/recovery |
| OPT-2 | Ollama `num_ctx` `2048 → 4096` (matches `llama-server -c 4096`) | `local_llm.py:199` | Same: ends context-overflow stub loop on 3B models |
| OPT-3 | Recovery widen capped: `top_k=min(2×dense, ctx+16)`, `max_ctx=min(2×ctx, ctx+4)` | `graph.py:203-211` | ~50% less Qdrant/rerank/Mongo per recovery (defaults: 40→24, 16→12) |
| OPT-4 | LLM-level `asyncio.Semaphore(1)` around local `_agenerate` (+ `LOCAL_LLM_MAX_CONCURRENCY`, documented in `.env.example`) | `local_llm.py:44-53,221-234,397-400` | Serializes the serial server; ends 18-way pile-up timeout cascades from 2 concurrent analyses |
| OPT-5 | Verification early-exit: contradiction rate already over threshold → `fallback_budget=0` | `verifier.py:480-498` | Saves up to 5 full-context calls on already-failed analyses (the hottest path) |
| OPT-6 | Normalized embedding cache keys (retriever LRU + SQLite disk cache) | `retriever.py:191-196`, `disk_cache.py:45-49` | Fewer repeat BGE forward passes on case/whitespace variants |
| OPT-7 | (No code) ranked follow-ups for next round: 2×4-claim NLI micro-batches; high-confidence (≥0.97) semantic-hit bypass of decomposition/NLI; batched self-heal re-index (64–128); end-to-end timeout alignment | — | Documented, not implemented (behavioral changes needing eval) |

---

## 6. Test report (blackbox + whitebox)

- `ruff check app/ tests/` — **clean**. `ruff format --check` — **clean** (1 auto-reformat applied to `graph.py`).
- `pytest tests/ -q --no-header --no-cov` — **162 passed** (was 159 passed + 2 failed on arrival; +1 new test).
- **PRE-EXISTING failure (not caused by this audit)**: `test_should_recover_router` assumed
  `max_recovery_attempts=2`; working-tree `models.yaml` sets `1`. Made the test config-aware.
- **Caused-by-fix updates**: stream-ticket tests patched for the new ownership check
  (`analysis_service.get_analysis` mocked); added `test_stream_ticket_requires_ownership`.
- Manual verification: `py_compile` on all 8 touched source files — OK.

---

## 7. Files changed

- `apps/api/app/agent/graph.py` — CRIT-1, CRIT-2, OPT-3, semantic-cache wiring, unused-import cleanup
- `apps/api/app/retrieval/retriever.py` — HIGH-1, HIGH-7, MED-1
- `apps/api/app/generation/generator.py` — HIGH-2, OPT-1
- `apps/api/app/core/local_llm.py` — HIGH-5, HIGH-6, OPT-2, OPT-4
- `apps/api/app/verification/verifier.py` — OPT-5
- `apps/api/app/core/semantic_cache.py` — HIGH-8
- `apps/api/app/core/disk_cache.py` — MED-2
- `apps/api/app/api/v1/analyses.py` — HIGH-9
- `apps/api/tests/test_agent.py` — stale ceiling fixed (config-aware)
- `apps/api/tests/test_analyses.py` — ticket tests updated + ownership test added
- `.env.example` — `LOCAL_LLM_MAX_CONCURRENCY` documented

## 8. Round 2 — live Playground trace forensics (user-reported abstention)

Trigger: `what are steps of IRS?` → ABSTAINED, 16 evidence chunks, 0 claims
(analysis `6aa29c7b…77584d47`, `llama_cpp` EXAONE-3.5-2.4B). Method: Mongo forensics
on `analyses` / `claims` / `evidence` / `trace_events` + context-budget replay.

Findings:
- R1. Retrieval is HEALTHY: 16 VERIFIED chunks incl. the answer text ("the first
  step in any IRS is item normalization…"). The model refused twice (initial +
  recovery) → 0 claims → ABSTAIN per spec. Same query also abstained on 2026-09-08
  with SmolLM3-3B under the old 5500-char budget → the OPT-1 budget cut (5500→3000)
  is NOT the cause; small-model refusal on this query predates it.
- R2. Diagnosis label is misleading: stored as `RETRIEVAL_FAILURE / "Model abstained:
  insufficient grounded evidence"` while retrieval returned 8 verified segments
  twice. Generation-side refusal is misfiled as retrieval failure (cosmetic;
  verdict math unaffected). Recommend a `GENERATION_ABSTAIN` diagnosis type.
- R3. NEW BUG (fixed): with the CRIT-2 fix live, `query_rewrite` ran for the first
  time — and the 2.4B model returned an EMPTY rewrite, producing `Searching knowledge
  base for query: ''` (full wasted retrieval+generation round). Fixed with an
  empty/short-rewrite guard that keeps the original query (`graph.py`), plus the
  `recovery.rewrite` trace event now fires only on success.
- R4. NEW OPT (fixed): `re_retrieve` downgrades to `regenerate` on identical chunks,
  and the model had already answered ABSTAIN → certain repeat refusal costing a
  full local generation (~60s). Added a futile-regeneration guard in
  `generation_node`: regenerate + prior ABSTAIN + unchanged chunks → skip with a
  `generation.skipped` trace event (retrieval already short-circuits on regenerate).
  Non-ABSTAIN failed answers still retry as before (both paths covered by tests).
- R5. ENV OBSERVATION: at diagnosis time neither llama-server (:8080) nor Ollama
  (:11434) was reachable. Users hitting Run with the server down previously burned
  minutes of 120s timeouts before abstain/fail. Fixed, see §9.

## 9. Round 2 — local-server offline alert + phantom-model cleanup (fixed)

- S1. `POST /api/v1/analyses` now preflights local providers
  (`probe_local_llm_server`, ~3s): stopped server → synchronous **503
  `LLM_UNAVAILABLE`** naming the base URL + exact start command
  (`ollama serve` / `./scripts/start_local_llm.sh`), via a new exception handler in
  `main.py` that surfaces the (secret-free) message instead of the generic 503.
  Background pipeline already mapped mid-run connection loss to `analysis.failed`.
- S2. llama.cpp selector over-listed: `/v1/models` (actually loaded) was unioned
  with `--cache-list` + HF-hub GGUF scan (downloaded ≠ servable — llama-server
  serves only `--model`), so phantom models were selectable and failed at
  generation. When connected, the list is now exactly the API set; cache/HF remain
  as offline fallback + `cache_models` field. `merge_discovered_llms(..., replace=True)`
  prunes uninstalled models on every successful refresh (empty refresh never wipes).
  Ollama union unchanged (every pulled model is servable on demand).
- S3. Frontend: Playground shows an amber **"Inference server offline"** alert with
  the per-provider start command + Recheck button when the selected local provider
  reports `connected:false`; `handleSubmit`/`fetchFinalAnalysis` now read the
  backend `{error:{code,message}}` shape so the 503 instruction text actually renders
  (previously fell through to "Request failed with status code 503").
- Tests added (7): probe up/down, merge-replace + empty-no-wipe, connected-API-only
  listing, 503 preflight, skip/futile-regenerate pair. Suite: **169 passed**.

## 10. Round 2 — scoped Apple-design UI polish (skill applied)

Applied from the `apple-design` skill where it earns its place, without redesigning
working screens: warning-before-problem offline banner (feedback kind: warning);
critically-damped spring enter (`bounce: 0, duration: 0.35`) on the banner, matching
the existing `whileTap: 0.95` press feedback; tight tracking on the banner title;
global `:focus-visible` ring (keyboard path for every pointer path). Verified:
`npm run lint` clean, 15/15 Vitest green, `npm run build` succeeds. Deliberately
deferred: gesture-driven sheets/carousels (no such component), haptics/audio
(utility rule — no meaningful moment), full-type-scale retune (needs design review).

## 11. Residual risks / next round

1. `lru_cache` on user-controlled model strings can pin HF models/HTTP clients (RAM/GPU leak) — needs bounded registry with eviction + close.
2. `InMemoryCache` LLM cache is unbounded and keyed on never-repeated NLI prompts — scope to generation or key on `(query, chunk-hash)`.
3. `graph.py` self-heal path loads/embeds/upserts up to 10k chunks in one shot — batch (64–128) with progress events.
4. SQLite `set_cached_embedding` per-vector connections in `aembed_documents` N+1 loop — batch writes in one transaction.
5. `ru_maxrss` memory guard reads peak, not current — switch to `psutil` RSS.
6. In-process SSE pub/sub breaks under multi-worker — external bus (Redis) if workers > 1.
7. Upload validation (magic bytes, per-entry inflation caps) + `X-Request-ID` sanitization + explicit CORS origins before internet exposure.
