# Architecture Audit — TrustRAG ui-redesign

**Scope reviewed:** layering (routes → services → domain → infra), module dependency graph, config architecture, the agent graph's contracts with services, docs/spec vs. reality, concurrency & process model, recovery design. READ-ONLY; FINAL pass (supersedes any earlier draft of this report). Findings deduplicated against sibling reports — shared items are cross-referenced.

---

## Critical

**[Critical] C1 — Config precedence inversion: models.yaml is unreachable; hardcoded Settings defaults always win** (Confirmed)
- Location: `app/core/config.py:113-122,250-262,302-311,338-346`; `apps/api/config/models.yaml:10-15` (whose header explicitly says "NEVER hardcode values from this file")
- Evidence: Getters resolve `settings.X or yaml_value`, but every `Settings` default is non-empty (`llm_provider="ollama"`, `embedding_provider="huggingface"`, …) — the `or` never falls through to yaml. The yaml-declared LLM, verifier, and embedding models, plus every `optimization:` block (prompt_caching, KV quantization), are silently dead.
- Impact: The declared model architecture is fiction. Operators editing models.yaml get zero effect with no warning — a spec-violating (D-07) and operationally dangerous inversion.
- Recommendation: Invert the getters to yaml-first (or make Settings fields `Optional` so "unset" is distinguishable), delete the 6 hardcoded model IDs from Python, and log the resolved provider/model triple at startup.
- (Same root cause as AI-ML.md Critical 3 — owned here for the architectural contract violation.)

**[Critical] C2 — Trust verdict is split-brained across the agent graph and the service layer** (Confirmed)
- Location: `app/agent/graph.py:463-471` (decides only PASS/FAIL) vs `app/services/analysis_service.py:384-408` (owns the full ABSTAIN→ABSTAINED / PASS→TRUSTED / score≥abstain_below→UNCERTAIN / else FAILED taxonomy); string contracts at `graph.py:355` (`answer == "ABSTAIN"`, `state.get("diagnosis_failures") == ["Knowledge base contains 0 indexed chunks"]`)
- Evidence: The final verdict semantics live outside the graph, bound by exact string equality on human-readable messages. Reusing the graph without the service wrapper yields *different verdicts* for identical inputs; renaming an error message silently changes product behavior.
- Impact: The single most important output of the system — the trust label — is emergent from string matching across a module boundary. This is the highest-leverage correctness risk in the codebase.
- Recommendation: One typed verdict module (enum + a single function producing the final label) imported by both; replace string contracts with typed states.

## High

**[High] H1 — Circular dependency agent↔services, resolved only by a deferred import** (Confirmed)
- Location: `graph.py:24` imports `add_trace_event` from `analysis_service`; `analysis_service.py:369` imports `graph` inside a function body to avoid the cycle.
- Recommendation: Extract `add_trace_event` (:244-258) into a `tracing.py` module (~30-line move) — kills the cycle and the deferred import.

**[High] H2 — Ingestion logic lives in the route layer (spec §22 violation)** (Confirmed)
- Location: `app/api/v1/knowledge_bases.py:83-160` — parse/chunk/validate orchestration in the router; contrast the thin `analyses.py` exemplar.
- Recommendation: Move orchestration into the ingestion pipeline/service; router stays a translator.

**[High] H3 — graph.py is a 765-line god module duplicating ingestion** (Confirmed)
- Location: `app/agent/graph.py` — includes a ~108-line self-healing re-index (:103-210) duplicating pipeline logic, and reaches into private `cfg._get` (:504).
- Recommendation: Extract `reindex_kb`, recovery, and verdict nodes into separate modules; reuse pipeline code for re-indexing.

**[High] H4 — Web evidence auto-stamped "VERIFIED", bypassing the integrity audit** (Confirmed)
- Location: `graph.py:262` → `verified_chunks` at `:265-266` (genuine sha256 audit at `integrity.py:53-88` applies only to local chunks).
- Impact: Also misfeeds the conflicts endpoint, which filters `$nin [VERIFIED, None]` — unverified web data is classified as if hash-audited.
- Recommendation: `WEB_UNVERIFIED` status for web chunks; NLI remains their only validation; surface the distinction in UI/trace.
- (Cross-ref AI-ML.md High — shared finding; the provenance-honesty theme also covers FRONTEND.md's fabricated metrics and the export-dossier gap at H8.)

**[High] H5 — Docs/spec/README describe a different system** (Confirmed)
- Location: spec §5 module tree (files don't exist), §8 (omits `document_chunks`), §13 (UNSUPPORTED/UNKNOWN vs code's SUPPORTED/CONTRADICTED/NEUTRAL); README claims tools `trustrag_search`/`trustrag_verify_claim` vs actual `tavily_search`/`duckduckgo_search`/`hybrid_web_search`; README thresholds 0.60/0.15 vs yaml 0.80/0.20; README test counts contradictory; decision log ends at D-17 with no local-first ADR; D-03 says "Local MongoDB NOT used" vs `docker-compose.yml:65`.
- Impact: The documents the next contributor will trust are wrong at a dozen points.
- Recommendation: One reconciliation pass over spec/README/architecture docs/decision log.

**[High] H6 — All rate limiting, caching, and concurrency is single-process in-memory; SSE polls Mongo at 1 Hz per client** (Confirmed)
- Location: `analysis_service.py:261-310` (SSE 1 Hz polling); semaphore default 2; semantic cache in-process (0.94 threshold).
- Impact: Multi-worker deployment (or even uvicorn `--workers 2`) silently breaks rate limits, the analysis semaphore, and cache hit rates.
- Recommendation: Document + assert single-process; or change streams / single poller broadcasting to subscribers; fail-fast at startup if workers > 1.

**[High] H7 — Recovery: 7 strategies configured, 2 implemented; 5 structurally unreachable** (Confirmed)
- Location: `models.yaml:112-123` vs `graph.py:504-590` — only `query_rewrite` and `re_retrieve` exist; max 2 attempts anyway.
- Recommendation: Trim the config to what exists, or implement the remainder — a config that promises behavior the code can't deliver is a trust bug in a trust product.

**[High] H8 — Export dossier promises SHA-256 provenance but emits no hash on any evidence item** (Confirmed)
- Location: `analysis_service.py:599-674`; the docstring and JSON-LD `@context` declare `trustrag:contentHash`, but evidence objects emit only `integrityStatus`/`retrievalScore`/`rerankScore`.
- Recommendation: Thread the existing chunk content hash (already computed for the integrity audit) into export objects.

## Medium

**[Medium] M1 — Evidence/claims inconsistently carry `user_id`; fallback `$in` over ≤1000 analyses** (Confirmed) — `analysis_service.py:477-522`. Backfill user_id and drop the fallback.
**[Medium] M2 — Conflicts derived per-request by scanning the user's full corpus; no `reason` field** (Confirmed) — `analysis_service.py:525-596`. Precompute on write or bound the scan; include a reason for each conflict pair.
**[Medium] M3 — Substring error classification at the most important call site** (Confirmed) — `analysis_service.py:427-467`; branch on exception types instead. (Cross-ref BACKEND.md Low.)
**[Medium] M4 — SSE token in query param** (Confirmed) — `analyses.py:117-151`; short-lived single-analysis stream tickets. (Cross-ref BACKEND.md High 3, SECURITY.md High.)
**[Medium] M5 — Per-request Mongo user fetch, no short-TTL cache** (Confirmed) — `deps.py:44`; a 5-15s cache would remove most of these round trips.
**[Medium] M6 — Possibly-orphaned code: FEEDBACK collection, local_llm/disk_cache paths, lib/api.js vs services/api.js duplication** (Likely/Potential) — grep importers; delete or document each.
**[Medium] M7 — Three Qdrant storage directories on disk** (Confirmed: `data/qdrant` explained by qdrant.py:21,40; `apps/data/qdrant` + `apps/api/data/qdrant` unexplained) — delete stale trees, gitignore, log the active path at startup.
**[Medium] M8 — 60-min JWT, no refresh** (Confirmed) — long analyses + SSE outlive tokens mid-session; sliding expiry or refresh tokens. (Cross-ref SECURITY.md Medium.)

## Low

**[Low] L1 — Dynamic limit lambdas registered per route** — `@limiter.limit(lambda: ...)` per handler; register named limit strings/objects for greppability.

## Keep as-is (do not "fix" — these are correct)

1. `main.py` app factory + the 14 never-leak exception handlers.
2. Single Mongo access module with idempotent index creation.
3. Per-run `config_snapshot` persistence (`analysis_service.py:112-172`) — reproducibility backbone.
4. Per-KB Qdrant collection isolation (kb_{id}, 384d COSINE, INT8).
5. SSRF-hardened web grounding (`search_service.py:37-79`).
6. Background-execution pattern: POST → ANALYSES doc → BackgroundTasks → SSE + REST fallback.
7. Bounded recovery loop (max attempts enforced).
8. Thin-route exemplar: `analyses.py`.
9. JWT secret strength validation (≥32 chars, no fallback).

---

## Architecture Score: 5.5 / 10

**Justification:** The macro-structure is sound and consistent — clean route→service→domain layering (one spec-violating exception), per-KB vector isolation, a bounded recovery loop, per-run config snapshots for reproducibility, and a genuinely hardened web-grounding path. That is a solid 7-skeleton. It drops to 5.5 for two Critical structural lies the system tells: the entire models.yaml optimization surface is unreachable, and the trust verdict — the product's output — is split across a module boundary and held together by string equality. Add a god-module agent duplicating ingestion, a route layer doing ingestion work, docs describing a different system, and single-process assumptions nowhere asserted, and the architecture is *good code organized around two broken contracts*.

## Top 5 structural quick wins

1. **Fix config precedence (C1)** — invert getters to yaml-first; every declared optimization becomes reachable.
2. **Consolidate the verdict into one typed module (C2)** — kills the string contracts and the split-brain.
3. **Extract `add_trace_event` to tracing.py (H1)** — ~30-line move breaking the only circular dependency.
4. **Move ingestion out of the route + dedupe the graph's re-index (H2+H3)** — restores layering, shrinks graph.py by a third.
5. **Restore provenance honesty (H4+H8)** — WEB_UNVERIFIED status + real hashes in the export — plus a zero-code docs reconciliation pass (H5).
