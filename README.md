# TRUSTRAG — AI Reliability Workbench

> **Retrieve. Verify. Diagnose. Recover.**  
> Production-oriented RAG reliability pipeline with claim verification, failure diagnosis, and adaptive recovery.

---

## What TRUSTRAG Does

Standard RAG pipelines fail silently — they retrieve irrelevant evidence, generate unsupported claims, and cite documents that don't actually say what's claimed.

TRUSTRAG implements a structured reliability loop:

```
Query → Retrieve → Rerank → Generate → Decompose Claims → Verify Claims
     → Analyze Evidence Integrity → Diagnose Failure → Adaptive Recovery
     → Re-verify → Grounded Answer / Abstain
```

The portfolio differentiator is the **diagnosis → recovery loop**. When a reliability failure is detected, TRUSTRAG diagnoses the specific failure type and applies the cheapest targeted strategy to recover — rather than just warning the user.

---

## Engineering Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS + React Router + TanStack Query + Recharts |
| Backend | FastAPI + Python 3.11 + Pydantic Settings |
| LLM | Google Gemini (via LangChain `ChatGoogleGenerativeAI`) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 · **local, free, no API key** |
| Agentic workflow | LangGraph (recovery + Agentic-RAG) |
| Vector store | Qdrant — dense + sparse/BM25 + hybrid RRF |
| Database | MongoDB Atlas (M0 free tier) |
| Streaming | Server-Sent Events (SSE) |

**All services are free-tier compatible. No paid dependencies.**

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Architecture | ✅ Complete | ADRs, threat model (9 threats), architecture docs |
| 1 — Foundation | ✅ Complete | Monorepo, centralized config, Docker, CI/security workflows |
| 2 — Frontend | ✅ Complete | React shell, all routes, workbench design system, all pages |
| 3 — Backend | 🔲 Next | FastAPI CRUD routes, MongoDB, analysis lifecycle |
| 4 — Security | 🔲 | JWT auth, bcrypt, authorization, IDOR prevention |
| 5 — Ingestion | 🔲 | Document processing (PDF/TXT/MD), Qdrant indexing |
| 6 — Baseline RAG | 🔲 | LangChain + Gemini + hybrid retrieval + generation |
| 7 — Verification | 🔲 | Claim decomposition, evidence matching, citation check |
| 8 — Integrity | 🔲 | Provenance, temporal validity, conflict detection |
| 9 — Recovery | 🔲 | Failure diagnosis, LangGraph recovery workflow |
| 10 — Observability | 🔲 | SSE live traces, persisted trace events |
| 11 — Evaluation | 🔲 | Experiment configs, metrics, ablations |
| 12 — Production | 🔲 | Hardening, cost controls, deployment |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-username/trustrag
cd trustrag

# 2. Configure
cp .env.example .env
# Edit .env: add GEMINI_API_KEY, MONGODB_URI, JWT_SECRET

# 3. Start (Docker — API + local Qdrant)
docker compose up

# 4. Verify
curl http://localhost:8000/api/v1/health
# Frontend dev server
cd apps/web && npm install && npm run dev
# Open http://localhost:5173
```

See [docs/deployment/README.md](docs/deployment/README.md) for full deployment instructions.

---

## Repository Structure

```
TRUSTRAG/
├── apps/
│   ├── web/                  # React + Vite frontend
│   │   └── src/
│   │       ├── components/
│   │       │   ├── ui/            # Design system primitives
│   │       │   └── workbench/     # TRUSTRAG-specific components
│   │       │       ├── ReliabilityBadge.jsx
│   │       │       ├── ClaimInspector.jsx
│   │       │       ├── EvidenceViewer.jsx
│   │       │       └── ExecutionTrace.jsx
│   │       ├── pages/         # All 11 pages from spec
│   │       ├── layouts/       # AppLayout + AuthLayout
│   │       ├── services/      # API service modules
│   │       ├── store/         # Auth state
│   │       └── lib/api.js     # Axios client + SSE helper
│   │
│   └── api/                  # FastAPI backend
│       ├── app/
│       │   ├── core/          # Config, ModelRegistry, Logging, Exceptions
│       │   ├── db/            # MongoDB client + index creation
│       │   ├── ai/            # LangChain wrappers (Phase 6)
│       │   ├── ingestion/     # Document pipeline (Phase 5)
│       │   ├── retrieval/     # Hybrid retrieval (Phase 6)
│       │   ├── generation/    # Grounded generation (Phase 6)
│       │   ├── verification/  # Claim verification (Phase 7)
│       │   ├── integrity/     # Evidence integrity (Phase 8)
│       │   ├── reliability/   # Reliability engine (Phase 9)
│       │   ├── recovery/      # Adaptive recovery (Phase 9)
│       │   ├── workflows/     # LangGraph workflow (Phase 9)
│       │   └── evaluation/    # Experiment runner (Phase 11)
│       └── config/
│           └── models.yaml   # Centralized AI config
│
├── docs/
│   ├── architecture/         # System architecture + ADRs
│   ├── security/             # Threat model + security controls
│   ├── deployment/           # Full deployment guide
│   └── evaluation/           # Evaluation methodology
│
├── .github/workflows/        # CI + security scanning
├── docker-compose.yml        # Local dev (API + Qdrant)
└── .env.example
```

---

## Configuration

**All AI model IDs, thresholds, and tuning parameters live in `apps/api/config/models.yaml`.**  
No model IDs appear anywhere in Python or JavaScript source code. Changing the LLM or embedding model requires only `models.yaml` updates.

Secrets (API keys, URIs) stay in `.env` only — never in code or `models.yaml`.

```yaml
# models.yaml excerpt
llm:
  model: gemini-2.5-flash     # Change here only
  temperature: 0.2

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  output_dimensionality: 384  # Must match Qdrant collection

reliability:
  abstain_below: 0.50         # Threshold for abstention
  max_recovery_attempts: 2    # Prevents infinite loops
```

---

## TRUSTRAG Reliability Pipeline

```
Claim States:    SUPPORTED | CONTRADICTED | UNSUPPORTED | UNKNOWN
Failure Types:   RETRIEVAL_FAILURE | EVIDENCE_FAILURE | GENERATION_FAILURE
Recovery:        QueryRewrite | ReRetrieve | EvidenceExpansion |
                 ConflictResolution | ClaimFiltering | ControlledRegeneration | Abstention
```

Recovery is bounded by `max_recovery_attempts` to prevent infinite loops and cost explosion.

---

## License

MIT — see [LICENSE](LICENSE)
