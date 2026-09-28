# TrustRAG Production Pass — 2026-09-28 (ui-redesign)

- **Branch:** `ui-redesign` (local only, never pushed)
- **Scope:** full-repo audit — architecture/code quality, security, backend/API, RAG pipeline, AI/ML inference, DevOps, frontend UX, QA
- **Method:** inspect → audit → fix → verify (unit + live E2E) → regression-check → document → commit, phase by phase
- **Supersedes:** extends `docs/audit-2026-09-28-ui-redesign-full.md` (its findings remain fixed; this file covers the 2026-09-28 production pass on top)

---

## Baseline (before changes)

| Check | Result |
|-------|--------|
| Backend `pytest` (with coverage) | 734 passed, 79% line coverage |
| Backend `ruff check` | clean |
| Frontend `vitest` | 33 passed (8 files) |
| Frontend `eslint --max-warnings 0` | clean |
| Frontend `vite build` | green, vendor-chunked |
| Secrets in tracked files | none (verified by pattern scan incl. git history) |

## Findings & fixes

| ID | Area | Severity | Finding | Fix | Verification |
|----|------|----------|---------|-----|--------------|
| A-1 | Architecture | MEDIUM | Function-level `app.*` imports scattered across 12 modules (schemas/analysis validator, tracing, hardware, llm_ledger, llm_utils, onnx_runtime, sparse_vector, internal routes, main lifespan) — violated the repo's own imports-at-top rule; several re-imported symbols already bound at module top | Hoisted all cycle-free imports to file top; verified cycle-freedom by import probe before each hoist; updated test patch targets to the consumer module (`app.main.*`, `app.api.v1.schemas.analysis.*`, `app.core.llm_ledger.get_model_config`) since patching the source module no longer intercepts top-level-bound names | 734/734 pytest; ruff clean |
| A-2 | Dead code | LOW | `onnx_embeddings.py`: `_onnx_intra_op_threads()` (alias, unused) and `_resolve_embedding_defaults()` (defined, never called — superseded by constructor-arg + config resolution) | Removed both + now-unused `resolve_intra_op_threads` import | ruff F401 clean; onnx test group green |
| A-3 | Observability | LOW | `onnx_reranker.py` used stdlib `logging.getLogger` while every other `app/core` module uses structlog — mixed formats break JSON log parsing in prod | Switched to `structlog.get_logger(__name__)` | reranker + onnx tests green |
| UX-1 | Frontend | MEDIUM | **DashboardPage had no error or first-load state**: `useQuery` failures were swallowed by `= []` defaults (a backend outage silently rendered zeros, indistinguishable from an empty account), and first paint showed "No analysis runs yet" + zeroed metrics while data was still loading | Added `isLoading/isError/error` per query; error banner with per-feed message + Retry button (`role="alert"`); `SkeletonRows` first-paint state for the recent-analyses feed (`aria-busy`); error/skeleton mutually exclusive with real content | eslint/vitest/build green; manual UI inspection |
| OPS-1 | Tooling | LOW | `ruff format` drift: 1 file unformatted (`sparse_vector.py`, introduced by A-1 edit) — would fail CI `ruff format --check` | Formatted; `140 files already formatted` | format check clean |

## Verified-solid (audited, no change needed)

This pass deliberately did **not** churn working code. Key areas inspected and confirmed sound:

- **Security**
  - JWT: HS256 with `iss`/`aud` verification, `jti` revocation denylist (Mongo TTL), user-vs-service token type separation both directions (deps.py rejects service-as-user and vice versa).
  - Passwords: bcrypt cost 12, 72-byte ceiling enforced at hash time; login has user-enumeration timing parity (dummy-hash path) and Mongo-backed lockout with TTL janitor.
  - AuthZ: every KB/document/analysis read/write is ownership-checked at the service layer; cross-user access returns 403 (live-verified below); `/internal/*` requires service token + scoped permission; MCP tools require `service_token`.
  - SSRF: URL ingestion uses origin allowlist (request can narrow, never widen), blocked hostnames incl. metadata endpoints, non-canonical-IP spellings rejected, per-hop revalidation with IP pinning (DNS-rebinding resistant), size/timeout ceilings, redirect cap.
  - Uploads: extension allowlist from config, null-byte + path sanitization, 20MB streaming guard in 1MB chunks (no full-buffer OOM).
  - CORS locked to configured origins (dev-only platform regex), credentials on, security headers (nosniff/DENY/referrer/permissions-policy/HSTS-in-prod) present; no cookies used for auth (Bearer only); no `dangerouslySetInnerHTML`/`innerHTML` in frontend; `.env` gitignored with secret-scan CI gate; log redaction patterns for API keys in `logging.py`.
  - `jwt_secret` validator rejects short/placeholder secrets (live-verified rejection).
- **Backend/API**: DB pool sizing (50/2, idle 45s) sensible; index coverage complete incl. compound owner+time indexes backing every list endpoint, TTL indexes for trace events / revoked tokens / stream tickets / failed logins; SSE pub/sub bounded queues with proper unsubscribe; background analysis wrapped in a global concurrency semaphore; blocking parser/embed work consistently off-loaded via `asyncio.to_thread`; GZip at 1KB; response models typed (Pydantic direct serialization).
- **RAG pipeline**: fan-out sub-query retrieval is concurrent with per-branch degradation and outage classification (never silent "no evidence"); RRF fusion dedups by chunk id; context builder dedups near-identical segments and enforces whole-segment char budgets (no desynced segment numbering); fused decompose+verify collapses 2 LLM calls into 1 with kill-switch and reasoning-model skip; claim cap by hardware tier; semantic answer cache reuses only the answer text while retrieval + NLI re-run fresh (stale-evidence safe); recovery loop bounded by tokens/latency/attempt budgets; retrieval skipped on regeneration retries (no wasted embedding/rerank spend); re-retrieve widening capped by context need.
- **AI/ML inference**: ONNX-only embedding engine (BGE-small) + int8 ONNX reranker; shared session factory (thread caps, full graph optimization, sequential exec); tier-aware micro-batching for ingest embeddings and reranker pairs; two-tier embedding cache (in-mem LRU + SQLite disk, namespaced by model) with batch read/write; query-embedding LRU feeding both retrieval and the semantic cache (no duplicate embed of the same query); LLM registry LRU with RAM-derived instance caps, cloud clients never evicted; dynamic `num_ctx` from tiktoken counts; non-reasoning local temperature 0.0 for verification; model warmup at startup non-blocking.
- **DevOps**: multi-stage Dockerfile (uv-locked builder, slim non-root runtime, no build tools), healthcheck with generous start-period matching MongoDB retry policy, exec-form CMD honoring `$PORT`, `MALLOC_ARENA_MAX=1`, `TOKENIZERS_PARALLELISM=false`; compose wires Qdrant + host services, no secrets baked into images; CI gates lint/format/config/tests/frontend/cross-platform + security workflow (pip-audit, npm audit, secret scan, Bandit).

## Manual verification (black-box, live stack)

Added `scripts/e2e_manual_verify.sh` — a one-shot live E2E that boots API + Vite in a single shell (the sandbox kills children between commands, so a persistent interactive session was not possible), exercises the real flow, and tears down:

```
RESULT: 15 passed, 0 failed
```

Coverage of the run:
1. Stack boot — API healthy on :8000, Vite serving on :5173
2. Auth — register returns profile (no token leak), login returns JWT, `auth/me` resolves, wrong password → 401
3. KB — create, upload MD doc, async indexing reaches `completed`
4. Analysis — created, reached terminal state (`completed`/`abstained` both observed across runs), claims persisted, execution trace populated
5. AuthZ — cross-user KB fetch rejected (403)
6. UI — SPA shell served

Plus white-box regression after every change: backend 734 passed (79% cov), frontend 33 passed, eslint/ruff/ruff-format/build all green.

## Performance notes

- Startup measured during live run: ~4s to API-ready, +11s non-blocking warmup (discovery → hardware probe → ONNX embed load; RSS 178MB → ~700MB resident, expected for ONNX + Qdrant embedded + FastAPI).
- No perf regressions introduced: this pass removed per-call import lookups on hot paths (config resolution in sparse-vector params, ONNX session options, tracing middleware, schema validator) and two dead functions. Structural RAG/inference optimizations (batching, caching, budgets) were already present and are listed above as verified.

## Remaining risks & recommended upgrades (not blocking)

1. **Coverage gaps**: `analysis_service.py` at 54% — the create/finalize branches deserve integration-level tests beyond `test_analysis_pipeline_integration.py`.
2. **Rate limiter multi-worker**: in-memory limiter means N workers multiply the ceiling; production already documents `SLOWAPI_STORAGE_URI` — wire Redis in the deploy template.
3. **E2E in CI**: the new `scripts/e2e_manual_verify.sh` could run as a nightly CI job with MongoDB service container; today it is local-only.
4. **Pydantic-model reuse**: `AnalysisResponse` serialization is hand-rolled in `serialize_*` helpers; `model_validate` from ORM docs would shrink ~80 lines (left as-is to avoid behavior risk late in the pass).
5. **UI polish backlog**: Dashboard error UX now exists; Evidence/Claims/Conflicts/Trace already had full loading/error/empty states; the next UX step is streaming token-level rendering in the Playground (SSE plumbing already exists).

## Final re-audit checklist (all ✅)

- Secrets: pattern scan over app/tests/scripts/config + git history — clean; `.env` ignored; CI secret-scan gate present
- Imports: all cycle-free `app.*` imports at file top; remaining 21 deferred imports are documented genuine cycles (local_llm ↔ model_registry ↔ onnx_*, analysis_service → agent.graph) or heavy-optional loads (onnx/torch probes)
- Config: single source `models.yaml` + `.env` for secrets only; no duplicated thresholds introduced
- Tests updated to match new import binding; no test weakened or deleted
- Lint/format/typecheck/test/build all green before commit
