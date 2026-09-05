# TrustRAG — ui-redesign Branch End-to-End Audit

Status: **COMPLETE** — all 10 reports written (8 scored audits + 2 synthesis docs). Findings rolled up below; implementation order in [ROADMAP.md](ROADMAP.md).

Scope: `apps/web` (React UI), `apps/api` (FastAPI RAG backend), infra (docker-compose, CI workflows), tests.

| Report | Status |
|---|---|
| [UI-UX.md](UI-UX.md) | ⚠️ partial — 5/10 provisional (~40% of surface audited; agent died mid-run) · 0 Critical · 2 High · **15 findings fixed in UI polish pass** |
| [FRONTEND.md](FRONTEND.md) | ✅ complete — 5.5/10 · 2 Critical (SSE/polling race; fabricated metrics POSTed as real experiments) · 7 High · **12 findings fixed in UI polish pass** |
| [BACKEND.md](BACKEND.md) | ✅ complete — **7.0/10** · 0 Critical · 3 High |
| [AI-ML.md](AI-ML.md) | ✅ complete — **6.5/10** · 2 Critical (dead embedding disk cache; double query embedding) · 7 High |
| [SECURITY.md](SECURITY.md) | ✅ complete — **6.5/10** · 0 Critical (coverage gaps disclosed) · 1 High |
| [QA.md](QA.md) | ✅ complete — **5.5/10** · 0 Critical (CI test gate fixed) · 4 High · **12 findings fixed in UI polish pass** |
| [PERFORMANCE.md](PERFORMANCE.md) | ✅ complete — 5/10 · 1 Critical (sync QdrantClient on event loop) · 5 High |
| [ARCHITECTURE.md](ARCHITECTURE.md) | ✅ complete — **6.5/10** · 1 Critical (trust verdict split-brain) · 8 High |
| [LOAD-OPTIMIZATION.md](LOAD-OPTIMIZATION.md) | ✅ complete — synthesis/plan doc (per-request load arithmetic; not scored) |
| [ROADMAP.md](ROADMAP.md) | ✅ complete — synthesis/plan doc (sequenced phases 0–5; not scored) · **UI Polish phase completed** |

---

## Rollup

Findings are deduplicated across reports — one defect confirmed by multiple lenses is counted once and attributed to its primary owner; cross-references are merged.

**Counts across the 8 scored reports (UI-UX partial):** 9 Critical reported → **6 unique after dedup** (2 fixed: P0-1 CI test gate, P0-2 config precedence; AI-ML C3 ≡ ARCH C1 still counts as 1) · 38 High · 57 Medium · 34 Low. The P0 table lists all unique Criticals; the P1 table lists the highest-impact deduplicated Highs.

**UI Polish Pass (commits `91746b1`, `bbcfe53`):** Fixed 27 findings across UI-UX and Frontend reports — brand casing, CTA routing, internal detail leakage, accessibility (press feedback, aria-labels, font sizes), spring physics standardization, reduced-motion support, staggered animations, layout consistency, CSS deduplication, and vendor chunk optimization.

### P0 — Critical (deduplicated)

| # | Finding | Primary | Cross-refs | Where |
|---|---|---|---|---|
| P0-1 | **~~CI runs only 1 of 18 test files~~ ✅ Fixed** — Changed `pytest tests/test_config.py` → `pytest tests/` (full 103-test suite) | [QA](QA.md) | — | `ci.yml:72-74` |
| P0-2 | **~~Config precedence inversion: models.yaml unreachable~~ ✅ Fixed** — Replaced `getattr(settings, "X", None)` with `os.environ.get("X")` for all ModelConfig properties; precedence now: env vars > models.yaml > hardcoded defaults | [ARCH](ARCHITECTURE.md) C1 | [AI-ML](AI-ML.md) C3 | `config.py:113-122,296-311` |
| P0-3* | **Trust verdict split-brain** — graph decides only PASS/FAIL while service owns the full taxonomy, bound by exact string equality (`answer == "ABSTAIN"`, `diagnosis_failures == [...]`); highest-leverage correctness risk | [ARCH](ARCHITECTURE.md) C2 | — | `graph.py:463-471,355` vs `analysis_service.py:384-408` |
| P0-4 | **Sync QdrantClient on the FastAPI event loop** — blocks every query and ingestion batch; systemic; choke point is `db/qdrant.py` | [PERF](PERFORMANCE.md) C | [BACKEND](BACKEND.md) H2 | `db/qdrant.py:12,25-57` |
| P0-5 | **Persistent embedding disk cache is dead code** — `CachedEmbeddingsWrapper` is built but never returned; cache is never consulted or populated | [AI-ML](AI-ML.md) C1 | [PERF](PERFORMANCE.md) | `disk_cache.py` (whole file), `model_registry.py:274-375` |
| P0-6 | **Query embedded twice per uncached request** — `graph.py` bypasses the `QueryEmbeddingLRUCache` wrapping only `dense_search`; ~5-line fix, saves one embedding call per request | [AI-ML](AI-ML.md) C2 | — | `graph.py:701-705` |
| P0-7 | **SSE stream + fallback polling race** — both paths can finalize the same analysis concurrently; no shared "finished" flag; silent catch | [FRONTEND](FRONTEND.md) C1 | — | `PlaygroundPage.jsx:184-229` |
| P0-8 | **Fabricated benchmark metrics POSTed as real experiment records** — hardcoded `metrics: { evidence_coverage: 0.95, … }`; empty-state chart renders fake numbers | [FRONTEND](FRONTEND.md) C2 | — | `ExperimentsPage.jsx:8-63` |

> *P0-3* is a Critical by finding severity, but the roadmap sequences it into Phase 1.2 (typed verdict module) because it is a refactor-scale change (M), not a same-day fix.

### P1 — High (deduplicated highlights)

| # | Finding | Primary | Cross-refs | Where |
|---|---|---|---|---|
| P1-1 | **~~Operational endpoints unauthenticated~~ ✅ Partially Fixed** — Added `Depends(get_current_user)` to GET /hardware and POST /memory/trim; GET /providers remains public (login page) | [BACKEND](BACKEND.md) H1 | [SEC](SECURITY.md) M1 | `models.py:200-215,186-197,31-54` |
| P1-2 | JWT in SSE query string — 60-min tokens land in access logs; use short-lived single-use stream tickets | [SEC](SECURITY.md) H1 | [BACKEND](BACKEND.md) H3, [ARCH](ARCHITECTURE.md) | `analyses.py:118-135` |
| P1-3 | `delete_document` swallows Qdrant failure then deletes the Mongo record → permanent orphan vectors | [BACKEND](BACKEND.md) H4 | — | `kb_service.py:201-223` |
| P1-4 | Ingestion logic lives in the route layer (spec §22 violation); `graph.py` duplicates a ~108-line re-index block | [ARCH](ARCHITECTURE.md) H2/H3 | — | `knowledge_bases.py:83-160`, `graph.py:103-210` |
| P1-5 | Agent↔services circular dependency via deferred import; extract `tracing.py` (~30 lines) | [ARCH](ARCHITECTURE.md) H1 | — | `graph.py:24`, `analysis_service.py:369` |
| P1-6 | Hardware-probe subprocess (`vm_stat`/`/proc/meminfo`) fires per `/health` + `/models` request; Dashboard 3–5 s polling multiplies it | [PERF](PERFORMANCE.md) H1 | — | `hardware.py:66` |
| P1-7 | `trim_memory` gc runs synchronously on the loop, incl. after every ingestion | [PERF](PERFORMANCE.md) H2 | — | `models.py:201-208`, `analysis_service.py:469-474` |
| P1-8 | Rerank `torch model.predict` runs sync inside async graph | [PERF](PERFORMANCE.md) H3 | — | `reranker.py:58` |
| P1-9 | Stale closure — trace fallback always submits submit-time empty array | [FRONTEND](FRONTEND.md) H1 | — | `PlaygroundPage.jsx:279` |
| P1-10 | react-markdown v10 removed the `inline` prop → inline code renders as block `<pre>` | [FRONTEND](FRONTEND.md) H2 | — | `FormattedAnswer.jsx:70` |
| P1-11 | Web chunks hardcoded `"VERIFIED"` — misfeeds conflicts `$nin [VERIFIED, None]`; should emit `WEB_UNVERIFIED` | [AI-ML](AI-ML.md) H | [ARCH](ARCHITECTURE.md) H4 | `graph.py:262` |
| P1-12 | Five endpoint modules zero test coverage (models, conflicts, evidence, claims, documents GET); no E2E of upload→ingest→search→answer | [QA](QA.md) H1/H2 | — | `apps/api/tests/` |
| P1-13 | Invalid Tailwind classes (`w-18`, `py-0.2`) silently generate no CSS — 9 sites | [UI-UX](UI-UX.md) H2 | [FRONTEND](FRONTEND.md) | `EvidenceViewer.jsx:154` + 8 more |
| P1-14 | Orphaned `/traces/:id` route — reachable from nowhere in the app | [UI-UX](UI-UX.md) H1 | — | `src/App.jsx:76` |

---

## Implementation order

Full sequenced plan in [ROADMAP.md](ROADMAP.md) (effort: **S** hours · **M** 1–2 days · **L** 3–5 days). Summary:

| Phase | Focus | Key items |
|---|---|---|
| **0 — Safety net** (S, do first) | Unblock safe shipping | 0.1 CI test gate (`ci.yml:72-74` → `pytest -v`, patch `test_local_llm.py` first) · 0.2 purge duplicate Python 3.12+3.14 site-packages (~1 GB+, torch ×2) with regrowth guard |
| **1 — Correctness & configuration** (M) | Make model-config work non-placebo | 1.1 config precedence inversion (P0-2) · 1.2 typed verdict module (P0-3) · 1.3 stop hardcoding `"VERIFIED"` for web chunks · 1.4 delete-order fix for orphan vectors · 1.5 upload idempotency (unique `(kb_id, content_hash)` + 409) · 1.6 remove fabricated frontend metrics + LandingPage claims + real API-status badge (P0-8) · 1.7 react-markdown `inline` fix + invalid Tailwind classes |
| **2 — Load reduction** (M–L) | Cut calls, tokens, blocking | 2.1 async Qdrant (P0-4) · 2.2 dedup query embedding (P0-6) · 2.3 wire + rewrite embedding disk cache (P0-5) · 2.4 semantic cache rewrite · 2.5 cache hardware profile · 2.6 CPU work off the loop · 2.7 web "both" cap + SSE pub/sub · 2.8 verifier economics · 2.9 frontend idle load (incl. SSE race guard, P0-7) |
| **3 — Security hardening** (M) | Close the auth gaps | 3.1 SSE auth stream tickets (P1-2) · 3.2 auth-lock `/models` (P1-1) · 3.3 token lifecycle (refresh + revocation) · 3.4 CORS wildcard |
| **4 — Structure & docs debt** (M, can trail) | Structure | 4.1 extract `tracing.py` · 4.2 ingestion out of route layer · 4.3 dossier `contentHash` or spec fix · 4.4 docs/spec alignment · 4.5 recovery strategies · 4.6 duplicate `api.js`, orphaned routes/collections |
| **5 — Test debt** (L, continuous) | Coverage | 5 endpoint modules, one E2E run, minimal frontend tests, a11y pass (UI-UX gap), `--cov` + mypy |

**Quick wins (hours each):** CI gate fix (P0-1) · kill the wasted query embedding (P0-6) · remove fabricated metrics POST (P0-8) · react-markdown `inline` prop (P1-10) · site-packages purge (0.2).

**Guidance from the reports:** fix Phase 0–1 before any model-config work ("without these, model-config work is placebo"); keep the verified strengths list in [ROADMAP.md](ROADMAP.md) §"What NOT to change" as-is; do not add Redis/Celery, bigger models, or horizontal scale before the sync-Qdrant fix is measured.
