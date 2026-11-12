# TRUSTRAG — Backend Performance & Quality Audit (Phase B1)

**Status:** AUDIT COMPLETE — READ-ONLY. No source changes have been made to `app/`.
**Date:** 2026-11-12
**Scope:** `apps/api/app/**` (+ `apps/api/scripts/**` for the benchmark harness).
**Method:** static read + live measurement against local services (embedded Qdrant,
MongoDB 9.0, Ollama `gemma3:1b`).

---

## 1. Measurement environment

| Item | Value |
|---|---|
| Host | macOS (darwin), Apple Silicon, 16 GB class |
| MongoDB | `mongodb://localhost:27017`, DB `trustrag_db` (local, index creation on) |
| Qdrant | embedded mode (`QDRANT_URL=local`) → `apps/api/app/data/qdrant` |
| LLM | Ollama `gemma3:1b` (1B params, GGUF) — `models.yaml` default provider |
| Embedding | ONNX Runtime `BAAI/bge-small-en-v1.5`, 384-d, int8 weights absent (fp32 134 MB) |
| Reranker | ONNX `ms-marco-MiniLM-L-6-v2` int8 present, but `reranker.enabled: false` |
| API server | already running on `127.0.0.1:8000` (uvicorn) |
| Test suite | `pytest` 761 passed, 18 warnings, 36.5 s, coverage **77.82 %** (`--cov-fail-under=78`) |

> **Pre-existing condition:** the suite *fails its own coverage gate* (77.82 % < 78 %).
> This is the state on `main` before any of my changes. It must be addressed before
> B5 can be called green.

---

## 2. Architecture map

```
HTTP client
  └─ app/main.py:create_app()            CORS + GZip + 3 custom middlewares + slowapi limiter
      └─ app/api/router.py:api_router    /api/v1 prefix
          ├─ health.py      /health /health/ready /health/detailed /metrics
          ├─ auth.py        /auth/register /auth/login /auth/me /auth/logout
          ├─ knowledge_bases.py  CRUD + /documents upload + /snapshots + /rollback
          ├─ documents.py   /documents/{id} + page-image serve
          ├─ analyses.py    POST /analyses (background) + poll + SSE stream
          ├─ models.py      /models/providers /models/hardware /models/memory/trim
          ├─ evidence.py /claims.py /conflicts.py
          └─ internal.py    service-token routes (ingest/search/verify)

Background pipeline:  app/services/pipeline.py:run_analysis_pipeline
  └─ app/rag/agent/graph/coordinator.py:execute_agentic_rag_flow
      └─ LangGraph (app/rag/agent/graph/build.py)
          retrieval → generation → verification
                        ↓ (should_recover)
                     recovery → should_end  ← ALWAYS "end"  (see F-2)
      └─ app/rag/verification/pipeline/orchestrator.py:execute_claim_verification
          fused_decompose_verify | decompose → batch NLI → per-claim fallback
          → targeted claim retrieval → NLI re-check
```

Model layer:
```
app/llm/model_registry.py    get_llm / get_verification_model / get_embedding_model / get_reranker
app/llm/providers/           base (HTTP pool), ollama, llama_cpp, mlx, health, discovery
app/llm/embedding/engine.py  ONNX BGE engine  ← DUPLICATE of app/rag/embedding/engine.py
app/llm/embedding/cache.py   ONNXBGEEmbeddingsWrapper ← DUPLICATE of app/rag/embedding/cache.py
app/llm/registry/            ← DEAD PACKAGE (import fails; see F-5)
```

---

## 3. Latency baseline (live, n=12 analyses + read paths)

### 3.1 API endpoints (black-box HTTP)

| Endpoint | p50 | p95 | p99 | n |
|---|---|---|---|---|
| `GET /api/v1/health` | **5.66 ms** | 7.59 | 7.59 | 3 |
| `GET /api/v1/metrics` | **2.63 ms** | 2.99 | 2.99 | 3 |
| `GET /api/v1/knowledge-bases` | **18.26 ms** | 20.46 | 20.46 | 3 |
| `GET /api/v1/analyses` | **8.54 ms** | 16.21 | 16.21 | 3 |
| `POST /api/v1/analyses` (returns 201) | **18.92 ms** | 35.63 | 78.57 | 12 |
| `GET /api/v1/models/providers` | **2601.42 ms** | 2603.03 | 2603.03 | 3 |
| **POST→terminal analysis (end-to-end)** | **4909.69 ms** | 4938.90 | 5840.31 | 12 |

### 3.2 Stage latency (from server trace events, same runs)

| Stage | latency_ms (observed) |
|---|---|
| retrieval node | 108–128 |
| generation node | ~1401 |
| recovery node | 0 (no-op — see F-2) |
| total analysis | 2886–5840 |

### 3.3 Micro-benchmarks

| Operation | p50 | p95 |
|---|---|---|
| `get_settings()` (re-reads 5 env files from disk) | **1.46 ms** | 1.52 |
| `get_model_config()` (mtime-cached) | 0.002 ms | 0.002 |
| `tiktoken.get_encoding()` | 0.000 ms | — |
| `tiktoken.encode()` of a 8-segment context | 0.494 ms | 0.520 |
| `format_context_with_chunk_indices()` | 0.112 ms | 0.124 |
| `reciprocal_rank_fusion()` (20+20) | 0.016 ms | 0.017 |
| `gc.collect()` | 2.45 ms | 3.11 |
| `trim_memory()` (gc + malloc_trim) | 3.70 ms | 4.53 |
| ONNX embedding **model load** | **6829 ms** | — |
| ONNX embedding `embed_query()` cold | 4.6 ms | 6.3 |
| ONNX embedding `embed_query()` cached | 0.0 ms | 4.1 |
| Process RSS after model load | 52 MB → **692 MB** | — |

### 3.4 Provider status probes (the `/models/providers` cost)

| Probe | p50 | connected |
|---|---|---|
| `check_ollama_status` | 25.5 ms | yes |
| `check_llamacpp_status` | 20.9 ms | no |
| **`check_mlx_status`** | **2601.0 ms** | no |

`check_mlx_status` walks **5 ports sequentially**, and `_fetch_json_with_retry`
**never retries** (the `raise` sits inside the `except`, so attempt 1 is dead code).
Each refused port therefore costs a full 4 s-timeout client *plus* a fresh
`httpx.AsyncClient` — 5 clients, 5 connections, ~2.6 s.

---

## 4. RAG accuracy baseline

Seeded a known-ground-truth corpus (retrieval policy, 5 probes with an expected
substring) and scored the stored evidence.

| Query | Recall@K | Precision@K | MRR | n | status |
|---|---|---|---|---|---|
| reciprocal rank fusion constant | 1.00 | 0.33 | 1.00 | 3 | **3× abstained** |
| fused candidates before reranking | 1.00 | 0.33 | 1.00 | 3 | 3× completed |
| embedding model for dense retrieval | 1.00 | 0.33 | 1.00 | 3 | 3× completed |
| evidence does not support answer | 1.00 | 0.33 | 1.00 | 3 | **3× abstained** |
| what the temporal filter drops | — | — | — | 0 | (not probed) |
| **overall** | **1.00** | **0.33** | **1.00** | 12 | — |

**Retrieval is perfect. The failures are all downstream of retrieval.**

Overall run outcome: **6 completed / 6 abstained**, mean reliability **0.50**.

---

## 5. Findings

Severity: **S1** = correctness/data-loss · **S2** = material latency/cost · **S3** = cleanup.

---

### F-1 — `probe_cloud_llm` is called with the wrong signature (S1)

`app/services/pipeline.py:390`
```python
await local_llm_mod.probe_cloud_llm(effective_llm_provider, effective_llm_model)
```
but the real signature is keyword-only and needs two more arguments:
```python
async def probe_cloud_llm(*, norm: str, model: str, base_url: str, timeout: float, hint: str = "") -> None
```
**Reproduced:** `TypeError: probe_cloud_llm() takes 0 positional arguments but 2 were given`.

Impact: `create_analysis` for the `gemini` provider raises `TypeError` **before the
analysis document is written** → 500 with no persisted run, no trace, no
recoverability. The Gemini path is completely broken. The call is also not
wrapped in a `try`, so it cannot be caught by the pipeline's error handler
(which only wraps the *background* task, not `create_analysis` itself).

---

### F-2 — The recovery loop is a no-op; the graph can never re-run a round (S1)

`app/rag/agent/graph/edges.py:67`
```python
def should_end(state: AgentState) -> str:
    """Route after recovery: end if attempts exhausted, else loop back."""
    return "end"
```
The docstring promises a loop back; the body always returns `"end"`. The graph
mapping is `{"retrieve": "retrieval", "end": "__end__"}` — the `"retrieve"`
branch is unreachable.

**Verified:** `should_recover(state)` → `"recover"`, then `should_end(state)` → `"end"`.
Every recovery attempt runs the recovery node and then terminates the graph.

Consequence chain (all verified in a live run):
1. `recovery_node` sets `state["answer"] = None` and `state["claims"] = []`.
2. The graph ends. `final_state` carries the **cleared** state.
3. `pipeline.py` computes the verdict from that cleared state.

Measured effect on a real analysis:
```
WITH verification result : FAILED 0.0 EVIDENCE_CONFLICT  ['1/1 claims contradicted by evidence', ...]
AFTER recovery cleared   : FAILED 0.0 RETRIEVAL_FAILURE  ['No claims extracted for verification']
```
The specific contradiction diagnosis is **destroyed** and replaced by a generic
"No claims extracted for verification". The stored `analysis.diagnosis` for that
run read `['No claims extracted for verification']` even though a claim *had*
been extracted and verified. The claim itself survived in the `claims`
collection, so the DB is internally inconsistent.

`recovery_node` also persists a `recovery_runs` document with a strategy
(`re_retrieve` observed) that was then never acted on.

---

### F-3 — A correct answer is discarded because a *good* claim was labelled CONTRADICTED (S1, accuracy)

Live run, query *"What is the reciprocal rank fusion constant?"*:

- retrieval: correct segment **rank 1** (RRF 0.0328)
- generation: correct answer *"The reciprocal rank fusion constant is sixty."*
- decomposition: claim **"Sixty is a number"** — the 1B model produced a
  content-free claim, not the answer's actual proposition
- NLI: **CONTRADICTED**, with explanation *"The premise states that sixty is a
  number, while the hypothesis claims it judges."* — a nonsense explanation
- verdict: FAILED / score 0 → grounding gate withheld the correct answer →
  **abstained**

Two independent defects compound here:
- **The decomposer lost the predicate.** "Sixty is a number" is not the
  proposition the answer asserted. `_filter_degenerate_claims` does not catch
  it: it is 4 words, ends without terminal punctuation, and "Sixty" is
  capitalised, so the "title-case heading" rule (`all(w[0].isupper() ...)`)
  does not fire — "is", "a", "number" are lowercase.
- **A single CONTRADICTED claim on one claim ⇒ coverage 0/1 ⇒ score 0.**
  `minimum_evidence_coverage = 0.80` means one bad verdict out of one claim
  produces score 0 and a full abstention. With `max_verification_claims: 5`
  (lean tier) and a 1B model, this is the dominant failure mode.

Note the contrast: the *"Which embedding model…"* probe produced the claim
*"Dense retrieval uses BGE-small embeddings computed locally through ONNX
Runtime"* — a real proposition, correctly SUPPORTED. The difference is
whether the 1B decomposer preserved the predicate. **The abstention rate is
governed by 1B-model decomposition fidelity, not by evidence quality.**

---

### F-4 — `/api/v1/models/providers` costs 2.6 s per call (S2)

`app/llm/providers/health.py:200` `check_mlx_status` probes 5 ports
**sequentially**, each through `_fetch_json_with_retry`, which:
- creates a **new `httpx.AsyncClient` per attempt** (no pooling, new TLS
  handshake each time);
- has a **broken retry** — `raise` is inside the `except`, so attempt 1 never
  runs; the function sleeps 0.5 s then re-raises.

Measured: 2601 ms p50 for a *disconnected* MLX provider. The frontend polls
`/models/providers` **every 8 s** (`refetchInterval: 8000`), so a single idle
browser tab costs the server ~325 ms/s of pure provider probing, and a
`GET /api/v1/models/providers` blocks a worker for 2.6 s.

Compounding: `check_ollama_status` and `check_llamacpp_status` use
`async with _shared_http_client(...)` — but `httpx.AsyncClient.__aexit__`
**closes** the client. The pooled client is destroyed and rebuilt on every
health check. **Verified:** after the `async with` block `client.is_closed is
True`, and the next `_shared_http_client()` call returns a *different* object.
So the shared-connection pool is effectively defeated on the health path.

---

### F-5 — `app/llm/registry/` is a dead package that fails to import (S3)

`python -c "import app.llm.registry"` →
```
ModuleNotFoundError: No module named 'app.llm.registry.factories.reranker'
```
`__init__.py` imports `factories.reranker` and `factories.status`; neither
file exists. The package is referenced by **no** module and **no** test
(`grep` over the repo finds only its own self-references). 438 LOC of
unreachable, broken code. The live equivalents live in
`app/llm/model_registry.py`.

---

### F-6 — Duplicated embedding engine + cache (S3)

`app/llm/embedding/engine.py` (263 LOC) and `app/rag/embedding/engine.py`
(245 LOC) are near-identical forks — the diff is only the `_is_ort_available()`
shim indirection. Likewise `app/llm/embedding/cache.py` and
`app/rag/embedding/cache.py` differ **only** in the import line
(`app.llm.embedding.engine` vs `app.rag.embedding.engine`).

Confusingly, `app/llm/embedding/__init__.py` re-exports from `app.rag.embedding.*`,
while `app/llm/onnx_embeddings.py` imports from `app.llm.embedding.engine`
directly — so **two different `ONNXBGEEmbeddings` classes exist**, and
`model_registry.py:364` constructs the `app.llm.embedding.engine` one while
`model_registry.py:375` imports the wrapper from the `app.rag` tree. The
`_ORT_AVAILABLE` shim exists solely so `tests/test_onnx_engines.py` can patch
`app.llm.onnx_embeddings._ORT_AVAILABLE` — i.e. the duplication was created
to satisfy a test, not by design.

Also: both cache files claim in their docstring **"Tier 2: persistent SQLite
disk cache (across restarts)"** — **no SQLite code exists** (`grep -c sqlite`
→ 0 in both). The wrapper is an in-memory LRU only. The docstring is false.

---

### F-7 — `get_settings()` re-reads 5 files from disk on every call (S2)

`app/config/settings.py:287` deliberately builds a fresh `Settings()` per call.
`pydantic-settings` then re-reads and re-parses all five `env_file` paths
(`.env`, `../.env`, `../../.env`, repo-root `.env`, `apps/api/.env`).

**Measured: 1.46 ms p50 / 1.52 ms p95 per call.** It is called **29 times** in
the codebase, including on the per-request auth path
(`security.py:118` in `_decode_jwt`, hit by every authenticated request) and
in `model_registry.get_llm` / `get_verification_model` (once per LLM call).

On a 1B local model this is not the dominant cost, but it is pure,
unconditional, avoidable I/O on every request — and it makes the "no
stale-state bugs" claim expensive: the *values* only change when `.env`
changes, which is detectable by mtime exactly as `models.yaml` already does.

---

### F-8 — The global rate limit is configured but never enforced (S2, security)

`app/main.py:530`:
```python
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
```
slowapi applies `default_limits` **only via `SlowAPIMiddleware`**, which is
never added. The per-route `@_auth_limiter.limit(...)` decorators in
`auth.py` *do* work (they are self-contained), but every other endpoint has
**no rate limit**.

**Verified:** 70 consecutive authenticated `GET /api/v1/models/providers`
requests → **70 × HTTP 200**, zero 429s. The same test on
`POST /api/v1/auth/login` correctly returned `429` after 5 attempts.

The `RateLimitExceeded` exception handler is therefore dead code for
non-auth routes.

---

### F-9 — Duplicate trace events (S2)

Every node emits `X.started` / `X.completed` **and** `_execute_with_fallback`
emits its own `X.started` / `X.completed`. A live analysis produced:
```
retrieval.started   ×2      retrieval.completed ×2
generation.started  ×2      generation.completed ×1
```
11 trace events for one analysis, each a **separate MongoDB `insert_one`**.
The `_execute_with_fallback` pair duplicates the node's own pair; the
`generation.completed` count is asymmetric with `generation.started` because
the node's own completion event never fires on the failure path.

---

### F-10 — `trim_memory()` runs twice per analysis, off the hot path (S3)

`app/rag/agent/graph/coordinator.py:112` (in the `finally`) and
`app/services/pipeline.py:911` (in the `finally`) both call
`asyncio.to_thread(memory.trim_memory)`. Measured `trim_memory()` = 3.70 ms
p50 (a full `gc.collect()` is 2.45 ms of that). The coordinator's call
already covers the whole analysis; the pipeline's is redundant.

`check_and_enforce_memory_guard` exists but has **no production caller**
(only `tests/test_hardware.py`).

---

### F-11 — N+1 and unbounded-query patterns (S2)

| Site | Pattern |
|---|---|
| `app/rag/verification/pipeline/retrieval.py:65` | `find_one` **per chunk** inside a loop (N+1 round-trips to Mongo) |
| `app/rag/verification/integrity.py:62` | `{"$or": [ … up to 100 clauses ]}` — one giant OR per audit |
| `app/services/claims_evidence.py:78,179,203` | fetch up to **1000** analysis ids, then `{"$in": [...]}` — the `$in` can exceed Mongo's 16 MB BSON limit on large tenants |
| `app/rag/retrieval/retriever.py:346` | `find({"_id": {"$in": doc_objs}})` — unbounded `$in` from result payloads |
| `app/rag/agent/graph/nodes/retrieval.py:207` | `.to_list(10_000)` self-heal — unbounded RAM spike per document |

---

### F-12 — Embedding "no query-vector cache" comment is wrong (S2)

`app/rag/retrieval/retriever.py:125` says *"No query-vector cache: embed fresh
every call."* But `get_embedding_model()` returns the **wrapper**
(`ONNXBGEEmbeddingsWrapper`), whose `embed_query` consults a 512-entry
in-memory LRU. Measured: cached `embed_query` p50 **0.0 ms** vs cold 4.6 ms.

`models.yaml` also declares `retrieval.query_cache_capacity: 1024` — a key
that **no code reads** (`grep` → 0 hits). The wrapper's `max_cache_size`
hardcodes 512 instead. The comment, the yaml key, and the implementation
disagree three ways.

---

### F-13 — `_fetch_json_with_retry` retry is unreachable (S3)

`app/llm/providers/health.py:75` — `raise` sits inside the `except`, so the
second loop iteration can never execute. Verified: one 0.5 s sleep, then
re-raise. Either remove the loop or move the `raise` under `attempt == 1`.

---

### F-14 — Small-module hygiene (S3)

- `ruff check app/` → **13 errors** (12 × E402 in `app/rag/verification/verifier.py`,
  1 × RUF022 unsorted `__all__`).
- `ruff format --check app/` → **13 files would be reformatted**.
- `app/core/observability/` and `app/core/config/` contain **only** `__pycache__`
  — stale directories left behind by the restructure (git-tracked files: none).
- `app/api/v1/routes/` contains **only** an empty `__init__.py`; the routers
  live in `app/api/v1/*.py` and are registered by `app/api/router.py`.
- `app/llm/embedding/cache.py` (147 LOC) and `app/rag/embedding/cache.py`
  (147 LOC) are byte-identical except one import line.

---

## 6. Prioritized recommendations

### Tier 1 — correctness (must fix first; each is a small, isolated change)

| # | Fix | Files | Risk |
|---|---|---|---|
| R-1 | Call `probe_cloud_llm` with the correct keyword args (`norm=`, `model=`, `base_url=`, `timeout=`); add a `base_url` for Gemini | `app/services/pipeline.py`, `app/llm/providers/health.py` | low — restores the broken cloud path |
| R-2 | Make `should_end` honour the recovery budget so the graph can loop back to retrieval | `app/rag/agent/graph/edges.py`, `app/rag/agent/graph/build.py` | **medium** — changes graph behaviour; needs regression tests |
| R-3 | Preserve the verdict + answer across the recovery node (don't clear what the final verdict is computed from) | `app/rag/agent/graph/nodes/recovery.py`, `app/services/pipeline.py` | medium |
| R-4 | Add `SlowAPIMiddleware` so the configured global rate limit is actually enforced | `app/main.py` | low |
| R-5 | Stop asserting "persistent SQLite disk cache" when only an in-memory LRU exists | `app/rag/embedding/cache.py`, `app/llm/embedding/cache.py` | none (docs) |

### Tier 2 — latency & resource

| # | Fix | Expected effect (to be measured) |
|---|---|---|
| R-6 | Probe the MLX ports **concurrently**, with one pooled client and a short connect timeout | `/models/providers` 2601 ms → target <100 ms |
| R-7 | Stop closing the shared HTTP client in the health probes (`async with` → plain use) | restores connection pooling on the health path |
| R-8 | Cache `Settings` behind an mtime check on the `.env` files (same pattern `models.yaml` already uses) | −1.46 ms per `get_settings()` call; removes 5 file reads/request |
| R-9 | Collapse the duplicate trace events; batch the MongoDB inserts | fewer round-trips per analysis |
| R-10 | Drop the redundant second `trim_memory()` | −3.7 ms per analysis |
| R-11 | Fix `_fetch_json_with_retry` (real retry, pooled client) | −0.5 s per unreachable provider |
| R-12 | Batch the per-chunk `find_one` in `_persist_claim_evidence` | N+1 → 1 Mongo round-trip |

### Tier 3 — accuracy (must not regress; benchmark-gated)

| # | Fix | Rationale |
|---|---|---|
| R-13 | Improve claim decomposition fidelity for small models — reject content-free claims like *"Sixty is a number"* (predicate-bearing heuristic) | directly targets the 50 % abstention rate |
| R-14 | Stop letting a single CONTRADICTED claim out of one claim force score 0 → full abstention (require a minimum claim count or use a contradiction-rate floor) | F-3: one bad verdict ⇒ score 0 |
| R-15 | Reconcile `retrieval.query_cache_capacity` with the wrapper's real capacity; fix the stale "no query-vector cache" comment | config/impl coherence |
| R-16 | Bound the `{"$in": …}` id lists in `claims_evidence.py` and the self-heal `to_list(10_000)` | removes the unbounded-query class |

### Tier 4 — cleanup (mechanical, low risk)

| # | Fix |
|---|---|
| R-17 | Delete the dead, unimportable `app/llm/registry/` package (438 LOC) |
| R-18 | Collapse the duplicated `app/llm/embedding/{engine,cache}.py` into one canonical module + a thin re-export shim |
| R-19 | Remove the stale `app/core/observability/` and `app/core/config/` directories and the empty `app/api/v1/routes/` |
| R-20 | `ruff check --fix` + `ruff format` (13 errors, 13 files) |
| R-21 | Wire `check_and_enforce_memory_guard` into the post-analysis path (or delete it) |

### Explicitly **not** recommended without evidence
- **Enabling the reranker** (`reranker.enabled: false` today). The int8 weights
  are present, but enabling it changes latency *and* ordering; it must be
  benchmarked against the Recall@K/Precision@K baseline above before any
  decision. It is a candidate, not a fix.
- **Quantisation of the embedding model.** `bge-small-en-v1.5.onnx` is fp32
  (134 MB, 692 MB RSS after load). An int8 export could cut RAM materially,
  but BGE recall under int8 is **not** measured here — the models.yaml comment
  itself warns "1 % clipping can drop the true nearest neighbour at the
  reranker boundary". Requires its own before/after recall benchmark.
- **Switching the default model away from `gemma3:1b`.** The abstention rate
  is a model-fidelity issue (F-3), but changing the shipped default is a
  product decision with cost implications, not a performance fix. Worth
  measuring `qwen3:1.7b` (already installed) as an alternative — the
  `deep_reasoning_mode` path exists — but it must be presented as a
  measured trade-off, not an assumed win.

---

## 7. Measurement plan for B5 (so every claim is falsifiable)

1. **Latency** — `scripts/bench_api.py` (black-box HTTP, p50/p95/p99 per
   endpoint, analysis create + end-to-end). Baseline captured:
   `bench_api_results_BASELINE.json`.
2. **Retrieval quality** — `scripts/analyze_quality.py` over the seeded
   ground-truth corpus → Recall@K / Precision@K / MRR per query.
   Baseline: `quality_results_BASELINE.json`.
3. **Stage latency / resource** — `scripts/bench_pipeline.py` (in-process:
   dense / sparse / fusion / temporal / rerank / generation / verification,
   RSS before-after). Requires exclusive access to the embedded-Qdrant path.
4. **Regression** — full `pytest` suite; the 77.82 % coverage gate must pass
   (fixing it is a prerequisite, not a side effect of this work).

Every change in B2–B5 must be re-benchmarked against these baselines, and
the numbers reported must come from the harness — not from estimates.

---

## 8. Change log

See `docs/backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md`. As of this commit
it records **audit findings only** — no performance or quality improvement is
claimed, because none has been implemented or measured yet.

---

## 9. Blockers

- **B-1:** the embedded-Qdrant storage path is locked by the already-running
  uvicorn worker, so in-process stage benchmarks cannot run concurrently with
  it. Either stop the worker, or point `QDRANT_URL` at a separate path for the
  benchmark. The HTTP black-box harness is unaffected.
- **B-2:** the Gemini path cannot be end-to-end benchmarked locally (no cloud
  key, and cloud egress is opt-in per `pyproject.toml` `cloud` extra). F-1
  will be verified by unit test + signature contract, not by live call.
- **B-3:** the test suite currently fails its own coverage gate
  (77.82 % < 78 %) on `main`, before any change.
