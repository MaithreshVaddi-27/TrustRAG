# TrustRAG Local-LLM Load and RAG Performance Audit

**Date:** 2026-09-07  
**Branch:** `ui-redesign`  
**Audit roles:** Senior Backend Engineer, Senior AI/ML Engineer, Senior Optimization Engineer, Senior Testing Engineer  
**Scope:** Local LLM request patterns, retrieval, embeddings, reranking, context construction, semantic cache, background jobs, memory pressure, test/load infrastructure.

## Executive summary

The system already uses several useful load controls: a hardware-aware analysis semaphore, token/context caps, semantic caching, model caching, LZU/LRU caches, and bounded recovery. However, several implementation details increase local LLM load or block the FastAPI event loop:

1. Every Ollama/llama.cpp request constructs a new `httpx.AsyncClient`. **→ Fixed: pooled clients with lifespan cleanup**
2. Upload parsing and chunking execute synchronously inside async endpoints. **→ Fixed: moved to `asyncio.to_thread()`**
3. A shared embedding manager is initialized at startup but does not appear to be the serving path used elsewhere. **→ Fixed: removed unused SharedEmbeddingManager**
4. Semantic-cache payloads are oversized and include non-JSON-safe evidence metadata. **→ Fixed: minimal answer-only payloads**
5. Per-query Qdrant collection metadata, SQLite cache access, repeated context formatting, and fallback NLI requests add avoidable overhead. **→ Fixed: Qdrant dim caching, SQLite batch IN query, context reuse, async disk I/O**
6. Ingestion has no equivalent global concurrency cap, so rapid uploads can overload a local model host. **→ Fixed: ingestion semaphore + upload rate limits**

## Optimization update — 2026-09-07

The highest-risk local-load items were implemented:

- Local generation now uses pooled HTTP clients and closes them during shutdown.
- Upload parsing/chunking no longer blocks the event loop.
- The unused duplicate embedding-manager load was removed from startup and the registry; the one cached registry model remains the serving path.
- Semantic cache stores only a minimal JSON-safe answer and reruns retrieval/verification on a hit instead of trusting stale evidence.
- KB/document changes invalidate semantic-cache entries.
- Ingestion jobs are serialized per API process.
- Qdrant collection dimensions are cached per collection.
- SQLite embedding-cache batch lookup now uses one indexed `IN` query; async wrapper paths move disk I/O to worker threads.
- The dead `ContextManager` block and unimplemented recovery strategies were removed from the active loop.
- The in-memory embedding cache now uses `OrderedDict` LRU semantics, eliminating duplicate key growth and stale eviction.
- Upload and URL-ingestion endpoints now have per-endpoint rate limits (10/minute default) and background ingestion is serialized per API process.

## Findings

### PERF-H1: Local-LLM requests do not reuse HTTP clients

- **Severity:** High
- **Files:**
  - `apps/api/app/core/local_llm.py:163`
  - `apps/api/app/core/local_llm.py:331`
- **Status:** **Fixed on 2026-09-07** — Pooled `httpx.AsyncClient` per base URL/timeout/loop, closed on lifespan shutdown.

### PERF-H2: Upload parsing and chunking block the FastAPI event loop

- **Severity:** High
- **Files:**
  - `apps/api/app/api/v1/knowledge_bases.py:152-155`
  - `apps/api/app/api/v1/knowledge_bases.py:273-277`
- **Status:** **Fixed on 2026-09-07** — `parse_document()` and `chunk_text()` moved to `asyncio.to_thread()`.

### PERF-H3: Startup loads a shared embedding manager that later paths do not consume

- **Severity:** High
- **Files:**
  - `apps/api/app/main.py:145-159`
  - `apps/api/app/core/model_registry.py`
- **Status:** **Fixed on 2026-09-07** — Removed unused `SharedEmbeddingManager` initialization and class.

### PERF-H4: Semantic-cache payloads are too large and not JSON-safe

- **Severity:** High
- **Files:**
  - `apps/api/app/core/semantic_cache.py`
  - `apps/api/app/agent/graph.py:1071-1083`
- **Status:** **Fixed on 2026-09-07** — Stores only minimal JSON-safe answer; ObjectIds removed; cache hits rerun fresh retrieval/verification.

### PERF-M1: Dense retrieval queries Qdrant collection metadata on every request

- **Severity:** Medium
- **File:** `apps/api/app/retrieval/retriever.py:170-198`
- **Status:** **Fixed on 2026-09-07** — Added per-collection dimension cache (`_get_collection_dimension`).

### PERF-M2: SQLite embedding cache performs synchronous I/O on async paths

- **Severity:** Medium
- **Files:**
  - `apps/api/app/core/disk_cache.py`
  - `apps/api/app/core/model_registry.py`
- **Status:** **Fixed on 2026-09-07** — Disk calls moved to `asyncio.to_thread()`.

### PERF-M3: Batch embedding-cache probes use one query per text

- **Severity:** Medium
- **File:** `apps/api/app/core/disk_cache.py:113-121`
- **Status:** **Fixed on 2026-09-07** — Single `IN (...)` query with duplicate handling.

### PERF-M4: Fallback verification repeats identical context formatting per claim

- **Severity:** Medium
- **Files:**
  - `apps/api/app/verification/verifier.py:301-303`
  - `apps/api/app/verification/verifier.py:459-465`
  - `apps/api/app/generation/generator.py:137-163`
- **Status:** **Fixed on 2026-09-07** — `format_context_with_chunk_indices` returns context + mapping; `batch_verify_claims_nli` and `verify_claim_nli` accept pre-built `context_str`.

### PERF-M5: Semantic-cache embedding exception can block on the synchronous Hugging Face path

- **Severity:** Medium
- **File:** `apps/api/app/agent/graph.py:1027-1028`
- **Status:** **Fixed on 2026-09-07** — Fallback uses `asyncio.to_thread()`.

### PERF-M6: Dead context-management work remains in generation

- **Severity:** Medium
- **Files:**
  - `apps/api/app/agent/graph.py:552-581`
  - `apps/api/app/core/context.py`
- **Status:** **Fixed on 2026-09-07** — Removed unused `ContextManager` block from `generation_node`.

### PERF-M7: Ingestion has no global concurrency cap

- **Severity:** Medium
- **Files:**
  - `apps/api/app/api/v1/knowledge_bases.py`
  - `apps/api/app/ingestion/pipeline.py`
- **Status:** **Fixed on 2026-09-07** — Ingestion semaphore in `pipeline.py` + upload rate limits (10/min) in `knowledge_bases.py`.

### PERF-M8: Provider status checks spawn subprocesses on request

- **Severity:** Medium
- **Files:**
  - `apps/api/app/api/v1/models.py`
  - `apps/api/app/core/local_llm.py:463-514`
- **Status:** Open at audit-file creation
- **Impact:** Frontend polling can repeatedly execute `ollama list` or `llama-server --cache-list` and perform HTTP probes.
- **Recommended fix:** Cache provider discovery results for a short TTL and support explicit refresh.

## Local-LLM optimization plan

### Immediate code-level optimizations

1. Reuse local LLM HTTP clients and close them cleanly.
2. Keep all parse/chunk CPU work off the event loop.
3. Remove or consolidate duplicate embedding model loading.
4. Reduce semantic-cache payload to minimal JSON-safe fields.
5. Format verification context once per pipeline attempt and preserve that order end to end.
6. Cache Qdrant collection metadata per collection.
7. Move SQLite cache calls off the event loop or batch them.
8. Add ingestion and provider-discovery concurrency/TTL controls.

### Configuration and operations optimizations

1. Run one API worker for local-LLM mode so the hardware-aware semaphore is authoritative.
2. Keep `num_ctx` and `max_context_chunks` aligned with the installed model's practical context window.
3. Limit concurrent analyses to one or two on 8 GB hosts; expose this as an environment override.
4. Prefer keep-alive Ollama/llama.cpp servers with warmed model weights.
5. Keep reranking disabled on very small hosts or use a small local cross-encoder only when accuracy gains justify latency.
6. Use semantic cache only after evidence reconstruction is deterministic and cache invalidation is complete.
7. Split public liveness from provider/model diagnostics to avoid expensive health checks.

## Testing and load gaps

1. No regression test currently forces a slow document parser while another request must remain responsive.
2. No test asserts that local LLM calls reuse a pooled HTTP client.
3. No direct test covers semantic-cache persistence with evidence metadata.
4. No test covers dead embedding manager versus actual registry usage.
5. Existing k6 smoke coverage focuses on health and knowledge-base listing; it does not exercise upload ingestion, analysis execution, SSE streams, provider discovery, or local LLM queueing.

## Verification commands

```bash
cd apps/api
python -m pytest tests -q --no-cov
python -m ruff check app tests
python -m mypy app
```

With the backend running:

```bash
API_BASE_URL=http://localhost:8000 k6 run load-test/smoke.js
```

## Recommended implementation order

1. Fix correctness-critical evidence ordering and cache persistence before tuning.
2. Add shared local-LLM HTTP client lifecycle.
3. Move upload CPU work off the event loop and add ingestion backpressure.
4. Remove duplicate embedding model loading.
5. Shrink and invalidate semantic cache.
6. Cache retrieval/provider metadata.
7. Extend tests and load scripts to cover the real local-LLM path.
