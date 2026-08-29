# TRUSTRAG — Production AI Reliability Workbench

> **Retrieve. Verify. Diagnose. Recover.**  
> An open-source, multi-tenant AI reliability platform that detects hallucinations, audits evidence integrity, decomposes assertions into atomic claims, and self-heals low-confidence RAG responses using an adaptive LangGraph loop.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-FF6F00)](https://langchain-ai.github.io/langgraph/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Hybrid_Vector-DC2626?logo=qdrant&logoColor=white)](https://qdrant.tech)
[![MongoDB](https://img.shields.io/badge/MongoDB-Community_&_Atlas-47A248?logo=mongodb&logoColor=white)](https://mongodb.com)
[![Tests](https://img.shields.io/badge/Tests-69%20Passing-brightgreen)](apps/api/tests)
[![Bandit](https://img.shields.io/badge/Bandit%20SAST-0%20Issues-brightgreen)](docs/audits/final-audit-report.md)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Self-Healing Reliability Loop](#-self-healing-reliability-loop)
- [System Architecture](#-system-architecture)
- [Core Engineering Capabilities](#-core-engineering-capabilities)
  - [1. Multi-Tenant User Isolation & Anti-IDOR](#1-multi-tenant-user-isolation--anti-idor)
  - [2. Rule-Based Stemming & Document Zoning](#2-rule-based-stemming--document-zoning)
  - [3. Hybrid Retrieval with RRF](#3-hybrid-retrieval-with-rrf)
  - [4. Batch NLI Claim Verification](#4-batch-nli-claim-verification)
  - [5. SHA-256 Provenance & Temporal Filtering](#5-sha-256-provenance--temporal-filtering)
  - [6. Adaptive LangGraph Recovery Loop](#6-adaptive-langgraph-recovery-loop)
- [Technology Stack](#-technology-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#1-environment-configuration)
  - [Running with Docker (Recommended)](#option-a-running-with-docker-recommended)
  - [Running Locally (Non-Docker)](#option-b-running-locally-non-docker)
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
              │ 2. Hybrid Retrieval       │ ── Dense (all-MiniLM-L6-v2, 384d)
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
│       │   ├── ingestion/            # PDF/TXT/MD parsers, Porter stemmer, chunker, sparse vectors
│       │   ├── retrieval/            # Dense search, sparse search, RRF fusion, CrossEncoder reranking
│       │   ├── services/             # Business logic: analysis runs, KB, auth, experiments
│       │   └── verification/         # Batch NLI verifier & SHA-256 evidence integrity auditor
│       ├── config/
│       │   └── models.yaml           # Centralized configuration registry for models and thresholds
│       └── tests/                    # 69 automated unit & integration test suites (100% pass)
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
- **Dense Vectors**: 384-dimensional semantic embeddings generated locally via `sentence-transformers/all-MiniLM-L6-v2` (free, zero external API latency, zero rate limits).
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

---

## 🛠️ Technology Stack

| Layer | Component | Version / Specification | Role in TRUSTRAG |
|---|---|---|---|
| **Frontend** | React + Vite | React 18, Vite 6, Tailwind CSS | High-performance glassmorphic UI, responsive tables, Recharts |
| **Telemetry** | Server-Sent Events (SSE) | EventSource protocol | Real-time agent execution graph streaming to the workbench UI |
| **Backend** | FastAPI | Python 3.11, Pydantic v2 | High-throughput asynchronous REST API, custom middleware |
| **State Machine** | LangGraph | `StateGraph` | Multi-node deterministic agent state machine |
| **Primary Database** | MongoDB Community | v7.0+ (Local Host / Docker Bridge) | Permanent storage of metadata, chunks, claims, and execution traces |
| **Vector Engine** | Qdrant | v1.10.1 (HTTP & gRPC) | Hybrid dense and sparse vector storage, payload filtering |
| **Embeddings** | HuggingFace Local | `sentence-transformers/all-MiniLM-L6-v2` | 384-dimensional dense vectors running locally in container |
| **Reasoning LLM** | Google Gemini | `gemini-2.5-flash-lite` / `gemini-3.5-flash-lite` | Grounded reasoning, claim extraction, and batch NLI verification |
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

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# MongoDB Connection
# Option 1: Local MongoDB Community (Recommended for permanent local storage):
MONGODB_URI=mongodb://host.docker.internal:27017/trustrag_db
# Option 2: MongoDB Atlas Cloud:
# MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/trustrag_db?retryWrites=true&w=majority

# Qdrant Vector Store
# In Docker compose, container communicates via internal network:
QDRANT_URL=http://qdrant:6333
```

---

### Option A: Running with Docker (Recommended)

1. **Start Backend & Vector Store**:
   ```bash
   # Start FastAPI backend and Qdrant in detached mode
   docker compose up -d
   ```

2. **Verify Multi-Service Health**:
   ```bash
   curl -s http://localhost:8000/api/v1/health | jq
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

3. **Start Frontend Workbench**:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

   Open your browser at **http://localhost:5173**.

---

### Option B: Running Locally (Non-Docker)

1. **Start Qdrant**:
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:v1.10.1
   ```

2. **Start Backend Service**:
   ```bash
   cd apps/api
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"

   # Load environment variables and launch Uvicorn
   set -a && source ../../.env && set +a
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Start Frontend**:
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
BASE=http://localhost:8000/api/v1

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

```bash
# Allow ~3s for embedding and indexing
sleep 3

# Submit query to the LangGraph reliability loop
ANALYSIS=$(curl -s -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"What is the refund policy for annual contracts?\"}")

ANALYSIS_ID=$(echo $ANALYSIS | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Analysis Run Initiated. ID: $ANALYSIS_ID"
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
| `GET` | `/api/v1/analyses/{id}/stream` | User | Server-Sent Events (SSE) live telemetry stream |
| `GET` | `/api/v1/analyses/{id}/claims` | User | Fetch decomposed claims and NLI verification states |
| `GET` | `/api/v1/analyses/{id}/evidence` | User | Fetch retrieved evidence chunks with provenance and integrity status |
| `GET` | `/api/v1/conflicts` | User | Fetch all claim contradictions and compromised evidence for the user |
| `GET` | `/api/v1/experiments` | User | List objective RAG benchmark evaluation experiments |
| `POST` | `/api/v1/experiments` | User | Record an evaluation experiment run |

Interactive Swagger documentation is available at `http://localhost:8000/docs` in development mode.

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

Detailed engineering documentation is located in [**`docs/`**](docs/README.md):

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
