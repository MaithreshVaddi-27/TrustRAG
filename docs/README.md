# TRUSTRAG Documentation Index

Welcome to the technical documentation for the TRUSTRAG AI Reliability Workbench. This directory is organized by domain: product specification, architecture, security, evaluation methodology, and deployment.

> **Note:** Point-in-time audit reports (`docs/audits/`, `PHASE_AUDIT_*.md`) and the stale agent work-plan (`docs/superpowers/`) were removed during cleanup. Their history remains in git (`git log -- docs/audits docs/PHASE_AUDIT_*.md docs/superpowers`).

---

## 📁 Documentation Structure

```
docs/
├── README.md                        # Master index (this file)
├── TRUSTRAG_specs.md                # Full product specification (source of truth)
├── TRUSTRAG-IMPLEMENTATION-PLAN.md  # Phase-by-phase plan, verified against code
├── TRUSTRAG-UPGRADE-PLAN.md         # Original upgrade plan with per-phase status
├── ROADMAP.md                       # Product vision, milestones, phase tracking
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
- [**Implementation Plan (`TRUSTRAG-IMPLEMENTATION-PLAN.md`)**](TRUSTRAG-IMPLEMENTATION-PLAN.md): phase order, per-phase files/changes/tests, evaluation gates, production risks — verified file-by-file against the repo.
- [**Upgrade Plan (`TRUSTRAG-UPGRADE-PLAN.md`)**](TRUSTRAG-UPGRADE-PLAN.md): original goal-by-phase plan with frozen status notes per phase.
- [**Roadmap (`ROADMAP.md`)**](ROADMAP.md): completed phases, pre-deployment checklist, and prioritized upcoming work.

### 2. Architecture & Design

- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): LangGraph agent loop, MCP tools, hybrid retrieval (dense + sparse RRF), claim decomposition → NLI verification → verdict pipeline.
- [**RAG Reference (`architecture/RAG_ARCHITECTURE.md`)**](architecture/RAG_ARCHITECTURE.md): pipeline flow, LangGraph state, ingestion/retrieval/generation/verification internals, data stores, frontend architecture.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): ADRs covering providers, storage, ports, embeddings (local-only BGE, ONNX), NLI parsing, BM25+IDF, reranker cap, RapidOCR, chunking, citations, claim retrieval, router, lifecycle, recovery, security, observability.

### 3. Security

- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): JWT, bcrypt, JTI revocation, anti-IDOR, SSRF guards, rate limiting, defensive headers, red-team suite.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): assets, STRIDE threats T-01…T-11, mitigations, residual risks, out-of-scope items.

### 4. Evaluation

- [**Methodology (`evaluation/methodology.md`)**](evaluation/methodology.md): experiment configs, metrics, ablation plan, frozen `baseline_v1` dataset, live run procedure, measured snapshot table.

### 5. Deployment

- [**Production Runbook (`deployment/DEPLOYMENT_GUIDE.md`)**](deployment/DEPLOYMENT_GUIDE.md): deploy order (data plane → API → frontend), Render/Railway/Koyeb/Cloud Run, Cloudflare Pages, CORS, smoke test, production gotchas.
- [**Deploy Reference (`deployment/README.md`)**](deployment/README.md): environment variables, local/Compose setup, Atlas + Qdrant Cloud setup, health checks, re-indexing, pre-production checklist, troubleshooting.

---

## Current Stack (`models.yaml` v1.15, verified against code)

- **LLM**: llama.cpp default (`LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M`), Ollama (`gemma3:1b`), Gemini, NVIDIA NIM — selectable per request.
- **Embeddings**: local-only `BAAI/bge-small-en-v1.5` (384d) — `huggingface` (torch, default) or `onnx` (torch-free; export via `scripts/export_bge_onnx.py`).
- **Retrieval**: dense BGE + BM25-TF sparse with Qdrant server-side IDF + RRF (`rrf_k=60`, `fusion_top_k=20` enforced); `sparse_top_k: 0` disables the sparse leg (current default — set `20` for full hybrid); deterministic router (simple/temporal/comparison/complex, fan-out ≤3); reranker off by default (depth cap `top_k: 20`, needs the `local-models` extra).
- **Ingestion**: newline-preserving normalization; `chunking_strategy` (`sliding_window` default, 512/64); RapidOCR-ONNX per-page fallback (default on; models download to `~/.onnx` on first scanned page — pre-warm on deploy).
- **Verification**: fused decompose+verify fast path with classic two-step fallback; tolerant parsing of small-model near-miss JSON; inline `[Segment N]` citations with invalid-ref strip; NEUTRAL-only targeted claim retrieval (≤3/analysis).
- **Lifecycle**: KB snapshots + rollback (returns a NEW live id; 409 on vector-less snapshots); deletes purge Mongo + Qdrant.
- **Recovery**: diagnose-then-act (retrieval→rewrite, coverage/conflict→expand, verification/generation→regenerate), ≤2 attempts, token (2000) + latency (180s) budgets, abstain on exhaustion.
- **Security**: JWT `iss`/`aud` on both token types, JTI revocation, service-token KB/user binding, login lockout (5/900s), EICAR + best-effort clamd upload AV, 24-test red-team suite.
- **Observability**: public `GET /api/v1/metrics` (dependency-free Prometheus exposition), pre-request `max_input_tokens` enforcement (422, kill-switchable), per-analysis token accounting; k6 covers `/metrics` + `/analyses` reads.
- **Local LLM server**: `./scripts/start_local_llm.sh` (auto GPU offload + KV budget) or `ollama serve`.
- **Tests**: backend 383 collected, frontend 22 Vitest + 2 Playwright E2E; `ruff check` + `format` clean (verified 2026-09-20).
- **Pending operator runs**: reranker-threshold calibration from Hybrid-vs-Hybrid+Rerank ablation; pre-IDF KBs need document re-upload; chunking/normalization change needs re-index; OCR models not pre-warmed.
