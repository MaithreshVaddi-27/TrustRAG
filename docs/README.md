# TRUSTRAG Documentation Index

Welcome to the technical documentation for the TRUSTRAG AI Reliability Workbench.
This directory holds only canonical, maintained documents: the product
specification, architecture and decision records, security controls, evaluation
method, the living backend log, and the design system. Point-in-time audits,
superseded plans, archived concept boards and review reports have been removed;
their history remains in git.

> The backend audit and every change made against it live in one **living log**:
> [`backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md`](backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md).
> The JSON files under `backend/` are **frozen evidence snapshots** cited by that
> log, not disposable output. Regenerate them deliberately with the scripts in
> `apps/api/scripts/`; new local runs should stay out of the tracked tree.

---

## Running locally (all platforms)

```bash
python scripts/serve.py doctor   # prerequisites + health
python scripts/serve.py serve    # MongoDB, Ollama, API and Vite; Ctrl+C stops all
python scripts/serve.py status
python scripts/serve.py stop
```

Windows: `powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 serve`.
The launcher is documented in [`scripts/README.md`](../scripts/README.md) and
the per-OS troubleshooting table in
[`ONBOARDING-TROUBLESHOOTING.md`](ONBOARDING-TROUBLESHOOTING.md).

---

## Documentation structure

```
docs/
├── README.md                          # Master index (this file)
├── TRUSTRAG_specs.md                  # Full product specification (source of truth)
├── TRUSTRAG_PROJECT_GUIDE.md          # Code-first walkthrough of the whole product
├── TRUSTRAG_RAG_DEEP_DIVE.md          # Beginner-to-mentor guide to the RAG subsystem
├── ROADMAP.md                         # Product vision, milestones, phase tracking
├── PERFORMANCE-GUIDE.md               # Free speed/RAM tuning + MLX on Mac
├── ONBOARDING-TROUBLESHOOTING.md      # Per-OS setup guide + failure table
├── backend/
│   ├── BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md  # Living engineering log
│   └── *.json                         # Frozen benchmark / quality / accuracy snapshots
├── architecture/
│   ├── architecture.md                # End-to-end system design, MCP tools, LangGraph loop
│   ├── RAG_ARCHITECTURE.md            # RAG pipeline technical reference
│   ├── decision-log.md                # ADRs D-01 onward
│   └── PRODUCTION_CONFIG_GUIDE.md     # Every models.yaml key, what it does
├── security/
│   ├── security-controls.md           # Auth, anti-IDOR, SSRF, rate limits, headers
│   └── threat-model.md                # STRIDE threat model and mitigations
├── evaluation/
│   ├── methodology.md                 # Dataset, metrics, ablation plan, run procedure
│   └── results/                       # Live eval-run JSON (gitignored, local only)
├── design/
│   ├── README.md                      # Current design decision record
│   ├── dark-luxury/                   # Canonical design system
│   ├── UI_RE_DEEP_AUDIT_2026-11-25.md # Verification of the shipped UI
│   └── UI_RE_DEEP_PLAN_2026-11-25.md  # Executed cleanup plan and verification
└── deployment/
    ├── DEPLOYMENT_GUIDE.md            # Cloud production runbook
    └── README.md                      # Env vars, local/Compose setup
```

---

## Core sections

### Product & planning

- [**Specification**](TRUSTRAG_specs.md) — product definition, architecture,
  configuration, ingestion → recovery pipeline, API, testing and acceptance
  criteria. Read this first before contributing.
- [**Roadmap**](ROADMAP.md) — completed phases and prioritized upcoming work.
- [**Performance Guide**](PERFORMANCE-GUIDE.md) — config-only speed/RAM wins and
  MLX local inference on Apple Silicon.
- [**Onboarding & Troubleshooting**](ONBOARDING-TROUBLESHOOTING.md) — per-OS setup,
  failure table and live verification backlog.
- [**Project Guide**](TRUSTRAG_PROJECT_GUIDE.md) — code-first walkthrough for
  someone who did not build the system.
- [**RAG Deep Dive**](TRUSTRAG_RAG_DEEP_DIVE.md) — beginner-to-mentor guide to
  ingestion, retrieval, generation, verification and recovery.

### Backend engineering

- [**Backend Changelog & Recommendations**](backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md)
  — the living engineering log: findings, measured before/after, accepted
  degradations, refinements and open decisions.
- **Benchmark artifacts** (`backend/*.json`) — frozen API latency, retrieval
  quality, RAG accuracy, resilience and integration snapshots cited by the log.

### Architecture

- [**System Architecture**](architecture/architecture.md) — LangGraph agent loop,
  MCP tools, hybrid retrieval, claim decomposition → NLI → verdict.
- [**RAG Reference**](architecture/RAG_ARCHITECTURE.md) — pipeline flow, state,
  ingestion/retrieval/generation/verification internals and data stores.
- [**Decision Log**](architecture/decision-log.md) — ADRs covering providers,
  storage, ports, embeddings, NLI, reranking, chunking, recovery and security.
- [**Production Config Guide**](architecture/PRODUCTION_CONFIG_GUIDE.md) — every
  `models.yaml` key, what it does, and when to change it.

### Security

- [**Security Controls**](security/security-controls.md) — auth, anti-IDOR, SSRF,
  rate limits, headers and upload scanning.
- [**Threat Model**](security/threat-model.md) — assets, STRIDE threats,
  mitigations and residual risks.

### Evaluation

- [**Methodology**](evaluation/methodology.md) — experiment configs, metrics,
  ablation plan, frozen `baseline_v1` dataset and live run procedure.

### Design

- [**Design system**](design/dark-luxury/README.md) — Obsidian / Chrome Silver /
  Laser Crimson foundations, tokens, components, patterns, accessibility, voice,
  verification and pages. The shipped implementation is
  [`apps/web/DESIGN.md`](../apps/web/DESIGN.md).
- [**UI re-deep audit**](design/UI_RE_DEEP_AUDIT_2026-11-25.md) — verification of
  the shipped UI, top findings and the full evidence register.
- [**UI re-deep plan**](design/UI_RE_DEEP_PLAN_2026-11-25.md) — the executed
  cleanup plan, implementation log and final verification.

### Deployment

- [**Production Runbook**](deployment/DEPLOYMENT_GUIDE.md) — deploy order,
  providers, CORS, smoke test and production gotchas.
- [**Deploy Reference**](deployment/README.md) — environment variables, local and
  Compose setup, health checks, re-indexing and pre-production checklist.

---

## Verification snapshot

Measured on `feature/trustrag-refined`; full numbers and method are in the
[backend living log](backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md).

- **Backend tests**: 870 passed. Coverage 80.66 % (gate 78 %).
- **Frontend**: 85 Vitest tests across 18 files, ESLint clean, Vite build green.
- **UI**: Lighthouse desktop and mobile 100 / 100 / 100 / 100 on the landing
  page; no console errors, no overflow, no idle animations; reduced motion
  resolves to static states.
- **CI**: Ubuntu jobs plus a Windows/macOS smoke matrix, Playwright E2E and a k6
  load smoke.
- **Integration**: every frontend API call matches a backend route — 0 missing —
  verified by `apps/api/scripts/verify/validate_integration.py`.
- **Resilience**: concurrency, rate limit, provider outage and database outage
  all behave — verified by `apps/api/scripts/verify/validate_resilience.py`.
- **Stack**: Python 3.11–3.12, Node 22+, ONNX-only local model runtime.
