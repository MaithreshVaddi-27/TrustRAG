# Performance Audit — TrustRAG ui-redesign

**Scope reviewed:** retrieval hot path, ingestion pipeline, caches (semantic, disk, LRU), db clients, startup sequence, system calls, model registry, frontend load profile (partial), on-disk dependency footprint. READ-ONLY; cross-verified against BACKEND.md and AI-ML.md — duplicated findings are cross-referenced, not restated.

---

## Critical

**[Critical] Synchronous QdrantClient blocks the event loop on every query and ingestion batch** (Confirmed)
- Location: `app/db/qdrant.py:12,25-57` (sync singleton); `app/retrieval/retriever.py:79,95,120` (query_points ×2 per hybrid search); `app/ingestion/pipeline.py:173` (100-point upsert batches); `db/qdrant.py` async-def `init`/`delete` calling the blocking client
- Evidence: Every dense and sparse search performs two synchronous network round trips on the loop (query + scroll/decode); every ingestion batch blocks for the upsert duration. Embedding calls are already `to_thread`'d (pipeline.py:111) — Qdrant is the remaining blocking I/O and it sits on the hottest path in the system.
- Impact: One slow Qdrant round trip (cold Atlas M0 network, disk-backed collection) freezes ALL concurrent requests — SSE streams, health checks, other users' analyses — for the duration. This is the single largest latency and throughput defect in the repo.
- Recommendation: `AsyncQdrantClient`, or `asyncio.to_thread`-wrap `query_points` (×2) and `upsert` at the `db/qdrant.py` choke point. One fix repairs every call site.
- (Same finding as BACKEND.md High 2 — owned here for the performance lens.)

## High

**[High] Hardware-profile probe (subprocess `vm_stat` / `/proc/meminfo`) runs on every /health and /models request** (Confirmed)
- Location: `app/core/hardware.py:66` (`detect_hardware_profile`); called from `health.py:50,59-60`, `models.py:186,195-197`
- Evidence: The probe shells out per request to build a profile that changes only on hardware changes/reboots.
- Impact: Subprocess spawn + output parse on the loop per health check; Dashboard's default 3-5s polling (FRONTEND.md) multiplies it into a constant subprocess churn.
- Recommendation: Cache the profile at startup (TTL or manual refresh endpoint); invalidate on demand.

**[High] `trim_memory` (gc.collect + malloc_trim) runs synchronously on the loop** (Confirmed)
- Location: `app/api/v1/models.py:201-208`; also called in `finally` blocks (`analysis_service.py:469-474`, `pipeline.py:194-197`)
- Evidence: A multi-hundred-ms stop-the-world GC executes inline in async handlers — including after EVERY ingestion, unconditionally.
- Recommendation: `return await asyncio.to_thread(trim_memory)`; make the post-ingestion call conditional on real RSS growth (see Medium).

**[High] Rerank `torch model.predict` is synchronous inside the async graph** (Likely — call-site gated on `reranker.enabled`)
- Location: `app/retrieval/reranker.py:58`
- Evidence: `model.predict(pairs)` is a blocking torch forward pass invoked from async code. Currently dormant (`reranker.enabled: false`), so it is a loaded gun rather than a live cost.
- Recommendation: `asyncio.to_thread` now, before anyone enables the reranker and freezes the loop for every request.

**[High] disk_cache.py (embedding SQLite cache) is inefficient — and currently dead code** (Confirmed — corrected)
- Location: `app/core/disk_cache.py:27-42,105-113`; `model_registry.py:342,363`
- Evidence: The implementation opens a **new SQLite connection per call**, re-runs PRAGMAs and DDL statements on every call, does batch lookups as an **N+1 SELECT loop**, writes back per-text individually, and stores `created_at` that is never read (no eviction exists).
- **Correction of the initial audit pass:** this cache is **NOT production-wired** — `get_embedding_model()` (model_registry.py:379-561) never returns `CachedEmbeddingsWrapper` on any path (verified by full read of all five return branches). So today these costs are latent, not live. See AI-ML.md Critical 1 (sole owner of the dead-code finding).
- Impact: As written, wiring it in would trade saved embedding compute for per-call connection churn and N+1 queries inside the `to_thread` pool. The ~5-line wiring fix should land together with a disk_cache.py rewrite, not before.
- Recommendation: Persistent connection (or per-thread), PRAGMAs/DDL once at init, `WHERE key IN (...)` batched SELECTs, batched/executemany write-backs, and an eviction pass keyed on `created_at`.

**[High] Duplicate Python 3.12 + 3.14 site-packages — ~1GB+ of dead disk footprint; apps/api totals 2.5GB** (Confirmed)
- Location: apps/api virtualenv — torch 529+504MB, transformers 108+58MB, scipy 98+81MB, sympy 72+42MB, pymupdf 58+58MB, sklearn 47+33MB, mypyc `.so` 38+38MB, numpy 34+25MB, mypy 23+17MB (both trees present)
- Impact: Double disk usage, double cold-cache pressure, ambiguous which tree resolves at runtime; packaging/deploy images inherit the bloat.
- Recommendation: Delete the unused interpreter's tree; pin one Python; move mypy/mypyc to a dev extra so prod images don't carry 40MB of compiled type-checker.

## Medium

**[Medium] Semantic cache: two linear scans + pure-Python cosine over ≤500×384 floats per lookup + `pop(0)` O(n) eviction** (Confirmed)
- Location: `app/core/semantic_cache.py:29,32-44,62-78,109`
- Evidence: Each lookup scans the list twice (similarities then best-match) computing ~384,000 interpreted multiply-adds; eviction `pop(0)` shifts the whole list; entries are process-local (die on restart).
- Recommendation: One pass, numpy stacked matrix (normalize on write → single dot product on read), `OrderedDict.move_to_end` for eviction; or move to a Qdrant cache collection (durable, shared across workers).
- (Cross-ref AI-ML.md Medium — shared finding.)

**[Medium] ~22 sequential `create_index` round trips at startup** (Confirmed)
- Location: `app/db/mongodb.py:181-288`
- Evidence: Every index creation is an awaited round trip in sequence; against Atlas M0 latency this stretches startup.
- Recommendation: `asyncio.gather` the creates (Mongo handles concurrent index ops).

**[Medium] `get_collection()` round trip on every dense search** (Confirmed)
- Location: `app/retrieval/retriever.py:79-93`
- Recommendation: Cache `{collection_name: dim}`; hard-error on mismatch instead of silently truncating.
- (Cross-ref AI-ML.md Medium.)

**[Medium] `ru_maxrss` (peak RSS) misused as current memory** (Confirmed)
- Location: `app/core/memory.py:46-50`
- Evidence: The tier guard reads peak RSS; one transient spike permanently pins the system in the lean tier until restart.
- Recommendation: Read current RSS (`/proc/self/statm` or `psutil`) for tier decisions; keep peak for telemetry.

**[Medium] Full `gc.collect` + `malloc_trim` after EVERY ingestion, unconditionally** (Confirmed)
- Location: `app/ingestion/pipeline.py:194-197`
- Recommendation: Conditional on measured RSS growth since last trim (e.g., >256MB), else skip.

## Low

**[Low] Two stacked `@app.middleware("http")` decorators** (Confirmed) — `main.py:292,295-304`; two middleware objects where one merged function would do; marginal per-request overhead. Merge them.
**[Low] TavilyClient and DDGS constructed per search call** (Potential) — `search_service.py:99,158`; stateless clients → module-level singletons. (Cross-ref BACKEND.md Low, AI-ML.md Low.)

## Potential (flagged, not verified)

- Eager torch import in `main.py:48` — check `python -X importtime`; lazy-importing torch would cut cold-start.
- `registry_status()` cost per health call.
- Frontend load profile only partially audited: React.lazy verified for routes, but HUD animation loops and LandingPage mousemove re-renders (see FRONTEND.md Medium) remain the open render-cost items.

## Credited (working well — do not regress)

- `gather` for parallel hybrid + web retrieval; `to_thread` for embeddings; QueryEmbeddingLRUCache (1024, thread-safe); non-blocking warmup via `create_task`; offline env flags; Motor pooling (50/2/45s idle); batched `$in` temporal filtering; adaptive top-K rerank bound; Qdrant INT8 quantization; zero-LLM contextual chunk prefixes; deterministic token pruning.

---

## Performance Score: 5 / 10

**Justification:** The design shows real performance awareness — thread-offloaded embeddings, an LRU on query vectors, batched Mongo filtering, INT8 quantization, non-blocking warmup. But the two hottest I/O paths violate the model: Qdrant is called synchronously on the event loop for every query AND every upsert (Critical), and the system's own telemetry/GC (hardware subprocess, trim, full GC after ingestion) taxes the loop per request. The flagship efficiency feature (disk embedding cache) is dead code — and its implementation would need a rewrite before wiring. On disk, the environment carries a gigabyte of duplicated libraries. Fix Qdrant async + the hardware probe and the runtime score alone plausibly reaches 7-8.

## Top 10 optimizations (ranked)

1. **AsyncQdrantClient / to_thread-wrap the sync client** (db/qdrant.py choke point) — removes the only loop-blocking I/O in the system.
2. **Purge the duplicate 3.12/3.14 site-packages tree** — frees ~1GB+ immediately, unambiguous runtime.
3. **Cache `detect_hardware_profile()` at startup** — kills per-request subprocess churn.
4. **Wire + rewrite disk_cache.py together** (persistent connection, PRAGMAs once, batched IN-selects, executemany, eviction) — saves 100% of repeat-embedding compute (with AI-ML.md Critical 1).
5. **`to_thread` rerank predict + trim_memory; conditional post-ingestion GC** — pre-empts two loop freezes.
6. **Cache collection dims per name** — removes 1 network round trip per query.
7. **Numpy-matrix semantic cache + move_to_end eviction** — O(500) Python cosine → one dot product.
8. **`gather` the ~22 startup create_index calls** — faster cold boot.
9. **Current-RSS (statm/psutil) instead of peak for the tier guard** — ends the permanent lean-tier lock-in.
10. **TavilyClient/DDGS singletons + merge the two HTTP middlewares** — cheap hygiene sweep.
