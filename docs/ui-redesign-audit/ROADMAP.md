# TrustRAG ui-redesign — Implementation Roadmap

Sequenced from the eight audit reports ([INDEX.md](INDEX.md)). Ordered by: (1) unblock safe shipping, (2) fix correctness/config so later work isn't placebo, (3) reduce load, (4) harden security, (5) pay down test debt. No item here requires app-code changes beyond what the finding recommends; nothing is speculative.

Effort labels: **S** (hours) · **M** (1–2 days) · **L** (3–5 days).

---

## Phase 0 — Safety net (S, do first, unblocks everything)

| # | Task | Source | Detail |
|---|---|---|---|
| 0.1 | Fix CI test gate: `ci.yml:72-74` runs only `pytest tests/test_config.py` (23/103 tests). Change to `pytest -v`; first patch `tests/test_local_llm.py` health checks that hit real side effects | [QA](QA.md) Critical | Every later refactor needs the full suite as a net |
| 0.2 | Purge duplicate Python 3.12 + 3.14 site-packages (~1 GB+, torch ×2); rebuild venv on one interpreter; add a guard so it can't regrow | [PERF](PERFORMANCE.md) High 5 | Pure deletion; reduces disk/RAM/import time |

## Phase 1 — Correctness & configuration (M; without these, model-config work is placebo)

| # | Task | Source |
|---|---|---|
| 1.1 | **Config precedence inversion**: `models.yaml` is unreachable — always-truthy Settings defaults win (`config.py:113-122,296-311`). Make yaml-first getters, delete the 6 hardcoded model IDs, log the resolved triple at startup | [ARCH](ARCHITECTURE.md) C1, [AI-ML](AI-ML.md) C3 |
| 1.2 | **One typed verdict module**: trust verdict computed twice differently (`graph.py:463-471` vs `analysis_service.py:384-408`) + string contracts (`answer == "ABSTAIN"`, `diagnosis_failures == [...]`, `graph.py:355`). Extract a single `verdict.py` with typed enums | [ARCH](ARCHITECTURE.md) C2 |
| 1.3 | **Web evidence**: stop hardcoding `"VERIFIED"` for web chunks (`graph.py:262`) — emit `WEB_UNVERIFIED`; also fixes conflicts `$nin [VERIFIED, None]` misfeed | [AI-ML](AI-ML.md) High, [ARCH](ARCHITECTURE.md) H4 |
| 1.4 | **Delete order**: `delete_document` swallows Qdrant failure then deletes the Mongo record → permanent orphan vectors (`kb_service.py:201-223`). Delete vectors first (or compensate); make `delete_kb` transactional | [BACKEND](BACKEND.md) High 4 |
| 1.5 | **Upload idempotency**: unique `(kb_id, content_hash)` index + `409` on conflict (`kb_service.py`) | [BACKEND](BACKEND.md) Medium |
| 1.6 | Frontend trust fixes: remove fabricated metrics POST (`ExperimentsPage.jsx:8-63` — send config_name only), remove invented LandingPage benchmark claims (`LandingPage.jsx:189-228`), real API-status badge (`AppLayout.jsx:118-121`) | [FRONTEND](FRONTEND.md) Critical 2, [UI-UX](UI-UX.md) |
| 1.7 | `react-markdown` v10: remove `inline` prop usage (`FormattedAnswer.jsx:70`); fix invalid Tailwind classes (`w-18`, `py-0.2` — 9 sites; add `eslint-plugin-tailwindcss` to CI) | [FRONTEND](FRONTEND.md), [UI-UX](UI-UX.md) |

## Phase 2 — Load reduction (M–L; details in [LOAD-OPTIMIZATION.md](LOAD-OPTIMIZATION.md))

| # | Task | Source |
|---|---|---|
| 2.1 | **Async Qdrant**: migrate the choke point `db/qdrant.py:12,25-57` to `AsyncQdrantClient` (or `run_in_executor` minimally) — removes systemic event-loop blocking | [PERF](PERFORMANCE.md) Critical, [BACKEND](BACKEND.md) High 2 |
| 2.2 | **Dedup query embedding**: route `graph.py:701-705` through `QueryEmbeddingLRUCache` (−1 embed per uncached request, ~5 lines) | [AI-ML](AI-ML.md) Critical 2 |
| 2.3 | **Wire + rewrite embedding disk cache together** (`model_registry.py:379-563` never returns the wrapper; `disk_cache.py` needs persistent connection, batched `IN` queries, `executemany`, PRAGMAs once) | [AI-ML](AI-ML.md) Critical 1, [PERF](PERFORMANCE.md) |
| 2.4 | **Semantic cache rewrite**: numpy vectorized cosine + deque eviction + disk persistence (`semantic_cache.py`) | [AI-ML](AI-ML.md), [PERF](PERFORMANCE.md) |
| 2.5 | **Cache hardware profile at startup** (subprocess-per-`/health`-and-`/models`, `hardware.py:66`); cache Qdrant collection dims; TTL user cache (`deps.py:44`) | [PERF](PERFORMANCE.md) High 1 |
| 2.6 | **CPU work off the loop**: `to_thread` for `trim_memory` (`models.py:201-208`), rerank predict (before ever enabling it), parse/chunk; `gather` the ~22 startup `create_index` calls; drop unconditional post-ingestion full GC; current-RSS (not `ru_maxrss`) for tier guards (`memory.py:46-50`) | [PERF](PERFORMANCE.md) |
| 2.7 | **Web "both" cap** at `max_results` total (`search_service.py:246`); Tavily/DDGS singletons; SSE delivery via in-process pub/sub instead of 1 Hz Mongo polling per client (`analysis_service.py:261-310`) | [AI-ML](AI-ML.md), [BACKEND](BACKEND.md), [ARCH](ARCHITECTURE.md) H6 |
| 2.8 | **Verifier economics**: preserve provider/model in fallback (`verifier.py:378`); heuristic claim decomposition on failure (`verifier.py:213-214`); different model family from generator; byte-stable prompt prefix for Ollama KV cache | [AI-ML](AI-ML.md) |
| 2.9 | **Frontend idle load**: `autoRefresh` default off (`DashboardPage.jsx:62`); `finalizedRef` SSE/poll race guard (`PlaygroundPage.jsx:184-229`); lazy `enabled: isExpanded` KB-card queries (`KnowledgeBasesPage.jsx:245-248`); drop 15 s provider-sync overwrite (`PlaygroundPage.jsx:90-97`) | [FRONTEND](FRONTEND.md) |

## Phase 3 — Security hardening (M)

| # | Task | Source |
|---|---|---|
| 3.1 | **SSE auth**: replace JWT-in-query-string (`analyses.py:118-135`) with short-lived single-use stream tickets (30–60 s TTL); scrub token params from logs | [SEC](SECURITY.md) High, [BACKEND](BACKEND.md) High 3 |
| 3.2 | **Auth-lock `/models`** router (`models.py:18-19`): no unauthenticated memory-GC trigger, no `base_url`/key-boolean exposure, rate-limit `trim`; also `POST /hardware` | [SEC](SECURITY.md) Med, [BACKEND](BACKEND.md) High 1 |
| 3.3 | **Token lifecycle**: short-lived access (10–15 min) + refresh, `jti`, revocation path for logout; default per-IP rate limiting on all routers; `--proxy-headers` + trust last untrusted hop (email+IP key for login) | [SEC](SECURITY.md) Med |
| 3.4 | CORS: drop credentialed wildcard for `*.pages.dev`/`*.vercel.app`/`*.netlify.app` (or make explicit origins) | [SEC](SECURITY.md) Low |

## Phase 4 — Structure & docs debt (M, can trail)

| # | Task | Source |
|---|---|---|
| 4.1 | Extract `add_trace_event` from `graph.py:244-258` into `tracing.py` (~30 lines) to break agent↔services circular import | [ARCH](ARCHITECTURE.md) H1 |
| 4.2 | Move ingestion out of the route layer (`knowledge_bases.py:83-160`) into `kb_service`; delete `graph.py`'s duplicated ~108-line re-index block (`:103-210`) in favor of the service | [ARCH](ARCHITECTURE.md) H2/H3 |
| 4.3 | Make the dossier export emit the promised `trustrag:contentHash` fields (`analysis_service.py:599-674`) or fix the format spec | [ARCH](ARCHITECTURE.md) H8 |
| 4.4 | Docs/spec/README alignment: real module tree, real tool names (`tavily_search`/`duckduckgo_search`/`hybrid_web_search`), real thresholds, real docker service name | [ARCH](ARCHITECTURE.md) H5 |
| 4.5 | Recovery: implement or remove the 5 unimplemented strategies in `models.yaml:112-123` | [ARCH](ARCHITECTURE.md) H7 |
| 4.6 | Fix duplicate `lib/api.js` vs `services/api.js`; remove/own the orphaned `FEEDBACK` collection; consolidate the three Qdrant storage dirs; remove the orphaned `/traces/:id` route or link it | [ARCH](ARCHITECTURE.md) M6/M7, [UI-UX](UI-UX.md) |

## Phase 5 — Test debt (L, continuous)

- Endpoint coverage for the 5 untested modules (models, conflicts, evidence, claims, `documents.py` GET `/{doc_id}`) — [QA](QA.md)
- One E2E run (upload → ingest → analyze → SSE completion → evidence/claims present) — [QA](QA.md)
- Minimal frontend tests (Vitest + React Testing Library) for the SSE race guard and mutations' error paths — [QA](QA.md), [FRONTEND](FRONTEND.md)
- A11y pass (the dedicated UI/UX audit died mid-run — [UI-UX.md](UI-UX.md) is partial; keyboard/screen-reader review is an open gap)
- Add `--cov`, mypy, and remove `pip-audit || true` — [QA](QA.md) Lows

---

## High-value missing features (add *after* the phases above; nothing else)

1. **Experiment runner parity** — the experiments UI can't run real A/B comparisons because metrics are fabricated; once Phase 1.6 lands, wire actual runs with per-config snapshots (the backend already stores `config_snapshot` per run — reuse it).
2. **Settings-driven model routing surfaced in UI** — once Phase 1.1 (config precedence) is fixed, expose the resolved generator/verifier/embedder triple (already logged at startup per the fix) in Settings instead of hardcoded names in 5+ frontend files.
3. **"Already ingested" UX** — with Phase 1.5's `409`, show a friendly duplicate-document state instead of an error toast.
4. **Consolidated dashboard endpoint** — one aggregate call replacing the 4 polled endpoints (cuts idle load further than 2.9 alone).
5. **Token refresh UX** — silent refresh on 401 (pairs with Phase 3.3) instead of a hard logout at 60 min.

## What NOT to change / add

**Keep as-is (verified strengths — do not "improve" these):**
- App factory + 14 never-leak exception handlers; single Mongo access module with idempotent index creation
- Per-run `config_snapshot`; per-KB Qdrant collections (COSINE, INT8); deterministic point IDs
- SSRF-hardened `search_service.py:37-79`; the gold-standard route pattern of `analyses.py`
- POST → ANALYSES → BackgroundTasks → SSE+REST flow; bounded recovery loop
- `to_thread` embeddings; `LRU(1024)` caches; `gather` of hybrid+web; non-blocking warmup; offline flags; Motor pooling; batched `$in`; adaptive top-K; zero-LLM prefixes; deterministic token pruning
- bge-small embeddings (384 d) + disabled reranker — retrieval quality is not the bottleneck; tokens and calls are
- HS256 pinned, jwt_secret ≥ 32 no default, QDRANT_API_KEY prod-required, bcrypt cost 12, timing-equalized dummy bcrypt, docs/OpenAPI off in prod, secret-scrubbing, `.env` hygiene, per-request authz reload

**Do not add (over-engineering for this system's scale):**
- Redis / Celery / message-queue infra — single-process pub/sub solves the SSE polling problem at this scale
- Bigger models, bigger embeddings, vector dimensions > INT8 384 d
- Microservice split or multi-worker horizontal scale before the sync-Qdrant fix is even measured
- Additional caching layers stacked on the unfixed semantic cache
- Any new polling in the frontend

---

*Scores, deduplicated P0/P1 rollup, and quick wins: [INDEX.md](INDEX.md). Load-reduction detail with per-request arithmetic: [LOAD-OPTIMIZATION.md](LOAD-OPTIMIZATION.md).*
