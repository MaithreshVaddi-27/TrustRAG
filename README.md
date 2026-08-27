# TRUSTRAG — AI Reliability Workbench

> **Retrieve. Verify. Diagnose. Recover.**  
> Production-oriented RAG reliability pipeline with claim verification, failure diagnosis, and adaptive recovery.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-latest-green) ![React](https://img.shields.io/badge/React-18-61DAFB) ![LangGraph](https://img.shields.io/badge/LangGraph-agentic-orange) ![Qdrant](https://img.shields.io/badge/Qdrant-hybrid--RAG-red)

---

## What TRUSTRAG Does

Standard RAG pipelines fail silently — they retrieve irrelevant evidence, generate unsupported claims, and cite documents that don't actually say what's claimed.

TRUSTRAG implements a structured reliability loop:

```
Query → Retrieve (dense + sparse hybrid) → Rerank
      → Generate (Gemini grounded) → Decompose Claims
      → Verify Claims (NLI) → Analyze Evidence Integrity (SHA-256)
      → Diagnose Failure → Adaptive Recovery (LangGraph)
      → Re-verify → Grounded Answer / ABSTAIN
```

The portfolio differentiator is the **reliability → diagnosis → recovery loop**. When a reliability threshold fails, TRUSTRAG diagnoses the specific failure type (retrieval gap, evidence conflict, low coverage) and applies a targeted recovery strategy — query rewrite or expanded re-retrieval — rather than just warning the user.

---

## Engineering Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite 6 + Tailwind CSS + React Router + TanStack Query + Recharts |
| Backend | FastAPI + Python 3.11 + Pydantic v2 + Motor (async MongoDB) |
| LLM | Google Gemini Flash (via `langchain-google-genai`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` · local, free, no API key |
| Agentic Workflow | LangGraph (StateGraph — retrieval → generation → verification → recovery) |
| Vector Store | Qdrant — dense + sparse/BM25 + hybrid RRF fusion |
| Database | MongoDB Atlas (M0 free tier) |
| Streaming | Server-Sent Events (SSE) for live execution traces |
| Auth | JWT (HS256) + bcrypt password hashing |
| Rate Limiting | SlowAPI (per-IP, configurable per endpoint) |

**All services are free-tier compatible. No paid dependencies required.**

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Architecture | ✅ Complete | ADRs, threat model, system design docs |
| 1 — Foundation | ✅ Complete | Monorepo, centralized config, Docker, CI/security workflows |
| 2 — Frontend | ✅ Complete | React shell, workbench design system, all 11 pages |
| 3 — Backend | ✅ Complete | FastAPI CRUD routes, MongoDB Atlas, analysis lifecycle |
| 4 — Security | ✅ Complete | JWT auth, bcrypt, IDOR prevention, rate limiting |
| 5 — Ingestion | ✅ Complete | Document processing (PDF/TXT/MD), Qdrant hybrid indexing |
| 6 — Baseline RAG | ✅ Complete | LangChain + Gemini + hybrid dense/sparse retrieval + RRF fusion |
| 7 — Verification | ✅ Complete | Claim decomposition, NLI verification, evidence matching |
| 8 — Integrity | ✅ Complete | Provenance, SHA-256 integrity, temporal validity filtering |
| 9 — Recovery | ✅ Complete | LangGraph agentic adaptive recovery (query rewrite + re-retrieval) |
| 10 — Observability | ✅ Complete | SSE live traces, persisted trace events, inactivity timeout |
| 11 — Evaluation | ✅ Complete | Experiment configs, custom metrics, ablation runs |
| 12 — Production | ✅ Complete | Cost controls, error hardening, security audit, CI/CD |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local API + Qdrant)
- [Node.js 20+](https://nodejs.org/) (for frontend dev server)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) free M0 cluster
- [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier)

### 1. Clone

```bash
git clone https://github.com/MaithreshVaddi-27/TrustRAG
cd TrustRAG
```

### 2. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and fill in these values:

```env
JWT_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(64))">
GEMINI_API_KEY=<your Gemini API key>
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
```

> [!IMPORTANT]
> The `MONGODB_URI` must be a valid MongoDB Atlas connection string.
> The `JWT_SECRET` must be at least 32 characters long.

### 3. Start Backend + Qdrant (Docker)

```bash
docker compose up
```

> **First run takes ~2 minutes** — the API container downloads the sentence-transformer embedding model (~90MB).

Wait for both containers to be healthy:
```bash
# Qdrant health
curl http://localhost:6335/readyz

# API health
curl http://localhost:8000/api/v1/health
```

### 4. Start Frontend

```bash
cd apps/web
npm install
npm run dev
# Open http://localhost:5173
```

### 5. Verify end-to-end

1. Open `http://localhost:5173`
2. Register a new account → Login
3. Create a Knowledge Base → Upload a PDF/TXT/MD document
4. Wait for ingestion to complete (check document status)
5. Run an Analysis on the knowledge base
6. View live execution trace via SSE stream
7. Inspect Claims, Evidence, and Reliability score

---

## Repository Structure

```
TRUSTRAG/
├── apps/
│   ├── web/                        # React + Vite frontend
│   │   └── src/
│   │       ├── components/
│   │       │   ├── ui/             # Design system primitives
│   │       │   └── workbench/      # TRUSTRAG-specific components
│   │       │       ├── ReliabilityBadge.jsx
│   │       │       ├── ClaimInspector.jsx
│   │       │       ├── EvidenceViewer.jsx
│   │       │       └── ExecutionTrace.jsx
│   │       ├── pages/              # All 11 pages
│   │       ├── layouts/            # AppLayout + AuthLayout
│   │       ├── services/           # API service modules
│   │       ├── store/              # Auth state (Zustand)
│   │       └── lib/api.js          # Axios client + SSE helper
│   │
│   └── api/                        # FastAPI backend
│       ├── app/
│       │   ├── core/               # Config, ModelRegistry, Logging, Exceptions, Rate Limiter
│       │   ├── db/                 # MongoDB client + Qdrant client
│       │   ├── api/v1/             # REST routes + Pydantic schemas
│       │   ├── services/           # Business logic (auth, KB, analysis)
│       │   ├── ingestion/          # Document pipeline (parse, chunk, embed, index)
│       │   ├── retrieval/          # Hybrid retrieval (dense + sparse + RRF + rerank)
│       │   ├── generation/         # Grounded answer generation (Gemini)
│       │   ├── verification/       # Claim decomposition + NLI verification
│       │   ├── integrity/          # Evidence integrity audit (SHA-256)
│       │   ├── reliability/        # Reliability scoring engine
│       │   ├── recovery/           # Adaptive recovery strategies
│       │   ├── agent/              # LangGraph StateGraph workflow
│       │   └── evaluation/         # Experiment runner
│       ├── config/
│       │   └── models.yaml         # Centralized AI configuration
│       └── tests/                  # 54 unit tests (pytest)
│
├── docs/
│   ├── architecture/               # System design + ADRs
│   ├── audits/                     # Security audit logs (audit.md, audit-v2.md)
│   └── deployment/                 # Deployment guides
│
├── .github/workflows/              # CI + security scanning workflows
├── docker-compose.yml              # Local dev (API + Qdrant)
├── .env.example                    # Template (copy to .env)
└── TRUSTRAG_specs.md               # Full project specification
```

---

## Configuration

**All AI model IDs, thresholds, and tuning parameters live in `apps/api/config/models.yaml`.**  
No model IDs appear in Python or JavaScript source code. Changing the LLM or embedding model requires only a `models.yaml` update.

Secrets (API keys, URIs) stay in `.env` only — never in code or `models.yaml`.

```yaml
# models.yaml excerpt
llm:
  model: gemini-2.5-flash
  temperature: 0.2
  max_output_tokens: 2048

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  output_dimensionality: 384      # Must match Qdrant collection size

reliability:
  abstain_below: 0.50             # Reliability score → ABSTAIN threshold
  minimum_evidence_coverage: 0.60 # Min fraction of claims that must be SUPPORTED
  maximum_contradiction_rate: 0.20

recovery:
  max_recovery_attempts: 2        # Hard ceiling — prevents infinite loops
  strategy_priority:
    - query_rewrite
    - re_retrieve
```

---

## TRUSTRAG Reliability Pipeline

```
Claim States:    SUPPORTED | CONTRADICTED | NEUTRAL
Failure Types:   RETRIEVAL_FAILURE | EVIDENCE_CONFLICT | LOW_COVERAGE
Recovery:        query_rewrite | re_retrieve
Answer States:   Grounded Answer | ABSTAIN
```

Recovery is bounded by `max_recovery_attempts` to prevent infinite loops and token cost explosion.

---

## API Reference (key endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login → JWT token |
| `POST` | `/api/v1/knowledge-bases` | Create knowledge base |
| `POST` | `/api/v1/knowledge-bases/{id}/documents` | Upload document (PDF/TXT/MD, max 20MB) |
| `POST` | `/api/v1/analyses` | Run analysis (rate-limited) |
| `GET`  | `/api/v1/analyses/{id}/stream` | SSE live trace stream |
| `GET`  | `/api/v1/analyses/{id}/claims` | Verified claims list |
| `GET`  | `/api/v1/analyses/{id}/evidence` | Retrieved evidence |
| `GET`  | `/api/v1/health` | System health check |

Full OpenAPI docs available at `http://localhost:8000/docs` (development mode only).

---

## Security Highlights

- JWT HS256 tokens with configurable expiry (default 60 min)
- bcrypt password hashing (12 rounds)
- All resources protected by server-side ownership validation (IDOR prevention)
- Rate limiting on analysis, login, and register endpoints (SlowAPI)
- Prompt injection defense — system/context delimiters, untrusted label sanitization
- Raw exceptions never sent to clients — logged server-side only
- Docs endpoints (`/docs`, `/openapi.json`) disabled in production
- CORS locked to configured origin allowlist

See [`docs/audits/audit-v2.md`](docs/audits/audit-v2.md) for the full security audit report.

---

## Development

### Backend

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint + format
ruff check app/ tests/
ruff format app/ tests/
```

### Frontend

```bash
cd apps/web
npm install
npm run dev       # Dev server with HMR
npm run build     # Production bundle
npm run lint      # ESLint check
```

---

## License

MIT — see [LICENSE](LICENSE)
