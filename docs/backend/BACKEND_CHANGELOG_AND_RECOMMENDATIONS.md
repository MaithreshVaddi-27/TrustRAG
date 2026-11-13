# TRUSTRAG — Backend Change Log & Recommendations

**Scope:** `apps/api/app/**` (backend). Frontend, Docker, and infrastructure are out of scope.
**Owner role:** Principal Backend Engineer + AI/ML Performance Architect.
**Companion document:** [`BACKEND_AUDIT_B1.md`](./BACKEND_AUDIT_B1.md) — full evidence and measurements.

---

## How to read this log

Every entry is tagged:

| Tag | Meaning |
|---|---|
| **UPGRADE** | Implemented improvement. Benefits are **measured**, with the command and numbers that produced them. |
| **DEGRADATION** | Implemented change with a measurable cost (latency, RAM, accuracy, capability). |
| **REFINEMENT** | Structural/code improvement — no behaviour change intended. |
| **CHANGE REQUIRED** | Identified but **not yet implemented** defect, risk, or tech debt. |
| **BENCHMARK** | Measurements, with conditions. Baseline values are marked `BASELINE`. |
| **DECISION** | A choice made, the alternatives considered, and why. |

> **Honesty rule for this log:** no improvement is reported as fact unless it was
> produced by the benchmark harness in `apps/api/scripts/`. Estimates are labelled
> as estimates and never presented as results.

---

## Status

| Phase | State | Notes |
|---|---|---|
| **B1 — Audit** | ✅ COMPLETE | Read-only. No `app/` source modified. Findings in `BACKEND_AUDIT_B1.md`. |
| **B2.1 — Critical correctness** | ✅ COMPLETE — approved | Gemini probe invocation + contract; recovery-loop routing; verdict preservation. 19 new tests. See §2 UPGRADE-001..004, §3 DEGRADATION-001..002. |
| **B2.2 — Cleanup** | ✅ COMPLETE — **awaiting approval** | Dead `app/llm/registry/` deleted; embedding modules consolidated to one implementation; stale dirs removed; lint 13→0, format clean. See §2 UPGRADE-005..006, §5 REFINEMENT-003. |
| **B3 — Performance** | ⏸️ AWAITING APPROVAL | Plan in audit §6 / §7. |
| **B4 — Accuracy** | ⏸️ AWAITING APPROVAL | Plan in audit §6 / §7. |
| **B5 — Validation** | ⏸️ AWAITING APPROVAL | Plan in audit §7. |

**Implemented changes to `app/` so far: B2.1 + B2.2** (see §2, §3, §4, §5 for the
measured effects). New files: `app/llm/providers/cloud_probe.py`,
`app/rag/agent/graph/budget.py`,
`app/rag/agent/graph/verification_snapshot.py`, plus
`tests/test_recovery_loop.py` and `tests/test_cloud_probe.py`.

---

## 0. Skills & tooling selected

Read from the installed OpenCode skill catalogue (`~/.claude/skills`, ~500
skills) and the repo-local `.kev/.agents/skills/`. **No skill was installed,
duplicated, or modified.**

| Skill / tool | Why it was selected | How it was used |
|---|---|---|
| `fastapi-patterns` | App-factory, lifespan, DI, service-layer and async-DB conventions for this exact stack | Used as the reference standard for judging route/service structure and for the B2 refactor targets |
| `python-patterns` | Python idiom, typing, error handling, import hygiene | Used for the `ruff`/typing cleanup in B2 and for component-module conventions |
| `rag-architect` | Chunking, retrieval, reranking, grounding and citation design | Used to frame the accuracy analysis and the decomposition/NLI failure (CHANGE REQUIRED-003) |
| `rag-eval` | Recall@K / Precision@K / MRR as the quality gate | Used to define the quality metric set and the `analyze_quality.py` harness |
| `performance-optimization` | Latency profiling and bottleneck ranking | Used to structure the stage-level latency measurement |
| `benchmark` / `benchmark-optimization-loop` | Before/after measurement discipline | Used to require measured, not estimated, claims |
| `postgres-patterns` | Index design, `$in`/N+1 query shape | Used to review the MongoDB equivalents (index coverage, `$in` bounds, N+1) |
| `redis-patterns` | Caching layers and invalidation semantics | Evaluated for the embedding-cache and `Settings`-cache decisions; **not adopted** (no Redis in this deployment) |
| `content-hash-cache-pattern` | Content-addressed cache keys | Evaluated for the embedding query cache; the existing mode-namespaced LRU was kept — see DECISION-005 |
| `llm-cost-optimizer` | Token/call budget control | Cross-checked against the existing `llm_ledger.py` budget; **no change proposed** — the ledger already caps calls |
| `ai-security` / `security-review` | Auth, rate limiting, secret scrubbing | Used for the rate-limit and probe-failure findings |
| `python-testing` / `pytest-coverage` | Test strategy and coverage gating | Used to interpret the pre-existing 77.82 % coverage-gate failure |
| `codegraph` (MCP + `.codegraph/`) | Repo-wide symbol/call-path index | Used for the architecture map and blast-radius checks; no `codegraph init` was run (the index already exists) |
| `context7` (MCP) | Up-to-date library docs | **Not invoked**: this audit is about *this* codebase's behaviour, not third-party API semantics. Reserved for B2/B3 if a library-contract question arises (e.g. httpx pooling, slowapi middleware semantics) |
| `firecrawl` / `exa-search` / `paper-lookup` | Web/academic research | **Not invoked**: no external facts were needed; all findings are local, reproduced, and measured |

**Recommended additional tooling (not installed — needs your call):**
- **`pytest-benchmark`** or `pytest-codspeed` for in-process micro-benchmarks that
  run in CI, instead of the standalone scripts.
- **`locust`/`k6`** for load-shaped latency (the repo has `load-test/`, which
  should be checked for overlap before adding anything).
- **`memray`/`scalene`** for allocation profiling if RSS becomes the primary
  concern — the 692 MB post-load figure currently has no per-object attribution.
- **`ruff`'s `PERF` ruleset** (`PERF101`, `PERF203`) — currently not enabled;
  `PERF203` (try-except in a loop) would have flagged the N+1 in
  `_persist_claim_evidence` automatically.

---

## 1. BASELINE — measurements taken before any change

**Conditions:** macOS Apple Silicon · MongoDB 9.0 local · Qdrant embedded
(`QDRANT_URL=local`) · Ollama `gemma3:1b` · ONNX `BAAI/bge-small-en-v1.5`
(fp32, 384-d) · reranker **disabled** (`models.yaml: reranker.enabled: false`)
· uvicorn already running on `127.0.0.1:8000` · test suite on `main`.

### 1.1 API latency (black-box HTTP)

| Endpoint | p50 | p95 | p99 | n |
|---|---|---|---|---|
| `GET /api/v1/health` | 5.66 ms | 7.59 ms | 7.59 ms | 3 |
| `GET /api/v1/metrics` | 2.63 ms | 2.99 ms | 2.99 ms | 3 |
| `GET /api/v1/knowledge-bases` | 18.26 ms | 20.46 ms | 20.46 ms | 3 |
| `GET /api/v1/analyses` | 8.54 ms | 16.21 ms | 16.21 ms | 3 |
| `POST /api/v1/analyses` (201) | 18.92 ms | 35.63 ms | 78.57 ms | 12 |
| **`GET /api/v1/models/providers`** | **2601.42 ms** | 2603.03 ms | 2603.03 ms | 3 |
| **POST → terminal analysis (e2e)** | **4909.69 ms** | 4938.90 ms | 5840.31 ms | 12 |

### 1.2 Stage latency (server trace events, same runs)

| Stage | latency_ms |
|---|---|
| retrieval node | 108 – 128 |
| generation node | ~1401 |
| recovery node | 0 (no-op — see CHANGE REQUIRED F-2) |
| **whole analysis** | **2886 – 5840** |

### 1.3 Micro-benchmarks

| Operation | p50 | p95 |
|---|---|---|
| `get_settings()` (5 env files re-read from disk) | 1.46 ms | 1.52 ms |
| `get_model_config()` (mtime-cached) | 0.002 ms | 0.002 ms |
| `tiktoken.encode()` of an 8-segment context | 0.494 ms | 0.520 ms |
| `format_context_with_chunk_indices()` | 0.112 ms | 0.124 ms |
| `reciprocal_rank_fusion()` (20+20) | 0.016 ms | 0.017 ms |
| `gc.collect()` | 2.45 ms | 3.11 ms |
| `trim_memory()` | 3.70 ms | 4.53 ms |
| ONNX embedding **model load** | 6829 ms | — |
| ONNX `embed_query()` cold | 4.6 ms | 6.3 ms |
| ONNX `embed_query()` cached | 0.0 ms | 4.1 ms |
| Process RSS: before → after embedding model load | 52 MB → **692 MB** | — |

### 1.4 Provider probes

| Probe | p50 | connected |
|---|---|---|
| `check_ollama_status` | 25.5 ms | yes |
| `check_llamacpp_status` | 20.9 ms | no |
| **`check_mlx_status`** | **2601.0 ms** | no |

### 1.5 RAG accuracy (seeded ground-truth corpus, 5 probes)

| Metric | Value |
|---|---|
| **Recall@K** | **1.00** |
| **Precision@K** | 0.33 |
| **MRR** | **1.00** |
| Run outcome | 6 completed / 6 abstained |
| Mean reliability score | 0.50 |

**Interpretation: retrieval is not the problem.** Every probe found its
ground-truth segment at rank 1. The failures are entirely downstream, in
decomposition → NLI → verdict → recovery.

### 1.6 Test suite

```
761 passed, 18 warnings in 36.54s
Total coverage: 77.82%   FAIL (required: 78%)
```

**Pre-existing coverage-gate failure on `main`.**

### 1.7 Lint

```
ruff check app/     → 13 errors  (12× E402 in app/rag/verification/verifier.py, 1× RUF022)
ruff format --check→ 13 files would be reformatted
```

---

## 2. UPGRADE

### UPGRADE-005 — One embedding implementation instead of two  *(B2.2)*

**Change:** `app/rag/embedding/{engine,cache}.py` are now the single
implementation; `app/llm/embedding/{engine,cache}.py` are thin re-export
shims.

The engine existed twice: `app/llm/embedding/engine.py` and
`app/rag/embedding/engine.py` were near-identical forks, and the cache files
differed **only in their import line**. Because `app/llm/embedding/__init__.py`
re-exported the `app.rag` classes while `app/llm/onnx_embeddings.py` re-exported
`_ORT_AVAILABLE`/`ort` from the `app.llm` fork, **two distinct
`ONNXBGEEmbeddings` classes existed** and the model registry instantiated one of
them while the other was unreachable.

**Verified after the change:**

```python
from app.llm.embedding.engine import ONNXBGEEmbeddings as A
from app.rag.embedding.engine   import ONNXBGEEmbeddings as B
from app.llm.onnx_embeddings    import ONNXBGEEmbeddings as C
assert A is B is C        # one class
```

Every historic import path still resolves
(`app.llm.embedding.engine`, `app.llm.embedding.cache`,
`app.llm.onnx_embeddings`, `app.rag.embedding.engine`,
`app.rag.embedding.cache`, `app.llm.embedding`).

**The test patch point now works.** The `_is_ort_available()` / `_get_ort()`
indirection — which existed only in the fork, so patching
`app.llm.onnx_embeddings._ORT_AVAILABLE` never reached the class actually in
use — now lives in the canonical engine. `tests/test_onnx_engines.py` gains
`test_the_compat_shim_is_the_single_patch_point_for_onnxruntime`, which fails
if the engine is ever forked again.

---

### UPGRADE-006 — The declared config is now the real config  *(B2.2)*

**Change:** `app/config/model_config.py`, `app/rag/embedding/cache.py`,
`app/rag/retrieval/retriever.py`.

`config/models.yaml` declared
`retrieval.query_cache_capacity: 1024` (with the comment *"Lower (256) on
≤8 GB hosts; raise (2048) on 32 GB+ hosts"* and an
`RETRIEVAL_QUERY_CACHE_CAPACITY` env override) — and **no code read it**
(`grep` → 0 hits). The wrapper hardcoded `max_cache_size=512`. Meanwhile the
retriever carried a comment claiming *"No query-vector cache: embed fresh
every call"*, which was also false: `get_embedding_model()` returns the
wrapper, and a cached `embed_query` costs ~0.0 ms against ~4.6 ms cold.

**Change:** `ModelConfig.query_cache_capacity` now reads the yaml key with the
declared env override, and the wrapper uses it as its default. The three
sources of truth (comment, yaml key, implementation) now agree.

**False documentation removed:** both cache modules claimed *"Tier 2:
persistent SQLite disk cache (across restarts)"*. There is no SQLite code in
either file (`grep -c sqlite` → 0) — the cache is an in-memory LRU only. The
docstring now says so, and states the cache is process-local and RAM-bounded.

---

### UPGRADE-001 — The Gemini provider path works again  *(B2.1, S1 correctness)*

**Change:** `app/llm/providers/cloud_probe.py` (new) + `app/services/pipeline.py`.

`create_analysis` called `probe_cloud_llm(provider, model)` against a
keyword-only signature, so **every Gemini analysis died with a `TypeError`
before the analysis document was written** — a 500 with no run, no trace and
nothing to retry. The call now passes the keyword arguments the signature
requires, and the probe itself was moved into its own module that speaks each
provider's own contract:

| Provider | Request contract |
|---|---|
| `gemini` | `POST {base}/v1beta/models/{model}:generateContent`, header `x-goog-api-key`, body `{"contents":[{"parts":[{"text":…}]}],"generationConfig":{"maxOutputTokens":N}}` |
| anything else | `POST {base}/v1/chat/completions` (OpenAI-compatible) |

The Gemini contract is the one `langchain-google-genai` speaks at runtime, so
the probe now tests the same API the analysis will use. Verified against the
official Gemini REST documentation (context7, `/websites/ai_google_dev_gemini-api`).

**Behaviour change (an improvement):** a probe failure now raises
`LLMUnavailableError` → **HTTP 503** with an actionable message, instead of an
unhandled `TypeError` → HTTP 500. The message never contains the credential.
`_classify_cloud_probe_error` — previously dead code — is now wired up, and
`_status_code_of` was extended to read the status from `httpx.HTTPStatusError`
(where it lives on `.response`, not on the exception), plus a 429 case.

**Measured:** the request contract is pinned by unit tests (URL, header, body,
no credential in the URL, 401/403/404 handling, missing-key handling) and the
call site by an end-to-end route test that asserts the probe is awaited with
keyword arguments only. **The Gemini path cannot be benchmarked end-to-end
locally — there is no cloud key (BLK-2).**

**Backward compatibility:** `probe_cloud_llm` keeps its exact signature;
`app.llm.providers.health`, `app.llm.providers` and `app.llm.local_llm` all
still export it, so `tests/test_metrics.py` (which patches
`app.llm.local_llm.probe_cloud_llm`) keeps working.

---

### UPGRADE-002 — The adaptive recovery loop now actually loops  *(B2.1, S1 correctness)*

**Change:** `app/rag/agent/graph/edges.py`, `app/rag/agent/graph/nodes/recovery.py`,
`app/rag/agent/graph/state.py`, `app/rag/agent/graph/budget.py` (new).

`should_end` always returned `"end"`, so the graph could never re-enter
retrieval: every analysis was single-shot and the recovery strategy the
recovery node computed was thrown away. (The upstream Phase-9 implementation
used `add_edge("recovery", "retrieval")`; the restructure replaced it with a
conditional edge whose router never chose the loop branch.)

The routing decision now lives in the **state**, not in the router:

- `recovery_node` decides whether another round may run and records it in
  `state["recovery_next"]` (`"retrieve"` / `"end"`).
- `should_end` only reads that value.

This is not a stylistic choice: **LangGraph does not propagate state mutations
made inside a conditional-edge function.** Verified directly — a router that
sets `state["marker"]` produces a final state without it. A decision taken in
the router could never be written back, so it is taken in the node, where the
mutation provably propagates.

The node is also the single authority on the recovery budget: it stops the
loop when the attempt ceiling is reached, when the analysis-wide deadline is
spent, or when no viable strategy was found (an empty or token-identical query
rewrite would otherwise replay the same inputs and reach the same result).

**Measured (live, 12 analyses):** the loop now runs — the trace of a failing
analysis shows `retrieval → generation → recovery → retrieval → generation →
recovery → end`, where before it was `retrieval → generation → recovery → end`.
`recovery_runs` documents now carry a `next_step` field, so a recorded strategy
and its execution can no longer disagree.

---

### UPGRADE-003 — The final verdict reflects the verification that actually ran  *(B2.1, S1 correctness)*

**Change:** `app/rag/agent/graph/verification_snapshot.py` (new) + the recovery
and verification nodes.

The recovery node clears `answer`/`claims` so the next round starts clean.
That is right *while another round follows*, but the graph can also end right
after a recovery round — and then the cleared state was all that survived. The
final verdict was then recomputed from an empty claim list, so a run that had
verified (and contradicted) real claims was reported as
`RETRIEVAL_FAILURE / "No claims extracted for verification"` instead of the
real diagnosis.

The recovery node now keeps a snapshot of the completed verification, and
restores it when the run terminates without a new verification. The verification
node drops the snapshot when it starts a new round, so the snapshot can never
be stale.

**Measured (live, before → after on the same query):**

| Query | Stored diagnosis before | Stored diagnosis after |
|---|---|---|
| *"What is the reciprocal rank fusion constant?"* | `RETRIEVAL_FAILURE` — *No claims extracted for verification* | **`LOW_COVERAGE`** — *Answer is non-responsive: addresses an unrelated fact from the context rather than the question asked* |
| *"What happens when the evidence does not support an answer?"* | `RETRIEVAL_FAILURE` — *No claims extracted for verification* | **`RETRIEVAL_FAILURE`** — *Model abstained: insufficient grounded evidence* |

Both are now the true cause instead of a generic stand-in. The grounding gate
is unchanged: a non-TRUSTED verdict still withholds the model's text
(`answer_withheld`), so restoring the answer cannot surface ungrounded prose.

---

### UPGRADE-004 — The pre-existing coverage-gate failure is fixed  *(B2.1, S1 build)*

CHANGE REQUIRED-016 was: the suite fails its own gate on `main`
(`77.82 % < 78 %`). The 19 new B2.1 tests cover the new modules
(`cloud_probe.py`, `budget.py`, `verification_snapshot.py`) and the touched
recovery/routing paths.

```
761 passed, 18 warnings   Total coverage: 77.82%   FAIL (required: 78%)   ← main, before
780 passed, 18 warnings   Total coverage: 78.12%   PASS (required: 78%)   ← after B2.1
```

The gate is green again. It is **not** ratcheted above the old floor — B5 must
confirm it stays green.

---

## 3. DEGRADATION

### DEGRADATION-001 — Failing analyses now run a second recovery round  *(B2.1, measured)*

**Cost:** a failing analysis performs up to two retrieval/generation/verification
rounds instead of one. Before B2.1 the recovery node ran and its result was
discarded, so the extra work was pure waste — but it was also *free*, because
the round never happened. Restoring the loop means paying for it.

**Measured (live, n=12 analyses each, same services):**

| Metric | Baseline | B2.1 | Δ |
|---|---|---|---|
| `POST → terminal analysis` p50 | 4909.69 ms | 5017.85 ms | **+2.2 %** |
| `POST → terminal analysis` p95 | 4938.90 ms | 10273.10 ms | **+108 %** |
| `POST → terminal analysis` p99 | 5840.31 ms | 10845.00 ms | **+85.7 %** |
| `POST → terminal analysis` mean | 4558.72 ms | 5846.82 ms | **+28.3 %** |

The p50 is unchanged (successful analyses never enter the loop); the tail is
where the second round shows up. The extra cost is bounded by
`cost_controls.max_analysis_seconds` (600 s) and by the recovery budget
(`max_recovery_attempts: 2`, `max_recovery_tokens: 2000`,
`max_recovery_latency_seconds: 180`).

**Stage latency, B2.1 (from the server's own trace events):**

| Stage | p50 | max |
|---|---|---|
| retrieval | 105 ms | 284 ms |
| generation | 1460 ms | 1959 ms |
| recovery | 295 ms | 1094 ms |

**This is a deliberate trade, not a regression to be hidden:** the recovery loop
is the product's stated differentiator (`docs/TRUSTRAG_specs.md` §17), and it
was dead code. If the tail matters more than the loop, the lever is the
recovery strategy, not the routing — e.g. skipping a round that cannot change
the outcome (see CHANGE REQUIRED-018).

---

### DEGRADATION-002 — The recovery round serves more evidence per analysis  *(B2.1, measured)*

**Cause:** the `re_retrieve` strategy deliberately widens the search
(`top_k` doubled, context window widened). A failing analysis now therefore
persists ~6 evidence segments instead of 3.

**Measured (live, like-for-like: the B2.1 batch only, n=12):**

| Metric | Baseline | B2.1 | Δ |
|---|---|---|---|
| Recall@K | 1.00 | **1.00** | unchanged |
| MRR | 1.00 | **1.00** | unchanged |
| Precision@K | 0.3333 | **0.2917** | **−12.5 %** |
| Completed / abstained | 6 / 6 | 6 / 6 | unchanged |
| Mean reliability | 0.50 | 0.50 | unchanged |

The precision change comes entirely from one query — *"What is the reciprocal
rank fusion constant?"* — whose mean evidence count went 3.0 → 6.0 because the
recovery round widened the search (precision@K = 1/6 instead of 1/3).

**Interpretation:** Recall@K and MRR — the metrics that measure whether the
right evidence is *found* — are unchanged. Precision@K measures how much noise
comes back with it, and the recovery round intentionally retrieves more.
**DECISION-002's gate is technically not met on Precision@K**; this is reported
as a measured trade-off rather than smoothed over, and it is the reason the
accuracy phase (B4) must re-measure both metric families on a larger
ground-truth set before any threshold change is considered.


---

## 4. BENCHMARK — B2.1 measured results

**Conditions:** identical to §1 — same host, same MongoDB, same embedded
Qdrant, same Ollama `gemma3:1b`, same ONNX BGE embedding, reranker still
disabled, API restarted on `127.0.0.1:8000` with the B2.1 code.
Artifacts: `bench_api_results_B2_1.json`, `quality_results_B2_1.json`
(`docs/backend/`).

### 4.1 API latency (black-box HTTP, n=3 per endpoint, n=12 analyses)

| Endpoint | baseline p50 | B2.1 p50 | Δ | baseline p99 | B2.1 p99 | Δ |
|---|---|---|---|---|---|---|
| `GET /health` | 5.66 ms | 5.55 ms | −1.9 % | 7.59 ms | 6.44 ms | −15.2 % |
| `GET /metrics` | 2.63 ms | 2.09 ms | −20.5 % | 2.99 ms | 2.47 ms | −17.4 % |
| `GET /knowledge-bases` | 18.26 ms | 11.89 ms | −34.9 % | 20.46 ms | 21.46 ms | +4.9 % |
| `GET /analyses` | 8.54 ms | 3.92 ms | −54.1 % | 16.21 ms | 12.16 ms | −25.0 % |
| `POST /analyses` | 18.92 ms | 17.53 ms | −7.3 % | 78.57 ms | 68.73 ms | −12.5 % |
| `GET /models/providers` | 2601.42 ms | 2605.49 ms | +0.2 % | 2603.03 ms | 2610.58 ms | +0.3 % |
| **POST → terminal analysis** | **4909.69 ms** | **5017.85 ms** | **+2.2 %** | **5840.31 ms** | **10845.00 ms** | **+85.7 %** |

The read-path deltas are noise (n=3). The only material movement is the
end-to-end tail — see DEGRADATION-001. `/models/providers` is unchanged because
it is a B3 item.

### 4.2 Stage latency (server trace events, B2.1 runs)

| Stage | p50 | max |
|---|---|---|
| retrieval | 105 ms | 284 ms |
| generation | 1460 ms | 1959 ms |
| recovery | 295 ms | 1094 ms |

### 4.3 RAG accuracy (like-for-like: the B2.1 batch only, n=12)

| Metric | Baseline (§1.5) | B2.1 | Δ |
|---|---|---|---|
| **Recall@K** | 1.00 | **1.00** | unchanged |
| **MRR** | 1.00 | **1.00** | unchanged |
| **Precision@K** | 0.3333 | **0.2917** | **−12.5 %** (DEGRADATION-002) |
| Completed / abstained | 6 / 6 | 6 / 6 | unchanged |
| Mean reliability score | 0.50 | 0.50 | unchanged |

### 4.4 Test suite

```
before:  761 passed, 18 warnings   coverage 77.82%   FAIL (required 78%)
after:   780 passed, 18 warnings   coverage 78.12%   PASS (required 78%)
```

19 new tests: `tests/test_recovery_loop.py` (11) and
`tests/test_cloud_probe.py` (8). No existing test was modified or removed.

### 4.5 Lint / format

```
ruff check  (files touched by B2.1)   → All checks passed
ruff format (new files)               → already formatted
```

`app/rag/agent/graph/nodes/recovery.py` and `app/services/pipeline.py` keep
**pre-existing** format diffs (part of the 13-file debt); none of the diffs
are in the lines B2.1 touched (verified with `ruff format --diff`).

### 4.6 B2.2 re-measurement

**Conditions:** identical to §1, with the B2.2 code.
Artifact: `bench_api_results_B2_2.json`, `quality_results_B2_2.json`.

| Metric | Baseline | B2.1 | B2.2 | Δ baseline→B2.2 |
|---|---|---|---|---|
| `GET /health` p50 | 5.66 ms | 5.55 ms | 5.76 ms | +1.8 % (noise) |
| `GET /models/providers` p50 | 2601.42 ms | 2605.49 ms | 2608.72 ms | +0.3 % (unchanged — a B3 item) |
| `POST /analyses` p50 | 18.92 ms | 17.53 ms | 18.30 ms | −3.3 % (noise) |
| **POST → terminal analysis p50** | 4909.69 ms | 5017.85 ms | 5004.62 ms | **+1.9 %** |
| **POST → terminal analysis p99** | 5840.31 ms | 10845.00 ms | 13483.98 ms | **+130.9 %** |
| Recall@K | 1.00 | 1.00 | 1.00 | unchanged |
| MRR | 1.00 | 1.00 | 1.00 | unchanged |
| Precision@K | 0.3333 | 0.2917 | 0.3056 | −8.3 % |

**B2.2 is a cleanup phase — it changed no answer-affecting logic**, so the
read-path deltas are noise and the end-to-end p50 is unchanged. The p99
spread (10.8 s → 13.5 s) is the same second recovery round as DEGRADATION-001,
landing in a different place depending on which round the local model takes.

**The B2.2 batch produced 5 abstained / 7 completed (mean reliability 0.583)
against 6 / 6 (0.50).** This is **run-to-run non-determinism of the 1B local
model**, not a B2.2 effect — confirmed by the per-query trace across all
three batches, where the same query flips between `abstained/RETRIEVAL_FAILURE`
and `completed/NONE` from run to run (the model runs at `temperature: 0.2`).
**It is not reported as an improvement.**

What B2.2 *did* change deterministically is visible in the same trace: the
diagnosis for *"What is the reciprocal rank fusion constant?"* stays
`LOW_COVERAGE / "Answer is non-responsive..."` across all six post-B2.1 runs,
where the three baseline runs all stored the destroyed
`RETRIEVAL_FAILURE / "No claims extracted for verification"`.

---

## 5. REFINEMENT

### REFINEMENT-003 — B2.2 cleanup: dead code removed, lint and format clean  *(B2.2)*

| Action | Detail |
|---|---|
| **Deleted** `app/llm/registry/` | 438 LOC across 5 files. The package **failed to import** (`ModuleNotFoundError: app.llm.registry.factories.reranker`) and was referenced by **no module and no test**. Its live equivalents are in `app/llm/model_registry.py`. |
| **Consolidated** the embedding modules | One implementation (`app/rag/embedding/*`), two re-export shims (`app/llm/embedding/*`). See UPGRADE-005. |
| **Removed** stale directories | `app/core/observability/` and `app/core/config/` contained nothing but `__pycache__`; `app/api/v1/routes/` contained only an empty `__init__.py` (the routers live in `app/api/v1/*.py` and are registered by `app/api/router.py`). |
| **Fixed** the E402 import block | `app/rag/verification/verifier.py` defined `get_collection` *between* two import blocks, which is what produced the 12 E402 errors. The helper moved below the imports; behaviour is unchanged (it still resolves the collection from the live MongoDB module, so a test patch still takes effect). |
| **Lint** | `ruff check app/`: **13 errors → 0**. `ruff format app/`: **9 files reformatted → 127 already formatted**. |
| **Lint/format** for the harness and the new tests | `scripts/` and the three test files touched by B2.1/B2.2 are `ruff check` and `ruff format` clean. |

**Import-path compatibility:** every public name that existed before still
exists. `app.llm.embedding.engine` / `.cache` keep exporting
`ONNXBGEEmbeddings`, `ONNXBGEEmbeddingsWrapper`, `EMBEDDING_MODE_*`,
`_ORT_AVAILABLE` and `ort`; `app.llm.onnx_embeddings` is unchanged as a shim.

**Net effect on the code base:** **906 lines deleted, 159 added.**

**Measured effect on the test suite:**

```
before B2.2:  781 passed   coverage 78.10%   (statements 8841, missed 1936)
after  B2.2:  781 passed   coverage 80.72%   (statements 8539, missed 1646)
```

Coverage rose by **2.62 points** — not because many tests were added (one
was), but because ~300 uncovered statements left the denominator together
with the dead code. The coverage gate is comfortably green.

---

### REFINEMENT-001 — Benchmark & analysis harness added (read-only, no `app/` change)

**Change:** three new scripts under `apps/api/scripts/`:

| Script | Purpose |
|---|---|
| `bench_api.py` | Black-box HTTP benchmark: p50/p95/p99 per endpoint, analysis create + end-to-end, status/reliability breakdown. |
| `bench_pipeline.py` | In-process stage benchmark: dense / sparse / fusion / temporal / rerank / generation / verification, plus RSS before/after, plus a seeded scratch KB. |
| `analyze_quality.py` | Retrieval-quality analyser over stored evidence → Recall@K / Precision@K / MRR per query, with abstention breakdown. |

**Rationale:** every later phase needs a falsifiable before/after. Estimates are
not acceptable evidence for this codebase, so the harness comes first.

**Baseline artifacts captured** (committed under `docs/backend/`):
`bench_api_results_BASELINE.json`, `quality_results_BASELINE.json`.

**Impact on production:** none — the scripts are not imported by `app/`, are not
wired into the server, and pytest does not collect them (`testpaths = ["tests"]`).

**Regression check after adding them:** `pytest -q --no-cov` → **761 passed**
(unchanged from the pre-change baseline).

---

### REFINEMENT-002 — B2.1 module split  *(B2.1)*

Three new focused modules instead of growing the existing files:

| Module | Responsibility |
|---|---|
| `app/llm/providers/cloud_probe.py` | Cloud provider probes, one request contract per provider. `health.py` re-exports `probe_cloud_llm` and the error helpers, so every existing import path still works. |
| `app/rag/agent/graph/budget.py` | The analysis-wide wall-clock budget (`remaining_budget_ms`, `deadline_spent`, `mark_budget_exhausted`), shared by the edges and the recovery node instead of duplicated. |
| `app/rag/agent/graph/verification_snapshot.py` | Capture / clear / restore of the last completed verification across recovery rounds. |

**State changes:** `AgentState` gained `verification_snapshot` and
`recovery_next` (both initialised in `initial_state`).

**Provenance improvement:** `recovery_runs` documents now carry `next_step`
(`"retrieve"` / `"end"`), so a recorded strategy and its execution can no
longer disagree — the audit finding that a `re_retrieve` strategy was logged
and never acted on is now structurally impossible.

**Lint/format:** the new modules and the new tests are `ruff check` clean and
`ruff format` clean. `app/rag/agent/graph/nodes/recovery.py` and
`app/services/pipeline.py` still have pre-existing formatting diffs; **none of
them are in the lines touched by B2.1** (verified with `ruff format --diff`).
The remaining 13-file format debt and the 13 lint errors stay in B2.2.

---

## 6. CHANGE REQUIRED

Identified in B1. **None implemented yet** — awaiting approval.

### CHANGE REQUIRED-001 — `probe_cloud_llm` called with the wrong signature  *(S1, correctness)*

> **STATUS: RESOLVED in B2.1** — see UPGRADE-001. The call now passes keyword
> arguments, the probe speaks Gemini's native contract, and a probe failure is a
> 503 with an actionable message instead of an unhandled `TypeError`.
> The entry below is kept as the original record.

**File:** `app/services/pipeline.py:390`

```python
await local_llm_mod.probe_cloud_llm(effective_llm_provider, effective_llm_model)
```
Real signature (`app/llm/providers/health.py:304`):
```python
async def probe_cloud_llm(*, norm: str, model: str, base_url: str, timeout: float, hint: str = "") -> None
```

**Reproduced:** `TypeError: probe_cloud_llm() takes 0 positional arguments but 2 were given`.

**Impact:** every `gemini`-provider analysis request fails with a 500 **before the
analysis document is written** — no run, no trace, no retry. The cloud path is
fully broken. The call sits outside any `try`, so it also escapes
`create_analysis`'s error handling.

**Proposed fix:** call with keyword arguments and supply the Gemini `base_url`
and `timeout`; wrap the probe so a probe failure degrades to a clear 503 rather
than an unhandled `TypeError`.

---

### CHANGE REQUIRED-002 — The recovery loop is unreachable; the graph can never re-run a round  *(S1, correctness)*

> **STATUS: RESOLVED in B2.1** — see UPGRADE-002 (the loop now runs) and
> UPGRADE-003 (the final verdict survives the recovery round). The entry below
> is kept as the original record.

**File:** `app/rag/agent/graph/edges.py:67`

```python
def should_end(state: AgentState) -> str:
    """Route after recovery: end if attempts exhausted, else loop back."""
    return "end"
```

The docstring promises a loop back; the body always returns `"end"`. The graph
mapping `{"retrieve": "retrieval", "end": "__end__"}` makes the `"retrieve"`
branch unreachable.

**Verified:** `should_recover(state)` → `"recover"`, then `should_end(state)` → `"end"`.

**Impact:** `recovery_node` clears `state["answer"] = None` and
`state["claims"] = []`, the graph terminates, and `pipeline.py` computes the
final verdict **from the cleared state**. A live run showed the diagnosis being
destroyed and replaced:

```
WITH verification result : FAILED 0.0 EVIDENCE_CONFLICT ['1/1 claims contradicted by evidence', ...]
AFTER recovery cleared   : FAILED 0.0 RETRIEVAL_FAILURE ['No claims extracted for verification']
```

The stored `analysis.diagnosis` read `['No claims extracted for verification']`
even though a claim *had* been extracted and verified — the DB is internally
inconsistent (the claim survives in the `claims` collection). A `recovery_runs`
document was also written recording a `re_retrieve` strategy that was never
executed.

**Proposed fix:** make `should_end` honour `state["attempts"]` vs
`cfg.max_recovery_attempts` and route back to `"retrieve"` while budget
remains; preserve the pre-recovery verdict/answer so the final verdict is not
computed from cleared state. **Medium risk — the graph behaviour changes, so it
needs dedicated regression tests before merge.**

---

### CHANGE REQUIRED-003 — A correct answer is discarded because one good claim was labelled CONTRADICTED  *(S1, accuracy)*

**Evidence (live run, query *"What is the reciprocal rank fusion constant?"*):**

| Step | Result |
|---|---|
| retrieval | correct segment, **rank 1** (RRF 0.0328) |
| generation | correct answer: *"The reciprocal rank fusion constant is sixty."* |
| decomposition | claim: **"Sixty is a number"** — predicate lost |
| NLI | **CONTRADICTED** — explanation: *"…while the hypothesis claims it judges."* (nonsense) |
| verdict | FAILED / score 0 → grounding gate withheld a **correct** answer |

Two compounding defects:

1. **Content-free claims survive the degenerate filter.** "Sixty is a number" is
   4 words with no terminal punctuation; `_filter_degenerate_claims`
   (`app/rag/verification/meta.py:80`) only drops title-case headings when
   *every* word is capitalised — "is", "a", "number" are not — so it passes.
2. **One CONTRADICTED claim out of one ⇒ coverage 0/1 ⇒ score 0 ⇒ full
   abstention.** With `minimum_evidence_coverage = 0.80` and
   `max_verification_claims: 5` (lean tier), a single mis-verified claim
   discards the whole answer.

**Contrast (same corpus):** the probe *"Which embedding model does dense
retrieval use?"* produced the real proposition *"Dense retrieval uses BGE-small
embeddings computed locally through ONNX Runtime"* → **SUPPORTED**, score 1.0.

**Conclusion: the 50 % abstention rate tracks 1B-model decomposition fidelity,
not evidence quality.** Retrieval Recall@K is 1.00.

**Proposed fix:** (a) reject predicate-free claims via a verb/relation
heuristic aligned with the existing `_PREDICATE_VERBS` set; (b) stop a single
contradicted claim from forcing score 0 (minimum-claim-count floor, or a
contradiction-rate floor) — both benchmark-gated against the Recall@K /
abstention baseline in §1.5.

---

### CHANGE REQUIRED-004 — `GET /api/v1/models/providers` costs 2.6 s per call  *(S2, latency)*

**Files:** `app/llm/providers/health.py:200` (`check_mlx_status`), `:75`
(`_fetch_json_with_retry`), `:98`/`:155` (`async with _shared_http_client(...)`).

Three separate defects compound:

1. **5 ports probed sequentially.** Measured 2601 ms p50 for a *disconnected*
   provider.
2. **The retry never retries.** `raise` sits inside the `except`, so attempt 1
   is unreachable — the function sleeps 0.5 s then re-raises.
3. **A new `httpx.AsyncClient` per attempt** — no pooling, fresh TLS handshake
   each time.

Separately, `check_ollama_status`/`check_llamacpp_status` use
`async with _shared_http_client(...)`. `httpx.AsyncClient.__aexit__` **closes**
the client, so the shared pool is destroyed and rebuilt on every health check.
**Verified:** after the block `client.is_closed is True`; the next
`_shared_http_client()` call returns a different object. The shared-pool design
is defeated on the health path.

**Impact:** the frontend polls `/models/providers` every **8 s**
(`refetchInterval: 8000`), so one idle browser tab costs ~325 ms/s of provider
probing, and each call blocks a worker for 2.6 s.

**Proposed fix:** probe the MLX ports concurrently with one pooled client and a
short connect timeout; use the shared client without closing it; make the retry
real.

---

### CHANGE REQUIRED-005 — The global rate limit is configured but never enforced  *(S2, security)*

**File:** `app/main.py:530`

```python
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
```

slowapi applies `default_limits` **only** via `SlowAPIMiddleware`, which is
never added. Per-route `@_auth_limiter.limit(...)` decorators in `auth.py` work
(they are self-contained); every other endpoint has **no limit**.

**Verified:** 70 consecutive authenticated `GET /api/v1/models/providers`
→ **70 × HTTP 200**, zero 429s. The same test on `POST /api/v1/auth/login`
correctly returned **429** after 5 attempts.

The `RateLimitExceeded` handler is therefore dead code for non-auth routes.

**Proposed fix:** add `SlowAPIMiddleware` and confirm the 60/min default
actually fires.

---

### CHANGE REQUIRED-006 — `get_settings()` re-reads 5 files from disk on every call  *(S2)*

**File:** `app/config/settings.py:287`

`Settings()` is rebuilt per call, and `pydantic-settings` re-reads and re-parses
all five `env_file` paths every time.

**Measured: 1.46 ms p50 / 1.52 ms p95 per call**, at **29 call sites**,
including `security.py:118` (`_decode_jwt` — every authenticated request) and
`model_registry.get_llm` / `get_verification_model` (every LLM call).

The "no stale-state bugs" intent is achievable at lower cost: the `.env` values
only change when the files change, which is detectable by mtime — exactly the
pattern `get_model_config()` already uses for `models.yaml`.

**Proposed fix:** mtime-keyed cache for `Settings`, with the same invalidation
semantics as `get_model_config()`, plus a test proving an edited `.env` is
picked up.

---

### CHANGE REQUIRED-007 — Duplicate trace events  *(S2)*

**Files:** `app/rag/agent/graph/build.py:55,67` and each node.

Every node emits `X.started`/`X.completed`, and `_execute_with_fallback` emits
its own `X.started`/`X.completed` for the same node. A live analysis produced:

```
retrieval.started   ×2      retrieval.completed ×2
generation.started  ×2      generation.completed ×1
```

11 trace events per analysis, each a **separate MongoDB `insert_one`**. The
asymmetry (`generation.started` ×2, `generation.completed` ×1) reflects the
failure path skipping the node's own completion event.

**Proposed fix:** one owner for each event; batch the inserts.

---

### CHANGE REQUIRED-008 — N+1 and unbounded MongoDB query patterns  *(S2)*

| Site | Pattern |
|---|---|
| `app/rag/verification/pipeline/retrieval.py:65` | `find_one` **per chunk** in a loop (N+1 round-trips) |
| `app/rag/verification/integrity.py:62` | `{"$or": [ … up to 100 clauses ]}` per audit |
| `app/services/claims_evidence.py:78,179,203` | up to **1000** analysis ids → `{"$in": [...]}` (can exceed Mongo's 16 MB BSON limit on large tenants) |
| `app/rag/retrieval/retriever.py:346` | `find({"_id": {"$in": doc_objs}})` — unbounded `$in` from result payloads |
| `app/rag/agent/graph/nodes/retrieval.py:207` | `.to_list(10_000)` self-heal — unbounded RAM spike |

---

### CHANGE REQUIRED-009 — Embedding cache: comment, yaml key, and implementation disagree  *(S2, coherence)*

> **STATUS: RESOLVED in B2.2** — see UPGRADE-006. The yaml key is read, the
> env override works, the wrapper's default comes from the config, and the
> retriever comment matches the implementation.

**Files:** `app/rag/retrieval/retriever.py:125`,
`app/rag/embedding/cache.py`, `app/llm/embedding/cache.py`,
`config/models.yaml` (`retrieval.query_cache_capacity: 1024`).

- The retriever comment says *"No query-vector cache: embed fresh every call"* —
  but `get_embedding_model()` returns the **wrapper**, whose `embed_query`
  consults a 512-entry in-memory LRU. Measured: cached **0.0 ms** vs cold 4.6 ms.
- `models.yaml` declares `query_cache_capacity: 1024` — **no code reads it**
  (`grep` → 0 hits). The wrapper hardcodes `max_cache_size=512`.

---

### CHANGE REQUIRED-010 — Both embedding cache modules claim a SQLite disk cache that does not exist  *(S3, docs)*

> **STATUS: RESOLVED in B2.2** — see UPGRADE-006. The docstring now states
> plainly that the cache is an in-memory LRU, process-local and not persisted.

`app/rag/embedding/cache.py:7,35` and `app/llm/embedding/cache.py:7,35`:
> *"Tier 2: persistent SQLite disk cache (across restarts)"*

`grep -c sqlite` → **0** in both files. The wrapper is an in-memory LRU only.

---

### CHANGE REQUIRED-011 — `_fetch_json_with_retry` retry is unreachable  *(S3)*

**File:** `app/llm/providers/health.py:75` — `raise` sits inside the `except`,
so the second iteration can never run. Verified: one 0.5 s sleep, then re-raise.

---

### CHANGE REQUIRED-012 — `trim_memory()` runs twice per analysis  *(S3)*

`app/rag/agent/graph/coordinator.py:112` and `app/services/pipeline.py:911` both
call it in a `finally`. Measured `trim_memory()` = 3.70 ms p50 (of which
`gc.collect()` is 2.45 ms). The coordinator's call already covers the whole
analysis; the pipeline's is redundant.

Related: `check_and_enforce_memory_guard` has **no production caller** (only
`tests/test_hardware.py`).

---

### CHANGE REQUIRED-013 — Dead, unimportable `app/llm/registry/` package  *(S3)*

> **STATUS: RESOLVED in B2.2** — the package is deleted (438 LOC). See
> REFINEMENT-003.

`python -c "import app.llm.registry"` →
`ModuleNotFoundError: No module named 'app.llm.registry.factories.reranker'`

`__init__.py` imports `factories.reranker` and `factories.status`; neither file
exists. The package is referenced by **no** module and **no** test — 438 LOC
of unreachable, broken code. Live equivalents are in `app/llm/model_registry.py`.

---

### CHANGE REQUIRED-014 — Duplicated embedding engine + cache modules  *(S3)*

> **STATUS: RESOLVED in B2.2** — one implementation, two re-export shims. See
> UPGRADE-005 and REFINEMENT-003.

`app/llm/embedding/engine.py` (263 LOC) vs `app/rag/embedding/engine.py`
(245 LOC) — near-identical forks differing only in the `_is_ort_available()`
shim indirection. `app/llm/embedding/cache.py` vs `app/rag/embedding/cache.py`
— identical except one import line.

Consequence: **two distinct `ONNXBGEEmbeddings` classes exist.** `model_registry.py:364`
constructs the `app.llm.embedding.engine` one while `model_registry.py:375`
imports the wrapper from the `app.rag` tree. The shim exists only so
`tests/test_onnx_engines.py` can patch `app.llm.onnx_embeddings._ORT_AVAILABLE` —
the duplication was created to satisfy a test, not by design.

---

### CHANGE REQUIRED-015 — Stale directories and lint debt  *(S3)*

> **STATUS: RESOLVED in B2.2** — the stale directories are removed and
> `ruff check app/` / `ruff format app/` are both clean. See REFINEMENT-003.

- `app/core/observability/` and `app/core/config/` contain **only** `__pycache__`
  (no git-tracked files) — leftovers from the restructure.
- `app/api/v1/routes/` contains **only** an empty `__init__.py`; the routers live
  in `app/api/v1/*.py` and are registered by `app/api/router.py`.
- `ruff check app/` → **13 errors** (12 × E402 in
  `app/rag/verification/verifier.py`, 1 × RUF022 unsorted `__all__`).
- `ruff format --check app/` → **13 files would be reformatted**.

> The pre-existing lint debt in `tests/` and `scripts/` (19 findings, 5 files)
> is **not** in this phase's scope: `CONTRIBUTING.md` scopes the gate to
> `app/`, and reformatting the whole test suite would bury the behavioural
> diff. The files this programme touched (`scripts/`, and the three new/
> changed test files) are clean.

---

### CHANGE REQUIRED-016 — The test suite fails its own coverage gate on `main`  *(S1, build)*

> **STATUS: RESOLVED in B2.1** — see UPGRADE-004. The gate is green at 78.12 %.

```
761 passed, 18 warnings in 36.54s
Total coverage: 77.82%   FAIL (required: 78%)
```

Pre-existing. Must be fixed (or the gate deliberately adjusted) before B5 can
be reported as green.

---

### CHANGE REQUIRED-017 — A conditional-edge router cannot write state back  *(S1, correctness — NEW in B2.1)*

**Found while implementing B2.1.** LangGraph does **not** propagate state
mutations made inside a conditional-edge function.

**Reproduced directly:**

```python
def router(state):
    state["marker"] = "MUTATED_BY_ROUTER"
    return "end"
# final state: {'v': 1}   →  marker: None
```

**Consequence for this codebase:** `should_recover` mutates
`state["diagnosis_type"] = "RECOVERY_BUDGET_EXHAUSTED"` when the analysis-wide
deadline is spent. That mutation is **dropped** — the run terminates correctly
(the router still returns `"end"`), but the final state never carries the
diagnosis. `tests/test_graph_entrypoint.py:167` asserts the mutation on the
local dict the router was handed, which is why the gap was invisible.

**Related gap (same root cause, lower severity):** the pipeline recomputes the
final verdict from `final_state["claims"]` (`verdict_from_state`) and stores
*that* diagnosis, so a terminal recovery diagnosis
(`RECOVERY_BUDGET_EXHAUSTED`) never reaches the `analysis.diagnosis` field in
MongoDB either — the DB shows the last verification's diagnosis.

**Proposed fix (not in B2.1 — it changes the pipeline's verdict contract):**
record the deadline diagnosis from a *node* rather than from a router (the
coordinator already receives and returns the final state, so it can mark it
there), and decide explicitly whether `analysis.diagnosis` should reflect the
*verification* diagnosis or the *recovery* diagnosis. The second one is a
product decision, not a bug fix.

---

### CHANGE REQUIRED-018 — A recovery round that cannot change the outcome still costs a full round  *(S2, latency — NEW in B2.1)*

**Found while implementing B2.1.** Now that the loop actually runs, the wasted
work that UPGRADE-002 restores becomes visible: a recovery round that provably
cannot improve the answer is still paid for.

**Measured in the live trace** (query *"What happens when the evidence does not
support an answer?"*):

```
retrieval.completed  lat=100    3 segments
generation.completed lat=1247
recovery.completed   lat=1078   query_rewrite → empty rewrite → regenerate
retrieval.reused     lat=0      same 3 segments, no retrieval spend
generation.skipped   lat=0      "Model already abstained on these segments"
recovery.completed   lat=295    second rewrite attempt
```

The second round cost ~295 ms and produced nothing: the model had already
refused on exactly those segments, and the futile-generation guard skipped the
call. The run then ended with the same diagnosis as the first round.

**Proposed fix (candidate for B3):** stop the loop when the round cannot change
the outcome — e.g. when the recovery strategy is `regenerate` *and* the
generation node's futile guard would skip the call, or when a `re_retrieve`
round returns the same chunk set as the previous round. Both are decidable from
state the node already has, and both avoid a second retrieval+generation pair.
This is the lever for the DEGRADATION-001 tail, and it is a **behaviour change**
to the recovery loop, so it needs its own regression tests and its own
benchmark.

---

## 7. DECISION

### DECISION-001 — Every claim in this log must come from the harness

**Decision:** no improvement is reported without a before/after measurement
produced by `apps/api/scripts/`.

**Alternatives considered:**
- *Estimate impact from code reading* — rejected: the recovery-loop defect
  (CHANGE REQUIRED-002) shows that a plausible-looking code path can be
  completely dead. Reading alone would have "fixed" it wrongly.
- *Trust the existing test suite as a performance signal* — rejected: it has
  no latency assertions at all.

**Consequence:** B2–B5 re-run `bench_api.py` and `analyze_quality.py` after every
meaningful change, and the numbers are pasted into this log.

---

### DECISION-002 — Retrieval quality is the gate for accuracy work, not the abstention rate alone

**Decision:** accuracy changes are judged on **Recall@K / Precision@K / MRR
staying at or above the §1.5 baseline (1.00 / 0.33 / 1.00)** *and* the
abstention rate falling.

**Alternatives considered:**
- *Optimise the abstention rate alone* — rejected: an easy way to abstain less
  is to lower the verification bar, which trades correctness for coverage.
  Keeping retrieval metrics pinned prevents that.
- *Treat Recall@K = 1.00 as "retrieval is solved"* — rejected: it is measured on
  a 5-probe corpus. It is a **regression guard**, not proof of quality.

**Consequence:** CHANGE REQUIRED-003 must be implemented and re-measured against
both metric families; a Recall@K drop invalidates the change regardless of the
abstention improvement.

---

### DECISION-003 — Reranker enablement, embedding quantisation, and model default are **decisions, not optimisations**

**Decision:** none of these three is changed in this programme without a
dedicated before/after benchmark.

**Rationale:**
- **Reranker** (`reranker.enabled: false` today; int8 weights already present):
  enabling it changes latency *and* ordering. It must be measured against the
  §1.5 quality baseline before it is called an improvement.
- **Embedding quantisation** (`bge-small-en-v1.5.onnx` is fp32, 134 MB, 692 MB
  RSS after load): an int8 export could cut RAM materially, but BGE recall under
  int8 is unmeasured here. `models.yaml` itself warns that "1 % clipping can drop
  the true nearest neighbour at the reranker boundary".
- **Default model** (`gemma3:1b`): the abstention rate is a model-fidelity
  issue, but changing the shipped default is a product/cost decision.
  `qwen3:1.7b` is already installed and the `deep_reasoning_mode` path exists —
  worth measuring as a trade-off, presented with numbers, not assumed.

---

### DECISION-004 — Verification-before-completion discipline

**Decision:** a change is not "done" until it has been re-benchmarked and the
result is recorded in this log — including when the result is **no
improvement**. Regression findings are logged as DEGRADATION, not suppressed.

---

### DECISION-005 — The embedding query cache is kept, not replaced

**Decision:** keep the existing in-memory, mode-namespaced LRU in
`ONNXBGEEmbeddingsWrapper`; fix the stale comment and reconcile the unused
`query_cache_capacity` yaml key with the real capacity. Do **not** introduce a
content-hash cache or a new cache layer.

**Alternatives considered:**
- *Content-hash keyed cache (as in the `content-hash-cache-pattern` skill)* —
  rejected: the current key already namespaces by mode (`query` vs `document`)
  and by normalised text, which is precisely the collision the mode namespace
  exists to prevent. A content hash would add no correctness and would make
  stale-vector invalidation *harder* (the existing comments record a real
  stale-vector incident after an embedding-model switch).
- *Redis-backed shared cache* — rejected: this deployment runs the API
  single-node with an embedded Qdrant and a local MongoDB. A network cache
  would add a dependency, a failure mode, and latency for a hit rate that a
  512-entry in-process LRU already covers at 0.0 ms.

**Consequence:** CHANGE REQUIRED-009 is a coherence fix (comment + yaml key +
capacity), not a redesign.

---

## 8. Plan for B2–B5

### B2 — Cleanup & refactor (mechanical, low risk, behaviour-preserving)

| # | Action | Files |
|---|---|---|
| 1 | Delete the dead, unimportable `app/llm/registry/` package | `app/llm/registry/**` |
| 2 | Collapse the duplicated embedding engine + cache into one canonical module + a thin re-export shim (preserving `app.llm.onnx_embeddings` import paths and the `_ORT_AVAILABLE` patch point the test uses) | `app/llm/embedding/**`, `app/rag/embedding/**` |
| 3 | Remove the stale `app/core/observability/`, `app/core/config/` dirs and the empty `app/api/v1/routes/` | — |
| 4 | `ruff check --fix` + `ruff format` | 13 files |
| 5 | Correct the false SQLite docstrings | 2 files |
| 6 | Fix the stale "no query-vector cache" comment and reconcile `query_cache_capacity` | retriever, cache, models.yaml |

### B3 — Performance (each re-benchmarked)

| # | Action | Target |
|---|---|---|
| 1 | Concurrent MLX port probe + pooled client + short connect timeout | `/models/providers` 2601 ms → <100 ms |
| 2 | Stop closing the shared HTTP client in health probes | connection pooling restored |
| 3 | mtime-cached `Settings` | −1.46 ms/call, −5 file reads/request |
| 4 | Real retry in `_fetch_json_with_retry` | −0.5 s per unreachable provider |
| 5 | De-duplicate trace events + batch MongoDB inserts | fewer round-trips/analysis |
| 6 | Remove the redundant second `trim_memory()` | −3.7 ms/analysis |
| 7 | Batch the per-chunk `find_one` (N+1 → 1) | fewer MongoDB round-trips |

### B4 — Accuracy (benchmark-gated; see DECISION-002)

| # | Action |
|---|---|
| 1 | Reject predicate-free claims via a verb/relation heuristic aligned with `_PREDICATE_VERBS` |
| 2 | Stop a single contradicted claim forcing score 0 (minimum-claim-count or contradiction-rate floor) |
| 3 | Bound the `{"$in": …}` id lists and the self-heal `to_list(10_000)` |

### B5 — Validation

| # | Action |
|---|---|
| 1 | Full `pytest`; **fix the pre-existing coverage-gate failure** (CHANGE REQUIRED-016) |
| 2 | Re-run `bench_api.py` + `analyze_quality.py`; diff against the §1 baselines |
| 3 | Concurrency + failure-injection checks (rate limit fires, provider down, Qdrant down, Mongo down) |
| 4 | Record every regression honestly as DEGRADATION |

**Also required:** the graph-behaviour change (CHANGE REQUIRED-002) needs its own
regression tests, and the Gemini path (CHANGE REQUIRED-001) can only be verified
by unit test + a signature contract — there is no local cloud key, and cloud
egress is opt-in via the `cloud` extra.

---

## 9. Blockers

| # | Blocker | Impact | Mitigation |
|---|---|---|---|
| BLK-1 | Embedded-Qdrant storage path is locked by the running uvicorn worker | In-process stage benchmarks (`bench_pipeline.py`) cannot run concurrently | Stop the worker, or point `QDRANT_URL` at a separate path for the benchmark. The HTTP harness is unaffected. |
| BLK-2 | No cloud provider key; cloud egress is opt-in | The Gemini path cannot be end-to-end benchmarked | Verify by unit test + signature contract |
| BLK-3 | ~~The test suite fails its coverage gate on `main`~~ **RESOLVED in B2.1** (78.12 %) | — | B5 must confirm the gate is still green after B2.2–B4 |
| BLK-4 | `reranker.enabled: false`, and BGE int8 recall unmeasured | Two promising optimisations are blocked on measurement, not on effort | Dedicated before/after benchmarks (DECISION-003) |
