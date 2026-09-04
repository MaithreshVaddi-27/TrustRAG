# TrustRAG — Production AI Reliability Workbench

> **Retrieve. Verify. Diagnose. Recover.**  
> An open-source, multi-tenant AI reliability platform that detects hallucinations, audits evidence integrity, decomposes assertions into atomic claims, and self-heals low-confidence RAG responses using an adaptive LangGraph loop.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Offline-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![llama.cpp](https://img.shields.io/badge/llama.cpp-GGUF_Server-orange)](https://github.com/ggerganov/llama.cpp)
[![Tests](https://img.shields.io/badge/Tests-103%20Passing-brightgreen)](apps/api/tests)
[![Bandit](https://img.shields.io/badge/Bandit%20SAST-0%20Issues-brightgreen)](docs/audits/final-audit-report.md)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

### 🔗 Local Workbench Quick Links (Branch: `ui-redesign`)

| Service | Local URL | Description |
|---|---|---|
| 🌐 **Frontend Workbench** | **[http://localhost:5173](http://localhost:5173)** | AI Reliability Workbench & Local Model Playground |
| ⚡ **Backend REST API** | **[http://localhost:8080](http://localhost:8080)** | FastAPI Agentic RAG Engine with Local Model Support |
| 📖 **Interactive API Docs** | **[http://localhost:8080/docs](http://localhost:8080/docs)** | Swagger OpenAPI interactive documentation & test runner |
| 🩺 **System Health & Hardware** | **[http://localhost:8080/api/v1/health](http://localhost:8080/api/v1/health)** | Live hardware profiling (Metal/CUDA/CPU), memory guard & telemetry |

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Self-Healing Reliability Loop](#-self-healing-reliability-loop)
- [System Architecture](#-system-architecture)
- [Ultra-Premium Dark Workbench UI](#-ultra-premium-dark-workbench-ui)
- [Deployment & Production Readiness](#-deployment--production-readiness)
- [Core Engineering Capabilities](#-core-engineering-capabilities)
  - [1. Multi-Tenant User Isolation & Anti-IDOR](#1-multi-tenant-user-isolation--anti-idor)
  - [2. Rule-Based Stemming & Document Zoning](#2-rule-based-stemming--document-zoning)
  - [3. Hybrid Retrieval with RRF](#3-hybrid-retrieval-with-rrf)
  - [4. Batch NLI Claim Verification](#4-batch-nli-claim-verification)
  - [5. SHA-256 Provenance & Temporal Filtering](#5-sha-256-provenance--temporal-filtering)
  - [6. Adaptive LangGraph Recovery Loop](#6-adaptive-langgraph-recovery-loop)
  - [7. Ultra-Low RAM & On-Disk Storage Architecture](#7-ultra-low-ram--on-disk-storage-architecture)
  - [8. Universal Model Context Protocol (MCP) Server](#8-universal-model-context-protocol-mcp-server)
  - [9. Multi-Provider AI (Gemini + NVIDIA NIM)](#9-multi-provider-ai-gemini--nvidia-nim)
  - [10. Local SOTA Embeddings (BAAI/bge-small-en-v1.5)](#10-local-sota-embeddings-baaibge-small-en-v15)
  - [11. Live Web Search Grounding via MCP (Tavily + DuckDuckGo)](#11-live-web-search-grounding-via-mcp-tavily--duckduckgo)
  - [12. Enterprise Security Hardening & SSRF Defense](#12-enterprise-security-hardening--ssrf-defense)
  - [13. 100% Private Local LLMs (Ollama & llama.cpp)](#13-100-private-local-llms-ollama--llamacpp)
  - [14. Native CLI Model Discovery (ollama list & llama-server)](#14-native-cli-model-discovery-ollama-list--llama-server)
  - [15. Multi-Dimensional Vector Embeddings & L2 Normalization](#15-multi-dimensional-vector-embeddings--l2-normalization)
- [Technology Stack](#-technology-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#1-environment-configuration)
  - [Option A: Running Locally with Native Resources (Recommended)](#option-a-running-locally-with-native-resources-recommended)
  - [Option B: Running with Docker Compose](#option-b-running-with-docker-compose)
  - [Zero-API-Key Local Mode (DuckDuckGo + Local BGE)](#zero-api-key-local-mode-duckduckgo--local-bge)
- [End-to-End Walkthrough via CLI](#-end-to-end-walkthrough-via-cli)
- [API Reference](#-api-reference)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [Documentation Index](#-documentation-index)
- [License](#-license)

---

## 🎯 Overview

Standard RAG (Retrieval-Augmented Generation) systems fail silently. When dense embeddings retrieve tangential context or LLMs extrapolate unsupported claims, traditional applications present hallucinations as fact without warning or auditability.

**TRUSTRAG transforms RAG into a verifiable, closed-loop reliability pipeline:**
1. **Decomposes** generated responses into verifiable, atomic claims.
2. **Validates** each assertion against retrieved context using high-throughput batch Natural Language Inference (NLI).
3. **Audits** underlying chunks against cryptographic SHA-256 source hashes and temporal validity windows (`Effective from: YYYY-MM-DD`).
4. **Self-Heals** when confidence is low — rewriting queries and expanding search parameters via an adaptive LangGraph state machine before choosing between a **Trusted Grounded Answer** or a **Safe Abstention**.

---

## 🔄 Self-Healing Reliability Loop

```
                        User Query
                            │
                            ▼
              ┌───────────────────────────┐
              │ 1. Text Normalization     │ ── NFKD, de-hyphenation, query-noise removal
              │    & Document Zoning      │ ── Porter Stemmer (5 steps), Title/Header weights
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │ 2. Hybrid Retrieval       │ ── Dense (Gemini Embeddings, 384d)
              │    & Reciprocal Fusion    │ ── Sparse Token-Frequency BM25
              └─────────────┬─────────────┘ ── RRF Scoring & Temporal Window Filter
                            │
                            ▼
              ┌───────────────────────────┐
              │ 3. Grounded Generation    │ ── Gemini 2.5/3.5, strictly conditioned
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │ 4. Claim Decomposition    │ ── Extracts atomic verifiable statements
              │    & Batch NLI Verify     │ ── SUPPORTED | CONTRADICTED | NEUTRAL
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │ 5. SHA-256 Hash Audit     │ ── Tamper detection vs MongoDB document_chunks
              │    & Reliability Scoring  │ ── Coverage & Contradiction Thresholds
              └─────────────┬─────────────┘
                            │
             ┌──────────────┴──────────────┐
             │                             │
    [Meets Thresholds]            [Below Threshold]
             │                             │
             ▼                             ▼
   ┌───────────────────┐        ┌──────────────────────────────────┐
   │  Grounded Answer  │        │ 6. Adaptive LangGraph Recovery   │
   │  + Evidence Cards │        │    Loop (Max 2 attempts)         │
   │  + Citations Trace│        └─────────────────┬────────────────┘
   └───────────────────┘                          │
                         ┌────────────────────────┴────────────────────────┐
                         │                                                 │
                   [Recovered]                                    [Recovery Exhausted]
                         │                                                 │
                         ▼                                                 ▼
               ┌───────────────────┐                             ┌───────────────────┐
               │  Grounded Answer  │                             │   Safe ABSTAIN    │
               │  (After Healing)  │                             │   (No Guessing)   │
               └───────────────────┘                             └───────────────────┘
```

---

## 🏛️ System Architecture

TRUSTRAG is architected as a modular monorepo comprising a reactive frontend workbench and an asynchronous, domain-driven API service:

```
TrustRAG/
├── apps/
│   ├── web/                          # React 18 + Vite 6 Workbench Application
│   │   ├── src/
│   │   │   ├── components/workbench/ # ClaimInspector, EvidenceViewer, ExecutionTrace, ReliabilityBadge
│   │   │   ├── layouts/              # Responsive AppLayout, Sidebar, and AuthGuard
│   │   │   ├── pages/                # 11 Pages: Playground, KBs, Claims, Conflicts, Evidence, Trace...
│   │   │   ├── services/             # Axios instance, Bearer interceptors, SSE streaming client
│   │   │   └── index.css             # Glassmorphic dark design system with micro-animations
│   │   └── package.json
│   │
│   └── api/                          # FastAPI Asynchronous Service
│       ├── app/
│       │   ├── agent/                # LangGraph StateGraph state machine & adaptive recovery loop
│       │   ├── api/                  # FastAPI routers, dependency injection, and Pydantic v2 schemas
│       │   ├── core/                 # App config, logging, rate limiting, security, model registry
│       │   ├── db/                   # MongoDB (Motor async driver) & Qdrant vector database clients
│       │   ├── generation/           # Context-grounded generation prompts and LLM invocation
│       │   ├── ingestion/            # Multi-format parsers (PDF/DOCX/TXT/MD/CSV/JSON/HTML), Porter stemmer, chunker
│       │   ├── retrieval/            # Dense search, sparse search, RRF fusion, CrossEncoder reranking
│       │   ├── services/             # Business logic: analysis runs, KB, auth, experiments
│       │   └── verification/         # Batch NLI verifier & SHA-256 evidence integrity auditor
│       ├── config/
│       │   └── models.yaml           # Centralized configuration registry for models and thresholds
│       └── tests/                    # 79 automated unit & integration test suites (100% pass)
│
├── docs/                             # Engineering documentation repository
│   ├── architecture/                 # End-to-end design specifications and ADRs
│   ├── audits/                       # Quality audits, fix logs, and multi-tenant verification
│   ├── security/                     # Security controls, threat modeling, and defense-in-depth
│   ├── evaluation/                   # Reliability benchmark methodology and metric models
│   └── deployment/                   # Docker deployment, scaling, and operations guides
│
├── docker-compose.yml                # Multi-service composition (FastAPI + Qdrant + MongoDB bridge)
├── .env.example                      # Template for secrets and environment configuration
└── TRUSTRAG_specs.md                 # Baseline architectural specification
```

---

## 💎 Ultra-Premium Dark Workbench UI

The frontend interface has been rebuilt from the ground up to deliver a state-of-the-art developer and observability experience. The `ui-redesign` branch delivers a production-grade React 18 + Vite 6 workbench with per-component CSS, Apple Design motion principles, and zero runtime bugs.

### Design System
- **Cyber Cyan Palette**: Electric Azure & Cyan (`#0ea5e9`, `#38bdf8`) on obsidian surfaces (`#040711`, `#080c16`). Verified = Emerald, warnings = Amber, contradictions = Crimson.
- **Typography**: Inter (sans) + JetBrains Mono (code). Font scale from `text-[10px]` (metadata) to `text-2xl` (headings).
- **Glassmorphism**: Translucent `glass-card`, `glass-nav`, `glass-sidebar` with backdrop blur and subtle borders.
- **Micro-Animations**: Spring-based motion (damping 15, stiffness 150) via `motion/react`. Staggered entrance animations. Global `:active` press feedback on all interactive elements.

### Architecture
```
apps/web/src/
├── styles/              # 16 external CSS files (typography, animations, materials, per-component)
├── components/
│   ├── landing/         # 8 sub-components: Hero, Bento, Simulation, Benchmarks, etc.
│   └── workbench/       # ClaimInspector, EvidenceViewer, ExecutionTrace, FormattedAnswer
├── layouts/             # AppLayout (sidebar + telemetry navbar), AuthLayout
├── pages/               # 12 lazy-loaded pages with React.Suspense boundaries
└── lib/                 # API client, auth store, React Query providers
```

### Key Features
- **Vendor-Split Code Splitting**: 26 optimized chunks — `react-vendor` (180 kB), `motion-vendor` (127 kB), `chart-vendor` (393 kB), `ui-vendor` (103 kB). AppLayout reduced from 140 kB → 14 kB (90% reduction).
- **Full Favicon Set**: PNG favicons (16/32/180/192/512px) with PWA manifest.
- **Accessibility**: `prefers-reduced-motion` support in CSS animations and `motion/react` springs. `aria-label` on all icon-only buttons. Touch targets ≥ 44px on coarse pointers.
- **Responsive**: Collapsible sidebar (desktop), slide-out drawer (mobile), responsive page padding (`p-4 sm:p-6 lg:p-8`).

---

## 🚀 Deployment & Production Readiness

This branch (**`ui-redesign`**) serves as the **Local-First AI Reliability Workbench** and is structured to be 100% production-ready for self-hosted, on-premises, or containerized deployments.

### 1. Backend Service (`apps/api/Dockerfile`)

The backend is packaged as a high-efficiency multi-stage container ready for deployment on any Docker, Kubernetes, or cloud container platform:

1. **Production Runtime Highlights**:
   * **Base Image**: `python:3.11-slim` multi-stage build installing production-only dependencies (`pip install .`).
   * **Hardware-Aware Autotuning**: Automatically senses host hardware (Apple Silicon Metal / NVIDIA CUDA / CPU) and allocates layers/workers accordingly.
   * **Non-Root Execution**: Runs under unprivileged `trustrag` user (UID 1001) for strict container security.
   * **Instant Port Binding**: Non-blocking `lifespan` startup architecture binds `$PORT` immediately with `/api/v1/health` probes.
   * **SSE Keep-Alive**: Emits SSE comment pings to keep persistent HTTP connections alive through reverse proxies.

2. **Core Environment Variables**:
   | Variable | Description / Recommended Value |
   |---|---|
   | `APP_ENV` | `production` or `development` |
   | `MONGODB_URI` | MongoDB connection string (e.g. `mongodb://localhost:27017/trustrag_db` or Atlas) |
   | `MONGODB_DATABASE` | `trustrag_db` |
   | `QDRANT_URL` | Qdrant endpoint (e.g. `http://localhost:6335` or cloud cluster) |
   | `QDRANT_API_KEY` | Optional for local Qdrant, required for Qdrant Cloud |
   | `JWT_SECRET` | 64-character random hex string for signing JWT tokens |
   | `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` |

### 2. Frontend Web Application (`apps/web`)

Built with React 18 and Vite 6, compiling into high-performance static assets:

1. **Build & Preview Commands**:
   * **Build Command**: `npm --prefix apps/web run build`
   * **Production Output**: `apps/web/dist` (optimized chunks with Brotli/gzip support)
   * **Local Preview**: `npm --prefix apps/web run preview`
   * **Defensive HTTP Headers**: Enforced via [`apps/web/public/_headers`](apps/web/public/_headers) (CSP, HSTS, X-Content-Type-Options).

### 3. Database & Cluster Maintenance Utility

A dedicated Python maintenance script is included in [`scripts/clear_qdrant.py`](scripts/clear_qdrant.py) for inspecting and purging Qdrant Cloud collections:

```bash
# List all active collections and point counts
python scripts/clear_qdrant.py --list

# Purge and delete all collections in the Qdrant Cloud cluster
python scripts/clear_qdrant.py --purge
```

---

## 💡 Core Engineering Capabilities

### 1. Multi-Tenant User Isolation & Anti-IDOR
- **Strict Database Scoping**: Every record (`knowledge_bases`, `documents`, `document_chunks`, `analyses`, `claims`, `evidence`) explicitly indexes and enforces `user_id`.
- **Physical Vector Separation**: Qdrant partitions vectors into dedicated per-KB collections (`kb_{kb_id}`). Points also record `user_id` in their metadata payloads.
- **Server-Side Ownership Verification**: Every request cryptographically extracts `current_user` from the verified JWT. Cross-tenant access is blocked with `403 Forbidden` or `404 Not Found`.
- **Complete Cascade Cleanup**: Deleting a Knowledge Base or document automatically cleans up all associated chunks from MongoDB and points from Qdrant, preventing storage leaks or cross-tenant ghost data.

### 2. Rule-Based Stemming & Document Zoning
- **Deterministic 5-Step Porter Stemmer**: Zero external black-box NLP runtime dependencies; implements morphological suffix stripping rules (e.g., `policies` → `polici`, `retrieval` → `retriev`).
- **Zone Weighting**: Document parser identifies `Title` (2.0x weight), `Header` (1.5x weight), and `Body` (1.0x weight) to boost structural keyword matching during lexical search.
- **Stopword & Contraction Normalization**: Cleans conversational noise words (`"tell"`, `"explain"`, `"what is"`) and expands standard English contractions (`"can't"` → `"cannot"`).

### 3. Hybrid Retrieval with RRF
- **Dense Vectors**: 384-dimensional semantic embeddings generated via Google Gemini Matryoshka Representation Learning (`models/gemini-embedding-001`), operating with **0 MB local GPU RAM** and saving **88% storage** compared to 3072d vectors.
- **Sparse BM25 Keyword Vectors**: Term-frequency sparse vectors with sublinear scaling ($1 + \ln(\text{tf})$) and zone multipliers.
- **Reciprocal Rank Fusion (RRF)**: Combines dense and sparse candidates using reciprocal rank scoring:
  $$\text{RRF Score}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + \text{rank}_m(d)}$$

### 4. Batch NLI Claim Verification
- **Decomposition**: Parses responses into discrete, standalone factual claims.
- **Batch Structured Verification**: Leverages Pydantic structured output in a single batch LLM invocation, preventing sequential 429 quota exhaustion.
- **Strict Classification**: Claims are classified as `SUPPORTED`, `CONTRADICTED`, or `NEUTRAL` with citation evidence IDs attached.

### 5. SHA-256 Provenance & Temporal Filtering
- **Cryptographic Tamper Auditing**: Compares the SHA-256 hash of retrieved chunks against reference hashes in MongoDB `document_chunks` to verify content integrity.
- **Temporal Validity**: Extracts ISO dates (`Effective from: YYYY-MM-DD` / `Effective until: YYYY-MM-DD`) and discards outdated or expired documentation.

### 6. Adaptive LangGraph Recovery Loop
When evidence coverage falls below `minimum_evidence_coverage` (0.60) or contradiction rates exceed `maximum_contradiction_rate` (0.15):
- **Attempt 1**: Decomposes failure and rewrites the query targeting the missing concepts.
- **Attempt 2**: Doubles candidate retrieval limits (`top_k = 40`) and repeats hybrid search.
- **Bound Ceiling**: After 2 attempts (`max_recovery_attempts`), the system safely transitions to `ABSTAIN` rather than returning unverified hallucinations.

### 7. Ultra-Low RAM & On-Disk Storage Architecture
- **Embedded RocksDB Storage**: Qdrant runs embedded via native Rust engine (`./data/qdrant/`) with `on_disk=True` for raw dense vectors and sparse indices.
- **INT8 Scalar Quantization**: Vector embeddings are quantized from float32 to int8 (`ScalarQuantizationConfig`), cutting vector RAM by **75%** with $<0.5\%$ recall loss.
- **Query Embedding LRU Cache**: Thread-safe in-memory cache (1024 entries) provides instant $O(1)$ lookup for repeat questions and LangGraph recovery sub-queries, eliminating remote API latency.
- **PyTorch Container Pruning**: Decoupled heavy PyTorch and `sentence-transformers` into optional dependencies, shrinking deployment container images from **~2.8 GB to ~350 MB**.

### 8. Universal Model Context Protocol (MCP) Server
- **Universal Agent Interoperability**: Native MCP server in [`apps/api/app/mcp/server.py`](apps/api/app/mcp/server.py) operating over standard input/output (stdio JSON-RPC 2.0).
- **Tools Provided**:
  * `trustrag_search`: Hybrid RRF search with temporal filtering and cryptographic SHA-256 provenance checks.
  * `trustrag_verify_claim`: Standalone zero-temperature batch NLI claim verification.
- **Client Support**: Direct one-click integration with Claude Desktop, Cursor, and Antigravity IDE.

### 9. Multi-Provider AI (Gemini + NVIDIA NIM)
- **LangChain Unified Client Interface**: Seamlessly switch between Google Gemini and enterprise NVIDIA NIM models via `AI_PROVIDER=gemini|nvidia`.
- **Supported LLMs**:
  * **Google Gemini**: `gemini-3.5-flash-lite` (default, sub-second latency), `gemini-2.5-flash`, `gemini-2.5-pro`.
  * **NVIDIA NIM**: `meta/llama-3.3-70b-instruct` (via `langchain-nvidia-ai-endpoints`), `mistralai/mistral-large-2-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`.
- **Deterministic Verification Protocol**: Claim verification runs on a dedicated temperature=0.0 model across all providers to eliminate variance and guarantee factual repeatability.

### 10. Local SOTA Embeddings (`BAAI/bge-small-en-v1.5`)
- **Top-Tier Open Benchmark Performance**: BGE-small achieves an MTEB retrieval score of **62.17**, outperforming many closed-source 1536d models while using only 384 dimensions.
- **BGE Query Instruction Prefixing**: [`BGEAwareHuggingFaceEmbeddings`](apps/api/app/core/model_registry.py) prepends `"Represent this sentence for searching relevant passages: "` to queries while vectorizing documents raw.
- **Zero API Cost & Offline Execution**: Runs entirely on local CPU with sub-35ms query latency and zero external network calls.
- **Full Backward Compatibility**: Automatically shares the 384-dimensional vector collection schema with Gemini Matryoshka embeddings without database migrations.

### 11. Live Web Search Grounding via MCP (Tavily + DuckDuckGo)
- **Native MCP Tools**:
  * `tavily_search`: Curated AI search with high-density content snippets (requires `TAVILY_API_KEY`).
  * `duckduckgo_search`: 100% free, zero-API-key search executed over `ddgs`.
  * `hybrid_web_search`: Runs Tavily and DuckDuckGo in parallel, deduplicating findings by canonical URL.
- **Interactive UI Toggle**: Select Tavily, DuckDuckGo, or Both directly from the Playground drawer to augment document evidence with live internet citations.
- **Transparent Citations**: Web results are highlighted as `[Web Source ↗]` links with target/rel tabnabbing protections.

### 12. Enterprise Security Hardening & SSRF Defense
- **Strict RFC URL Sanitization**: [`sanitize_url()`](apps/api/app/services/search_service.py) parses and validates all citation URLs against strict `http://` and `https://` schemes, dropping malicious `javascript:`, `data:`, `file:`, and `vbscript:` vectors.
- **SSRF Defense-in-Depth**: Automatically discards private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopbacks (`127.0.0.1`, `localhost`), and cloud metadata IP addresses (`169.254.169.254`, `metadata.google.internal`).
- **Tabnabbing & Reverse Window Protection**: Every external link enforces `target="_blank" rel="noopener noreferrer"`.
- **Query Bounds**: 500-character ceiling prevents buffer overflow and DoS attacks.
- **Timeout Protection**: Web search requests are bounded by `SEARCH_TIMEOUT_SECONDS = 8.0` with `asyncio.wait_for` to guarantee pipeline resilience.
- **Zero Secret Leakage**: The health endpoint and telemetry snapshots only return boolean status flags (`gemini_configured`, `nvidia_configured`, `tavily_configured`), keeping credentials completely secure.

### 13. 100% Private Local LLMs (Ollama & llama.cpp)
- **Local-First Native Async Engines**: [`ChatOllamaClient`](apps/api/app/core/local_llm.py) and [`ChatLlamaCppClient`](apps/api/app/core/local_llm.py) conform to LangChain's `BaseChatModel` interface with native async non-blocking execution.
- **Pre-Configured Models**:
  * **Ollama**: Defaulted to `gemma4:e2b` (5.1B params, dynamically aliased to local `gemma4:e2b-it-qat` or prefix-matched fallback).
  * **llama.cpp**: Defaulted to `gemma-4-E2B-it-qat-q4_0-gguf:Q4_0` served over port `8081` (`http://localhost:8081/v1`).
- **Structured Pydantic Output**: Native support for `with_structured_output(...)` enables reliable, schema-validated atomic claim decomposition and NLI verdict generation without cloud dependencies.
- **Complete Zero-Key Operation**: TRUSTRAG boots and executes 100% offline without requiring any third-party cloud API keys.

### 14. Native CLI Model Discovery (ollama list & llama-server)
- **Real-Time Shell Introspection**:
  * **`ollama list`**: Automatically introspects local models, isolating text LLMs (`qwen3.5:4b`, `gemma4:e2b-it-qat`, `granite4.2:3b`) from embedding models (`embeddinggemma:300m-qat-q8_0`).
  * **`llama-server --cache-list`**: Introspects cached GGUF model blobs directly from the local HuggingFace / llama.cpp cache (`ggml-org/embeddinggemma-300M-GGUF:Q8_0`).
- **Interactive UI Model Switcher**: The Playground workbench and Settings diagnostic page dynamically display detected models, active endpoints, and port telemetry.

### 15. Multi-Dimensional Vector Embeddings & L2 Normalization
- **Choice of SOTA Embedding Engines**:
  * **Local HuggingFace**: `BAAI/bge-small-en-v1.5` & `all-MiniLM-L6-v2` (384-dimensional dense vectors, zero API cost, sub-35ms CPU latency).
  * **Local Ollama**: `embeddinggemma:300m-qat-q8_0` (768-dimensional dense representations).
  * **Cloud Gemini**: `models/gemini-embedding-001` (384-dimensional Matryoshka representations).
  * **Cloud NVIDIA NIM**: `nvidia/nv-embedqa-e5-v5` (384-dimensional vectors).
- **Dimension-Safe Retrieval with L2 Normalization**: When querying a 384d Qdrant collection with a 768d embedding model, [`dense_search()`](apps/api/app/retrieval/retriever.py) automatically truncates and re-normalizes the vector ($\|v\|_2 = 1.0$), ensuring strict mathematical consistency for cosine similarity calculations.

---

## 🛠️ Technology Stack

| Layer | Component | Version / Specification | Role in TRUSTRAG |
|---|---|---|---|
| **Frontend** | React + Vite | React 18, Vite 6, Tailwind CSS, Motion 13 | Ultra-premium dark theme UI, spring animations, Recharts |
| **Telemetry** | Server-Sent Events (SSE) | EventSource protocol | Real-time agent execution graph streaming to the workbench UI |
| **Backend** | FastAPI | Python 3.11, Pydantic v2 | High-throughput asynchronous REST API, custom middleware |
| **Local LLMs** | Ollama & llama.cpp | Port 11434 & Port 8081 | 100% private, offline LLM synthesis and NLI verification |
| **Cloud LLMs** | Google Gemini & NVIDIA NIM | Gemini 3.5 Flash Lite / Llama 3.3 70B | Cloud-native grounded reasoning and batch NLI claim verification |
| **Dense Embeddings** | Multi-Provider Engine | 384d (BGE / Gemini) & 768d (Ollama) | Dense semantic vector representations with dimensional alignment |
| **Agent Protocols** | Model Context Protocol (MCP) | JSON-RPC 2.0 (stdio) | Universal tool interface for external AI coding agents & local LLM chat |
| **State Machine** | LangGraph | `StateGraph` | Multi-node deterministic agent state machine |
| **Primary Database** | MongoDB Community | v7.0+ (Local Host / Atlas Cloud) | Permanent storage of metadata, chunks, claims, and execution traces |
| **Vector Engine** | Qdrant | Embedded Local Rust Engine / Cloud | Hybrid dense & sparse vectors; on-disk storage with INT8 scalar quantization |
| **Security Suite** | JWT + Bcrypt + SlowAPI | HS256, 12 Bcrypt rounds, IP rate limits | Authentication, timing-attack protection, defensive HTTP headers |

---

## 🚀 Getting Started

### Prerequisites

- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** ≥ v4.x
- **[Node.js](https://nodejs.org/)** ≥ 20.x (with npm)
- **[MongoDB Community Edition](https://www.mongodb.com/try/download/community)** running locally on port `27017` (or a MongoDB Atlas connection string)
- **[Google Gemini API Key](https://aistudio.google.com/app/apikey)** (Free tier available)

---

### 1. Environment Configuration

Clone the repository and create your local environment file:

```bash
git clone https://github.com/MaithreshVaddi-27/TrustRAG.git
cd TrustRAG
cp .env.example .env
```

Open `.env` in your editor and configure your variables:

```ini
# Application Environment
APP_ENV=development
LOG_LEVEL=INFO

# Security (generate with: python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET=replace_with_a_secure_random_64_character_hex_string
JWT_EXPIRY_MINUTES=60

# ── AI Provider Selection ─────────────────────────────────────────────────────
# Options: 'gemini' (Google AI Studio) or 'nvidia' (NVIDIA NIM)
AI_PROVIDER=gemini

# Google Gemini API (Required if AI_PROVIDER=gemini or EMBEDDING_PROVIDER=google_genai)
GEMINI_API_KEY=your_gemini_api_key_here

# NVIDIA NIM API (Required if AI_PROVIDER=nvidia)
NVIDIA_API_KEY=nvapi-your_nvidia_api_key_here

# ── Embedding Model Provider ─────────────────────────────────────────────────
# Options:
#   'huggingface': Local SOTA BAAI/bge-small-en-v1.5 (384d, 0 API cost, ~32ms query latency) [DEFAULT]
#   'google_genai': Cloud Google Gemini models/gemini-embedding-001 (384d Matryoshka)
EMBEDDING_PROVIDER=huggingface

# ── Live Web Grounding Search Providers (MCP) ─────────────────────────────────
# Options: 'auto', 'tavily', 'duckduckgo', 'both'
SEARCH_PROVIDER=auto

# Tavily AI Search (Optional, for AI-curated web snippets)
TAVILY_API_KEY=tvly-your_tavily_api_key_here

# DuckDuckGo Search requires ZERO API keys and runs 100% free out of the box!

# ── MongoDB Connection ────────────────────────────────────────────────────────
# Option 1 (Recommended Local): Native MongoDB
MONGODB_URI=mongodb://localhost:27017
# Option 2: MongoDB Atlas Cloud:
# MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/trustrag?retryWrites=true&w=majority

# ── Qdrant Vector Store ───────────────────────────────────────────────────────
# Option 1 (Recommended Local): Embedded in-process Rust engine (0MB idle RAM, no Docker needed):
QDRANT_URL=local
# Option 2 (Docker / Server): http://localhost:6333
# Option 3 (Qdrant Cloud):    https://<cluster-id>.<region>.aws.cloud.qdrant.io
```

---

### Zero-API-Key Local Mode (DuckDuckGo + Local BGE)

Want to run TRUSTRAG with **zero external API calls for search and embeddings**?
1. Set `EMBEDDING_PROVIDER=huggingface` in `.env`.
   - The system automatically loads `BAAI/bge-small-en-v1.5` locally in CPU memory.
2. Toggle **DuckDuckGo** in the Playground Web Search drawer.
   - Live internet grounding runs completely free without needing any Tavily API key!
3. Provide your LLM key (`GEMINI_API_KEY` or `NVIDIA_API_KEY`) for reasoning.

### Option A: Running Locally with Native Resources (Recommended)

This is the fastest, lightest method for development on macOS/Linux. It bypasses Docker Desktop's 4GB RAM overhead and boots in under 1 second.

1. **Verify Local MongoDB**:
   ```bash
   # Ensure local MongoDB is running (e.g. via Homebrew on macOS)
   brew services start mongodb-community
   ```

2. **Start Backend Service (Embedded Qdrant)**:
   ```bash
   cd apps/api
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"

   # Launch FastAPI with hot-reload (automatically mounts embedded Qdrant in ./data/qdrant)
   uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

3. **Verify Health Endpoint**:
   ```bash
   curl -s http://localhost:8080/api/v1/health | jq
   ```
   *Expected Response:*
   ```json
   {
     "status": "ok",
     "app": "TRUSTRAG",
     "version": "0.1.0",
     "services": {
       "mongodb": "ok",
       "qdrant": "ok"
     }
   }
   ```

4. **Start Frontend Workbench**:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

   Open your browser at **http://localhost:5173**.

---

### Option B: Running with Docker Compose

For multi-container or staging testing:

1. **Start Backend, Vector Store & MongoDB Bridge**:
   ```bash
   docker compose up -d
   ```

2. **Start Frontend**:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

---

## 💻 End-to-End Walkthrough via CLI

You can interact with TRUSTRAG directly using `curl`:

### Step 1: Register & Authenticate

```bash
BASE=http://localhost:8080/api/v1

# 1. Register account
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@company.com","password":"Password123!","full_name":"Lead Engineer"}' | jq

# 2. Authenticate and obtain JWT
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@company.com","password":"Password123!"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

echo "Authenticated JWT: ${TOKEN:0:28}..."
```

### Step 2: Create a Knowledge Base

```bash
KB_RESPONSE=$(curl -s -X POST $BASE/knowledge-bases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Service Policies","description":"Customer policy agreements"}')

KB_ID=$(echo $KB_RESPONSE | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Knowledge Base ID: $KB_ID"
```

### Step 3: Ingest a Document

Create sample documentation with temporal validity metadata:

```bash
cat << 'EOF' > /tmp/sample_policy.txt
Effective from: 2026-01-01
Effective until: 2026-12-31

# Enterprise Refund Policy
Customers on an Annual Contract are eligible for a full refund within 30 days of purchase.
Monthly subscriptions can be canceled at any time with immediate effect.
Data backups are retained for 90 days following account deactivation.
EOF

# Upload document
DOC_RESPONSE=$(curl -s -X POST $BASE/knowledge-bases/$KB_ID/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/sample_policy.txt;type=text/plain")

DOC_ID=$(echo $DOC_RESPONSE | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Document Uploaded. ID: $DOC_ID"
```

### Step 4: Execute Agentic Analysis

#### Option 1: Standard Document Analysis
```bash
# Allow ~1-2s for indexing
sleep 2

# Submit query to the LangGraph reliability loop
ANALYSIS=$(curl -s -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"What is the refund policy for annual contracts?\"}")

ANALYSIS_ID=$(echo $ANALYSIS | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Analysis Run Initiated. ID: $ANALYSIS_ID"
```

#### Option 2: Live Web Search Grounding (MCP)
```bash
# Submit query augmented with live internet citations (Tavily, DuckDuckGo, or Both)
ANALYSIS_WEB=$(curl -s -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"knowledge_base_id\": \"$KB_ID\",
    \"query\": \"What is the latest revenue for NVIDIA in 2025?\",
    \"enable_web_search\": true,
    \"web_search_provider\": \"both\"
  }")

ANALYSIS_ID=$(echo $ANALYSIS_WEB | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Web-Grounded Analysis Run Initiated. ID: $ANALYSIS_ID"
```

### Step 5: Stream Live Execution Telemetry

```bash
# Connect to live Server-Sent Events stream
curl -N "$BASE/analyses/$ANALYSIS_ID/stream?token=$TOKEN"
```

### Step 6: Inspect Results & Provenance

```bash
# 1. Fetch grounded answer and reliability verdict
curl -s $BASE/analyses/$ANALYSIS_ID -H "Authorization: Bearer $TOKEN" | jq

# 2. Inspect verified claims
curl -s $BASE/analyses/$ANALYSIS_ID/claims -H "Authorization: Bearer $TOKEN" | jq

# 3. View retrieved evidence and SHA-256 integrity status
curl -s $BASE/analyses/$ANALYSIS_ID/evidence -H "Authorization: Bearer $TOKEN" | jq
```

---

## 📡 API Reference

All protected endpoints require `Authorization: Bearer <JWT>`.

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | Public | Live readiness probe checking MongoDB and Qdrant vector store |
| `POST` | `/api/v1/auth/register` | Public | User registration (rate-limited: 20/min) |
| `POST` | `/api/v1/auth/login` | Public | Credential verification & JWT issuance |
| `GET` | `/api/v1/auth/me` | User | Fetch authenticated user profile |
| `GET` | `/api/v1/knowledge-bases` | User | List all Knowledge Bases owned by current user |
| `POST` | `/api/v1/knowledge-bases` | User | Create a new Knowledge Base |
| `DELETE` | `/api/v1/knowledge-bases/{id}` | User | Cascade-delete a Knowledge Base, all its documents, chunks, and vectors |
| `POST` | `/api/v1/knowledge-bases/{id}/documents` | User | Upload document (`.pdf`, `.txt`, `.md`, ≤20MB) for chunking and vector indexing |
| `GET` | `/api/v1/knowledge-bases/{id}/documents` | User | List documents in a Knowledge Base |
| `GET` | `/api/v1/documents/{id}` | User | Fetch single document metadata |
| `DELETE` | `/api/v1/documents/{id}` | User | Delete single document, associated MongoDB chunks, and Qdrant points |
| `POST` | `/api/v1/analyses` | User | Trigger LangGraph agentic analysis pipeline (rate-limited: 10/min) |
| `GET` | `/api/v1/analyses` | User | List analysis history for authenticated user |
| `GET` | `/api/v1/analyses/{id}` | User | Fetch analysis details, answer, reliability score, and diagnosis |
| `GET` | `/api/v1/analyses/{id}/export` | User | Export complete verifiable JSON / JSON-LD audit dossier |
| `GET` | `/api/v1/analyses/{id}/stream` | User | Server-Sent Events (SSE) live telemetry stream |
| `GET` | `/api/v1/analyses/{id}/claims` | User | Fetch decomposed claims and NLI verification states |
| `GET` | `/api/v1/analyses/{id}/evidence` | User | Fetch retrieved evidence chunks with provenance and integrity status |
| `GET` | `/api/v1/conflicts` | User | Fetch all claim contradictions and compromised evidence for the user |
| `GET` | `/api/v1/experiments` | User | List objective RAG benchmark evaluation experiments |
| `POST` | `/api/v1/experiments` | User | Record an evaluation experiment run |

Interactive Swagger documentation is available at `http://localhost:8080/docs` in development mode.

---

## 🧪 Testing & Quality Assurance

TRUSTRAG enforces automated quality checks across both backend and frontend layers:

```bash
# 1. Run complete pytest test suite (69 tests covering agent, NLI, auth, and IDOR)
docker exec trustrag_api pytest -v

# 2. Run backend static analysis and style formatting
docker exec trustrag_api ruff check app/ tests/

# 3. Run frontend code linting and production bundle compilation
cd apps/web
npm run lint
npm run build
```

---

## ❓ Troubleshooting & FAQ

### 1. MongoDB connectivity errors
- **Issue**: `ServerSelectionTimeoutError: host.docker.internal:27017`
- **Solution**: Ensure local MongoDB community is running on macOS:
  ```bash
  brew services list
  brew services start mongodb-community
  ```
  Check that MongoDB listens on `127.0.0.1:27017` in `/opt/homebrew/etc/mongod.conf`.

### 2. Qdrant port mappings
- **Issue**: Port `6333` conflict on host.
- **Solution**: In `docker-compose.yml`, Qdrant exposes host port `6335:6333`. Connect from host tools at `http://localhost:6335`. Inside the Docker network, containers communicate directly via `http://qdrant:6333`.

### 3. Gemini API 429 Quota Exhaustion
- **Issue**: `RESOURCE_EXHAUSTED` error during high-frequency testing.
- **Solution**: TRUSTRAG employs single-pass batch verification (`batch_verify_claims_nli`), reducing LLM calls from $O(N)$ claims to a single prompt. If running bulk experiments on the free tier, stay within Gemini's 15 RPM limit.

### 4. Embedding model initial container startup
- **Issue**: First container boot takes ~90 seconds.
- **Solution**: On the first start, the API container downloads the local embedding model (`all-MiniLM-L6-v2`, ~90MB) and caches it in the `model_cache` volume. Subsequent container boots are instantaneous.

---

## 📚 Documentation Index

- 📊 [**Master Architecture & Systems Audit (`docs/audit/comprehensive_audit_report.md`)**](docs/audit/comprehensive_audit_report.md) — Multi-disciplinary evaluation across Systems, Security, AI/ML, and QA.
- 🛡️ [**Deep Security & DevSecOps Audit (`docs/audit/security_audit.md`)**](docs/audit/security_audit.md) — Physical collection isolation, anti-IDOR defense, XXE protection, and cryptographic SHA-256 provenance.
- 🧠 [**AI/ML Performance & Latency Audit (`docs/audit/ai_ml_performance_audit.md`)**](docs/audit/ai_ml_performance_audit.md) — Matryoshka 384d MRL embeddings, hybrid RRF search, and zero local GPU RAM operation.
- 🧪 [**Quality Assurance Testing Report (`docs/audit/qa_testing_report.md`)**](docs/audit/qa_testing_report.md) — 79/79 automated tests across whitebox and blackbox test suites.
- 🛠️ [**Modernization & Refactoring Blueprint (`docs/audit/areas_for_improvement_and_refactoring.md`)**](docs/audit/areas_for_improvement_and_refactoring.md) — Qdrant on-disk INT8 quantization, LRU embedding caching, and container pruning.
- 🏛️ [**System Architecture (`docs/architecture/architecture.md`)**](docs/architecture/architecture.md) — Comprehensive technical design of the LangGraph state machine, hybrid search, and claim decomposition.
- 📐 [**Decision Log (`docs/architecture/decision-log.md`)**](docs/architecture/decision-log.md) — Architectural Decision Records (ADRs) explaining technology selections and tradeoffs.
- 🛡️ [**Security Controls (`docs/security/security-controls.md`)**](docs/security/security-controls.md) — Deep dive into JWT authentication, anti-IDOR validation, and defensive headers.
- 🔒 [**Threat Model (`docs/security/threat-model.md`)**](docs/security/threat-model.md) — STRIDE threat modeling, attack surface analysis, and countermeasure matrix.
- 🔍 [**Multi-Tenant Isolation Audit (`docs/audits/multi-tenant-isolation-audit.md`)**](docs/audits/multi-tenant-isolation-audit.md) — Independent audit validating tenant data scoping and cascade deletion.
- 📋 [**Quality Audit Dossier (`docs/audits/final-audit-report.md`)**](docs/audits/final-audit-report.md) — Formal quality sign-off verifying 0 open defects across P0–P3 categories.
- 🗺️ [**Product Roadmap (`docs/ROADMAP.md`)**](docs/ROADMAP.md) — Milestones, completed phases, and future releases.

---

## 📄 License

This project is licensed under the terms of the [MIT License](LICENSE).
