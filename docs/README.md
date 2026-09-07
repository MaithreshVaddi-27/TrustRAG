# TRUSTRAG Documentation Index

Welcome to the technical documentation for the TRUSTRAG AI Reliability Workbench. This directory is organized by domain: architecture, security, quality audits, evaluation methodology, and deployment.

---

## 📁 Documentation Structure

```
docs/
├── README.md                  # Master index (this file)
├── ROADMAP.md                 # Product vision, milestones, phase tracking
├── architecture/
│   ├── architecture.md        # End-to-end system design, MCP tools, LangGraph loop, data flow
│   └── decision-log.md        # ADRs D-01 through D-17
├── audits/
│   ├── 2026-09-07_embedding_removal_fix_audit.md  # Latest: llama.cpp-only embeddings cutover, OCC model, smart recovery
│   ├── 2026-09-06_full_stack_working_now_audit.md # Day-1 boot fixes + local model path
│   ├── comprehensive_system_audit.md              # Baseline systems audit
│   └── SENIOR_AUDIT.md                            # Senior audit sign-off
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
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): Architectural Decision Records covering technology choices and storage layers.

### 2. Audits (most current on top)
- [**2026-09-07 — Embedding Removal & Fix Pass**](audits/2026-09-07_embedding_removal_fix_audit.md): Ollama/llama.cpp embeddings removed (LLM-only), OCC-RAG model cutover, degenerate-output guards, timeout + recovery-loop fixes, hardware-aware launcher.
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

## Current Stack (2026-09-07)

- **LLM**: llama.cpp (local, `occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M`), Ollama (installed: `granite4.2:3b-q4_K_M`, `gemma3:1b`), Gemini, NVIDIA NIM — selectable per request.
- **Embeddings**: HuggingFace BGE (local, 384d) by default; Gemini/NVIDIA available via env.
- **Retrieval**: Qdrant (embedded local or cloud) + sparse BM25 + RRF; reranker runs on detected device (Metal/CUDA/CPU).
- **Local LLM server**: start via `./scripts/start_local_llm.sh` (auto GPU offload + KV budget).
