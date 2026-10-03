# TrustRAG — Local-First RAG Reliability Workbench

**Detect hallucinations. Audit evidence integrity. Self-heal low-confidence answers.**

TrustRAG adds a verification layer between your LLM and your data: answers are split into atomic claims, each claim is checked against retrieved evidence with Natural Language Inference (NLI), sources are audited with SHA-256 hashes, and the system self-heals — or safely abstains — when evidence is insufficient.

![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Node 22+](https://img.shields.io/badge/node-22%2B-339933.svg)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)
![React 18](https://img.shields.io/badge/frontend-React%2018-61dafb.svg)
![Docker](https://img.shields.io/badge/deploy-Docker-2496ED.svg)

**Repository:** <https://github.com/MaithreshVaddi-27/TrustRAG> · **Version:** 0.1.0 · **License:** MIT ([LICENSE](LICENSE))

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [macOS](#macos)
  - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
  - [Windows (PowerShell)](#windowspowershell)
  - [Docker (any OS)](#docker-any-os-recommended-for-demos)
- [Configuration](#configuration)
- [Usage](#usage)
  - [End-to-end via API](#end-to-end-via-api)
  - [Via the Playground UI](#via-the-playground-ui)
- [Supported LLM Providers](#supported-llm-providers)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Audit Tracker](#audit-tracker)
- [Deployment](#deployment)
- [Optimization](#optimization)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Note](#note)

---

## Overview

Standard RAG pipelines fail silently — confident-sounding answers with wrong or fabricated facts. TrustRAG closes that gap with an 8-stage pipeline:

```
Query → Route → Retrieve (hybrid) → Generate (grounded) → Decompose
      → Verify (NLI) → Audit (SHA-256) → Recover or Answer / Abstain
```

1. **Route** — deterministic query classification (no LLM call).
2. **Retrieve** — dense vectors (BGE-small, 384-d) + BM25 sparse + RRF fusion, optional cross-encoder rerank.
3. **Generate** — LLM answers only from retrieved chunks, each factual sentence pinned to a source segment for verification.
4. **Decompose** — answer split into atomic, checkable claims.
5. **Verify** — each claim judged `SUPPORTED` / `CONTRADICTED` / `NEUTRAL`.
6. **Audit** — SHA-256 tamper detection + temporal validity on sources.
7. **Recover** — budget-aware LangGraph loop (rewrite → re-retrieve → regenerate, ≤2 attempts).
8. **Answer or abstain** — returns the grounded answer, or refuses to guess.

The default stack runs **entirely locally** (Ollama or llama.cpp or MLX + local embeddings + embedded Qdrant + local MongoDB). No API keys required — Gemini and Tavily search are optional.

---

## Features

| Area | Highlights |
|------|------------|
| **Verification** | 8-stage pipeline: route → retrieve → rerank → generate → decompose → verify → audit → recover |
| **Retrieval** | Hybrid dense + BM25 with server-side IDF and RRF fusion; deterministic router; 4 chunking strategies |
| **Ingestion** | PDF, DOCX, CSV, JSON, HTML, TXT, MD + RapidOCR fallback for scanned pages |
| **Reliability** | LangGraph self-heal loop with token/latency budgets; safe abstention; conflict detection |
| **Auth & security** | JWT (HS256, `iss`/`aud`), bcrypt, JTI revocation, login lockout, rate limits, SSRF guards |
| **Integrations** | MCP server (JSON-RPC 2.0) for Claude Desktop / Cursor / Windsurf; SSE live-progress streaming |
| **Workbench UI** | Dashboard, Playground, knowledge bases, evidence, claims, conflicts, trace viewer |
| **Efficiency** | ONNX embedding runtime (torch-free, ~500–1000 MB RAM saved); Metal/CUDA auto-detection |
| **Inference Acceleration** | KV cache quantization (q8_0 default), flash attention, prompt caching, context compression |
| **Ops** | KB snapshots + rollback; Prometheus `/metrics` |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite 6, Tailwind CSS 3, TanStack Query 5, React Router 7 |
| **Backend** | FastAPI 0.115, Python 3.11+, Pydantic v2, LangGraph, LangChain |
| **LLM** | Ollama / llama.cpp / **MLX** (local, default) · Gemini (optional cloud) |
| **Embeddings** | `BAAI/bge-small-en-v1.5` via ONNX Runtime (torch-free, default) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` via ONNX Runtime (int8) |
| **Storage** | Qdrant (vectors) + MongoDB 7 (documents, async `motor`) |
| **Quality gates** | Ruff, ESLint, pytest, Vitest, Playwright, k6 |

---

## Project Structure

```
TrustRAG/
├── apps/
│   ├── api/                    # FastAPI backend (Python 3.11+)
│   │   ├── app/
│   │   │   ├── agent/          # LangGraph self-heal loop + query router
│   │   │   ├── api/v1/         # REST routes (auth, KBs, analyses, claims, …)
│   │   │   ├── core/           # config, security, LLM, embeddings, metrics
│   │   │   ├── db/             # MongoDB + Qdrant clients
│   │   │   ├── generation/     # grounded answer generator
│   │   │   ├── ingestion/      # parsers, chunkers, OCR fallback
│   │   │   ├── mcp/            # MCP tool server (JSON-RPC 2.0)
│   │   │   ├── retrieval/      # hybrid retriever + reranker
│   │   │   ├── services/       # analysis, KB, auth, experiment services
│   │   │   └── verification/   # NLI verifier + SHA-256 integrity audit
│   │   ├── config/models.yaml  # model IDs, thresholds, tuning (v1.23)
│   │   ├── tests/              # backend suite (mocked, no live services)
│   │   └── pyproject.toml
│   └── web/                    # React frontend (Node 22+)
│       ├── src/{pages,components,services,lib,store,hooks,layouts,styles}/
│       └── e2e/                # Playwright specs
├── config/ports.yaml           # canonical port registry
├── scripts/                    # bootstrap.py, setup.sh, start_local_llm.sh, start_mlx_server.sh, eval_provider.sh, apply_ports.py, …
├── docs/                       # specs, architecture, ADRs, evaluation, deployment
├── load-test/smoke.js          # k6 smoke test
├── docker-compose.yml          # api + web + qdrant
└── .env.example                # documented env template (copy to .env)
```

Model weights (`apps/api/.model_cache/*.onnx`, `*.gguf`, Hugging Face
snapshots) are **never committed to git** — every machine fetches them once
via `scripts/bootstrap.py` (see [Installation](#installation)).

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11–3.12 | Backend (3.13+ breaks the torch/onnxscript ONNX export) |
| Node.js (+ npm) | 22+ | Frontend |
| MongoDB | 7.0 | Document store (local or Atlas) |
| Ollama **or** llama.cpp **or** MLX | latest | Local LLM (at least one) |
| Docker + Compose | latest | Docker path only |
| Git | latest | Clone |
| Disk / RAM | ~8 GB free · 8 GB RAM min (16 GB recommended) | Models: embeddings ~120 MB, LLM ~1–5 GB |

---

## Installation

### 1. Clone and configure (all platforms)

```bash
git clone https://github.com/MaithreshVaddi-27/TrustRAG.git
cd TrustRAG
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(64))"
# Paste the output as JWT_SECRET=<value> in .env (min 32 chars)
```

### 2a. macOS

```bash
# Prerequisites
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew tap mongodb/brew   # required once for the mongodb-community formula
brew install python@3.11 node@22 mongodb-community ollama

# Services
brew services start mongodb-community
ollama serve &
ollama pull gemma3:1b        # lightweight default (or: ollama pull llama3)

# llama.cpp (local GGUF models) — hardware-aware launcher, serves on :8080
brew install llama.cpp   # provides the `llama-server` binary used below
./scripts/start_local_llm.sh   # auto-detects Metal/CUDA, sets KV q8_0 + flash-attn, max 1 model on 8GB

# MLX (Apple Silicon only, optional) — serves on :8090
# See [MLX on Mac](docs/PERFORMANCE-GUIDE.md#4-mlx-on-mac-apple-silicon-free-fastest-toks-per-watt)
pipx install mlx-lm
./scripts/start_mlx_server.sh              # model + port come from config/ports.yaml
./scripts/start_mlx_server.sh --check      # scan :8090-:8094, list what is up
./scripts/start_mlx_server.sh --port 8091  # extra model on the next port (1 model/process)

# Backend (terminal 1)
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,local-models]"
python ../../scripts/bootstrap.py   # one-time: fetch ONNX weights, snapshot local LLMs
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd apps/web
npm install && npm run dev   # http://localhost:5173
```

> **8 GB RAM Macs:** before `ollama serve`, export `OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_FLASH_ATTENTION=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1`. Metal acceleration is auto-detected on Apple Silicon.

### 2b. Linux (Ubuntu/Debian)

```bash
# Prerequisites (Ubuntu 22.04 jammy; on 24.04 noble or other distros adjust
# the MongoDB repo line below. Stock Ubuntu ≤22.04 ships Python ≤3.10 — add
# the deadsnakes PPA first: sudo add-apt-repository ppa:deadsnakes/ppa)
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3.11-dev \
  python3-pip build-essential curl git
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# MongoDB 7.0
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod   # no systemd (WSL2/Docker)? use: sudo service mongod start

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:1b        # or: ollama pull llama3

# llama.cpp (local GGUF models) — hardware-aware launcher
# Install the binary first: download a release from
# https://github.com/ggerganov/llama.cpp/releases (needs `llama-server` on PATH)
./scripts/start_local_llm.sh   # auto-detects CUDA, sets KV q8_0 + flash-attn, max 1 model on 8GB

# Backend (terminal 1)
cd apps/api
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,local-models]"
python ../../scripts/bootstrap.py   # one-time: fetch ONNX weights, snapshot local LLMs
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd apps/web
npm install && npm run dev   # http://localhost:5173
```

> CUDA is auto-detected with NVIDIA drivers. For low-RAM hosts set `TOKENIZERS_PARALLELISM=false` in `.env`.

### 2c. Windows (PowerShell)

```powershell
winget install Python.Python.3.11
winget install OpenJS.NodeJS.LTS
winget install MongoDB.Server
winget install Ollama.Ollama
winget install Git.Git
# Close and reopen PowerShell, then:
net start MongoDB
ollama pull gemma3:1b
```

```powershell
# llama.cpp (local GGUF models) — use the provided startup script or run llama-server directly
# For now, use WSL2 for llama.cpp on Windows (see Linux instructions)
# Start: wsl ./scripts/start_local_llm.sh
```

```powershell
# Backend (terminal 1)
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,local-models]"
python ..\..\scripts\bootstrap.py   # one-time: fetch ONNX weights, snapshot local LLMs
uvicorn app.main:app --reload --port 8000
```

```powershell
# Frontend (terminal 2)
cd apps\web
npm install
npm run dev   # http://localhost:5173
```

> Execution-policy error → `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`. Prefer WSL2? Run `wsl --install` and follow the Linux steps inside it.

### 2d. Docker (any OS, recommended for demos)

MongoDB and the LLM stay on the host; `api` reaches them via `host.docker.internal`, Qdrant runs in a container.

```bash
cp .env.example .env   # set JWT_SECRET (see step 1)
# One-time on the HOST (the api image is torch-free and cannot export itself):
apps/api/.venv/bin/python scripts/bootstrap.py   # Windows: apps\api\.venv\Scripts\python.exe scripts\bootstrap.py
docker compose up -d
# One-time: copy the host-exported weights into the api container's cache volume:
docker cp apps/api/.model_cache/. trustrag_api:/app/.model_cache/
docker compose logs -f
docker compose down        # stop (keeps volumes)
docker compose down -v     # stop + fresh start
```

- Frontend: <http://localhost:5173> · API docs: <http://localhost:8000/docs> · Health: <http://localhost:8000/api/v1/health>

### 3. Fetch model weights (all platforms, one-time)

Model weights are **never committed to git** — every machine (new clone or
fresh `git pull`) fetches them once: ~120 MB ONNX embeddings + reranker.
Multi-GB LLM blobs stay with ollama / llama-server and are never
auto-downloaded.

```bash
# From the repo root, using the backend venv (macOS/Linux):
apps/api/.venv/bin/python scripts/bootstrap.py
# Check only, no downloads (also covered by ./scripts/setup.sh):
apps/api/.venv/bin/python scripts/bootstrap.py --verify
# Windows PowerShell:
apps\api\.venv\Scripts\python.exe scripts\bootstrap.py
```

What it does: verifies `apps/api/.model_cache/` (canonical
`bge-small-en-v1.5.onnx` + `reranker-ms-marco-MiniLM-L-6-v2_int8.onnx`),
exports anything missing with ONNX as the default provider, and snapshots
your installed local LLMs so the backend serves them from the first request.
Already cached → exits in ~1 s. After `git pull`, re-run it: a changed
`models.yaml` model ID is detected automatically and only the new weights are
fetched (`--force` rebuilds everything).

### 4. Verify the install

```bash
./scripts/setup.sh                          # prerequisite checker (prints fixes)
curl http://localhost:8000/api/v1/health   # → {"status":"ok"}
# Open http://localhost:5173 in your browser
```

> **Run both llama.cpp and MLX simultaneously (Apple Silicon):**
> ```bash
> # Terminal 1: llama.cpp on :8080
> ./scripts/start_local_llm.sh
>
> # Terminal 2: MLX on :8090 (id must match MLX_MODEL in .env / model_mlx in models.yaml)
> ./scripts/start_mlx_server.sh mlx-community/Llama-3.2-3B-Instruct-4bit
>
> # Terminal 3: Backend (auto-detects both)
> cd apps/api && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
> ```
>
> Both servers appear in `/api/v1/models/providers` and the Playground dropdown independently.

---

## Configuration

Resolution order: `apps/api/config/models.yaml` (defaults) → `config/ports.yaml` (ports) → `.env` (secrets + overrides win).

### Required (`.env`)

```bash
JWT_SECRET=<output of: python3 -c "import secrets; print(secrets.token_hex(64))">
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=trustrag_db
```

### Common optional overrides (full list in [.env.example](.env.example))

```bash
LLM_PROVIDER=llama_cpp            # ollama | llama_cpp | mlx | gemini
LLM_MODEL=LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M
MLX_MODEL=mlx-community/Llama-3.2-1B-Instruct-4bit   # Apple Silicon only
# Embeddings: single ONNX engine (BAAI/bge-small-en-v1.5, 384d) from
# apps/api/config/models.yaml `embedding.model` — no provider choice, no env flag.
QDRANT_URL=local                  # local (embedded) | http://localhost:6335 (Docker) | cloud URL
TAVILY_API_KEY=                   # empty → DuckDuckGo fallback for web grounding
VITE_API_URL=http://localhost:8000
APP_ENV=production                # production requires QDRANT_API_KEY
CORS_ORIGINS=https://your-domain.com
```

Default ports: API `8000` · Vite `5173` · llama-server `8080` · **MLX server `8090`** · Ollama `11434` · MongoDB `27017` · Qdrant `6335→6333`. Change ports in `config/ports.yaml`, then run `python3 scripts/apply_ports.py` (enforced in CI with `--check`).

---

## Usage

### End-to-end via API

```bash
# 1. Register (returns the user profile — NOT a token)
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"Str0ng!Passphrase2026","full_name":"You"}'

# 2. Log in to get the JWT (registration does not return one)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"Str0ng!Passphrase2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Create a knowledge base
KB_ID=$(curl -s -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"My First KB","description":"Test knowledge base"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. Upload a document (PDF, DOCX, CSV, JSON, HTML, TXT, MD — 20 MB max)
curl -X POST "http://localhost:8000/api/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $TOKEN" -F "file=@./my_document.pdf"

# 5. Run a verified analysis
ANALYSIS_ID=$(curl -s -X POST http://localhost:8000/api/v1/analyses \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"What is this document about?\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 6. Inspect verified claims, evidence, and the execution trace
curl -s "http://localhost:8000/api/v1/analyses/$ANALYSIS_ID/claims" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
curl -s "http://localhost:8000/api/v1/analyses/$ANALYSIS_ID/evidence" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

> **Password rules.** Registration enforces complexity: at least 12 characters,
> with an uppercase letter, a lowercase letter, a digit, and a special
> character, and at most 72 bytes (the bcrypt limit). A password that fails
> these is rejected with `422` and a specific message. `Str0ng!Passphrase2026`
> above satisfies all of them.

> **Status codes.** Analysis runs are asynchronous — `POST /analyses` returns
> immediately with `status: "pending"`. Poll `GET /analyses/{id}` (or stream
> `GET /analyses/{id}/stream`) until the status settles, otherwise the claims
> and evidence endpoints will return nothing useful.

On Windows PowerShell, use `Invoke-RestMethod` / `Invoke-WebRequest` against the same endpoints.

### Via the Playground UI

Open <http://localhost:5173/playground> → pick a knowledge base → ask a question → inspect the answer side-by-side with per-claim verdicts, evidence cards, reliability badges, conflict flags, and the full LangGraph trace. Other pages: `/dashboard`, `/knowledge-bases`, `/evidence`, `/claims`, `/conflicts`, `/traces/:id`, `/settings`.

---

## Supported LLM Providers

TrustRAG supports multiple LLM providers interchangeably. Switch via `LLM_PROVIDER` env var or per-request `llm_provider` parameter.

| Provider | Models | RAM | Notes |
|----------|--------|-----|-------|
| **llama_cpp** | LFM2.5-1.2B, Granite-4.2-3B, SmolLM3-3B, EXAONE-2.4B, SmolLM2-1.7B | 2–4 GB | Default. Hardware-aware `scripts/start_local_llm.sh` auto-detects Metal/CUDA, sets KV q8_0 + flash-attn, max 1 concurrent model on 8 GB |
| **ollama** | gemma3:1b, qwen3:1.7b, llama3 | 1–3 GB | `ollama serve` + `ollama pull <model>`. Set `OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_FLASH_ATTENTION=1` for 8 GB RAM |
| **mlx** | Llama-3.2-1B-4bit, Llama-3.2-3B-4bit, LFM2.5-1.2B-4bit | 1–3 GB | Apple Silicon only. `./scripts/start_mlx_server.sh [id]` on :8090. Runs alongside llama.cpp on :8080 |

#### Small vs large models

The pipeline adapts to model size automatically — no env var, no separate mode:

| | ≤3B (LFM2.5-1.2B, Llama-3.2-1B, Qwen3-1.7B) | larger (Granite-16B, Gemini, …) |
|---|---|---|
| Generation prompt | compact CRAFT — 4 rules + 1 worked example (~770 chars) | full CRAFT — 6 rules, scope/loop guidance (~2350 chars) |
| Verification | two-step decompose → NLI | fused decompose+verify in one call |
| Claim/context caps | `lean_tier` (5 / 5) | `balanced_tier` / `cloud_tier` (8 / 8) |

Detection is by model-id size marker (`is_small_model()` in `app/llm/local_llm.py`), deliberately conservative: an unrecognised id keeps the full-strength path, and cloud providers are never downgraded. To compare providers on the frozen dataset:

```bash
./scripts/eval_provider.sh llama_cpp --email you@example.com --password '…' --kb-id $ID
./scripts/eval_provider.sh gemini    --email you@example.com --password '…' --kb-id $ID
```

Each provider writes to its own `docs/evaluation/results/<provider>/` and records a separate experiment.
| **gemini** | gemini-3.5-flash-lite | Cloud | Requires `GEMINI_API_KEY`. Fast, cheap, supports structured output natively |

### Per-tier caps (auto-selected by provider + RAM)

| Tier | `max_verification_claims` | `max_context_chunks` | `max_claim_retrievals` |
|------|---------------------------|----------------------|------------------------|
| Lean (≤8 GB) | 5 | 5 | 2 |
| Balanced (≤16 GB) | 8 | 8 | 3 |
| Cloud | 8 | 8 | 3 |

### Provider-aware temperature

For factual/verification queries with local models, temperature is automatically set to **0.0** to minimize hallucination. Generation uses 0.2 by default.

---

## API Reference

Interactive docs: <http://localhost:8000/docs> (Swagger) · `/redoc`. Base URL `http://localhost:8000`.

| Group | Endpoints |
|-------|-----------|
| **Auth** | `POST /api/v1/auth/register` · `POST /api/v1/auth/login` · `GET /api/v1/auth/me` · `POST /api/v1/auth/logout` |
| **Knowledge bases** | `POST/GET /api/v1/knowledge-bases` · `GET/DELETE /api/v1/knowledge-bases/{id}` · `POST …/{id}/documents` · `POST …/{id}/documents/from-url` · `POST …/{id}/snapshots` · `POST …/{id}/rollback/{snapshot_id}` |
| **Analyses** | `POST/GET /api/v1/analyses` · `GET /api/v1/analyses/{id}` · `…/{id}/claims` · `…/{id}/evidence` · `…/{id}/trace` · `…/{id}/detail` · `…/{id}/export` · `POST …/{id}/stream-ticket` · `GET …/{id}/stream` (SSE) |
| **Evidence & claims** | `GET /api/v1/evidence` · `GET /api/v1/claims` · `GET /api/v1/conflicts` |
| **Documents** | `GET/DELETE /api/v1/documents/{id}` |
| **Ops** | `GET /api/v1/health` · `GET /api/v1/health/detailed` · `GET /api/v1/metrics` · `GET /api/v1/models/providers` · `GET /api/v1/models/hardware` · `POST /api/v1/internal/ingest/document` · `POST /api/v1/internal/ingest/url` · `POST /api/v1/internal/search` · `POST /api/v1/internal/verify/claims` (service-token auth) |

---

## Testing

```bash
# Backend — pytest (no live services needed; mocked). macOS/Linux:
cd apps/api && source .venv/bin/activate && python3 -m pytest -v
# Windows:
cd apps\api; .\.venv\Scripts\Activate.ps1; python -m pytest -v
# With coverage: python3 -m pytest -v --cov=app --cov-report=term-missing
```

```bash
# Frontend — Vitest unit tests
cd apps/web && npm test

# End-to-end — Playwright (needs the live stack running)
npx playwright install    # first time only
npm run test:e2e          # headless · npm run test:e2e:ui (interactive)

# Load — k6 (repo root)
k6 run load-test/smoke.js
```

Lint: `cd apps/api && ruff check app/ tests/ && ruff format --check app/ tests/` · `cd apps/web && npm run lint`.

> **Toolchain notes:** backend Python 3.11–3.12 with `uv` (`uv sync`), frontend Node 22+ (`engines`-pinned — Vitest breaks on Node 20). CI runs Ubuntu jobs plus a Windows + macOS smoke matrix (`cross-platform`), all gated in `ci-gate`.

---

## Audit Tracker

All bug/error/issue/dead-code findings from the latest production pass live in [`docs/AUDIT.md`](docs/AUDIT.md) — findings with severity, fix, and verification evidence; the verified-solid areas (security, RAG pipeline, inference, DevOps); manual/live E2E verification results; remaining risks; and the re-audit checklist. Earlier point-in-time audit reports were consolidated into it (history preserved in git).

Test-coverage gaps for the analysis service (the lowest-covered core module) are mapped in [`docs/ANALYSIS_SERVICE_TEST_GAPS.md`](docs/ANALYSIS_SERVICE_TEST_GAPS.md) — uncovered regions with risk, and a prioritized 17-test plan to lift it from 54% to ~85%.

---

## Deployment

| Component | Local dev | Docker Compose | Production |
|-----------|-----------|----------------|------------|
| **LLM** | Ollama / llama.cpp on host | Host via `host.docker.internal` | Self-hosted Ollama or Gemini |
| **Embeddings** | ONNX BGE-small via `scripts/bootstrap.py` (~120 MB, one-time) | Host-exported ONNX via `docker cp` into the cache volume | Same as dev |
| **Vectors** | Qdrant embedded (`local`) | `qdrant` container + volume | Qdrant Cloud |
| **Database** | Host MongoDB | Host via `host.docker.internal` | MongoDB Atlas |
| **API** | `uvicorn … --reload` | `api` container (non-root, hot-reload) | Cloud Run / Render / Railway / Fly.io |
| **Web** | `npm run dev` (HMR) | `web` container (Node 22 Alpine) | Cloudflare Pages / Vercel (`npm run build`) |

Production checklist: `APP_ENV=production` (+ `QDRANT_API_KEY`), `CORS_ORIGINS` locked to your domain, `SERVICE_TOKEN` set for `/internal/*`. Full runbook: [docs/deployment/DEPLOYMENT_GUIDE.md](docs/deployment/DEPLOYMENT_GUIDE.md).

---

## Optimization

TrustRAG implements extensive inference acceleration and memory optimization techniques. All options are configurable via `apps/api/config/models.yaml` (config version **1.23**) with environment variable overrides.

### Inference Acceleration

| Feature | Description | Config Key | Default |
|---------|-------------|------------|---------|
| **KV Cache Quantization** | Quantize KV cache to q8_0/q4_0/q4_1, honored by `start_local_llm.sh` (saves 50-75% VRAM) | `optimization.kv_cache_quantization` | `"q8_0"` |
| **Flash Attention** | O(N) memory attention via SRAM tiling (llama.cpp) | `optimization.flash_attention` | `true` |
| **Prompt Caching** | Reuse KV cache for static prompt prefixes (llama.cpp `cache_prompt`, Ollama `num_keep`) | `optimization.prompt_caching` | `true` |
| **Sampling Knobs** | Min-p / top-k sampling (disabled by default: `0.0`/`0` = off) + early EOS exit for faster generation | `local_llm.min_p`, `local_llm.top_k`, `local_llm.early_exit_eos` | `0.0`, `0`, `true` |
| **Batch Prompt Processing** | `n_batch` controls prompt encoding parallelism | `local_llm.num_batch` | `512` |
| **Connection Pooling** | HTTP keep-alive (30s) with connection limits for local servers | Internal | `5 keepalive / 10 max` |

### Memory Optimization

| Feature | Description | Config Key | Default |
|---------|-------------|------------|---------|
| **Dynamic Context Sizing** | Token-aware `num_ctx` per request using tiktoken | `local_llm.num_ctx` (base) | `4096` |
| **Aggressive Model Eviction** | Registry limits instances by RAM: 1 (≤8GB) / 2 (≤16GB) / 4 (32GB+) | Internal | Dynamic |
| **ONNX Reranker (int8)** | 3-4x CPU speedup, torch-free inference | `reranker.use_onnx` | `true` |
| **ONNX Runtime (shared)** | One tuned session factory for embeddings + reranker: capped threads, full graph fusion, sequential exec | `onnx.intra_op_threads`, `onnx.graph_optimization`, `onnx.cpu_mem_arena` | `0` (auto ≤4), `all`, `true` |
| **Reranker Batch/SeqLen** | Tokenize+infer micro-batches; max pair length | `reranker.batch_size`, `reranker.max_seq_length` | `16`, `512` |
| **Retrieval Budgets** | Per-branch + hybrid timeouts; one hung branch degrades instead of pinning a worker | `retrieval.branch_timeout_seconds`, `retrieval.hybrid_timeout_seconds` | `0` (45s/60s fallback) |
| **Qdrant Upsert Batch** | Points per upsert call (no network timeouts on big docs) | `ingestion.qdrant_upsert_batch` | `100` |
| **ONNX Embeddings** | Single torch-free embedding engine, ~500-1000 MB RAM saved | `embedding.model` | `BAAI/bge-small-en-v1.5` |
| **Context Compression** | Hierarchical summarization before LLM call | `optimization.context_compression_enabled` | `false` |
| **Adaptive Top-K** | Reduces retrieval when confidence high (RRF > 0.02) | `optimization.adaptive_top_k` | `true` |

### Environment Variable Overrides

All config options support env overrides:

| Config | Env Variable |
|--------|-------------|
| KV Cache Quantization | `KV_CACHE_QUANTIZATION` |
| Flash Attention | `FLASH_ATTENTION` |
| Prompt Caching | `PROMPT_CACHING` |
| Adaptive Top-K | `ADAPTIVE_TOP_K` |
| Adaptive Threshold/Cap | `ADAPTIVE_TOP_K_THRESHOLD`, `ADAPTIVE_TOP_K_CAP` |
| Retrieval Budgets | `RETRIEVAL_BRANCH_TIMEOUT_SECONDS`, `RETRIEVAL_HYBRID_TIMEOUT_SECONDS` |
| Qdrant Upsert Batch | `QDRANT_UPSERT_BATCH` |
| Context Compression | `CONTEXT_COMPRESSION_ENABLED`, `MAX_CONTEXT_TOKENS` |
| Local LLM Params | `LOCAL_LLM_NUM_CTX`, `LOCAL_LLM_NUM_BATCH`, `LOCAL_LLM_KEEP_ALIVE`, `LOCAL_LLM_MIN_P`, `LOCAL_LLM_TOP_K`, `LOCAL_LLM_EARLY_EXIT_EOS` |
| Reranker | `RERANKER_USE_ONNX`, `RERANKER_ONNX_MODEL_PATH`, `RERANKER_BATCH_SIZE`, `RERANKER_MAX_SEQ_LENGTH` |
| ONNX Runtime | `ONNX_PROVIDERS`, `ONNX_INTRA_OP_THREADS`, `ONNX_INTER_OP_THREADS`, `ONNX_GRAPH_OPTIMIZATION`, `ONNX_CPU_MEM_ARENA`, `ONNX_MEM_PATTERN`, `ONNX_EMBED_MICRO_BATCH` |
| Embedding model | `embedding.model` in `apps/api/config/models.yaml` (single engine, no env flag) |
| Model weights dir | `MODEL_CACHE_DIR` (ONNX embedding + reranker `.onnx` files) |

---

## Security

- **JWT** — HS256, `iss`/`aud` validation, JTI revocation denylist, 60 min expiry
- **Passwords** — bcrypt cost 12, timing-safe comparison
- **Login lockout** — MongoDB TTL collection (`failed_logins`), configurable attempts/window
- **Rate limiting** — SlowAPI with Redis backend (prod) or in-memory (dev), per-endpoint caps
- **SSRF protection** — URL validation with DNS allowlist, IP pinning, host-header guard
- **MCP auth** — Service token required for all tools, prompt/model caps
- **CORS** — Origins from `CORS_ORIGINS`, credentials allowed
- **Input validation** — Pydantic v2, filename sanitization, size limits, charset detection on sample

---

## Troubleshooting

Full per-OS field guide (20-row failure table): [docs/ONBOARDING-TROUBLESHOOTING.md](docs/ONBOARDING-TROUBLESHOOTING.md).

| Issue | Fix |
|-------|-----|
| `LLM_UNAVAILABLE` (llama.cpp) | Start `./scripts/start_local_llm.sh --max 1` (serves on :8080) |
| `LLM_UNAVAILABLE` (ollama) | `ollama serve` + `ollama pull <model>` |
| `LLM_UNAVAILABLE` (gemini) | Check API key, retry, or switch provider |
| `LLM_UNAVAILABLE` (MLX) | `./scripts/start_mlx_server.sh` (Apple Silicon); `--check` to see which ports are up |
| `Database not initialized` | Ensure MongoDB running; check `MONGODB_URI` |
| `503 Service Unavailable` | DB not connected; check `connect_db()` in lifespan |
| OOM on 8 GB | `export OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_FLASH_ATTENTION=1 OLLAMA_MAX_LOADED_MODELS=1` |
| ONNX weights missing / stale after `git pull` | `apps/api/.venv/bin/python scripts/bootstrap.py` (`--verify` to check, `--force` to rebuild) |
| ONNX export fails (`No module named 'onnxscript'` / `torch` / `onnx`) | Reinstall export deps: `cd apps/api && .venv/bin/pip install -e ".[local-models]"`, then re-run bootstrap |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) (workflow: `READ → PLAN → BUILD → VERIFY → FIX → DOCUMENT → NEXT`; model IDs in `apps/api/config/models.yaml`, secrets in `.env` only; conventional commits `feat:`/`fix:`/`docs:`/`test:`/`refactor:`). Security policy: [SECURITY.md](SECURITY.md).

```bash
./scripts/setup.sh
cd apps/api && ruff check app/ tests/ && python3 -m pytest -v
cd apps/web && npm run lint && npm test
```

---

## Note

- For **macOS**, use the provided brew commands and remember to set environment variables for JVM/Ollama tuning on low-memory machines.
- For **Linux**, ensure MongoDB service is enabled and started; Ollama service can be managed via systemd if preferred.
- For **Windows**, PowerShell execution policy may need adjustment; using WSL2 is recommended for a native Linux-like experience.
- Docker setup simplifies evaluation but expects MongoDB and LLM on the host; adjust `.env` for production secrets and external services.
- MLX is Apple‑Silicon only; ensure you have the appropriate hardware and follow the [MLX on Mac guide](docs/PERFORMANCE-GUIDE.md#4-mlx-on-mac-apple-silicon-free-fastest-toks-per-watt) if you wish to use it alongside Ollama or llama.cpp.