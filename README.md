# TrustRAG

> **Your local-first RAG reliability workbench** — catch hallucinations, audit evidence, and self-heal low-confidence answers using an adaptive LangGraph loop. Everything runs on your machine. No API keys required.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Ollama](https://img.shields.io/badge/Ollama-Local_Offline-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![llama.cpp](https://img.shields.io/badge/llama.cpp-GGUF_Server-orange)](https://github.com/ggerganov/llama.cpp)
[![Tests](https://img.shields.io/badge/Backend%20Tests-192%20Passing-brightgreen)](apps/api/tests)
[![Tests](https://img.shields.io/badge/Frontend%20Tests-21%20Passing-brightgreen)](apps/web)
[![E2E](https://img.shields.io/badge/Playwright%20E2E-2%20Passing-brightgreen)](apps/web/e2e)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

---

## What is this?

Standard RAG systems fail silently. They grab some context, generate an answer, and present it as fact — even when the answer is wrong. There's no audit trail, no verification, no way to know if you can trust the output.

TrustRAG fixes that. It's a full reliability pipeline that:

1. **Decomposes** responses into individual factual claims.
2. **Validates** each claim against your documents using batch NLI (Natural Language Inference).
3. **Audits** source integrity with SHA-256 hashes and temporal validity windows.
4. **Self-heals** when confidence is low — rewriting queries and expanding search via a LangGraph state machine, then either returning a grounded answer or safely abstaining.

Think of it as a fact-checking layer for RAG. It runs 100% locally on your machine with Ollama or llama.cpp — no cloud API keys needed unless you want them.

---

## Quick Links

| Service | URL | What it does |
|---|---|---|
| **Frontend Workbench** | [http://localhost:5173](http://localhost:5173) | The React UI — upload docs, ask questions, see verification results |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | FastAPI engine — all the RAG, NLI, and LangGraph magic |
| **Interactive Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI — test every endpoint right in your browser |
| **Health Check** | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | Live system status — MongoDB, Qdrant, hardware profile |

---

## Table of Contents

- [What is this?](#what-is-this)
- [Quick Links](#quick-links)
- [How the self-healing loop works](#how-the-self-healing-loop-works)
- [Getting Started](#getting-started)
  - [What you need](#what-you-need)
  - [Step 1 — Install platform tools](#step-1--install-platform-tools)
  - [Step 2 — Clone and configure](#step-2--clone-and-configure)
  - [Step 3 — Start services](#step-3--start-services)
  - [Step 4 — Open the UI](#step-4--open-the-ui)
- [Try it from the command line](#try-it-from-the-command-line)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [License](#license)

---

## How the self-healing loop works

```
                        Your Question
                             │
                             ▼
               ┌───────────────────────────┐
               │ 1. Text Normalization     │  clean up noise, fix hyphens, strip fluff
               │    & Document Zoning      │  weight titles/headers higher than body
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │ 2. Hybrid Retrieval       │  Dense vectors (BGE, 384d) + BM25 keywords
               │    + Reciprocal Fusion    │  combined with RRF scoring
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │ 3. Grounded Generation    │  LLM answer, strictly conditioned on evidence
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │ 4. Claim Decomposition    │  break answer into atomic facts
               │    + Batch NLI Verify     │  SUPPORTED | CONTRADICTED | NEUTRAL
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │ 5. SHA-256 Hash Audit     │  tamper detection on source chunks
               │    + Reliability Scoring  │  coverage vs contradiction thresholds
               └─────────────┬─────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     [Meets Thresholds]            [Below Threshold]
              │                             │
              ▼                             ▼
    ┌───────────────────┐        ┌────────────────────────────┐
    │  Grounded Answer  │        │ 6. Adaptive Recovery Loop  │
    │  + Evidence Cards │        │    rewrite query, expand   │
    │  + Citations      │        │    search, retry (1 round) │
    └───────────────────┘        └────────────┬───────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │                   │
                              [Recovered]      [Recovery Exhausted]
                                    │                   │
                                    ▼                   ▼
                          ┌───────────────┐   ┌───────────────┐
                          │  Grounded     │   │  Safe         │
                          │  Answer       │   │  ABSTAIN      │
                          └───────────────┘   └───────────────┘
```

When the system isn't confident in its answer, it doesn't guess. It either heals itself or tells you it doesn't know. That's the point.

---

## Getting Started

### What you need

| Tool | Version | Why |
|---|---|---|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 22+ | Frontend build tools (see `engines` in `apps/web/package.json`) |
| **MongoDB** | 7.0+ | Document & metadata storage |
| **Ollama** or **llama.cpp** | Latest | Local LLM inference (zero API keys) |
| **Git** | Any recent | Clone the repo |

Optional (only if you want cloud features):
- Google Gemini API key — for cloud LLM reasoning
- NVIDIA NIM API key — for enterprise NIM models
- Tavily API key — for AI-powered web search (DuckDuckGo is free and works without a key)

---

### Step 1 — Install platform tools

Pick your operating system and run the commands. This installs everything TrustRAG needs.

<details>
<summary><b>macOS (Apple Silicon or Intel)</b></summary>

```bash
# 1. Xcode command line tools (if not already installed)
xcode-select --install

# 2. Homebrew (the macOS package manager)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Core tools
brew install git python@3.11 node mongodb-community ollama

# 4. Start MongoDB (runs in background on boot)
brew services start mongodb-community

# 5. Start Ollama (runs in background)
brew services start ollama

# 6. Pull the default local LLM (~815MB)
ollama pull gemma3:1b

# 7. (Optional) llama.cpp — for GGUF models
#    Option A: Install via Homebrew
brew install llama.cpp

#    Option B: Build from source for latest features
git clone https://github.com/ggml-org/llama.cpp /tmp/llama.cpp
cd /tmp/llama.cpp
cmake -B build -DGGML_NATIVE=on
cmake --build build -j$(sysctl -n hw.ncpu)
# The binary is at build/bin/llama-server — add to PATH or use the full path
```

</details>

<details>
<summary><b>Linux (Ubuntu / Debian)</b></summary>

```bash
# 1. System packages
sudo apt update && sudo apt install -y \
  git python3.11 python3.11-venv python3-pip \
  build-essential cmake curl jq

# 2. Node.js 20+ (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 3. MongoDB 7.0
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod

# 4. Ollama
curl -fsSL https://ollama.com/install.sh | sh
# Start the daemon in background
ollama serve &
sleep 2

# 5. Pull the default local LLM (~815MB)
ollama pull gemma3:1b

# 6. (Optional) llama.cpp — build from source
git clone https://github.com/ggml-org/llama.cpp /tmp/llama.cpp
cd /tmp/llama.cpp
cmake -B build -DGGML_NATIVE=on
cmake --build build -j$(nproc)
# Binary at build/bin/llama-server — add to PATH or use the full path
```

</details>

<details>
<summary><b>Windows 11 (PowerShell + winget)</b></summary>

```powershell
# 1. Install core tools via winget
winget install --id Git.Git -e --source winget
winget install --id OpenJS.NodeJS.LTS -e --source winget
winget install --id Python.Python.3.12 -e --source winget
winget install --id MongoDB.CommunityServer -e --source winget
winget install --id Ollama.Ollama -e --source winget

# 2. Restart your terminal, then verify
python --version
node --version
git --version

# 3. Start MongoDB
#    Open PowerShell as Administrator:
Get-Service MongoDB | Start-Service

# 4. Start Ollama (opens a background terminal)
ollama serve

# 5. In a NEW terminal, pull the default LLM (~815MB)
ollama pull gemma3:1b

# 6. (Optional) llama.cpp — download a prebuilt release
#    Go to: https://github.com/ggml-org/llama.cpp/releases
#    Download the latest Windows zip (e.g. llama-*-bin-win-x64.zip)
#    Extract it and add the folder to your system PATH
#    Verify: llama-server --help
```

> **Note for Windows users:** TrustRAG uses bash scripts (`scripts/start_local_llm.sh`, `scripts/setup.sh`). Install **Git for Windows** (which includes Git Bash) and run those scripts from Git Bash, not PowerShell. The Python/Node commands work in both.

</details>

---

### Step 2 — Clone and configure

```bash
# Clone the repo
git clone https://github.com/MaithreshVaddi-27/TrustRAG.git
cd TrustRAG

# Create your local environment file
cp .env.example .env

# Generate a JWT secret (required for authentication)
python3 -c "import secrets; print(secrets.token_hex(64))"

# Copy that output into your .env file as JWT_SECRET
# Open .env in your editor and paste it:
#   JWT_SECRET=<the output from above>
```

> **Tip:** Run the setup checker to see if you missed anything:
> ```bash
> ./scripts/setup.sh
> ```
> It'll tell you exactly what's missing and how to fix it.

---

### Step 3 — Start services

You have two options: **Native** (recommended for development — faster, lighter) or **Docker** (good for staging/production testing).

#### Option A: Native (recommended)

Open **three terminal tabs**:

**Terminal 1 — Local LLM server (pick one):**

```bash
# Using Ollama (easiest — just make sure it's running)
ollama serve    # if not already running via brew services / systemctl

# OR using llama.cpp (auto-detects Metal on Mac, CUDA on Linux)
./scripts/start_local_llm.sh
```

**Terminal 2 — Backend API:**

```bash
cd apps/api

# Create virtual environment (first time only)
python3 -m venv .venv
source .venv/bin/activate        # Windows Git Bash: source .venv/Scripts/activate
pip install -e ".[dev]"

# Optional: discover installed models so they show up in the UI immediately
python ../../scripts/discover_local_models.py

# Start the server (hot-reload enabled)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 3 — Frontend:**

```bash
cd apps/web
npm install
npm run dev
```

#### Option B: Docker Compose

```bash
# Start backend (FastAPI + Qdrant + MongoDB)
docker compose up -d

# Check health
curl -s http://localhost:8000/api/v1/health | jq

# Start frontend separately (not in docker-compose)
cd apps/web
npm install
npm run dev

# Stop everything
docker compose down
```

The frontend always runs locally via `npm run dev` (it's not in docker-compose).

---

### Step 4 — Open the UI

Open **http://localhost:5173** in your browser. You'll see the TrustRAG workbench.

1. **Register** a new account (first time only).
2. **Create a Knowledge Base** and upload some documents (.pdf, .txt, .md, .docx, .csv, .json, .html).
3. **Ask a question** — TrustRAG will retrieve evidence, generate an answer, verify every claim, and show you exactly what it found.

The default local model is `gemma3:1b` via Ollama (or `LiquidAI/LFM2.5-1.2B-Instruct-GGUF` via llama.cpp). Both run on your CPU — no GPU required.

---

## Try it from the command line

No UI needed — here's the full flow via `curl`:

```bash
BASE=http://localhost:8000/api/v1

# 1. Register
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"Password123!","full_name":"Your Name"}'

# 2. Login (grab the token)
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"Password123!"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 3. Create a knowledge base
KB_ID=$(curl -s -X POST $BASE/knowledge-bases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Documents","description":"Test KB"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

# 4. Upload a document
cat << 'EOF' > /tmp/sample.txt
Effective from: 2026-01-01
Effective until: 2026-12-31

# Refund Policy
Annual contract customers can get a full refund within 30 days.
Monthly subscriptions can be canceled anytime with immediate effect.
Data backups are retained for 90 days after deactivation.
EOF

curl -s -X POST $BASE/knowledge-bases/$KB_ID/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/sample.txt;type=text/plain"

# 5. Ask a question
sleep 2  # let indexing finish
ANALYSIS_ID=$(curl -s -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"What is the refund policy?\"}" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

# 6. Stream the live execution trace
curl -N "$BASE/analyses/$ANALYSIS_ID/stream?token=$TOKEN"

# 7. Get the final answer
curl -s $BASE/analyses/$ANALYSIS_ID -H "Authorization: Bearer $TOKEN" | jq
```

---

## Architecture

```
TrustRAG/
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── app/
│   │   │   ├── agent/              # LangGraph state machine & recovery loop
│   │   │   ├── api/                # Routers, auth, Pydantic schemas
│   │   │   ├── core/               # Config, logging, security, model registry
│   │   │   ├── db/                 # MongoDB (async) & Qdrant clients
│   │   │   ├── generation/         # LLM prompts and grounded generation
│   │   │   ├── ingestion/          # PDF/DOCX/TXT/MD/CSV/JSON/HTML parsers, chunker
│   │   │   ├── retrieval/          # Dense search, BM25, RRF fusion
│   │   │   ├── services/           # Business logic: KB, analysis, auth
│   │   │   └── verification/       # Batch NLI verifier & SHA-256 auditor
│   │   ├── config/models.yaml      # Model IDs, thresholds, tuning
│   │   └── tests/                  # 192 tests (all passing)
│   │
│   └── web/                        # React 18 + Vite 6 frontend
│       ├── src/
│       │   ├── components/         # ClaimInspector, EvidenceViewer, ExecutionTrace
│       │   ├── layouts/            # AppLayout, Sidebar, AuthGuard
│       │   ├── pages/              # 13 lazy-loaded pages
│       │   └── lib/                # API client, auth store, SSE streaming
│       └── package.json
│
├── docs/                           # Project documentation
│   ├── TRUSTRAG_specs.md           # Full product specification
│   ├── architecture/               # System design, ADRs
│   ├── audits/                     # Dated audit trail
│   ├── deployment/                 # Deployment guide
│   ├── security/                   # Threat model, security controls
│   └── evaluation/                 # Methodology
│
├── scripts/
│   ├── discover_local_models.py    # Pre-boot model discovery snapshot
│   ├── start_local_llm.sh          # Hardware-aware llama-server launcher
│   ├── apply_ports.py              # Propagate port changes everywhere
│   ├── setup.sh                    # Prerequisite checker
│   └── clear_qdrant.py             # Qdrant collection purge utility
│
├── load-test/
│   └── smoke.js                    # k6 smoke test
│
├── config/ports.yaml               # Single source of truth for service ports
├── docker-compose.yml              # Backend + Qdrant + MongoDB
└── .env.example                    # Environment template
```

---

## Technology stack

| Layer | What | Details |
|---|---|---|
| **Frontend** | React 18 + Vite 6 | Tailwind CSS, Motion springs, dark glassmorphic theme |
| **Backend** | FastAPI + Python 3.11 | Async REST API, Pydantic v2, SSE streaming |
| **Local LLMs** | Ollama / llama.cpp | `gemma3:1b` (Ollama) or `LiquidAI/LFM2.5-1.2B` (llama.cpp) |
| **Cloud LLMs** | Gemini / NVIDIA NIM | Optional — for when you want cloud-scale reasoning |
| **Embeddings** | BAAI/bge-small-en-v1.5 | 384d local CPU vectors, zero API cost |
| **Vector Store** | Qdrant | Embedded Rust engine, INT8 quantization, on-disk vectors |
| **Database** | MongoDB 7.0 | Metadata, chunks, claims, execution traces |
| **Agent Protocol** | MCP (JSON-RPC 2.0) | Universal tool interface for AI coding agents |
| **State Machine** | LangGraph | Multi-node adaptive recovery loop |
| **Auth** | JWT + Bcrypt | HS256 tokens, 12-round hashing, rate limiting |

---

## Testing

TrustRAG has 192 backend tests, 21 frontend tests, and 2 E2E tests — all passing.

**Backend:**
```bash
cd apps/api
source .venv/bin/activate

# Run all tests
pytest tests/ -q

# Lint
ruff check app/ tests/
ruff format --check app/ tests/
```

**Frontend:**
```bash
cd apps/web

# Unit & component tests
npm run test

# E2E tests (starts backend + browser automatically)
npm run test:e2e

# Lint & type check
npm run lint

# Production build
npm run build
```

**Load testing (requires k6):**
```bash
k6 run load-test/smoke.js
# Thresholds: <1% failures, p95 < 300ms, p99 < 500ms
```

---

## Troubleshooting

**MongoDB won't connect:**
```bash
# macOS
brew services start mongodb-community

# Linux
sudo systemctl enable --now mongod

# Windows (PowerShell as Admin)
Get-Service MongoDB | Start-Service

# Verify it's running
mongosh --eval "db.runCommand({ ping: 1 })"
```

**Ollama not responding:**
```bash
# Check if it's running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve    # or: brew services start ollama (macOS)
```

**Port already in use:**
```bash
# Find what's using the port
lsof -i :8000     # macOS/Linux
netstat -ano | findstr :8000    # Windows

# Kill it or change the port in config/ports.yaml
```

**Qdrant port confusion:**
When running via Docker, Qdrant maps host port `6335` to container port `6333`. From your host, use `http://localhost:6335`. Inside Docker, services talk directly to `http://qdrant:6333`.

**Embedding model download on first boot:**
The BGE embedding model (~120MB) downloads automatically from HuggingFace on the first API startup. It's cached at `~/.cache/huggingface` after that. If you hit rate limits, set `HF_TOKEN` in your `.env`.

---

## Documentation

| Document | What's in it |
|---|---|
| [Architecture](docs/architecture/architecture.md) | Technical design of the LangGraph state machine, hybrid search, claim decomposition |
| [Decision Log](docs/architecture/decision-log.md) | 20 ADRs explaining technology choices and tradeoffs |
| [Security Controls](docs/security/security-controls.md) | JWT auth, anti-IDOR, SSRF defense, defensive headers |
| [Threat Model](docs/security/threat-model.md) | STRIDE analysis, attack surface, countermeasures |
| [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md) | Production container setup, cloud hosting, env management |
| [System Audit](docs/audits/comprehensive_system_audit.md) | Multi-disciplinary evaluation: systems, security, AI/ML, QA |
| [Audit Report](docs/AUDIT_REPORT.md) | Engineering quality report — zero open defects |
| [Roadmap](docs/ROADMAP.md) | Milestones, completed phases, upcoming work |

---

## License

MIT — see [LICENSE](LICENSE).
