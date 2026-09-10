# TrustRAG Senior Audit — Backend, AI/ML, Security, Optimization, Testing

**Date**: 2026-09-10 (Round 2 appended same day — live Playground trace diagnosis)
**Roles**: Senior Backend · Senior AI/ML · Senior Security · Senior Optimization · Senior Testing (blackbox + whitebox)
**Scope**: `apps/api` backend with emphasis on the RAG pipeline and local-LLM load (Ollama + llama.cpp); Round 2 adds Playground trace forensics + scoped Apple-design UI polish
**Status**: AUDITED · CRITICAL BUGS FIXED · RAG/LLM OPTIMIZATIONS APPLIED · 191/191 TESTS PASSING · RUFF CLEAN · FRONTEND LINT+21 TESTS+BUILD GREEN

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

## 11. Round 3 — Playground production-detail pass (screenshot-driven, skills applied)

Source: user screenshot of `/playground` mid-run. Skills: `apple-design` (motion,
materials, type, warning-feedback) + `frontend-ui-engineering` (a11y, system
adherence, verification checklist). No backend changes this round.

Formatting/content defects fixed (all verified against the screenshot):
- U1. Topbar showed the SERVER DEFAULT model (`llama.cpp: ibm-granite/granit…`,
  truncated) while the run used the Playground selection (EXAONE). Playground now
  publishes `{provider, model, embedding*}` to `localStorage` +
  `trustrag:engine-change` event; AppLayout pills show the effective selection with
  a cyan (Playground) / slate (server-default) source dot and full-id tooltips.
- U2. HUD model chip + Stage-3 subtitle rendered full GGUF ids across 3 lines,
  breaking card rhythm. New `src/lib/modelLabels.js` (`shortModelId`,
  `providerShortLabel`: `EXAONE-3.5-2.4B-Instruct`, `granite-4.2-3b`,
  `bge-small-en-v1.5`) used in HUD, results header, topbar; full ids kept in
  `title` tooltips. Cards back to uniform 2-line rhythm with ellipsis.
- U3. Event stream noise: backend emits lifecycle pairs plus summary events
  ("Retrieval completed" ×2, "…successfully" tautologies). New
  `compactTraceEvents` (collapse consecutive same-type, keep richest message) +
  `displayMessage` (suppress label-restating messages) in `traceEvents.js`,
  applied to the feed, the "N events logged" pill, and the HUD counter so all
  three agree. Timestamps now always visible (tabular-nums, `HH:MM:SS`) instead
  of hover-only.
- U4. Missing trace metadata: added EVENT_META for `retrieval.outage`,
  `generation.skipped` (Round 2), `cache.hit`, `recovery.started/completed`,
  `recovery.skipped` — previously fell back to raw `snake.case` labels.
- U5. HUD `isRecovering` checked a non-existent `recovery.expanded` event; now
  matches the real set (`recovery.rewrite/re_retrieve/regenerate/started`).
- U6. Embedding dropdown rendered `BAAI/bge-small-en-v1.5 (384d SOTA) [Recomm…`
  (truncated). Options now read `bge-small-en-v1.5 · 384d — Recommended` with
  full-id tooltips. LLM native select keeps full ids (accuracy over brevity in
  form controls).
- U7. Global `:focus-visible` ring (keyboard path for every pointer path).
Verification: `npm run lint` clean, Vitest 20/20 (new `modelLabels.test.js`, 5 tests),
`npm run build` succeeds. Other pages swept for the same truncation class — none found.

## 12. Round 4 — ultra-low-RAM techniques (web research + implementation)

Researched current (2026) llama.cpp/Ollama memory practice: KV-cache quantization
(`-ctk/-ctv q8_0`, `OLLAMA_KV_CACHE_TYPE=q8_0`) halves KV RAM at negligible quality
cost and must travel with flash-attention; `-c` is a TOTAL shared budget allocated
up front (never over-reserve); `-np` slots share that budget and compete for
bandwidth — serial clients (`LOCAL_LLM_MAX_CONCURRENCY=1`) are what keep a 4096
per-request window safe on a `-c 4096` server; `OLLAMA_MAX_LOADED_MODELS=1` on 8GB
(default keeps 3 models resident); `OLLAMA_NUM_PARALLEL` multiplies KV by N.

Applied (all local-only; cloud paths untouched):
- L1. `hardware.py`: `-ctk q8_0 -ctv q8_0` on Metal + CUDA launch paths (FA already
  on there — the required companion). CPU-only path keeps f16 (no FA → dequant
  overhead). Biggest server-side win: ~50% smaller KV reservation.
- L2. Task-sized output caps via new `local_cap_kwargs()` (`local_llm.py`), which
  returns `{}` for cloud providers so foreign params never leak to Gemini/NVIDIA:
  rewrite 128 (graph `bind`), decompose 768, batch NLI 768 (deliberately generous —
  a truncated batch JSON costs a retry + 5 fallbacks), single NLI 384. Generation
  stays 1024 (answer quality). Smaller `num_predict` = smaller per-call KV growth
  + shorter wall time on every one of the ~9 calls/analysis.
- L3. `Dockerfile`: `TOKENIZERS_PARALLELISM=false` (no forked tokenizer thread pool
  next to torch + embedded Qdrant). Docker already pins `--workers 1`, so torch/BGE
  can never double-load in two workers; lifespan embedding warmup closes the
  first-request race.
- L4. `.env.example`: documented Ollama-server env block (`KV_CACHE_TYPE`,
  `FLASH_ATTENTION`, `MAX_LOADED_MODELS=1`, `NUM_PARALLEL=1`, `KEEP_ALIVE`) —
  server-side vars, clearly labeled as not backend-read.
- Tests added (4): Metal KV flags, CPU-path exclusion, `local_cap_kwargs`
  provider matrix, local caps on all three structured calls, cloud no-cap proof,
  rewrite `bind(max_tokens=128)` assertion. Suite: **173 passed**.

Deferred (evaluated, not taken): ONNX BGE runtime (replaces torch+s-t, but a
migration with parity eval — needs its own round); `-np 1` on lean tier (saves
nothing — `-c` is the reservation, and `-np 2` preserves direct-server use);
`--cache-ram` spill (30-50% slower; wrong trade on 8GB unified memory);
`OLLAMA_CONTEXT_LENGTH` override (per-request `num_ctx` already governs spend).

## 13. Round 5 — DEFAULT-model runs, repeat-refusal short-circuit, heat triage

Trigger: `What are steps in DataMining?` → ABSTAINED/FAILED ("No claims extracted"),
HUD + header showing `llama.cpp: DEFAULT`; host heating/hanging (load avg ~4.7,
only ~2GB free of 8GB; 65s + 117s generations on a 2-3B model = thermal-throttle
spiral; no inference server process found running at diagnosis time).

Fixed:
- D1. Fresh page loads never selected a model (`selectedModel` stayed `""` until
  first click) → runs went out model-less and rendered DEFAULT everywhere.
  Playground now auto-selects the discovered provider default one-shot (never
  clobbers a user pick). Covered by new `PlaygroundPage.test.jsx`.
- D2. Analysis docs stored raw nullable `llm_model` (`""`) → provenance said
  DEFAULT. `create_analysis` now persists + executes + traces the EFFECTIVE
  engine (`schema ⩔ cfg` resolution), so doc, trace, HUD, and dossier agree.
- D3. Empty rewrite after an already-refused answer repeated a full
  retrieval+generation round (~2 min, all heat). Now routes through `regenerate`
  (retrieval short-circuits) with the ABSTAIN marker restored so the
  futile-generation guard skips the repeat call — the round costs one rewrite
  call. Real-answer failures still re-retrieve as before. (Implementation note:
  recovery clears `answer` first, so the guard keys off a `prior_answer`
  snapshot — the first version keyed off cleared state and could never fire.)
- Tests: 2 recovery short-circuit tests, effective-engine assertions,
  Playground auto-select test. Suite: backend **175 passed**, frontend **21 passed**.

Heat/hang triage (this machine): the applied cuts (KV-quant flags — NEED A SERVER
RESTART to take effect; task token caps; LLM semaphore; skipped futile rounds)
shrink both peak RAM and sustained full-tilt minutes, which is what cooks an 8GB
host. Remaining guidance: restart llama-server via `scripts/start_local_llm.sh`
(new flags print on launch), prefer the 3B granite default over 2.4B EXAONE for
instruction-following per watt, and optionally cap mongod (`wiredTiger
engineConfig cacheSizeGB: 1` — default sizes to ~3.5GB on 8GB). Lean-tier
analysis concurrency stays 2 (LLM already serialized; lowering it cuts throughput
without cutting total work). Thread caps (`-t`) deliberately untouched — a speed
trade with no measurement behind it.

## 14. Round 6 — refusal-gate cascade (AI/ML optimization, web-grounded)

Trigger: `what are steps in Information Retrevial system?` on granite-4.2-3b →
41s decomposition → `claims.empty` → full repeat round on the identical query.
Short labels + counts now render correctly (Rounds 3/5 verified live).

Analysis: the model didn't emit ABSTAIN — it hedged in prose, so every guard
missed it: decomposition burned 41s of throttled inference to return [], batch
NLI was skipped only by the empty-claims accident, and the rewrite came back
empty (twice across models — 2-3B models routinely blank on terse prompts).
Research consensus applied: (a) cascade architecture — deterministic filters
first, LLM as escalation only ("deciding what never reaches the LLM"); (b)
refusal-first RAG — a hard pre-inference gate beats a prompt plea; (c) never
blind-retry empties at temperature 0 (same output, doubled bill).

Applied:
- G1. `is_refusal_answer()` (`verifier.py`, 10 conservative regexes + ABSTAIN):
  hedged answers skip decomposition AND batch/fallback NLI entirely and take the
  existing FAIL→recovery/abstain path. False-positive cost is bounded by design
  (a misread FAILs into recovery, which can still regenerate and pass — the gate
  never asserts). Saves 1-7 LLM calls on every refusal (~1-4 throttled minutes).
- G2. Empty-rewrite short-circuit extended from exact-ABSTAIN to any refusal via
  the same helper; `prior_answer` snapshot retained (recovery clears state first).
- G3. Decompose cap 768→512 (≤15 short claims fit; loopers hit the wall sooner;
  truncation degrades to bounded single-claim fallback).
- G4. Both rewrite prompts gained "Never reply empty; if unsure, return the
  original query with spelling corrected" (also covers the `Retrevial` typo class).
- Tests: refusal matrix (incl. grounded-text non-matches), verification skip
  (execute not called), hedge-rewrite short-circuit. Suite: **178 passed**.

What this trace costs now: generation → refusal gate (0 calls) → rewrite (1 short
call) → empty + refusal → regenerate short-circuit (retrieval.reused,
generation.skipped, 0 calls) → abstain. From ~9 calls / ~4 min to ~2 calls.

Remaining (needs your terminal): backend logs stream to stdout only (no file
appender — confirm rewrite-empties vs errors via the `Query rewrite returned
empty` / `failed` log lines); restart llama-server for Round-4 flags; if
decompositions still crawl, the host is thermally throttled — cool it before
judging latency.

## 15. Round 7 — trailing-ABSTAIN poisoning + batch-failure design flaw (forensics)

Trigger: pasted answer — a GOOD grounded IRS overview ending in a stray `ABSTAIN`
token — surfaced as failed/abstained (analysis `6aa2baf0`, LFM2.5-1.2B). Mongo
forensics: status `completed`, reliability FAILED, `LOW_COVERAGE 0/5 supported`;
all 11 persisted claims read "Verification service unavailable or quota limit
reached." Control: gemini-3.5-flash-lite on the same query → TRUSTED 1.0. So the
KB is fine; the local path failed twice, in two distinct ways:

- F1. **Batch total-failure poisoned the individual fallback (design flaw).**
  `batch_verify_claims_nli` caught everything and returned all-NEUTRAL rows, so
  `execute`'s `if i in results_map` was always true and the budgeted per-claim
  fallback (smaller prompts, higher tiny-model success) NEVER ran — while the
  retry-on-raise code above it was dead. Fix: batch raises on total failure
  (partial maps unchanged), restoring retry-once → budgeted-individuals. No test
  depended on the poison rows. On this answer the claims read as genuinely
  supported, so the same run would plausibly verify instead of 0/5 FAIL.
- F2. **Stray trailing ABSTAIN token.** Small models append the token instead of
  emitting it alone. New `strip_stray_abstain()` (`generator.py`, wired into
  generation): drops trailing blank lines + bare uppercase ABSTAIN tokens,
  returns "ABSTAIN" only when nothing substantive remains; lowercase prose
  endings ("...right to abstain.") provably survive (tested).
- Production-readiness files: `.env.example` gained the missing documented
  surface (APP_ENV, LOG_LEVEL, JWT_EXPIRY_MINUTES, base-URL + provider/model
  overrides incl. KB-pin warnings, SEARCH_PROVIDER); `.gitignore` gained
  `.history/`, `*.code-workspace`, `.tool-versions`,
  `docker-compose.override.yml` (verified `apps/api/uv.lock` tracking +
  existing coverage — no other gaps found); README endpoint table completed
  (`detail`, `stream-ticket`, `models/*`) and upload formats corrected to the
  true seven.
- Tests: batch-raises, batch-failure→individual-recovery, stray-ABSTAIN matrix.
  Suite: **181 passed**.

## 16. Round 8 — local-LLM claims rescue + push readiness (screenshots)

Trigger: SmolLM2-1.7B run (`00f7855b`) — fluent 384-word answer, 16 VERIFIED
chunks, yet `completed/FAILED 0% / 0 assertions`; rewrite visibly polluted:
`Searching knowledge base for query: 'Expanded Search Query: What are…'` (the
model echoed the instruction frame and it was searched literally).

Forensics + fixes (claims for local LLMs):
- C1. **Empty-structured backstop.** ≤3B models return valid-but-empty
  `{"claims": []}`; the pipeline previously accepted it → claims.empty. Now a
  deterministic sentence split (zero LLM calls, same >40-char bar as the blob
  path, meta-filtered, capped) feeds NLI — every piece still verified, NEUTRAL
  when unsupported. The pasted answer would have produced ~9 sentence-claims.
- C2. **Rewrite sanitization.** `_sanitize_rewritten_query()` strips
  `Expanded/Rewritten/Search Query:` prefixes, wrapping quotes, and whitespace
  collapse — applied before state, trace event, and retrieval. The polluted
  query from the screenshot now searches cleanly.
- C3. **Prompt bias fix.** Both rewrite prompts used `IRS → Internal Revenue
  Service` as the acronym example — on a KB where IRS means Information
  Retrieval System this actively mis-expands (visible in the answer text).
  Replaced with a neutral API example; regression test asserts the tax-agency
  string never reappears.
- Cleanup: deleted 1332 lines of dead code — `core/secrets_manager.py` (Vault/
  SOPS/Age backends, zero importers) and `core/context.py` (ContextManager
  family; prior audits already record its removal from the loop) + one stale
  comment. Frontend orphan scan: none. No other unreferenced modules found.
- Docs: `.env.example` completed (APP_ENV, LOG_LEVEL, JWT_EXPIRY_MINUTES, base
  URLs, all provider/model overrides, SEARCH_PROVIDER); `.gitignore` +4
  (`.history/`, `*.code-workspace`, `.tool-versions`,
  `docker-compose.override.yml`); deployment env table completed; architecture
  recovery diagram + guardrails updated to match code; README endpoints/formats/
  counts synced.
- Push readiness: no secrets tracked (placeholders only), `.env` untracked,
  CI runs lint+format+tests+ports+models.yaml checks, tree contains exactly the
  audit work (27 modified + 2 deleted + 3 new files, zero CRLF noise).
- Tests: backstop (empty→sentences, refusal stays empty), batch-raises,
  batch-failure→individual-recovery, stray-ABSTAIN matrix, sanitize + prompt
  unit tests. Suite: backend **185 passed**, frontend **21 passed**.

## 17. Round 9 — cloud embeddings removed + new-user path (D-19)

Trigger: zero-key operation for new users; Gemini/NVIDIA embeddings deleted
project-wide. Recorded as ADR D-19 in `docs/architecture/decision-log.md`.

Removed (LLM-side Gemini/NVIDIA untouched — generation/verification only):
- `model_registry.py`: NVIDIA + Gemini embedding branches deleted; retired
  guard now accepts only huggingface/local/splade with re-upload guidance.
- `config.py`: cloud default branches + `GEMINI_EMBEDDING_MODEL` alias deleted.
- `schemas/analysis.py`: allowlists huggingface-only (`local` alias kept);
  empty-discovery now fails closed with install instructions (new-user 422).
- `analysis_service.py`, `ingestion/pipeline.py` (Gemini pacing sleep),
  `config/models.yaml` comment, `/models` endpoint (huggingface entry only).
- UI: provider buttons → static Local BGE card; Settings cloud cards deleted;
  legacy cloud-KB pins show re-upload guidance instead of a snap button;
  KB-pin auto-snap guarded to local models only.
- Docs: README (loop diagram, RRF, discovery, embedding engines, setup.sh
  step), deployment guide (diagnostics + cold starts), architecture diagram,
  deployment env table.

New users (`scripts/setup.sh`, new, verified exit 0 on this host): checks
toolchain, .env + JWT strength, venv, node_modules, MongoDB reachability,
inference-server presence, port availability — then prints exact boot commands.
Defaults are fully local (llama_cpp + BGE + embedded Qdrant); BGE weights
auto-download once. Migration note: KBs indexed with retired providers must be
re-uploaded (backend 422 + UI banner say so explicitly).
- Tests: retired-cloud rejection, new-user guided 422, mismatch-via-MiniLM,
  updated provider-matrix expectations. Suite: backend **187 passed**,
  frontend **21 passed**; ruff/eslint/build green.

## 18. Round 10 — chunk/dedup quality (context forensics on DM-U1.pdf)

Trigger: pasted generation context — format correct (`Segment N [Source, Page]`
headers intact, numbering aligned) but content defective: mid-word cuts
("sures 7.", "ead, user", "an be used") and near-duplicate segments 7/8/9
surviving side by side.

Root causes (both confirmed in code):
- W1. `chunker.py` used fixed character windows — cuts land inside words,
  polluting BM25 sparse tokens and displaying broken fragments.
- W2. Generation-time dedup keyed on raw 20-word prefixes, so
  punctuation-only variants ("mined. in" vs "mined in") compared unequal and
  each consumed context budget.

Fixes (coverage-safe by construction, no re-index needed — only new uploads
chunk differently):
- W1. Word-boundary windows: end snaps back to whitespace (bounded by the
  overlap so the next window still overlaps — no gaps); start advances over a
  leading fragment only when the previous window covered those characters;
  overlong tokens keep the hard cut. Loop-termination and `character_offset`
  bookkeeping preserved.
- W2. Dedup key is now punctuation-insensitive; the 7/8/9 triple collapses to
  one segment, freeing budget for genuinely different evidence.
- Tests: no-fragment windows, full-coverage (300 words, zero missing),
  long-token fallback, punctuation-variant collapse. Suite: **191 passed**.

## 20. Round 11 — UI refinement: Apple-design fluid motion + prompt replacement

### Changes

**A. Quick Prompts replaced (QueryPanel.jsx:8-12)**
- Original: domain-specific policy/compliance questions (cancellation policy, conflicting terms, compliance obligations)
- New: generic KB-oriented prompts with emoji icons
  - "Explain the key concepts in this document" (📖)
  - "Summarize the main findings and takeaways" (📝)
  - "Describe the knowledge base and its contents" (🔍)
  - "What are the important details I should know?" (💡)
- Presets now use `{ text, icon }` objects instead of raw strings
- Preset rendering updated with group hover pattern + icon + text

**B. Apple Design fluid motion applied to interactive elements**
- Provider buttons (Ollama, llama.cpp, Gemini, NVIDIA): added `whileHover={{ scale: 1.02 }}` + `whileTap={{ scale: 0.96, transition: { duration: 0.08 } }}` — instant press feedback per Apple Design principle #1
- Quick prompt buttons: added `whileHover={{ scale: 1.01 }}` + `whileTap={{ scale: 0.98, transition: { duration: 0.08 } }}`
- Transition durations reduced from default to 150ms for snappier feel
- Added `ease-out` to tailwind transitions for natural deceleration
- Border/shadow feedback on hover for provider buttons (subtle depth increase)
- Icon opacity animates on group hover for visual hierarchy

### Verification
- ESLint: 0 errors, 0 warnings
- Vite build: success (4.24s)
- Vitest: 21/21 tests passing

---

## 21. Residual risks / next round (updated)

1. `lru_cache` on user-controlled model strings can pin HF models/HTTP clients (RAM/GPU leak) — needs bounded registry with eviction + close.
2. `InMemoryCache` LLM cache is unbounded and keyed on never-repeated NLI prompts — scope to generation or key on `(query, chunk-hash)`.
3. `graph.py` self-heal path loads/embeds/upserts up to 10k chunks in one shot — batch (64–128) with progress events.
4. SQLite `set_cached_embedding` per-vector connections in `aembed_documents` N+1 loop — batch writes in one transaction.
5. `ru_maxrss` memory guard reads peak, not current — switch to `psutil` RSS.
6. In-process SSE pub/sub breaks under multi-worker — external bus (Redis) if workers > 1.
7. Upload validation (magic bytes, per-entry inflation caps) + `X-Request-ID` sanitization + explicit CORS origins before internet exposure.
