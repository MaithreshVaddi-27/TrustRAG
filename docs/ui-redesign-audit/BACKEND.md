# Backend Audit — TrustRAG ui-redesign (`apps/api`)

**Scope reviewed:** `app/main.py`, router registration, `api/deps.py`, all v1 route modules, `schemas/kb.py`, all 5 services (analysis, auth, experiment, kb, search), `db/mongodb.py`, `db/qdrant.py`, `core/{config,exceptions,logging,security}.py`, `ingestion/{pipeline,parser,chunker}.py`. (graph.py, retrieval, verification, preprocessor, sparse_vector covered in AI-ML.md.) READ-ONLY; no Critical defects found at this layer — the highest-severity items are High.

---

## High

**[High] Operational endpoints are unauthenticated — memory-trim DoS and internal-URL reconnaissance** (Confirmed)
- Location: `app/api/v1/models.py:200-215` (POST `/memory/trim`), `:186-197` (GET `/hardware` — runs blocking `detect_hardware_profile()`), `:31-54` (GET `/providers` — hardcoded `"connected": True` and internal `base_url` exposure at `:144,154`)
- Evidence: The models router has no auth dependency; any client can trigger `POST /memory/trim` (a global `gc.collect` + `malloc_trim`) repeatedly, or read backend topology (hardware profile, Ollama/llama.cpp base URLs).
- Impact: Unauthenticated resource-exhaustion (trim during in-flight generation) and infrastructure reconnaissance; the providers list also lies about connectivity.
- Recommendation: Admin-scoped router dependency (re-use `get_current_user` + role check); remove internal `base_url` from the providers payload or gate it.

**[High] Synchronous QdrantClient is called directly on the event loop — systemic blocking** (Confirmed)
- Location: `app/db/qdrant.py:12,25-57` (sync singleton, module-level client); called from `async def` in `pipeline.py:91,173` (upsert), `kb_service.py:198-214` (delete), `health.py:38`, retrieval paths (see PERFORMANCE.md)
- Evidence: Embedding calls are correctly offloaded via `to_thread` (pipeline.py:111), making Qdrant the remaining blocking I/O on the loop. Every dense/sparse query and every ingestion batch blocks all concurrent requests for the duration of the round trip.
- Impact: Under concurrent load, SSE streams, other requests, and health checks stall behind Qdrant network calls; latency spikes compound through the single-process design.
- Recommendation: `asyncio.to_thread` wrappers around the sync client, or migrate to `AsyncQdrantClient`. `db/qdrant.py` is the single choke point — one change fixes every call site.

**[High] JWT passed as SSE query parameter** (Confirmed)
- Location: `app/api/v1/analyses.py:118-135` — `token: str | None = Query(...)`
- Evidence: The SSE endpoint reads the bearer token from the URL query string (EventSource cannot set headers), so full 60-minute JWTs land in access logs, proxy logs, and browser history.
- Impact: Credential leakage via logs/referrers for the lifetime of the token (60 min default); tokens are valid against every other endpoint too.
- Recommendation: Short-lived single-use stream tickets (mint at POST /analyses, exchange for SSE), or per-event Authorization headers via fetch-based streaming instead of EventSource.

**[High] `delete_document` swallows Qdrant failure, then deletes the Mongo record — permanent orphan vectors** (Confirmed)
- Location: `app/services/kb_service.py:201-223` (warning at `:215-220`, `delete_one` at `:223`)
- Evidence: If the Qdrant delete raises, the handler logs a warning and proceeds to delete the Mongo document row anyway.
- Impact: Orphaned vectors remain searchable forever — deleted documents keep appearing in retrieval and answers, directly contradicting user intent and the product's integrity story. No code path ever re-reconciles them (the self-heal path only adds missing vectors, never removes extras).
- Recommendation: Delete Qdrant first and abort on failure (surface 503), or tombstone + async retry queue. At minimum, never destroy the record that identifies the orphaned vectors.

## Medium

**[Medium] `delete_kb` is non-transactional — orphans ANALYSES / CLAIMS / EVIDENCE / TRACE_EVENTS** (Confirmed) — `kb_service.py:103-123`; deleting a KB leaves its analyses and all downstream trust data unowned and unfindable. Recommendation: delete children first (or mark KB tombstoned and sweep async), with abort on failure.

**[Medium] Upload is not idempotent — content_hash computed but never checked** (Confirmed) — `knowledge_bases.py:134-158`, `mongodb.py:211-213` (non-unique index), `kb_service.py:141-155`. Re-uploading the same file creates a new doc_id; deterministic point IDs are `sha256(doc_id + chunk_index)`, so the same text is re-embedded and duplicated in Qdrant under different IDs. Recommendation: unique `(kb_id, content_hash)` index + 409 on duplicate.

**[Medium] Chunks are inserted into Mongo before Qdrant indexing — failure leaves orphan chunk rows** (Confirmed) — `pipeline.py:68-88,173,179-193`; if embedding/upsert fails mid-run, chunk rows exist with no vectors (or partial). The self-heal path partially masks this, but there is no rollback. Recommendation: stage chunks, write on Qdrant success, or reconcile on failure.

**[Medium] In-process BackgroundTasks with no crash recovery or startup sweep** (Confirmed) — `analysis_service.py:158-170`; analyses stuck in `"processing"` forever after a crash/restart. Recommendation: Startup sweep marking `processing` older than a threshold as `failed`.

**[Medium] Synchronous bcrypt (cost 12) inside async auth routes** (Confirmed) — `security.py:24-37`, `auth_service.py:42,73,76`; ~100-300ms of CPU on the event loop per login/register. Recommendation: `await asyncio.to_thread(hash_password, ...)` / verify.

**[Medium] CPU-bound parse/chunk runs on the event loop in the upload route** (Confirmed) — `knowledge_bases.py:139-142`; `parser.py:65` (chardet detection) is CPU-heavy for large files. Recommendation: `to_thread` the parse+chunk stage.

**[Medium] N+1 `count_documents` in `list_kbs`** (Confirmed) — `kb_service.py:96-100`; one count query per KB per list call. Recommendation: single `$facet`/aggregation, or store counts on the KB doc.

**[Medium] `/health` performs blocking sync work with no timeout** (Confirmed) — `health.py:38,59-60` (sync Qdrant ping + hardware probe, no timeout); health endpoint can hang the loop it is supposed to report on. Recommendation: `wait_for(..., timeout=1.0)` + degrade.

**[Medium] Pagination is inconsistent and lists are unbounded** (Confirmed) — `kb_service.py:91-100,160-169` (no limit), `experiments.py:32-37`, `conflicts.py:18-27` (untyped dict, dual independent cursor params). Recommendation: consistent `(skip, limit)` defaults with sane caps; typed response models.

**[Medium] SSE cursor filters on `_id $gt` but sorts by `timestamp`** (Likely) — `analysis_service.py:279-310`; if write order and timestamp order ever diverge (clock skew, bulk inserts), events can be skipped or repeated. Recommendation: sort and filter on the same field (`_id`).

**[Medium] Production-breaking defaults unguarded** (Confirmed) — `config.py:113-134`: localhost URLs (Mongo/Qdrant) and HF runtime download are valid defaults with no production validator distinguishing dev from prod. Recommendation: extend the production config validator to assert non-loopback service URLs.

## Low

**[Low] `connect_db` `except` path can hit UnboundLocalError** (Potential) — `mongodb.py:111-129`; a failure between client creation and assignment can reference an unbound local. Recommendation: initialize `client = None` and check before ping.
**[Low] CORS wildcard-subdomain origins + allow_credentials** (Confirmed) — `main.py:281-289` — `*.pages.dev`, `*.vercel.app`, `*.netlify.app` with `allow_credentials=True`; any tenant of those hosts is a valid origin. Recommendation: pin exact preview origins or drop wildcard patterns with credentials.
**[Low] Substring-based error classification** (Confirmed) — `analysis_service.py:434-450` (`"connection" in str(exc).lower()` style); brittle against message changes. Recommendation: branch on exception types (see ARCHITECTURE.md M3).
**[Low] Sync `trim_memory` in a `finally`** (Confirmed) — `analysis_service.py:469-474`, `pipeline.py:194-197`; blocking GC on the loop after every analysis. Recommendation: `to_thread` or conditional (see PERFORMANCE.md).
**[Low] 1000-row silent truncation** (Confirmed) — `analysis_service.py:485-515`; long-running users silently lose older rows. Recommendation: paginate or make the cap explicit in the response.
**[Low] Export dossier triple-fetches the same analysis** (Confirmed) — `analysis_service.py:599-674` (~`:608-610`); three DB round trips for data one query returns. Recommendation: single fetch.
**[Low] TavilyClient constructed per call** (Potential) — `search_service.py:99`; stateless client → module-level singleton.
**[Low] `verify_password` swallows all exceptions as False** (Confirmed) — `security.py:36-37`; an infrastructure failure is indistinguishable from a wrong password. Recommendation: let hash-comparison errors raise or log distinctly.
**[Low] `sanitize_url` blocks IP literals but not hostnames resolving to them** (Confirmed) — `search_service.py:37-79`; DNS-rebinding can still reach private ranges. Recommendation: resolve hostname, then check resolved IPs.
**[Low] `get_kb` uses `count_documents(1)` instead of `find_one`** (Confirmed) — `kb_service.py:84-86`; works, but slower and noisier than an existence probe.
**[Low] FEEDBACK / RECOVERY_RUNS collections appear write-only/unused** (Potential) — `mongodb.py:47-58`; grep for readers found none. Recommendation: delete or document.

## Done well (do not regress)

- Exception taxonomy (`app/core/exceptions.py`) never leaks internals; 14 handlers in `main.py` enforce consistent envelopes.
- Secret-scrubbing in the logging layer; JWT secret ≥ 32 chars enforced at startup.
- `lru_cache` on settings/model-config getters — no per-request re-parse.
- `search_service.py` async hygiene is the repo's gold standard (timeouts, cancellation, SSRF guard, per-provider failure isolation).
- Deterministic Qdrant point IDs (reproducible upserts); 429-aware embedding retry; streamed uploads; M0-friendly 12-attempt Mongo connect with backoff.
- Timing-equalized dummy bcrypt on auth failures (no user-enumeration timing signal).

Refuted during audit (checked, not bugs): Qdrant payload type mismatch; KB `description=None` crash; per-request settings re-read; `exc.detail` leak; ingestion `error_message` leak.

---

## Backend Score: 6.5 / 10

**Justification:** No Critical backend defect: the service layer is cleanly separated, the exception/observability discipline is unusually good, and the failure-handling philosophy (log, don't crash) is consistent. But four Highs share a theme — *correctness and safety of side-effecting paths*: unauthenticated operational endpoints, an async-safety violation at the single hottest I/O choke point (Qdrant), credential-bearing URLs, and a delete path that permanently corrupts retrieval truth. The twelve Mediums are mostly the same themes at lower stakes (idempotency, transactionality, loop hygiene, pagination). Individually small, collectively the difference between a demo and a dependable service.

## Top 5 quick wins

1. **Auth-lock `models.py`** — one router-level dependency fixes trim-DoS + recon (models.py:31-215).
2. **Move SSE JWT out of the query string** — short-lived stream tickets (analyses.py:118-135).
3. **`to_thread`-wrap the Qdrant client** — `db/qdrant.py` is the single choke point; fixes every blocking call site at once.
4. **Unique `(kb_id, content_hash)` index + 409** — makes uploads idempotent; stops duplicate vector ingestion (kb_service.py:141-155).
5. **Startup recovery sweep** — mark `processing` analyses older than threshold as `failed`; closes the permanent-stuck state (analysis_service.py:158-170).
