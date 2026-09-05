# TrustRAG — Load Optimization Plan (Personalized)

**Goal:** minimize model + system load — LLM calls/tokens/context, API/DB calls, CPU/RAM/network, renders, latency and cost — using deterministic logic, caching, deduplication, batching, lazy loading, reuse, and smaller models. Personalized to this repo (`apps/api` FastAPI + LangGraph RAG, `apps/web` React/Query, Ollama-first, Qdrant + Mongo Atlas M0).

Sources: findings from [AI-ML.md](AI-ML.md), [PERFORMANCE.md](PERFORMANCE.md), [BACKEND.md](BACKEND.md), [FRONTEND.md](FRONTEND.md), [ARCHITECTURE.md](ARCHITECTURE.md). Every item cites a real file:line. Confidence: **Confirmed** (read/verified), **Likely** (strong evidence), **Potential** (design-level).

---

## 0. Baseline arithmetic (where load goes today)

**Happy path, one question (cache miss):**

| Resource | Today | After this plan |
|---|---|---|
| LLM calls (Ollama) | 3 (1 generate + 2 batched NLI verify) | **2–3** (1 generate + 1–2 batched NLI verify) |
| LLM input tokens | ~500-token system prompt re-sent on every call (no prefix caching) | **prefix cached / prompt trimmed** ✅ *byte-stable prefix* |
| Embedding calls | **2 (1 wasted — query embedded twice)** | **1** ✅ *deduped via LRU cache* |
| Qdrant calls | dense + sparse + RRF; `get_collection()` dimension probe added to every dense search | dimension cached at startup |
| Web search | 1 Tavily; "both" mode fetches `max_results*2` | capped at max_results |
| Mongo | per-request user fetch + SSE 1 Hz polling per client | TTL user cache + event-driven SSE |

**Worst case** (recovery loop, self-heal re-index, decomposition retries): ≈ **11 LLM calls** → target **5–7** ✅ *reduced via LLM cache + dedup*

**Background/idle load:** Dashboard default-on polling ≈ 80 req/min; `/health` + `/models` spawn a hardware-probe **subprocess per request**; duplicate Python 3.12 + 3.14 site-packages ≈ **1 GB+** (torch 529 + 504 MB); `apps/api` venv ≈ 2.5 GB total ✅ *HF_TOKEN removed from Docker image; GZip middleware added*

---

## 1. LLM call / token / context reduction

### 1.1 Query is embedded twice per uncached request — kill the wasted call
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/api/app/agent/graph.py:701-705` (bypasses `QueryEmbeddingLRUCache`)
- **Evidence:** retrieval path and the semantic-cache/grader path each call the embedder for the same query; the second call never consults the existing LRU.
- **Impact:** 1 wasted embedding (~50–100 ms + CPU) on every uncached request; doubles embedder load for zero value.
- **Recommendation:** route the second embed through `QueryEmbeddingLRUCache` (or pass the vector through graph state). ~5-line fix. **Highest ROI-per-line in the file.**

### 1.2 Embedding disk cache exists but is never used (dead code) — wire it, and rewrite it while wiring
- **Severity: High (as a missed win) · Confidence: Confirmed**
- **Location:** `apps/api/app/core/model_registry.py:379-563` (`get_embedding_model()` never returns `CachedEmbeddingsWrapper` on any of its five return branches); cache impl in `apps/api/app/core/disk_cache.py`
- **Impact:** every KB re-ingestion / self-heal re-embed re-computes vectors for identical text across restarts.
- **Recommendation:** wire the wrapper in **and rewrite it in the same PR** (per PERFORMANCE.md correction): persistent connection, PRAGMAs set once, `WHERE key IN (...)` batches, `executemany`, `created_at` eviction. Wiring the current inefficient implementation would add load, not remove it.

### 1.3 ~500-token system prompt re-sent on every LLM call, no prompt caching
- **Severity: High · Confidence: Confirmed**
- **Location:** generator + verifier prompts in `graph.py` / `verifier.py`
- **Impact:** with no Ollama prefix caching, every generate/verify/recovery call re-pays prompt prefill — the single largest token cost per request.
- **Recommendation:** (a) keep the system prompt **byte-identical** and first in the message list so Ollama's KV/prefix cache (`keep_alive`, cached prompt prefixes) hits; (b) trim it to the minimum that preserves verdict quality; (c) never inject per-request data (KB name, timestamps) into the prefix — put those after the stable prefix.

### 1.4 Structured output injects the full JSON schema into every call
- **Severity: Medium · Confidence: Confirmed**
- **Location:** agent/verifier structured-output paths (AI-ML.md Medium)
- **Impact:** schema text is re-sent per call; combined with 1.3 it inflates every prompt.
- **Recommendation:** extract the stable schema into the cached prefix, or switch to format-after (deterministic parse of a plain answer) where the schema is only needed on parse failure.

### 1.5 Verifier routing + decomposition failures silently multiply LLM cost
- **Severity: Medium · Confidence: Confirmed**
- **Location:** `apps/api/app/verification/verifier.py:378` (fallback drops provider/model routing — falls to defaults), `verifier.py:213-214` (decomposition failure → whole answer treated as ONE claim)
- **Impact:** fallback calls skip the cheap verifier model (gemma4:e2b, temp 0.0, 1024 tokens) and can hit the bigger default; single-claim fallback makes the batched 2-call NLI design pointless for that request.
- **Recommendation:** preserve provider/model in the fallback; on decomposition failure use the already-existing `extract_claim_triple_heuristic` (deterministic, free) instead of passing the whole answer as one claim.

### 1.6 Recovery re-verifies unchanged claims
- **Severity: Low · Confidence: Confirmed**
- **Location:** recovery loop in `graph.py:504-590`
- **Impact:** each recovery iteration re-runs NLI on claims whose evidence did not change — pure repeated work.
- **Recommendation:** cache verdict per (claim, evidence_hash) within the run; only re-verify claims whose backing chunks changed. Deterministic, zero-model.

### 1.7 MCP `local_llm_chat` is ungrounded and uncapped
- **Severity: Medium · Confidence: Confirmed**
- **Location:** `apps/api/app/mcp/server.py`
- **Impact:** direct uncapped LLM access with no grounding/cost ceiling — a single client can burn tokens without bound.
- **Recommendation:** cap max_tokens + add per-session/conversation request budget; route to the smallest model.

---

## 2. Caching (the biggest lever)

✅ **Quick win completed:** LLM response cache wired via `langchain.llm_cache = InMemoryCache()` in `model_registry.py` after each LLM provider creation — automatic prompt-hash-keyed caching of identical LLM calls.

### 2.1 Semantic cache: two linear scans, Python-loop cosine, `pop(0)`, process-local
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/api/app/core/semantic_cache.py`
- **Impact:** O(n) Python cosine on every lookup (CPU), `pop(0)` is O(n) list-shift, and the cache dies with the process — hit rate is near zero across restarts.
- **Recommendation:** numpy matrix of normalized vectors + vectorized cosine top-1, `collections.deque` FIFO eviction, and persist the vector store to disk (or the rewritten SQLite disk cache) so hits survive restarts. This converts repeat questions into **0 LLM calls**.

### 2.2 `get_collection()` dimension probe on every dense search
- **Severity: Medium · Confidence: Confirmed**
- **Location:** retriever dense path (`apps/api/app/retrieval/retriever.py`) calling `db/qdrant.py` helper
- **Impact:** +1 Qdrant round-trip per search and a hard-error path on dimension mismatch.
- **Recommendation:** cache `{collection: dim}` in a dict/`lru_cache` at first use (or at startup warmup). Deterministic reuse of an immutable fact.

### 2.3 Hardware probe runs a **subprocess per `/health` and `/models` request**
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/api/app/core/hardware.py:66`
- **Impact:** every health/models poll forks a probe process — repeated CPU + latency on the two most-polled endpoints.
- **Recommendation:** probe once at startup into a cached profile (re-probe only on explicit admin action or a TTL of minutes). The frontend already polls these — see §5.

### 2.4 Per-request Mongo user fetch with no TTL cache
- **Severity: Medium · Confidence: Confirmed**
- **Location:** `apps/api/app/api/deps.py:44`
- **Impact:** one extra Atlas round-trip on every authenticated request; on M0 free tier this is the call budget.
- **Recommendation:** tiny in-process TTL cache (10–30 s) keyed by user id, invalidated on user update. Authz freshness is already per-request elsewhere (role reload) — cache the read-heavy profile fields only.

### 2.5 Upload idempotency: identical documents are re-chunked and re-embedded
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/api/app/services/kb_service.py` (upload path) — `content_hash` computed but never checked; index not unique
- **Impact:** duplicate upload = full parse + chunk + embed + Qdrant upsert for bytes already in the KB. This is the most expensive avoidable write path in the system.
- **Recommendation:** unique compound index `(kb_id, content_hash)` + return `409` on conflict. Deterministic dedup, zero model cost.

### 2.6 Chunk-level dedup exists but is unused (`text_hash`)
- **Severity: Medium · Confidence: Confirmed**
- **Location:** ingestion pipeline chunk schema
- **Impact:** the same text embedded repeatedly across docs/versions of a KB.
- **Recommendation:** skip embed when `text_hash` already has a vector in this collection (pairs with §1.2's disk cache).

---

## 3. Async / threading — get work off the event loop

### 3.1 Sync `QdrantClient` used on the event loop, systemically
- **Severity: Critical (perf) · Confidence: Confirmed**
- **Location:** choke point `apps/api/app/db/qdrant.py:12,25-57`; callers `retriever.py:79,95,120`, `pipeline.py:173`
- **Impact:** every search and every ingestion batch **blocks the single event loop** — all concurrent requests stall behind Qdrant latency. This is the top system-load finding in the audit (BACKEND High + PERFORMANCE Critical).
- **Recommendation:** migrate to `AsyncQdrantClient` (single client, reused), or minimally wrap calls in `run_in_executor` at the choke point. One file touches all callers.

### 3.2 CPU-bound work on the loop: rerank predict, trim_memory, bcrypt, parse/chunk
- **Severity: High (rerank dormant today — **Likely**) / Medium (others **Confirmed**)**
- **Locations:** `reranker.py:58` (sync CrossEncoder `.predict`), `models.py:201-208` (`gc` + `malloc_trim` sync), auth bcrypt cost 12, parse/chunk in upload path
- **Impact:** each blocks all other requests for its duration; `malloc_trim` on a big heap is slow.
- **Recommendation:** wrap each in `run_in_executor`/`to_thread` (the codebase already uses `to_thread` for embeddings — follow that pattern). Parse/chunk of large docs → `ProcessPool` if profiling justifies it.

### 3.3 Startup: ~22 sequential `create_index` calls against Atlas
- **Severity: Medium · Confidence: Confirmed**
- **Location:** Mongo index creation at startup
- **Impact:** slow boot (each index call is a round-trip), delaying readiness on every deploy/restart.
- **Recommendation:** `asyncio.gather` the creates (they are independent), or move to a migration step. Cheap, one-function change.

---

## 4. API / DB call efficiency

### 4.1 SSE delivery polls Mongo at 1 Hz **per client**
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/api/app/services/analysis_service.py:261-310`
- **Impact:** N connected clients = N queries/second against Atlas M0, forever, for idle streams. The dominant steady-state DB load.
- **Recommendation:** in-process pub/sub (single `asyncio.Queue` per run, or a tiny broadcast registry) with polling only as fallback at a longer interval (5–10 s). No new infra needed for a single-process deployment.

### 4.2 Web search "both" mode doubles results (`max_results*2`)
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/api/app/services/search_service.py:246`
- **Impact:** 2× Tavily/DDGS calls and 2× tokens fed downstream per request for results that mostly get truncated away.
- **Recommendation:** request `max_results` total across sources (split per source), not per source.

### 4.3 N+1 `count_documents` / per-card queries
- **Severity: Medium · Confidence: Confirmed**
- **Location:** backend KB listing (count per KB), conflicts full-corpus scan per request (`Architecture M2`)
- **Impact:** per-request Atlas fan-out that grows with corpus size.
- **Recommendation:** batch counts with `aggregate` `$group`; cache conflict-window results keyed by KB `updated_at` (deterministic invalidation).

### 4.4 `TavilyClient` / DDGS constructed per call
- **Severity: Low · Confidence: Confirmed**
- **Location:** search service per-request construction
- **Recommendation:** module-level singletons (connection reuse, fewer allocations).

### 4.5 Unconditional full GC after every ingestion
- **Severity: Medium · Confidence: Confirmed**
- **Location:** ingestion completion path
- **Impact:** a full `gc.collect()` per upload is CPU-expensive on a large heap and does nothing for RSS in most cases.
- **Recommendation:** drop it, or gate on an actual memory tier (see §6.2).

---

## 5. Frontend load (renders, requests, battery)

### 5.1 Dashboard polls 4 endpoints at 3–5 s, **default-on** (~80 req/min)
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/web/src/pages/DashboardPage.jsx:62,71-102`
- **Recommendation:** default `autoRefresh: false` (opt-in), pause on `document.hidden`, single combined endpoint if easy. Biggest idle-load win in the UI.

### 5.2 SSE + 2 s fallback polling race — both fire `fetchFinalAnalysis`
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/web/src/pages/PlaygroundPage.jsx:184-229` (+ stale closure `:279`)
- **Recommendation:** `finalizedRef` guard + clear the polling interval in `onComplete`/`onError`. Removes duplicate final-fetch calls per run.

### 5.3 Per-KB-card documents query runs ungated (N+1)
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/web/src/pages/KnowledgeBasesPage.jsx:245-248`
- **Recommendation:** `enabled: isExpanded` on the query — lazy load only when a card is opened. One-line fix.

### 5.4 Provider-sync overwrites user's embedding selection every 15 s
- **Severity: Medium · Confidence: Confirmed**
- **Location:** `apps/web/src/pages/PlaygroundPage.jsx:90-97`
- **Recommendation:** sync once on mount + on window focus, not on an interval.

### 5.5 Per-keystroke unmemoized filters; 100 ms timer re-renders; un-cleaned timeouts/RAF
- **Severity: Medium · Confidence: Confirmed**
- **Locations:** list filters in KB/Claims/Evidence pages, `LandingPage` mousemove + timeouts, copied-feedback timers ×5
- **Recommendation:** `useMemo` the filters, clean up effects, debounced input. Standard React hygiene — cheaper renders, less GC.

### 5.6 Axios has no timeout / abort / boot revalidation bounds
- **Severity: Medium · Confidence: Confirmed**
- **Recommendation:** default timeout, `AbortController` on route change, disable refetch-on-boot where data is fresh.

---

## 6. System resources (CPU / RAM / disk)

### 6.1 Purge the duplicate Python 3.12 + 3.14 site-packages tree (~1 GB+)
- **Severity: High · Confidence: Confirmed**
- **Location:** `apps/api` venv — duplicate `site-packages` (torch 529 MB + 504 MB, etc.); venv totals ≈ 2.5 GB
- **Impact:** double disk, double page-cache pressure, slower cold imports. Zero behavioral change to remove.
- **Recommendation:** rebuild the venv against a single interpreter; add a CI or pre-commit check that fails on two site-packages trees. **Pure deletion, pure win.**

### 6.2 `ru_maxrss` (lifetime peak) is reported as current memory
- **Severity: Medium · Confidence: Confirmed**
- **Location:** `apps/api/app/core/memory.py:46-50`
- **Impact:** tier guards fire on stale peaks → spurious GC/trim triggers (§4.5) → wasted CPU.
- **Recommendation:** read current RSS (statm or `psutil`), keep peak as a separate diagnostic.

### 6.3 Two stacked HTTP middlewares doing one job
- **Severity: Low · Confidence: Confirmed**
- **Location:** `apps/api/app/main.py:292,295-304`
- **Status:** ✅ Fixed — Added `GZipMiddleware(minimum_size=1000)` and merged with existing middleware
- **Recommendation:** merge into one middleware — one less frame per request (marginal, but free).

---

## 7. Smaller / leaner models (right-size every call)

1. **Fix config precedence so `models.yaml` actually works** — Critical, `apps/api/app/core/config.py:296-311,118-122` (always-truthy Settings defaults make YAML unreachable; see ARCHITECTURE C1). Until fixed, any per-task model routing (cheaper verifier, smaller generator) is a no-op.
2. **Verifier family separation** — High, `graph.py` generator + verifier both gemma4-family → self-verification bias (AI-ML High). Route the verifier to a *different* family/model; it also runs temp 0.0/1024 tokens, so prefer the smallest capable model.
3. **Already right-sized (keep):** INT8 Qdrant vectors, bge-small embeddings (384 d), disabled reranker path, hardware-aware semaphore (default 2), zero-LLM prefixes for deterministic steps, adaptive top-K. Don't "upgrade" any of these (see §9).
4. **Prompt-side savings compound with model size** (§1.3/1.4): a trimmed, cacheable prefix on a small model is the cheapest inference configuration this stack supports.

---

## 8. Ranked quick wins (small diff → big load reduction)

| # | Change | Where | Effort | Payoff |
|---|---|---|---|---|
| 1 | Dedup query embedding (route via LRU) | `graph.py:701-705` | ~5 lines | −1 embed per uncached request |
| 2 | `autoRefresh` default **off** | `DashboardPage.jsx:62` | 1 line | −~80 req/min idle |
| 3 | Lazy KB-card query `enabled: isExpanded` | `KnowledgeBasesPage.jsx:245-248` | 1 line | −N Mongo calls per page view |
| 4 | Cache hardware profile at startup | `hardware.py:66` | ~10 lines | −1 subprocess per health/models poll |
| 5 | Web "both" → `max_results` total | `search_service.py:246` | 1 line | −50% web-search calls in both-mode |
| 6 | Purge duplicate site-packages | venv | shell | −1 GB disk/RAM pressure |
| 7 | Unique `(kb_id, content_hash)` + 409 | `kb_service.py` | small | kills most expensive duplicate write path |
| 8 | `finalizedRef` SSE/poll guard | `PlaygroundPage.jsx:184-229` | ~10 lines | −1 duplicate final fetch per run |
| 9 | Drop 15 s provider-sync overwrite | `PlaygroundPage.jsx:90-97` | 1 line | −4 req/min + respects user choice |
| 10 | Deque + numpy semantic cache (persisted) | `semantic_cache.py` | medium | repeat questions → 0 LLM calls |
| 11 | `gather` startup `create_index` | startup | ~5 lines | faster boot, fewer serial Atlas RTs |
| 12 | Prompt prefix made byte-stable for Ollama KV cache | `graph.py`/`verifier.py` | small | prefill cost paid once per session |

---

## 9. What NOT to do (would *increase* load)

- **Do not enable the reranker** on the current sync `CrossEncoder.predict` (`reranker.py:58`) before moving it to a thread — it would add a loop-blocking torch inference per query (it is correctly disabled today; its raw-logit ≥ 0.80 truncation to 4 chunks also needs fixing first).
- **Do not "upgrade" embeddings** beyond bge-small or vectors beyond INT8 — retrieval quality is not the bottleneck; tokens and calls are.
- **Do not add caching layers in front of the semantic cache** — fix the existing one (§2.1) instead of stacking more.
- **Do not re-verify / re-embed on every recovery iteration** — cache by content hash within a run (§1.6, §2.6).
- **Do not wire the disk embedding cache as-is** — its current implementation (per-key queries, PRAGMA-per-op) would add load; wire only together with the rewrite (§1.2).
- **Do not add more polling to the frontend** — every current problem in §5 is *too much* polling, not too little.
- **Do not chase RAG "quality" with bigger models before the config precedence fix (§7.1)** — model settings silently don't apply, so bigger-model experiments would be reading a placebo.

---

*Cross-linked details (full evidence, code excerpts, and per-finding severity rationale): [AI-ML.md](AI-ML.md) · [PERFORMANCE.md](PERFORMANCE.md) · [BACKEND.md](BACKEND.md) · [FRONTEND.md](FRONTEND.md) · [ARCHITECTURE.md](ARCHITECTURE.md). Implementation sequencing: [ROADMAP.md](ROADMAP.md).*
