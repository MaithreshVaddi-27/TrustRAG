# TrustRAG Audit & Fix Status — Pause Point

**Date:** 2026-09-07  
**Branch:** `ui-redesign`  
**Status:** Paused by user after serious confirmed bugs were fixed with focused code changes  
**Scope completed tonight:** backend/RAG correctness, local-LLM load reduction, URL-ingestion security, trusted proxy handling, upload/resource handling, regression tests.

---

## Audit files created

1. `docs/audits/2026-09-07_backend_rag_correctness_audit.md`
2. `docs/audits/2026-09-07_security_audit.md`
3. `docs/audits/2026-09-07_performance_local_llm_audit.md`

This file is the handoff/status record for resuming tomorrow.

---

## Serious bugs fixed

### 1. NLI claim-to-evidence misalignment

**Risk:** Critical  
**Before:** The NLI prompt used sorted/deduplicated context, but claim evidence IDs were mapped using the unsorted chunk list. A claim could cite the wrong evidence record.

**Fix:**
- `format_context_with_chunk_indices()` now returns the exact original chunk index represented by each NLI segment.
- `execute_claim_verification()` maps NLI `supporting_segments` through that canonical mapping.
- Batch and fallback verification now reuse the same formatted context.

**Files:**
- `apps/api/app/generation/generator.py`
- `apps/api/app/verification/verifier.py`
- Regression tests in `tests/test_generation.py` and `tests/test_verification.py`

---

### 2. Semantic cache could return stale or internally inconsistent verified answers

**Risk:** High  
**Before:** Cache hits bypassed retrieval, evidence persistence, claim verification, and verdict recomputation.

**Fix:**
- Cache now stores **only a minimal answer payload**.
- On a cache hit, generation is skipped, but the graph still performs:
  - fresh retrieval,
  - evidence integrity audit,
  - evidence persistence,
  - claim decomposition,
  - NLI verification,
  - verdict calculation,
  - recovery if the cached answer no longer verifies.

**Files:**
- `apps/api/app/agent/graph.py`
- `apps/api/app/core/semantic_cache.py`
- Regression tests in `tests/test_agent.py` and `tests/test_semantic_cache.py`

---

### 3. Semantic cache disk persistence failed on BSON ObjectIds

**Risk:** High  
**Before:** cached evidence/claim payloads containing `ObjectId` made periodic JSON persistence fail silently.

**Fix:**
- Added JSON-safe cache serialization.
- Removed Mongo ObjectIds and audit records from semantic-cache payloads.

**Regression coverage:** `test_semantic_cache_sanitizes_object_ids_for_persistence`.

---

### 4. Semantic cache was not invalidated when knowledge changed

**Risk:** High  
**Before:** deleting a document/KB did not remove cached answers derived from it.

**Fix:** Added `invalidate_semantic_cache(kb_id)` and called it on:
- new document registration,
- document deletion,
- knowledge-base deletion,
- snapshot rollback.

**File:** `apps/api/app/services/kb_service.py`

---

### 5. Local LLM sync compatibility path could crash in a running event loop

**Risk:** High  
**Before:** `_generate()` called `asyncio.run()` even when an event loop was already active, producing `RuntimeError` and potentially leaking coroutines.

**Fix:**
- `_generate()` now detects an active event loop and raises a clear `ConfigurationError` telling callers to use `ainvoke()`.
- It still supports genuine synchronous callers.

**File:** `apps/api/app/core/local_llm.py`

---

### 6. Every local LLM call created a new HTTP client

**Risk:** High local-load issue  
**Before:** Ollama and llama.cpp generation created a new `httpx.AsyncClient` per request, preventing connection reuse across generation, decomposition, NLI, and recovery calls.

**Fix:**
- Added pooled clients per base URL, timeout, and event loop.
- Added `close_local_llm_clients()` and call it during FastAPI shutdown.

**File:** `apps/api/app/core/local_llm.py`

---

### 7. Suffix-domain and redirect SSRF bypasses

**Risk:** High  
**Before:** allowlist checks used URL prefix matching and redirects were followed without revalidation.

**Fix:**
- Exact scheme/hostname/port matching.
- Request-supplied allowlists can narrow but not widen the server default policy.
- Non-canonical numeric hostnames rejected.
- DNS answers must resolve only to globally routable IP addresses.
- Redirects are followed manually with a maximum of 3 and each hop is revalidated.

**Files:**
- `apps/api/app/services/search_service.py`
- Regression tests in `tests/test_search_mcp.py`

**Residual security note:** this closes the observed prefix, literal-IP, private-DNS, and redirect bypasses, but does not yet pin the validated IP through the actual TCP/TLS connection. Connection-time pinning is tomorrow's hardening follow-up.

---

### 8. Rate-limit identity trusted spoofed forwarding headers

**Risk:** High  
**Before:** any direct client could rotate `X-Forwarded-For` and receive a fresh rate-limit bucket.

**Fix:**
- Forwarding headers are honored only when the immediate peer is listed in `TRUSTED_PROXY_IPS`.
- Otherwise the direct remote address is used.
- `.env.example` documents the setting.

**Files:**
- `apps/api/app/core/config.py`
- `apps/api/app/core/rate_limiter.py`
- `.env.example`
- Regression tests in `tests/test_rate_limit.py`

---

### 9. API accepted arbitrary provider/model IDs

**Risk:** High  
**Before:** request bodies could pass arbitrary model names into local model loaders or cloud providers.

**Fix:**
- `AnalysisCreate` now validates LLM and embedding provider/model combinations against deployment-enabled model IDs.
- Local model choices are limited with canonical installed model lists plus operator-managed env overrides.
- Cloud models are limited to the supported provider catalogs.

**Files:**
- `apps/api/app/api/v1/schemas/analysis.py`
- Regression tests in `tests/test_config.py`

---

### 10. Upload parsing/chunking blocked the event loop

**Risk:** High on local deployments  
**Before:** PDF/DOCX/text parsing and chunking ran synchronously inside async upload routes.

**Fix:** both upload and URL-ingestion paths now move parsing/chunking into worker threads.

**File:** `apps/api/app/api/v1/knowledge_bases.py`

---

## Additional local-load and reliability fixes completed

- Removed the duplicate startup embedding-manager load; the registry's cached embedding model is now the single serving path.
- Removed the unused `SharedEmbeddingManager` implementation.
- Closed PyMuPDF documents with a context manager.
- Serialized background ingestion with a per-event-loop semaphore.
- Removed the unused generation `ContextManager` block so it cannot spawn unneeded summarization work.
- Recovery config now lists only strategies implemented by the graph: `query_rewrite`, `re_retrieve`, `regenerate`.
- Self-heal reindexing now uses the analysis's pinned embedding provider/model.
- Qdrant collection vector dimensions are cached per collection instead of fetched for every dense query.
- SQLite embedding batch lookup now uses one `IN` query and handles duplicate input texts correctly.
- Async embedding-cache disk calls now run through `asyncio.to_thread`.
- The in-memory embedding cache now uses `OrderedDict` LRU semantics instead of a duplicate-growing key list.

---

## Verification status

### Final full verification (after all fixes)

```bash
cd apps/api
python -m ruff format --check app tests
python -m ruff check app tests
python -m pytest tests -q --no-cov
```

Result: **133 passed**, Ruff clean.

### Type-check note

`python -m mypy app` is not clean on the current repository baseline:

- With the configured Python 3.11 target, current NumPy stubs use Python 3.12-only syntax.
- With `--python-version 3.12`, many pre-existing LangChain/Qdrant/`Any`/experiment typing errors remain.

No claim is made that mypy is green. This should be addressed as a separate typing cleanup.

---

## Files intentionally changed

### Backend application

- `.env.example`
- `apps/api/app/agent/graph.py`
- `apps/api/app/api/v1/knowledge_bases.py`
- `apps/api/app/api/v1/schemas/analysis.py`
- `apps/api/app/core/config.py`
- `apps/api/app/core/disk_cache.py`
- `apps/api/app/core/local_llm.py`
- `apps/api/app/core/model_registry.py`
- `apps/api/app/core/rate_limiter.py`
- `apps/api/app/core/semantic_cache.py`
- `apps/api/app/generation/generator.py`
- `apps/api/app/ingestion/parser.py`
- `apps/api/app/ingestion/pipeline.py`
- `apps/api/app/main.py`
- `apps/api/app/retrieval/retriever.py`
- `apps/api/app/services/kb_service.py`
- `apps/api/app/services/search_service.py`
- `apps/api/app/verification/verifier.py`
- `apps/api/config/models.yaml`
- `apps/api/Dockerfile`

### Regression tests

- `apps/api/tests/test_agent.py`
- `apps/api/tests/test_config.py`
- `apps/api/tests/test_disk_cache.py`
- `apps/api/tests/test_generation.py`
- `apps/api/tests/test_local_llm.py`
- `apps/api/tests/test_rate_limit.py`
- `apps/api/tests/test_retrieval.py`
- `apps/api/tests/test_search_mcp.py`
- `apps/api/tests/test_semantic_cache.py`
- `apps/api/tests/test_verification.py`

### Audit/handoff documentation

- `docs/audits/2026-09-07_backend_rag_correctness_audit.md`
- `docs/audits/2026-09-07_performance_local_llm_audit.md`
- `docs/audits/2026-09-07_security_audit.md`
- `docs/audits/2026-09-07_work_status_and_next_steps.md`

---

## What should be done tomorrow

### First: verify current tree

1. Run the full API suite and formatting checks listed above.
2. Run the frontend suite only if frontend files are touched:
   ```bash
   cd apps/web
   npm run lint
   npm test
   npm run build
   ```
3. If local infrastructure is available, run one controlled E2E:
   - start MongoDB/Qdrant,
   - start the chosen local LLM,
   - upload a small document,
   - run the same query twice,
   - confirm the second run logs cache reuse **but still performs retrieval and NLI verification**.

### Next correctness fixes

1. **Distinguish retrieval outage from no evidence** in `retriever.py`; infrastructure errors should not silently become an innocent retrieval failure.
2. **Add a test around the safe semantic-cache graph path** that proves fresh evidence IDs are persisted on cache reuse.
3. **Review `prune_context_tokens` handling of segment delimiters** so prompts keep clear segment boundaries after pruning.
4. **Review public `/health` output** and move model/provider/hardware details behind authentication if public detail is not required.

### Next security hardening

1. Implement redirect/DNS connection-time IP pinning for URL ingestion.
2. Tighten hosted-platform CORS regexes or remove them outside preview environments.
3. Add server scope checks to MCP tools or bind MCP to an explicit service identity.
4. Add tenant-bound service tokens for `/internal/ingest/document`.
5. Add bcrypt password maximum length and JWT audience/issuer claims.

### Next local-LLM/RAG optimizations

1. Format the verification context once per verification attempt and pass that same context into every fallback NLI call.
2. Consider controlled concurrency for fallback NLI calls only after measuring the local model's throughput.
3. Consider one SQL transaction for repeated embedding-cache writes instead of one write per text.
4. Add an eviction/TTL policy for the SQLite embedding cache.
5. Extend k6 beyond health/KB listing to uploads, analysis execution, model discovery, and SSE stream behavior.
6. Document and enforce one API worker for local-LLM mode unless external concurrency coordination is introduced.

---

## Current pause state

- Work is **not committed**.
- No production/live external API test was performed.
- The existing `.env` was not edited or printed into an audit file.
- The three detailed audit reports and this status file are saved under `docs/audits/`.
