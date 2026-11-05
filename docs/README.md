# TRUSTRAG Documentation Index

Welcome to the technical documentation for the TRUSTRAG AI Reliability Workbench. This directory is organized by domain: product specification, architecture, security, evaluation methodology, and deployment.

> **Note:** Point-in-time audit reports (`docs/audits/`, `PHASE_AUDIT_*.md`, `TRUSTRAG_AUDIT_2026-09-21.md`, `SESSION_SUMMARY_2026-09-21.md`, `TRUSTRAG_OPTIMIZATION_PLAN.md`) and the stale agent work-plan (`docs/superpowers/`) were removed during cleanup. Their history remains in git (e.g. `git log -- docs/TRUSTRAG_AUDIT_2026-09-21.md`).

---

## 📁 Documentation Structure

```
docs/
├── README.md                        # Master index (this file)
├── TRUSTRAG_specs.md                # Full product specification (source of truth)
├── ANALYSIS_SERVICE_TEST_GAPS.md    # Uncovered regions of analysis_service.py + prioritized test plan
├── ONBOARDING-TROUBLESHOOTING.md    # Per-OS setup guide + failure table + live verification backlog
├── ROADMAP.md                       # Product vision, milestones, phase tracking
├── PERFORMANCE-GUIDE.md             # Free speed/RAM tuning + MLX on Mac
├── audit/
│   ├── FRONTEND_AUDIT_2026-11-04.md # Frontend architecture, UI/UX overhaul, Brave DevTools inspection
│   ├── FRONTEND_AUDIT_2026-11-01.md # Initial frontend decomposition audit
│   ├── AUDIT_2026-10-03.md          # Engineering audit (critical/needed/later, improvements, dead code)
│   └── AUDIT_2026-10-03_STATUS.md   # Resolution status tracker
├── architecture/
│   ├── architecture.md              # End-to-end system design, MCP tools, LangGraph loop, data flow
│   ├── RAG_ARCHITECTURE.md          # RAG pipeline technical reference
│   └── decision-log.md              # ADRs D-01 through D-33
├── security/
│   ├── security-controls.md         # Auth, anti-IDOR, SSRF, rate limits, headers
│   └── threat-model.md              # STRIDE threat model and mitigations
├── evaluation/
│   ├── methodology.md               # Benchmark dataset, metrics, measured snapshot
│   └── results/                     # Live eval-run JSON (gitignored, local only)
├── deployment/
│   ├── DEPLOYMENT_GUIDE.md          # Cloud production runbook (Pages + GCR + Atlas)
│   └── README.md                    # Env vars, local/Compose setup, pre-prod checklist
```

---

## 📑 Core Sections

### 1. Product & Planning

- [**Specification (`TRUSTRAG_specs.md`)**](TRUSTRAG_specs.md): product definition, engineering principles, stack, architecture, config, ingestion → recovery pipeline, API, testing, acceptance criteria. Read this first before contributing.
- [**Roadmap (`ROADMAP.md`)**](ROADMAP.md): completed phases, pre-deployment checklist, and prioritized upcoming work.
- [**Performance Guide (`PERFORMANCE-GUIDE.md`)**](PERFORMANCE-GUIDE.md): free efficiency changes (config-only speed/RAM wins) plus MLX local inference on Apple Silicon.
- [**Onboarding & Troubleshooting (`ONBOARDING-TROUBLESHOOTING.md`)**](ONBOARDING-TROUBLESHOOTING.md): per-OS setup guide, failure table, live verification backlog.
- [**Frontend Engineering & Design Audit (`audit/FRONTEND_AUDIT_2026-11-04.md`)**](audit/FRONTEND_AUDIT_2026-11-04.md): complete UI/UX overhaul on `ui-redesign` branch: component decomposition, cyber-dark design tokens, Brave DevTools visual inspection, accessible MCP web search switch, and zero ESLint errors.
- [**Engineering Audit (`audit/AUDIT_2026-10-03.md`)**](audit/AUDIT_2026-10-03.md): findings split into CRITICAL / NEEDED / LATER, plus refine-refactor-small-change improvements, dead code, and a remove/add list gated on measurable benefit; constraint verification (NVIDIA-except-CUDA, ONNX-only embeddings/reranker, large-vs-small model parity, offline); and a measured test assessment with 24 named tests to add. Supersedes the 2026-09-28 production pass (history in git).
- [**Analysis Service Test Gaps (`ANALYSIS_SERVICE_TEST_GAPS.md`)**](ANALYSIS_SERVICE_TEST_GAPS.md): line-level map of uncovered regions in `app/services/analysis_service.py` (54% → target 80%+), with concrete test-case recipes.

### 2. Architecture & Design

- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): LangGraph agent loop, MCP tools, hybrid retrieval (dense + sparse RRF), claim decomposition → NLI verification → verdict pipeline.
- [**RAG Reference (`architecture/RAG_ARCHITECTURE.md`)**](architecture/RAG_ARCHITECTURE.md): pipeline flow, LangGraph state, ingestion/retrieval/generation/verification internals, data stores, frontend architecture.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): ADRs covering providers, storage, ports, embeddings (local-only BGE, ONNX), NLI parsing, BM25+IDF, reranker cap, RapidOCR, chunking, citations, claim retrieval, router, lifecycle, recovery, security, observability.
- [**Laya ROI Assessment (`architecture/LAYA_ROI_AUDIT_REPORT.md`)**](architecture/LAYA_ROI_AUDIT_REPORT.md): read-only assessment of typed-decision models for retrieval and recovery.

### 3. Security

- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): JWT, bcrypt, JTI revocation, service-token KB/user binding, login lockout (5/900s), EICAR + best-effort clamd upload AV, 24-test red-team suite.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): assets, STRIDE threats T-01…T-11, mitigations, residual risks, out-of-scope items.
- [**Guardrail Options Review (`security/ONNX_GUARDRAIL_OPTIONS_REVIEW.md`)**](security/ONNX_GUARDRAIL_OPTIONS_REVIEW.md): evidence-gated choice of deterministic defenses now and a future ONNX classifier pilot.

### 4. Evaluation

- [**Methodology (`evaluation/methodology.md`)**](evaluation/methodology.md): experiment configs, metrics, ablation plan, frozen `baseline_v1` dataset, live run procedure, measured snapshot table.

### 5. Deployment

- [**Production Runbook (`deployment/DEPLOYMENT_GUIDE.md`)**](deployment/DEPLOYMENT_GUIDE.md): deploy order (data plane → API → frontend), Render/Railway/Koyeb/Cloud Run, Cloudflare Pages, CORS, smoke test, production gotchas.
- [**Deploy Reference (`deployment/README.md`)**](deployment/README.md): environment variables, local/Compose setup, Atlas + Qdrant Cloud setup, health checks, re-indexing, pre-production checklist, troubleshooting.

---

### 6. Current Verification Snapshot (2026-09-28, `ui-redesign`)

- **Tests**: backend 665 pytest green, frontend 33 Vitest green; `ruff check` + `ruff format --check` clean (CI pins `ruff==0.16.9`); ESLint clean; `vite build` green.
- **CI**: Ubuntu jobs + `cross-platform` smoke (Windows + macOS: backend import/config smoke, frontend lint/test/build), all gated in `ci-gate`.
- **Runtimes**: models run ONNX-only (`onnxruntime` + `transformers` tokenizer; reranker fails closed to RRF when `use_onnx=true`); torch lives in the `local-models` extra for one-time export only. Embedding engine is ONNX-only (no provider choice, no PyTorch at runtime).
- **Stack**: Python 3.11–3.12 (`requires-python >=3.11,<3.13`), Node 22+ (`engines`), per-OS setup in `ONBOARDING-TROUBLESHOOTING.md`.
- **Pending operator runs**: pre-IDF KBs need document re-upload; chunking/normalization change needs re-index; OCR models not pre-warmed; live-model verification (Gemini via `cloud` extra / MLX) + k6 + Playwright e2e — see `ONBOARDING-TROUBLESHOOTING.md §5`.