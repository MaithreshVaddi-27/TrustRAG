# TRUSTRAG Documentation Index

Welcome to the technical documentation for the TRUSTRAG AI Reliability Workbench. This directory is organized by domain: product specification, architecture, security, evaluation, backend engineering, and design.

> **Note:** Point-in-time audit reports (`docs/audit/`, `PHASE_AUDIT_*.md`, `TRUSTRAG_AUDIT_2026-09-21.md`, `SESSION_SUMMARY_2026-09-21.md`, `TRUSTRAG_OPTIMIZATION_PLAN.md`) and the stale agent work-plan (`docs/superpowers/`) were removed during cleanup. Their history remains in git (e.g. `git log -- docs/TRUSTRAG_AUDIT_2026-09-21.md`).
>
> The backend audit and every change made against it now live in one **living log** — [`backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md`](backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md) — rather than in a series of point-in-time reports that go stale. It is updated after every change.

---

## 📁 Documentation Structure

```
docs/
├── README.md                          # Master index (this file)
├── TRUSTRAG_specs.md                  # Full product specification (source of truth)
├── EXECUTION_PLAN.md                  # Implementation plan and phase history
├── ROADMAP.md                         # Product vision, milestones, phase tracking
├── PERFORMANCE-GUIDE.md               # Free speed/RAM tuning + MLX on Mac
├── ONBOARDING-TROUBLESHOOTING.md      # Per-OS setup guide + failure table + live verification backlog
├── ANALYSIS_SERVICE_TEST_GAPS.md     # Measured gaps in app/services/** + test-case recipes
├── backend/                           # Backend engineering log (living) + benchmark artifacts
│   ├── BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md  # Audit → changes → measurements → decisions
│   ├── BACKEND_AUDIT_B1.md            # The audit that started the programme
│   └── *.json                         # Benchmark / quality / accuracy / resilience results
├── architecture/
│   ├── architecture.md                # End-to-end system design, MCP tools, LangGraph loop, data flow
│   ├── RAG_ARCHITECTURE.md            # RAG pipeline technical reference
│   ├── decision-log.md                # ADRs D-01 onward
│   ├── PRODUCTION_CONFIG_GUIDE.md     # Every models.yaml key, what it does, what to change
│   ├── MULTI_MODEL_ARCHITECTURE_REVIEW_2026-11-05.md
│   └── LAYA_ROI_AUDIT_REPORT.md       # Read-only assessment of typed-decision models
├── security/
│   ├── security-controls.md           # Auth, anti-IDOR, SSRF, rate limits, headers
│   ├── threat-model.md                # STRIDE threat model and mitigations
│   └── ONNX_GUARDRAIL_OPTIONS_REVIEW.md
├── evaluation/
│   ├── methodology.md                 # Benchmark dataset, metrics, ablation plan, run procedure
│   ├── MODEL_BENCHMARK_REPORT.md      # Local model inventory + RAG-task notes
│   ├── FUTURE_IMPROVEMENTS.md         # Deferred items
│   └── results/                       # Live eval-run JSON (gitignored, local only)
├── design/
│   ├── dark-luxury/                   # The design system: foundations → tokens → components → pages
│   └── *.svg                          # Palette, typography and layout references
├── deployment/
│   ├── DEPLOYMENT_GUIDE.md            # Cloud production runbook (Pages + GCR + Atlas)
│   └── README.md                      # Env vars, local/Compose setup, Atlas + Qdrant Cloud setup
├── PPT/                               # Review deck
└── Documentation/                     # Exported PDF
```

---

## 📑 Core Sections

### 1. Product & Planning

- [**Specification (`TRUSTRAG_specs.md`)**](TRUSTRAG_specs.md): product definition, engineering principles, stack, architecture, config, ingestion → recovery pipeline, API, testing, acceptance criteria. Read this first before contributing.
- [**Execution Plan (`EXECUTION_PLAN.md`)**](EXECUTION_PLAN.md): the implementation plan and what was actually built.
- [**Roadmap (`ROADMAP.md`)**](ROADMAP.md): completed phases, pre-deployment checklist, and prioritized upcoming work.
- [**Performance Guide (`PERFORMANCE-GUIDE.md`)](PERFORMANCE-GUIDE.md): free efficiency changes (config-only speed/RAM wins) plus MLX local inference on Apple Silicon.
- [**Onboarding & Troubleshooting (`ONBOARDING-TROUBLESHOOTING.md`)](ONBOARDING-TROUBLESHOOTING.md): per-OS setup guide (macOS / Linux / Windows), failure table, live verification backlog.
- [**Service-Layer Test Gaps (`ANALYSIS_SERVICE_TEST_GAPS.md`)**](ANALYSIS_SERVICE_TEST_GAPS.md): the measured gaps in `app/services/**` — the SSE pub/sub, the user-level claim/evidence vault, the auth service and the knowledge-base snapshots — with concrete test-case recipes.

### 2. Backend Engineering

- [**Backend Changelog & Recommendations (`backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md`)**](backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md): **the living engineering log.** The audit findings, every upgrade with its measured before/after, the degradations that were accepted, the refinements, the open decisions and the blockers. Updated after every change.
- [**Backend Audit B1 (`backend/BACKEND_AUDIT_B1.md`)**](backend/BACKEND_AUDIT_B1.md): the reproduced findings that started the programme.
- **Benchmark artifacts** (`backend/*.json`): API latency, retrieval quality, RAG accuracy across six model configurations, resilience, and the frontend↔backend integration check.

### 3. Architecture & Design

- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): LangGraph agent loop, MCP tools, hybrid retrieval (dense + sparse RRF), claim decomposition → NLI verification → verdict pipeline.
- [**RAG Reference (`architecture/RAG_ARCHITECTURE.md`)**](architecture/RAG_ARCHITECTURE.md): pipeline flow, LangGraph state, ingestion/retrieval/generation/verification internals, data stores, frontend architecture.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): ADRs covering providers, storage, ports, embeddings (local-only BGE, ONNX), NLI parsing, BM25+IDF, reranker cap, RapidOCR, chunking, citations, claim retrieval, router, lifecycle, recovery, security, observability.
- [**Production Config Guide (`architecture/PRODUCTION_CONFIG_GUIDE.md`)**](architecture/PRODUCTION_CONFIG_GUIDE.md): every `models.yaml` key, what it does, and when to change it.
- [**Multi-Model Architecture Review (`architecture/MULTI_MODEL_ARCHITECTURE_REVIEW_2026-11-05.md`)**](architecture/MULTI_MODEL_ARCHITECTURE_REVIEW_2026-11-05.md).
- [**Laya ROI Assessment (`architecture/LAYA_ROI_AUDIT_REPORT.md`)**](architecture/LAYA_ROI_AUDIT_REPORT.md): read-only assessment of typed-decision models for retrieval and recovery.

### 4. Security

- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): JWT, bcrypt, JTI revocation, service-token KB/user binding, login lockout, EICAR + best-effort clamd upload AV.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): assets, STRIDE threats, mitigations, residual risks, out-of-scope items.
- [**Guardrail Options Review (`security/ONNX_GUARDRAIL_OPTIONS_REVIEW.md`)**](security/ONNX_GUARDRAIL_OPTIONS_REVIEW.md): evidence-gated choice of deterministic defenses now and a future ONNX classifier pilot.

### 5. Evaluation

- [**Methodology (`evaluation/methodology.md`)**](evaluation/methodology.md): experiment configs, metrics, ablation plan, frozen `baseline_v1` dataset, live run procedure, measured snapshot table.
- [**Model Benchmark Report (`evaluation/MODEL_BENCHMARK_REPORT.md`)**](evaluation/MODEL_BENCHMARK_REPORT.md): the models discovered on the dev host, with their sizes and their suitability for interactive serving.
- [**Future Improvements (`evaluation/FUTURE_IMPROVEMENTS.md`)**](evaluation/FUTURE_IMPROVEMENTS.md): the deferred items, and why they are deferred.

The phase reports that once lived here (`PHASE0_FIXTURE_BASELINE_*`,
`POST_IMPLEMENTATION_QUALITY_AUDIT_*`, `RELIABILITY_PHASE1_*`) were removed in
the documentation cleanup: each was a point-in-time snapshot of the retired
27-query baseline, and the abstention audit's Critical findings were closed
in B2.1–B4 (the rationale for the `VERIFICATION_UNAVAILABLE` diagnosis now
lives in `app/rag/verification/verdict.py`). Their history remains in git —
`git log -- docs/evaluation/`.

### 6. Design

- [**Design system (`design/dark-luxury/`)**](design/dark-luxury/README.md): foundations → tokens → components → patterns → accessibility → voice → migration → verification → pages. The implementation-side companion is [`apps/web/DESIGN.md`](../apps/web/DESIGN.md).

### 7. Deployment

- [**Production Runbook (`deployment/DEPLOYMENT_GUIDE.md`)**](deployment/DEPLOYMENT_GUIDE.md): deploy order (data plane → API → frontend), Render/Railway/Koyeb/Cloud Run, Cloudflare Pages, CORS, smoke test, production gotchas.
- [**Deploy Reference (`deployment/README.md`)**](deployment/README.md): environment variables, local/Compose setup, Atlas + Qdrant Cloud setup, health checks, re-indexing, pre-production checklist, troubleshooting.

---

### 8. Current Verification Snapshot

Measured on `feature/trustrag-refined`; the full numbers and the
method behind them are in
[`backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md`](backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md).

- **Backend tests**: **817 passed** on Python 3.12, **813 passed + 4 skipped** on Python 3.11 (the four skips are the opt-in `cloud` extra — `tavily` and `langchain-google-genai` are not installed). Coverage **80.4 %** (gate 78 %).
- **Frontend**: **82 Vitest tests** across 17 files, ESLint clean (`--max-warnings 0`), Vite build green.
- **CI**: Ubuntu jobs + a `cross-platform` smoke matrix (Windows + macOS: backend import/config smoke, frontend lint/test/build), plus Playwright E2E and a k6 load smoke — all green.
- **Lint**: `ruff check app/ tests/` and `ruff format --check app/ tests/` clean on the pinned `ruff==0.16.9`; the mypy ratchet reports **no new** type errors against the committed ceiling.
- **Integration**: every frontend API call (25) matches a backend route (39) — 0 missing — and the user flow answers correctly both directly and through the frontend's proxy.
- **Runtimes**: models run ONNX-only (`onnxruntime` + `transformers` tokenizer; the reranker fails closed to RRF when `use_onnx=true`); torch lives in the `local-models` extra for one-time export only.
- **Stack**: Python 3.11–3.12 (`requires-python >=3.11,<3.13`), Node 22+ (`engines`), per-OS setup in `ONBOARDING-TROUBLESHOOTING.md`.
- **Pending operator runs**: pre-IDF knowledge bases need a document re-upload; the chunking/normalization change needs a re-index; OCR models are not pre-warmed; live-model verification (Gemini via the `cloud` extra / MLX) — see `ONBOARDING-TROUBLESHOOTING.md §5`.
