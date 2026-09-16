# TRUSTRAG Documentation Index

Welcome to the technical documentation for the TRUSTRAG AI Reliability Workbench. This directory is organized by domain: architecture, security, quality audits, evaluation methodology, and deployment.

---

## 📁 Documentation Structure

```
docs/
├── README.md                  # Master index (this file)
├── TRUSTRAG_specs.md          # Full product specification
├── ROADMAP.md                 # Product vision, milestones, phase tracking
├── IMPLEMENTATION_STATUS_2026-09-11.md  # Current implementation status & progress
├── architecture/
│   ├── architecture.md        # End-to-end system design, MCP tools, LangGraph loop, data flow
│   └── decision-log.md        # ADRs D-01 through D-22 (incl. ONNX embeddings, tolerant NLI)
├── audits/
│   └── 2026-09-11_unified_senior_audit.md  # Canonical audit (supersedes all prior audits; history in git)
├── security/
│   ├── security-controls.md   # Auth, anti-IDOR, SSRF, rate limits, headers
│   └── threat-model.md        # STRIDE threat model and mitigations
├── evaluation/
│   └── methodology.md         # Benchmark dataset and reliability metrics
├── deployment/
│   ├── DEPLOYMENT_GUIDE.md    # Cloudflare Pages + Google Cloud Run + MongoDB Atlas
│   └── README.md              # Docker Compose / local deployment runbook
```

---

## 📑 Core Sections

### 1. Architecture & Design
- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): LangGraph agent loop, MCP tools, hybrid retrieval (dense + sparse RRF), claim decomposition → NLI verification → verdict pipeline.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): Architectural Decision Records covering technology choices, storage layers, and code quality decisions (D-21 ONNX embeddings, D-22 tolerant NLI parsing).

### 2. Audits & Implementation Status
- [**2026-09-11 — Unified Senior Audit**](audits/2026-09-11_unified_senior_audit.md): **Canonical audit** — multi-role review (frontend, backend, AI/ML, security, optimization, testing) with Apple-design compliance, ultra-low RAM plan, and 2-day vs >2-day upgrade split. Supersedes all prior audits (history preserved in git).
- [**Implementation Status (`IMPLEMENTATION_STATUS_2026-09-11.md`)**](IMPLEMENTATION_STATUS_2026-09-11.md): What was fixed, current test state (backend 219/219, frontend 22/22), and remaining work. Covers the ≤2-day fixes, ONNX runtime, tolerant-NLI + fusion hardening, CI repairs, offline-warning and probe hardening, and the push-readiness passes.

### 3. Security
- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): JWT, bcrypt, anti-IDOR, SSRF guards, rate limiting, defensive headers.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): STRIDE analysis and countermeasures.

### 4. Evaluation
- [**Methodology (`evaluation/methodology.md`)**](evaluation/methodology.md): datasets and reliability metrics.

### 5. Deployment
- [**Production Deployment (`deployment/DEPLOYMENT_GUIDE.md`)**](deployment/DEPLOYMENT_GUIDE.md): Cloudflare Pages, GCR, MongoDB Atlas, Qdrant Cloud.
- [**Local/Compose Deployment (`deployment/README.md`)**](deployment/README.md): Docker Compose and local run instructions.

---

## Current Stack (2026-09-12)

- **LLM**: llama.cpp (local, default: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M`), Ollama (default: `gemma3:1b`), Gemini, NVIDIA NIM — selectable per request.
- **Embeddings**: BGE-small-en-v1.5 (local, 384d) — HuggingFace/torch by default, **ONNX Runtime** (`EMBEDDING_PROVIDER=onnx`, export via `scripts/export_bge_onnx.py`) for torch-free ultra-low RAM.
- **Retrieval**: Qdrant (embedded local or cloud) + sparse BM25 + RRF; reranker runs on detected device (Metal/CUDA/CPU).
- **Verification**: Batch NLI + per-claim fallback with tolerant parsing of small-model near-miss JSON (VERIFIED→SUPPORTED aliasing, segment coercion).
- **Local LLM server**: start via `./scripts/start_local_llm.sh` (auto GPU offload + KV budget).
- **Tests**: backend 219/219, frontend 22/22 + lint + build; ruff check + format clean.
