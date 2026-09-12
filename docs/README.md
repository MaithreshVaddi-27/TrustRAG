# TRUSTRAG Documentation Index

Welcome to the technical documentation for the TRUSTRAG AI Reliability Workbench. This directory is organized by domain: architecture, security, quality audits, evaluation methodology, and deployment.

---

## 📁 Documentation Structure

```
docs/
├── README.md                  # Master index (this file)
├── TRUSTRAG_specs.md          # Full product specification
├── ROADMAP.md                 # Product vision, milestones, phase tracking
├── AUDIT_REPORT.md            # Aggregated audit report
├── IMPLEMENTATION_STATUS_2026-09-11.md  # Current implementation status & progress
├── architecture/
│   ├── architecture.md        # End-to-end system design, MCP tools, LangGraph loop, data flow
│   └── decision-log.md        # ADRs D-01 through D-20
├── audits/
│   ├── 2026-09-11_unified_senior_audit.md  # Latest: multi-role senior audit (frontend/backend/AI/security/opt/test)
│   ├── 2026-09-10_senior_backend_ai_security_optimization_audit.md
│   ├── 2026-09-08_model_discovery_and_hardening_audit.md
│   ├── 2026-09-07_embedding_removal_fix_audit.md
│   ├── 2026-09-07_backend_rag_correctness_audit.md
│   ├── 2026-09-07_performance_local_llm_audit.md
│   ├── 2026-09-07_security_audit.md
│   ├── 2026-09-07_work_status_and_next_steps.md
│   ├── 2026-09-06_full_stack_working_now_audit.md
│   ├── comprehensive_system_audit.md
│   └── SENIOR_AUDIT.md
├── security/
│   ├── security-controls.md   # Auth, anti-IDOR, SSRF, rate limits, headers
│   └── threat-model.md        # STRIDE threat model and mitigations
├── evaluation/
│   └── methodology.md         # Benchmark dataset and reliability metrics
├── deployment/
│   ├── DEPLOYMENT_GUIDE.md    # Cloudflare Pages + Google Cloud Run + MongoDB Atlas
│   └── README.md              # Docker Compose / local deployment runbook
└── ui-redesign-audit/         # Historical frontend audit notes (archived reference)
```

---

## 📑 Core Sections

### 1. Architecture & Design
- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): LangGraph agent loop, MCP tools, hybrid retrieval (dense + sparse RRF), claim decomposition → NLI verification → verdict pipeline.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): Architectural Decision Records covering technology choices, storage layers, and code quality decisions.

### 2. Audits (most current on top)
- [**2026-09-11 — Unified Senior Audit**](audits/2026-09-11_unified_senior_audit.md): **Latest** — Multi-role senior audit (Senior Frontend/Backend/AI-ML/Security/Optimization/Testing) with Apple-design frontend compliance, ultra-low RAM backend optimization, ONNX BGE embeddings, security hardening. Supersedes all prior audits.
- [**2026-09-10 — Senior Backend AI Security & Optimization Audit**](audits/2026-09-10_senior_backend_ai_security_optimization_audit.md): Production-readiness pass — chunk quality, RAM/LLM tuning, security hardening, dead code removal.
- [**2026-09-08 — Model Discovery & Hardening Audit**](audits/2026-09-08_model_discovery_and_hardening_audit.md): Auto model discovery, registry hardening, provider-default fallback.
- [**2026-09-07 — Embedding Removal & Fix Pass**](audits/2026-09-07_embedding_removal_fix_audit.md): Ollama/llama.cpp embeddings removed (LLM-only), OCC-RAG model cutover, degenerate-output guards, timeout + recovery-loop fixes, hardware-aware launcher.
- [**2026-09-07 — Backend RAG Correctness Audit**](audits/2026-09-07_backend_rag_correctness_audit.md): RAG pipeline correctness, chunk quality, sentence-split backstop.
- [**2026-09-07 — Performance & Local LLM Audit**](audits/2026-09-07_performance_local_llm_audit.md): RAM tuning, KV-cache flags, single-flight LLM semaphore.
- [**2026-09-07 — Security Audit**](audits/2026-09-07_security_audit.md): JWT ownership checks, SSRF guards, input sanitization.
- [**2026-09-07 — Work Status & Next Steps**](audits/2026-09-07_work_status_and_next_steps.md): Status summary and prioritized task list.
- [**2026-09-06 — Full-Stack "Working Now" Audit**](audits/2026-09-06_full_stack_working_now_audit.md): Baseline boot fixes and local-model path validation.
- [**Comprehensive System Audit (`audits/comprehensive_system_audit.md`)**](audits/comprehensive_system_audit.md): Wide multi-domain review.
- [**Senior Audit (`audits/SENIOR_AUDIT.md`)**](audits/SENIOR_AUDIT.md): Senior-level review sign-off.

### 3. Security
- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): JWT, bcrypt, anti-IDOR, SSRF guards, rate limiting, defensive headers.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): STRIDE analysis and countermeasures.

### 4. Evaluation
- [**Methodology (`evaluation/methodology.md`)**](evaluation/methodology.md): datasets and reliability metrics.

### 5. Deployment
- [**Production Deployment (`deployment/DEPLOYMENT_GUIDE.md`)**](deployment/DEPLOYMENT_GUIDE.md): Cloudflare Pages, GCR, MongoDB Atlas, Qdrant Cloud.
- [**Local/Compose Deployment (`deployment/README.md`)**](deployment/README.md): Docker Compose and local run instructions.

---

## Current Stack (2026-09-11)

- **LLM**: llama.cpp (local, default: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M`), Ollama (default: `gemma3:1b`), Gemini, NVIDIA NIM — selectable per request.
- **Embeddings**: HuggingFace BGE (local, 384d) by default; **ONNX Runtime** (`EMBEDDING_PROVIDER=onnx`) for torch-free ultra-low RAM; Gemini/NVIDIA available via env.
- **Retrieval**: Qdrant (embedded local or cloud) + sparse BM25 + RRF; reranker runs on detected device (Metal/CUDA/CPU).
- **Local LLM server**: start via `./scripts/start_local_llm.sh` (auto GPU offload + KV budget).
