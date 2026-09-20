<a id="top"></a>

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

[Overview](#overview) · [Features](#features) · [Tech Stack](#tech-stack) · [Project Structure](#project-structure) · [Prerequisites](#prerequisites) · [Installation](#installation) · [Configuration](#configuration) · [Usage](#usage) · [API Reference](#api-reference) · [Testing](#testing) · [Deployment](#deployment) · [Troubleshooting](#troubleshooting) · [Contributing](#contributing)

---

## Overview

Standard RAG pipelines fail silently — confident-sounding answers with wrong or fabricated facts. TrustRAG closes that gap with an 8-stage pipeline:

```
Query → Route → Retrieve (hybrid) → Generate (grounded) → Decompose
      → Verify (NLI) → Audit (SHA-256) → Recover or Answer / Abstain
```

1. **Route** — deterministic query classification (no LLM call).
2. **Retrieve** — dense vectors (BGE-small, 384-d) + BM25 sparse + RRF fusion, optional cross-encoder rerank.
3. **Generate** — LLM answers only from retrieved chunks, with inline `[Segment N]` citations.
4. **Decompose** — answer split into atomic, checkable claims.
5. **Verify** — each claim judged `SUPPORTED` / `CONTRADICTED` / `NEUTRAL`.
6. **Audit** — SHA-256 tamper detection + temporal validity on sources.
7. **Recover** — budget-aware LangGraph loop (rewrite → re-retrieve → regenerate, ≤2 attempts).
8. **Answer or abstain** — returns the grounded answer, or refuses to guess.

The default stack runs **entirely locally** (Ollama or llama.cpp + local embeddings + embedded Qdrant + local MongoDB). No API keys required — Gemini, NVIDIA NIM, and Tavily search are optional.

---

## Features

| Area | Highlights |
|------|------------|
| Verification | 8-stage pipeline: route → retrieve → rerank → generate → decompose → verify → audit → recover |
| Retrieval | Hybrid dense + BM25 with server-side IDF and RRF fusion; deterministic router; 4 chunking strategies |
| Ingestion | PDF, DOCX, CSV, JSON, HTML, TXT, MD + RapidOCR fallback for scanned pages |
| Reliability | LangGraph self-heal loop with token/latency budgets; safe abstention; conflict detection |
| Auth & security | JWT (HS256, `iss`/`aud`), bcrypt, JTI revocation, login lockout, rate limits, SSRF guards |
| Integrations | MCP server (JSON-RPC 2.0) for Claude Desktop / Cursor / Windsurf; SSE live-progress streaming |
| Workbench UI | Dashboard, Playground, knowledge bases, evidence, claims, conflicts, experiments, trace viewer |
| Efficiency | ONNX embedding runtime (torch-free, ~500–1000 MB RAM saved); Metal/CUDA auto-detection |
| Ops | KB snapshots + rollback; Prometheus `/metrics`; A/B experiments with feature flags |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 6, Tailwind CSS 3, TanStack Query 5, React Router 7 |
| Backend | FastAPI 0.115, Python 3.11+, Pydantic v2, LangGraph, LangChain |
| LLM | Ollama / llama.cpp (local, default) · Gemini / NVIDIA NIM (optional cloud) |
| Embeddings | `BAAI/bge-small-en-v1.5` via PyTorch or ONNX Runtime |
| Storage | Qdrant (vectors) + MongoDB 7 (documents, async `motor`) |
| Quality gates | Ruff, ESLint, pytest, Vitest, Playwright, k6 |

---

## Project Structure

```
TrustRAG/
├── apps/
│   ├── api/                 # FastAPI backend (Python 3.11+)
│   │   ├── app/
│   │   │   ├── agent/       # LangGraph self-heal loop + query router
│   │   │   ├── api/v1/      # REST routes (auth, KBs, analyses, claims, …)
│   │   │   ├── core/        # config, security, LLM, embeddings, metrics
│   │   │   ├── db/          # MongoDB + Qdrant clients
│   │   │   ├── generation/  # grounded answer generator
│   │   │   ├── ingestion/   # parsers, chunkers, OCR fallback
│   │   │   ├── mcp/         # MCP tool server (JSON-RPC 2.0)
│   │   │   ├── retrieval/   # hybrid retriever + reranker
│   │   │   ├── services/    # analysis, KB, auth, experiment services
│   │   │   └── verification/# NLI verifier + SHA-256 integrity audit
│   │   ├── config/models.yaml  # model IDs, thresholds, tuning (v1.15)
│   │   ├── tests/           # backend suite (35 files)
│   │   └── pyproject.toml
│   └── web/                 # React frontend (Node 22+)
│       ├── src/{pages,components,services,lib,store,hooks,layouts,styles}/
│       └── e2e/             # Playwright specs
├── config/ports.yaml        # canonical port registry
├── scripts/                 # setup.sh, start_local_llm.sh, apply_ports.py, eval tools
├── docs/                    # specs, architecture, ADRs, evaluation, deployment
├── load-test/smoke.js       # k6 smoke test
├── docker-compose.yml       # api + web + qdrant
└── .env.example             # documented env template (copy to .env)
```

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Backend |
| Node.js (+ npm) | 22+ | Frontend |
| MongoDB | 7.0 | Document store (local or Atlas) |
| Ollama **or** llama.cpp | latest | Local LLM (at least one) |
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
brew install python@3.11 node@22 mongodb-community ollama

# Services
brew services start mongodb-community
ollama serve &
ollama pull gemma3:1b        # lightweight default (or: ollama pull llama3)

# Backend (terminal 1)
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,local-models]"
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd apps/web
npm install && npm run dev   # http://localhost:5173
```

> **8 GB RAM Macs:** before `ollama serve`, export `OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_FLASH_ATTENTION=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1`. Metal acceleration is auto-detected on Apple Silicon.

### 2b. Linux (Ubuntu/Debian)

```bash
# Prerequisites
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
sudo systemctl enable --now mongod

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:1b        # or: ollama pull llama3

# Backend (terminal 1)
cd apps/api
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,local-models]"
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd apps/web
npm install && npm run dev   # http://localhost:5173
```

CUDA is auto-detected with NVIDIA drivers. For low-RAM hosts set `TOKENIZERS_PARALLELISM=false` in `.env`.

### 2c. Windows (PowerShell)

Run installs as Administrator, then use a regular window afterwards.

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
# Backend (terminal 1)
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,local-models]"
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
docker compose up -d
docker compose logs -f
docker compose down        # stop (keeps volumes)
docker compose down -v     # stop + fresh start
```

- Frontend: <http://localhost:5173> · API docs: <http://localhost:8000/docs> · Health: <http://localhost:8000/api/v1/health>

### 3. Verify the install

```bash
./scripts/setup.sh                          # prerequisite checker (prints fixes)
curl http://localhost:8000/api/v1/health   # → {"status":"ok"}
# Open http://localhost:5173 in your browser
```

Prefer llama.cpp over Ollama? `./scripts/start_local_llm.sh` boots `llama-server` on `:8080` — the backend detects it automatically.

---

## Configuration

Resolution order: `apps/api/config/models.yaml` (defaults) → `config/ports.yaml` (ports) → `.env` (secrets + overrides win).

**Required** (`.env`):

```bash
JWT_SECRET=<output of: python3 -c "import secrets; print(secrets.token_hex(64))">
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=trustrag_db
```

**Common optional overrides** (full list in [.env.example](.env.example)):

```bash
LLM_PROVIDER=ollama            # ollama | llama_cpp | gemini | nvidia
LLM_MODEL=llama3               # provider-specific model name
EMBEDDING_PROVIDER=huggingface # huggingface (torch) | onnx (torch-free, low RAM)
QDRANT_URL=local               # local (embedded) | http://localhost:6335 (Docker) | cloud URL
TAVILY_API_KEY=                # empty → DuckDuckGo fallback for web grounding
VITE_API_URL=http://localhost:8000
APP_ENV=production             # production requires QDRANT_API_KEY
CORS_ORIGINS=https://your-domain.com
```

Default ports: API `8000` · Vite `5173` · llama-server `8080` · Ollama `11434` · MongoDB `27017` · Qdrant `6335→6333`. Change ports in `config/ports.yaml`, then run `python3 scripts/apply_ports.py` (enforced in CI with `--check`).

---

## Usage

### End-to-end via API

```bash
# 1. Register (saves the JWT)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"securepassword123","name":"You"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Create a knowledge base
KB_ID=$(curl -s -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"My First KB","description":"Test knowledge base"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Upload a document (PDF, DOCX, CSV, JSON, HTML, TXT, MD)
curl -X POST "http://localhost:8000/api/v1/knowledge-bases/$KB_ID/documents" \
  -H "Authorization: Bearer $TOKEN" -F "file=@./my_document.pdf"

# 4. Run a verified analysis
ANALYSIS_ID=$(curl -s -X POST http://localhost:8000/api/v1/analyses \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"What is this document about?\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 5. Inspect verified claims, evidence, and the execution trace
curl -s "http://localhost:8000/api/v1/analyses/$ANALYSIS_ID/claims" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
curl -s "http://localhost:8000/api/v1/analyses/$ANALYSIS_ID/evidence" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

On Windows PowerShell, use `Invoke-RestMethod` / `Invoke-WebRequest` against the same endpoints.

### Via the Playground UI

Open <http://localhost:5173/playground> → pick a knowledge base → ask a question → inspect the answer side-by-side with per-claim verdicts, evidence cards, reliability badges, conflict flags, and the full LangGraph trace. Other pages: `/dashboard`, `/knowledge-bases`, `/evidence`, `/claims`, `/conflicts`, `/experiments`, `/traces/:id`, `/settings`.

---

## API Reference

Interactive docs: <http://localhost:8000/docs> (Swagger) · `/redoc`. Base URL `http://localhost:8000`.

| Group | Endpoints |
|-------|-----------|
| Auth | `POST /api/v1/auth/register` · `POST /api/v1/auth/login` · `GET /api/v1/auth/me` · `POST /api/v1/auth/logout` |
| Knowledge bases | `POST/GET /api/v1/knowledge-bases` · `GET/DELETE /api/v1/knowledge-bases/{id}` · `POST …/{id}/documents` · `POST …/{id}/documents/from-url` · `POST …/{id}/snapshots` · `POST …/{id}/rollback/{snapshot_id}` |
| Analyses | `POST/GET /api/v1/analyses` · `GET /api/v1/analyses/{id}` · `…/{id}/claims` · `…/{id}/evidence` · `…/{id}/trace` · `…/{id}/detail` · `…/{id}/export` · `POST …/{id}/stream-ticket` · `GET …/{id}/stream` (SSE) |
| Evidence & claims | `GET /api/v1/evidence` · `GET /api/v1/claims` · `GET /api/v1/conflicts` |
| Experiments | `POST/GET /api/v1/experiments` · `GET /api/v1/experiments/{id}` |
| Documents | `GET/DELETE /api/v1/documents/{id}` |
| Ops | `GET /api/v1/health` · `GET /api/v1/health/detailed` · `GET /api/v1/metrics` · `GET /api/v1/models/providers` · `GET /api/v1/models/hardware` · `POST /api/v1/internal/ingest` |

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

---

## Deployment

| Component | Local dev | Docker Compose | Production |
|-----------|-----------|----------------|------------|
| LLM | Ollama / llama.cpp on host | Host via `host.docker.internal` | Self-hosted Ollama, Gemini, or NVIDIA NIM |
| Embeddings | BGE-small (auto-download ~120 MB) | Pre-exported ONNX copied into image | Same as dev |
| Vectors | Qdrant embedded (`local`) | `qdrant` container + volume | Qdrant Cloud |
| Database | Host MongoDB | Host via `host.docker.internal` | MongoDB Atlas |
| API | `uvicorn … --reload` | `api` container (non-root, hot-reload) | Cloud Run / Render / Railway / Fly.io |
| Web | `npm run dev` (HMR) | `web` container (Node 22 Alpine) | Cloudflare Pages / Vercel (`npm run build`) |

Production checklist: `APP_ENV=production` (+ `QDRANT_API_KEY`), `CORS_ORIGINS` locked to your domain, `SERVICE_TOKEN` set for `/internal/*`. Full runbook: [docs/deployment/DEPLOYMENT_GUIDE.md](docs/deployment/DEPLOYMENT_GUIDE.md).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port in use (`:8000`) | `lsof -i :8000 && kill <PID>` · Windows: `netstat -ano \| findstr :8000` → `taskkill /PID <PID> /F` |
| MongoDB refused | macOS: `brew services start mongodb-community` · Linux: `sudo systemctl start mongod` · Windows: `net start MongoDB` |
| Ollama down | `curl http://localhost:11434/api/tags` → `ollama serve &` → `ollama pull gemma3:1b` |
| Qdrant errors | `python3 scripts/apply_ports.py --print` · Docker: `docker compose ps` + `docker compose logs qdrant` |
| Embedding download fails | Check Hub reachability; or set `EMBEDDING_PROVIDER=onnx` (torch-free) / provide `HF_TOKEN` |
| Frontend can't reach API | `curl http://localhost:8000/api/v1/health`; ensure `VITE_API_URL=http://localhost:8000` (origin only) and `CORS_ORIGINS` includes the frontend |
| Web build errors | Delete `apps/web/node_modules`, `npm install`, `npm run build` |
| Full reset | Remove `apps/api/.venv`, `apps/web/node_modules`, `.env`; re-copy `.env.example` and redo [Installation](#installation) step 1 |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) (workflow: `READ → PLAN → BUILD → VERIFY → FIX → DOCUMENT → NEXT`; model IDs in `models.yaml`, secrets in `.env` only; conventional commits `feat:`/`fix:`/`docs:`/`test:`/`refactor:`). Security policy: [SECURITY.md](SECURITY.md).

```bash
./scripts/setup.sh
cd apps/api && ruff check app/ tests/ && python3 -m pytest -v
cd apps/web && npm run lint && npm test
```

---

## Documentation

| Document | Contents |
|----------|----------|
| [docs/TRUSTRAG_specs.md](docs/TRUSTRAG_specs.md) | Product specification (source of truth) |
| [docs/architecture/architecture.md](docs/architecture/architecture.md) | System design: LangGraph loop, MCP tools, data flow |
| [docs/architecture/decision-log.md](docs/architecture/decision-log.md) | ADRs D-01…D-33 |
| [docs/architecture/RAG_ARCHITECTURE.md](docs/architecture/RAG_ARCHITECTURE.md) | RAG pipeline reference |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Vision, milestones, phase tracking |
| [docs/evaluation/methodology.md](docs/evaluation/methodology.md) | Benchmarks + reliability metrics |
| [docs/deployment/DEPLOYMENT_GUIDE.md](docs/deployment/DEPLOYMENT_GUIDE.md) | Cloud production runbook |
| [docs/security/security-controls.md](docs/security/security-controls.md) · [docs/security/threat-model.md](docs/security/threat-model.md) | Controls + STRIDE model |

> Removed point-in-time audits/plans remain in git history (`git log -- docs/audits docs/PHASE_AUDIT_*.md docs/superpowers`).

---

## License

MIT — see [LICENSE](LICENSE).

---

[Back to Top](#top)
