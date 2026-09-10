# TrustRAG Backend and Agentic RAG Correctness Audit

**Date:** 2026-09-07  
**Branch:** `ui-redesign`  
**Audit roles:** Senior Backend Engineer, Senior AI/ML Engineer, Senior Testing Engineer (whitebox)  
**Scope:** FastAPI backend, LangGraph agent loop, retrieval, generation, verification, persistence, local LLM clients, caches, tests.

## Executive summary

The backend is organized and substantially hardened: FastAPI lifespan management, MongoDB ownership checks, Qdrant retrieval, hybrid dense/sparse search, deterministic context ordering, claim verification, and recoverable analysis jobs are all present. The baseline audit pass reported the backend unit suite as green (`118 passed`) and Ruff clean.

The most important defects are not style issues; they corrupt or weaken TrustRAG's core reliability guarantees:

1. **Claim-to-evidence links can point at the wrong evidence** because the verifier numbers a deterministically sorted/deduplicated context while evidence IDs remain in retrieval/rerank order.
2. **Semantic cache hits can produce internally inconsistent analyses**, skip evidence/claim persistence, and fail disk persistence because cached payloads include BSON `ObjectId` values.
3. **Deleting documents or a knowledge base does not invalidate semantic-cache entries**, so deleted evidence can continue to produce a verified answer.
4. **The synchronous local-LLM compatibility path can crash inside an active event loop**, and each local LLM request creates a new HTTP client, increasing overhead under the recovery loop.
5. **Large PDF uploads parse synchronously on the FastAPI event loop**, blocking unrelated requests.

## Fix update — 2026-09-07

The serious and confirmed defects listed above were fixed in this working tree:

- C-1 context-to-evidence mapping now uses the same sorted/deduplicated segment order used by the NLI prompt.
- H-1 synchronous local-LLM compatibility paths reject an active event loop without creating an un-awaited coroutine.
- H-2 Ollama and llama.cpp generation calls share pooled `httpx.AsyncClient` instances per endpoint, timeout, and event loop; clients close during FastAPI shutdown.
- H-3 semantic cache hits now reuse only the answer text and rerun fresh retrieval, integrity audit, evidence persistence, generation skip, claim verification, verdict computation, and recovery if needed.
- H-4 cache indexing stores JSON-safe minimal answers only; ObjectIds are no longer stored.
- H-5 cache entries are invalidated when a document is added, a document is deleted, a KB is deleted, or a rollback occurs.
- H-6 upload parsing and chunking run through `asyncio.to_thread`; PyMuPDF documents are explicitly closed.
- M-1, M-2, M-4, and L-1 were also corrected.
- M-3 remains open by design: distinguishing an empty retrieval from an infrastructure outage requires a larger retrieval error-contract review.

## Backend architecture map

- **API composition:** `apps/api/app/main.py` creates the FastAPI app; routers are mounted through `apps/api/app/api/router.py` under `/api/v1`.
- **Analysis submission:** `apps/api/app/api/v1/analyses.py` validates requests and calls `analysis_service.create_analysis`.
- **Background analysis:** `apps/api/app/services/analysis_service.py` queues `run_analysis_pipeline` through FastAPI background tasks and limits analysis concurrency with a hardware-aware semaphore.
- **Agent loop:** `apps/api/app/agent/graph.py` runs retrieval, generation, verification, and bounded recovery.
- **Retrieval:** `apps/api/app/retrieval/retriever.py` performs dense Qdrant search and sparse lexical retrieval, fuses results, applies temporal filtering, and optionally reranks.
- **Generation:** `apps/api/app/generation/generator.py` canonicalizes and prunes context before calling the selected model.
- **Verification:** `apps/api/app/verification/verifier.py` decomposes the answer and performs batch NLI with individual fallback.
- **Evidence persistence:** `apps/api/app/agent/graph.py` writes evidence documents and records returned ObjectIds.
- **Semantic cache:** `apps/api/app/core/semantic_cache.py` stores prior response payloads by query embedding.
- **Local model clients:** `apps/api/app/core/local_llm.py` wraps Ollama and llama.cpp-compatible servers.

## Findings

### C-1: NLI segment numbers can map to incorrect evidence IDs

- **Severity:** Critical
- **Files:**
  - `apps/api/app/generation/generator.py:119-163`
  - `apps/api/app/agent/graph.py:482-489`
  - `apps/api/app/verification/verifier.py:467-471`
- **Status:** Fixed on 2026-09-07
- **Evidence:** `format_context()` sorts chunks by `rrf_score`, falls back to `rerank_score`, then deduplicates near-identical text. The graph stores `evidence_ids` in `state["chunks"]` order after reranking/integrity filtering. The NLI prompt sees segment numbers from `format_context()`, but `execute_claim_verification()` maps those numbers back to `evidence_ids` using the original list order.
- **Impact:** A claim marked as supported by Segment 2 may be linked to a different evidence document. This corrupts claim cards, audit exports, citation traces, and TrustRAG's central reliability dossier.
- **Recommended minimal fix:** Make the verifier consume the exact ordered, deduplicated chunk list used to build the prompt, or attach stable evidence identifiers directly to each numbered segment and return those IDs from NLI.

### H-1: Synchronous local-LLM path can crash in an active event loop

- **Severity:** High
- **Files:**
  - `apps/api/app/core/local_llm.py:113-122`
  - `apps/api/app/core/local_llm.py:293-302`
- **Status:** Fixed on 2026-09-07
- **Evidence:** `_generate()` invokes `asyncio.run(self._agenerate(...))`. Calling the synchronous LangChain path from inside a running loop raises `RuntimeError` and leaves an un-awaited coroutine.
- **Impact:** The active pipeline currently uses async methods, but any sync LangChain wrapper, sync tool, or future retry integration can crash an otherwise valid analysis.
- **Recommended minimal fix:** Detect a running loop and fail with a clear, non-leaking error, while keeping `asyncio.run()` only for a true synchronous caller.

### H-2: A new HTTP client is created for every local-LLM call

- **Severity:** High
- **Files:**
  - `apps/api/app/core/local_llm.py:163`
  - `apps/api/app/core/local_llm.py:331`
- **Status:** Fixed on 2026-09-07
- **Evidence:** `_agenerate()` creates a short-lived `httpx.AsyncClient` per request.
- **Impact:** One analysis can make several calls for generation, claim decomposition, batch NLI, fallback NLI, and recovery. New client creation defeats connection reuse and increases latency, socket churn, and load on a local single-process LLM server.
- **Recommended minimal fix:** Reuse a shared async HTTP client per base URL and close it during application shutdown.

### H-3: Semantic-cache hits can skip evidence/claim persistence and produce inconsistent output

- **Severity:** High
- **Files:**
  - `apps/api/app/agent/graph.py:1031-1054`
  - `apps/api/app/services/analysis_service.py`
  - `apps/api/app/verification/verdict.py`
- **Status:** Fixed on 2026-09-07
- **Evidence:** A cache hit returns from the graph before the normal finalization path persists fresh claims and evidence. A cached payload with missing or empty claims can then be interpreted differently by downstream verdict reconstruction.
- **Impact:** The analysis may show a passing or trusted answer without evidence records, claims, or trace continuity.
- **Recommended minimal fix:** Persist only a minimal JSON-safe cached response, and on hits either reconstruct/persist the same downstream artifacts or bypass cache when audit evidence cannot be reproduced.

### H-4: Semantic-cache disk persistence fails for BSON ObjectIds

- **Severity:** High
- **Files:**
  - `apps/api/app/agent/graph.py:1071-1083`
  - `apps/api/app/core/semantic_cache.py:119-141`
- **Status:** Fixed on 2026-09-07
- **Evidence:** Cached responses may include `ObjectId` values. `json.dump()` cannot serialize BSON values, the exception is swallowed, and persistence retries indefinitely.
- **Impact:** Semantic-cache persistence silently degrades for the exact records that contain evidence metadata; the in-memory cache also retains unnecessary heavy payloads.
- **Recommended minimal fix:** Store only JSON-safe scalar fields needed to reproduce the answer and require explicit reconstruction of evidence and claims.

### H-5: Semantic cache is not invalidated after document or knowledge-base deletion

- **Severity:** High
- **Files:**
  - `apps/api/app/core/semantic_cache.py`
  - `apps/api/app/services/kb_service.py`
- **Status:** Fixed on 2026-09-07
- **Evidence:** No delete or rollback path removes semantic-cache entries for the affected knowledge base.
- **Impact:** A query that previously returned a verified answer can continue returning that answer after its source evidence was deleted.
- **Recommended minimal fix:** Add a knowledge-base-scoped `invalidate_semantic_cache()` and call it for document deletion, knowledge-base deletion, and ingestion rollback paths.

### H-6: Upload parsing and chunking block the FastAPI event loop

- **Severity:** High
- **Files:**
  - `apps/api/app/api/v1/knowledge_bases.py:152-155`
  - `apps/api/app/api/v1/knowledge_bases.py:273-277`
  - `apps/api/app/ingestion/parser.py`
- **Status:** Fixed on 2026-09-07
- **Evidence:** `parse_document()` and `chunk_text()` run synchronously inside async route handlers. PDF parsing and large-text chunking are CPU-bound.
- **Impact:** A multi-megabyte upload freezes unrelated requests, SSE traffic, health checks, and other uploads for hundreds of milliseconds or longer.
- **Recommended minimal fix:** Move parsing and chunking to `asyncio.to_thread()` and keep request-validation code on the event loop.

### M-1: PyMuPDF document is not explicitly closed

- **Severity:** Medium
- **File:** `apps/api/app/ingestion/parser.py:65-69`
- **Status:** Fixed on 2026-09-07
- **Impact:** Native memory and file resources can remain allocated until garbage collection.
- **Recommended minimal fix:** Use `fitz.open()` as a context manager.

### M-2: Self-healing reindex may use the ambient embedding model instead of the pinned KB model

- **Severity:** Medium
- **File:** `apps/api/app/agent/graph.py:279`
- **Status:** Fixed on 2026-09-07
- **Impact:** After configuration changes, repaired vectors can be generated in a different embedding space from the original collection.
- **Recommended minimal fix:** Re-embed with the provider/model recorded in the analysis state or knowledge base.

### M-3: Retrieval infrastructure errors can be represented as no evidence

- **Severity:** Medium
- **File:** `apps/api/app/retrieval/retriever.py:207-235`
- **Status:** Open at audit-file creation
- **Impact:** Qdrant failures may become `ABSTAIN`/retrieval failure instead of an operational error, obscuring outages.
- **Recommended minimal fix:** Distinguish empty search results from transport or schema failures.

### M-4: Concurrency controls do not cover ingestion and multi-process local deployments

- **Severity:** Medium
- **Files:**
  - `apps/api/app/services/analysis_service.py:477-505`
  - `apps/api/app/ingestion/pipeline.py`
- **Status:** Partially fixed on 2026-09-07; ingestion is serialized per API process, while multi-worker local-LLM deployment still needs one process or external coordination
- **Impact:** Multiple uploads can run embedding/indexing work concurrently, and each Uvicorn worker owns an independent analysis semaphore.
- **Recommended minimal fix:** Add an ingestion semaphore and document the one-worker local-LLM deployment constraint.

### L-1: Recovery configuration includes strategies not implemented by the graph

- **Severity:** Low
- **Files:**
  - `apps/api/config/models.yaml`
  - `apps/api/app/agent/graph.py`
- **Status:** Fixed on 2026-09-07
- **Impact:** A recovery attempt can be spent without changing retrieval or generation behavior.
- **Recommended minimal fix:** Either implement the configured strategies or reduce configuration to implemented strategies.

## Whitebox test gaps

Existing coverage is broad, but the following behaviors lack direct regression tests:

1. Claim-to-evidence mapping after context sorting and deduplication.
2. Semantic-cache persistence when evidence IDs are present.
3. Semantic-cache invalidation on document/KB deletion.
4. Local-LLM sync method behavior inside a running event loop.
5. Shared HTTP client reuse across multiple local-LLM calls.
6. Upload parsing offloading with a deliberately slow parser.
7. Retrieval failure versus true zero-result behavior.

## Verification commands

```bash
cd apps/api
python -m pytest tests -q --no-cov
python -m ruff check app tests
python -m mypy app
```

## Final verification — 2026-09-07

- `python -m ruff format --check app tests`: pass (all files formatted)
- `python -m ruff check app tests`: pass
- `python -m pytest tests -q --no-cov`: **133 passed**
- `python -m mypy app`: not yet a clean baseline. With the configured Python 3.11 target, NumPy 3.12 stubs stop parsing. With `--python-version 3.12`, 65 errors remain in 15 modules, including pre-existing LangChain typing, experiment collections, Qdrant typing, and `Any`-return errors. New typing issues found in touched code were corrected; the remaining failures need a dedicated typing cleanup and were not hidden as test regressions.
- New whitebox regressions include sorted/deduplicated NLI segment mapping, semantic-cache ObjectId persistence and KB invalidation, generation reuse without an LLM call, local-client loop guards and reuse, exact-origin SSRF allowlisting, public-DNS validation, redirect revalidation, trusted-proxy rate limiting, duplicate embedding-cache batch keys, collection-dimension caching, and provider/model allowlists.
- Blackbox coverage remains through the API unit/TestClient suites; no live Ollama/llama.cpp E2E was run because this pass intentionally avoids spending local inference time.

## Prioritized fix order

1. Fix claim-to-evidence segment mapping.
2. Make semantic-cache payloads JSON-safe and consistent.
3. Invalidate semantic-cache entries when knowledge-base data changes.
4. Make local-LLM sync fallback safe and reuse HTTP connections.
5. Move upload parsing/chunking off the event loop and close PDF documents.
6. Add regression tests for each fixed defect.
