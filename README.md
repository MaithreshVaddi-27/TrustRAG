# TRUSTRAG — AI Reliability Workbench

> **Retrieve. Verify. Diagnose. Recover.**  
> Production-oriented RAG reliability pipeline with claim verification, failure diagnosis, and adaptive recovery.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![React](https://img.shields.io/badge/React-18-61DAFB) ![LangGraph](https://img.shields.io/badge/LangGraph-agentic-orange) ![Qdrant](https://img.shields.io/badge/Qdrant-hybrid--RAG-red) ![CI](https://github.com/MaithreshVaddi-27/TrustRAG/actions/workflows/ci.yml/badge.svg)

---

## What TRUSTRAG Does

Standard RAG pipelines fail silently — they retrieve irrelevant evidence, generate unsupported claims, and cite documents that don't say what's claimed.

TRUSTRAG implements a **structured reliability loop**:

```
Query
  → Hybrid Retrieve (dense + sparse + RRF)
  → Generate (Gemini, grounded in evidence)
  → Decompose Claims (LLM)
  → Verify Claims (NLI per-claim)
  → Audit Evidence Integrity (SHA-256)
  → Score Reliability
  → [if low] Diagnose Failure → Adaptive Recovery (LangGraph)
    → Query Rewrite → Re-retrieve → Re-verify
  → Grounded Answer  OR  ABSTAIN
```

The differentiator: **diagnosis → recovery loop**. When reliability drops below threshold, TRUSTRAG diagnoses the failure type and applies the cheapest targeted recovery — rather than silently returning a bad answer.

---

## Engineering Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite 6 + Tailwind CSS + TanStack Query + Recharts |
| Backend | FastAPI + Python 3.11 + Pydantic v2 + Motor (async MongoDB) |
| LLM | Google Gemini 2.5 Flash Lite (configurable in `models.yaml`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` — local, free, no API key |
| Agentic | LangGraph `StateGraph` — retrieval → generation → verification → recovery |
| Vector Store | Qdrant — dense + BM25 sparse + hybrid RRF fusion |
| Database | MongoDB Atlas M0 (free tier) |
| Streaming | Server-Sent Events (SSE) for live execution traces |
| Auth | JWT HS256 + bcrypt (12 rounds) |
| Rate Limiting | SlowAPI per-IP on analysis, login, register endpoints |

**All services are free-tier compatible. No paid dependencies required.**

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Architecture | ✅ | ADRs, threat model, system design |
| 1 — Foundation | ✅ | Monorepo, centralized config, Docker, CI/CD |
| 2 — Frontend | ✅ | React workbench design system, all 11 pages |
| 3 — Backend | ✅ | FastAPI CRUD, MongoDB Atlas, analysis lifecycle |
| 4 — Security | ✅ | JWT auth, bcrypt, IDOR prevention, rate limiting |
| 5 — Ingestion | ✅ | PDF/TXT/MD parsing, Qdrant hybrid indexing |
| 6 — Baseline RAG | ✅ | LangChain + Gemini + hybrid dense/sparse + RRF |
| 7 — Verification | ✅ | Claim decomposition, NLI verification |
| 8 — Integrity | ✅ | SHA-256 provenance, temporal validity |
| 9 — Recovery | ✅ | LangGraph agentic adaptive recovery |
| 10 — Observability | ✅ | SSE live traces, persisted trace events |
| 11 — Evaluation | ✅ | Experiment configs, custom metrics, ablations |
| 12 — Production | ✅ | Cost controls, error hardening, security audit |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ v4.x
- [Node.js](https://nodejs.org/) ≥ 20 (for frontend dev server)
- [Python](https://python.org/) ≥ 3.11 (for local non-Docker run)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) free M0 cluster
- [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier)

---

## ⚡ Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/MaithreshVaddi-27/TrustRAG
cd TrustRAG
cp .env.example .env
```

Edit `.env`:

```env
# Generate: python -c "import secrets; print(secrets.token_hex(64))"
JWT_SECRET=<at-least-32-chars-random-string>

# From: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=<your-gemini-api-key>

# Optional: Speeds up initial embedding model downloads and prevents rate limits
# From: https://huggingface.co/settings/tokens
HF_TOKEN=<your-huggingface-token>

# From MongoDB Atlas → Connect → Drivers
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
```

---

## 🐳 Running with Docker (Recommended)

Docker runs the FastAPI backend + local Qdrant in containers. The React frontend runs separately.

```bash
# Start backend + Qdrant
docker compose up

# In a second terminal — start frontend
cd apps/web && npm install && npm run dev
```

**First run:** the API container downloads the sentence-transformer embedding model (~90MB). Wait ~2 minutes for `trustrag_api` to become healthy.

```bash
# Verify both services are healthy
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok","services":{"mongodb":"ok"}, ...}

curl http://localhost:6335/readyz
# Expected: all shards are ready
```

Then open **http://localhost:5173**.

> [!IMPORTANT]
> **Port mapping**: Qdrant is exposed on host port `6335` (not 6333) to avoid conflicts with any local Qdrant instance. The API container connects to Qdrant on `qdrant:6333` via Docker's internal network — this is automatic.

---

## 💻 Running Without Docker (Local Venv)

Run the backend directly using Python's virtual environment. Requires Qdrant running locally or via Docker.

### Step 1 — Start Qdrant only

```bash
# Spin up just Qdrant in Docker (background)
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:v1.10.1
```

Or download the [Qdrant binary](https://qdrant.tech/documentation/quick-start/) and run it directly.

### Step 2 — Set up Python environment

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate          # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Step 3 — Run the API

```bash
# From the repository root
set -a && source .env && set +a    # Load .env variables into shell
PYTHONPATH=apps/api uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --reload --reload-dir apps/api/app \
  --log-level info
```

### Step 4 — Start Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open **http://localhost:5173**.

---

## 🧪 Manual Testing with Sample Input

### Register & Login

```bash
BASE=http://localhost:8000/api/v1

# Register
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234!","full_name":"Demo User"}' \
  | python3 -m json.tool

# Login → get JWT token
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234!"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:40}..."
```

### Create a Knowledge Base

```bash
KB=$(curl -s -X POST $BASE/knowledge-bases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo KB","description":"Test knowledge base"}')

KB_ID=$(echo $KB | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "KB ID: $KB_ID"
```

### Upload a Sample Document

Create a sample text file:

```bash
cat > /tmp/sample_doc.txt << 'EOF'
TrustRAG implements a structured reliability loop for RAG pipelines.
The system decomposes LLM-generated answers into atomic claims.
Each claim is verified against retrieved evidence using Natural Language Inference.
When reliability drops below the configured threshold (default 0.50), the system
enters an adaptive recovery phase using LangGraph.
Recovery strategies include query rewriting and expanded evidence retrieval.
If recovery fails after max_recovery_attempts (default 2), the system abstains.
Abstention is safer than returning an unreliable answer.
EOF

# Upload to your KB
DOC=$(curl -s -X POST $BASE/knowledge-bases/$KB_ID/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/sample_doc.txt;type=text/plain")

DOC_ID=$(echo $DOC | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Doc ID: $DOC_ID | Status: $(echo $DOC | python3 -c "import json,sys; print(json.load(sys.stdin)['ingestion_status'])")"
```

### Run an Analysis

```bash
# Wait ~5s for ingestion to complete, then:
ANALYSIS=$(curl -s -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"What happens when reliability is low?\"}")

ANALYSIS_ID=$(echo $ANALYSIS | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Analysis ID: $ANALYSIS_ID"
```

### Stream Live Execution Trace (SSE)

```bash
# Stream the live trace (runs in foreground until analysis completes)
curl -N "$BASE/analyses/$ANALYSIS_ID/stream?token=$TOKEN"
```

### Fetch Results

```bash
# Answer + status
curl -s $BASE/analyses/$ANALYSIS_ID \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Verified claims
curl -s $BASE/analyses/$ANALYSIS_ID/claims \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Retrieved evidence segments
curl -s $BASE/analyses/$ANALYSIS_ID/evidence \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Persisted trace events
curl -s $BASE/analyses/$ANALYSIS_ID/trace \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Test Abstention Behavior

Upload conflicting or out-of-scope content and ask a query it can't answer reliably:

```bash
ANALYSIS2=$(curl -s -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"What is the capital of France?\"}")
echo $ANALYSIS2 | python3 -m json.tool
# Should eventually show status: "abstained" since this info isn't in the KB
```

### Test Input Validation

```bash
# Empty query → 422
curl -s -o /dev/null -w "Empty query: %{http_code}\n" \
  -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"\"}"

# Query > 2000 chars → 422
LONG=$(python3 -c "print('A'*2001)")
curl -s -o /dev/null -w "Long query: %{http_code}\n" \
  -X POST $BASE/analyses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_base_id\":\"$KB_ID\",\"query\":\"$LONG\"}"

# Wrong password → 401
curl -s -o /dev/null -w "Bad creds: %{http_code}\n" \
  -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"WRONGPASSWORD"}'

# Invalid file type → 422
echo "bad" > /tmp/bad.exe
curl -s -o /dev/null -w "Bad upload: %{http_code}\n" \
  -X POST $BASE/knowledge-bases/$KB_ID/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/bad.exe;type=application/octet-stream"
```

---

## Repository Structure

```
TRUSTRAG/
├── apps/
│   ├── web/                          # React + Vite frontend
│   │   └── src/
│   │       ├── components/workbench/ # ReliabilityBadge, ClaimInspector, EvidenceViewer
│   │       ├── pages/                # 11 pages (Dashboard, KB, Upload, Analysis, etc.)
│   │       ├── lib/                  # api.js — Axios client + SSE trace stream helper
│   │       ├── services/             # api.js (KB/analysis/experiment calls) + auth.js
│   │       └── store/                # authStore.js — lightweight pub/sub auth state
│   │
│   └── api/                          # FastAPI backend
│       ├── app/
│       │   ├── core/                 # Config, ModelRegistry, Logging, Exceptions, rate_limiter
│       │   ├── db/                   # MongoDB (motor) + Qdrant clients
│       │   ├── api/v1/               # REST routes + Pydantic schemas
│       │   ├── services/             # Business logic (auth, KB, analysis, experiment)
│       │   ├── ingestion/            # parser.py → chunker.py → sparse_vector.py → pipeline.py
│       │   ├── retrieval/            # retriever.py (dense+sparse+RRF) + reranker.py
│       │   ├── generation/           # generator.py (Gemini grounded generation)
│       │   ├── verification/         # verifier.py (NLI) + integrity.py (SHA-256)
│       │   ├── reliability/          # engine.py (reliability scoring)
│       │   ├── recovery/             # strategies.py
│       │   └── agent/                # graph.py (LangGraph StateGraph)
│       ├── config/
│       │   └── models.yaml           # ALL AI config lives here — no model IDs in code
│       └── tests/                    # 54 unit tests (pytest)
│
├── docs/
│   ├── architecture/                 # System design + ADRs
│   ├── audits/                       # audit-v2.md — security audit log
│   └── ROADMAP.md                    # Remaining steps + deployment checklist
│
├── .github/workflows/                # CI (lint+test+build) + security (Bandit+pip-audit)
├── docker-compose.yml                # Local dev: API + Qdrant
├── .env.example                      # Template — copy to .env
└── TRUSTRAG_specs.md                 # Full project specification
```

---

## Configuration

**All AI config lives in [`apps/api/config/models.yaml`](apps/api/config/models.yaml). Never in code.**

```yaml
llm:
  model: gemini-2.5-flash-lite    # Change LLM here only
  temperature: 0.2
  max_output_tokens: 2048

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  output_dimensionality: 384      # Must match Qdrant collection vector size

reliability:
  abstain_below: 0.50             # Score below this → ABSTAIN
  minimum_evidence_coverage: 0.60

recovery:
  max_recovery_attempts: 2        # Hard ceiling — prevents infinite loops
```

> [!WARNING]
> **Valid Gemini model IDs (as of 2026-08):**  
> `gemini-2.5-flash` (best quality) | `gemini-2.5-flash-lite` (faster, lower cost)  
> Model IDs like `gemini-3.5-flash-lite` **do not exist** and will cause runtime errors.

Secrets stay in `.env` only — never in `models.yaml` or code.

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/health` | No | System health check |
| `POST` | `/api/v1/auth/register` | No | Register new user |
| `POST` | `/api/v1/auth/login` | No | Login → JWT token |
| `GET` | `/api/v1/auth/me` | Yes | Current user profile |
| `POST` | `/api/v1/knowledge-bases` | Yes | Create knowledge base |
| `GET` | `/api/v1/knowledge-bases` | Yes | List your knowledge bases |
| `DELETE` | `/api/v1/knowledge-bases/{id}` | Yes | Delete KB + all documents |
| `POST` | `/api/v1/knowledge-bases/{id}/documents` | Yes | Upload document (PDF/TXT/MD, ≤20MB) |
| `GET` | `/api/v1/knowledge-bases/{id}/documents` | Yes | List documents in KB |
| `POST` | `/api/v1/analyses` | Yes | Run analysis (rate-limited: 10/min/IP) |
| `GET` | `/api/v1/analyses` | Yes | List analysis history |
| `GET` | `/api/v1/analyses/{id}` | Yes | Get analysis result |
| `GET` | `/api/v1/analyses/{id}/stream` | Token param | SSE live trace stream |
| `GET` | `/api/v1/analyses/{id}/claims` | Yes | Verified claims list |
| `GET` | `/api/v1/analyses/{id}/evidence` | Yes | Retrieved evidence segments |
| `GET` | `/api/v1/analyses/{id}/trace` | Yes | Persisted trace events |
| `POST` | `/api/v1/experiments` | Yes | Record evaluation experiment |
| `GET` | `/api/v1/experiments` | Yes | List experiments |

Full interactive docs at `http://localhost:8000/docs` (**development only** — disabled in production).

---

## Security

- JWT HS256 tokens with configurable expiry (default 60 min)
- bcrypt password hashing (12 rounds)
- Server-side resource ownership validation — IDOR prevented on all endpoints
- Rate limiting on `/analyses` (10/min), `/auth/login` and `/auth/register` (20/min)
- Prompt injection defense: XML delimiters isolate untrusted content in prompts
- Sanitized context labels: filenames/page numbers stripped of control characters before embedding
- Raw exceptions never returned to clients — only logged server-side
- `/docs` and `/openapi.json` disabled when `APP_ENV=production`
- CORS locked to configured origin allowlist

See [`docs/audits/audit-v2.md`](docs/audits/audit-v2.md) for the full independent security audit.

---

## Post-Audit Fix Log (2026-08-28)

A follow-up pass caught issues that both prior audits (`audit.md`, `audit-v2.md`) missed
because they relied on mocked collections and never exercised the real
build/runtime paths:

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| **Frontend build broken** | `apps/web/src/lib/api.js` was imported by `services/api.js`, `services/auth.js`, and `PlaygroundPage.jsx` but never existed in the repo | Added the file: Axios instance with JWT auth interceptor + 401 auto-logout, and `openAnalysisStream()` SSE helper |
| **Temporal filtering crash** | `parser.py` produced naive `datetime` values for `effective_from`/`effective_until`; `retriever.py` compares them against `datetime.now(UTC)` (aware) — naive/aware comparison raises `TypeError`, silently caught and reported as a generic pipeline failure | Parser now attaches `tzinfo=UTC`; Mongo client now sets `tz_aware=True` so dates round-trip as aware |
| **`document_chunks` bypassing collection registry** | `audit-v2.md` (V2-011) claimed this was fixed everywhere, but `integrity.py` still used the raw string `"document_chunks"` | Now uses `Collections.DOCUMENT_CHUNKS` |
| **Dead Mongo index** | `create_indexes()` indexed `claims.status`, but claim documents only ever store the verdict under `state` | Index now targets `state` |

54/54 backend tests still pass after these fixes. Existing tests didn't catch the
temporal-filtering bug because they mock the database and hand-construct
timezone-aware datetimes directly, bypassing the real parser/driver code path.

## Line-by-Line Review Pass (2026-08-28, cont.)

A full line-by-line pass of every backend and frontend file caught further issues,
none of which surfaced in either automated audit or the fix log above:

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| **Reliability score/diagnosis never populated** | `verification_node` computed `coverage`/`contradiction_rate` but discarded them; `reliability.score` and `diagnosis` stayed `null`/`PENDING` forever regardless of outcome, and the `abstain_below` config value was read but never used anywhere | Wired score computation, diagnosis type/failure detection, and persistence into `run_analysis_pipeline`; `abstain_below` now actually gates the `UNCERTAIN` vs `FAILED` verdict |
| **Timing-attack mitigation silently broken** | The dummy bcrypt hash used to equalize login timing for nonexistent users was malformed (38 chars, not the required 60) — `bcrypt.checkpw` failed fast instead of doing the real cost-12 computation, reopening the exact timing side-channel it was meant to close | Replaced with a valid dummy hash |
| **Ingestion chunker infinite loop** | `chunk_overlap >= chunk_size` zeroes/negates the slide step, hanging the chunking loop forever | Added a minimum-step guard with a warning log |
| **Internal error leakage** | `index_parsed_chunks` stored raw `str(exc)` into the document's user-facing `error_message` field, inconsistent with the sanitization used everywhere else in the codebase | Now stores a generic `type(exc).__name__`-based message |
| **Orphaned Qdrant collections** | `delete_kb` deleted MongoDB records but never called the already-existing `delete_kb_collection()`, leaking vector storage on every KB deletion | Wired it in |
| **Upload limits hardcoded** | The document upload route hardcoded `MAX_FILE_SIZE`/`ALLOWED_EXTENSIONS` instead of reading `models.yaml`, contradicting that file's own "never hardcode" rule | Now reads `cfg.max_file_size_mb` / `cfg.supported_formats` |
| **Retriever not actually parallel** | Comment claimed dense + sparse search ran in parallel; both were sequential `await`s | Now uses `asyncio.gather` |
| **Frontend/backend claim-state contract mismatch** | Backend only ever emits `SUPPORTED`/`CONTRADICTED`/`NEUTRAL`, but the frontend's badges, filters, and styling everywhere referenced `UNSUPPORTED`/`UNKNOWN` — every `NEUTRAL` claim rendered as a generic "Unknown" | Fixed in `ReliabilityBadge.jsx`, `index.css`, `ClaimInspector.jsx`, `ClaimsPage.jsx`, `PlaygroundPage.jsx` |
| **False integrity warnings** | `EvidenceViewer.jsx` checked `integrity_status === 'ok'`, but the backend only ever sets `VERIFIED`/`CORRUPTED` — every legitimately verified chunk showed a tamper-warning icon | Fixed the comparison |
| **Execution trace showed almost nothing** | `ExecutionTrace.jsx`'s event-to-label map was built from event names that don't exist in the backend (`retrieval.started`, `claims.extracted`, `recovery.started`, etc.); the actual emitted events (`claims.started`, `claims.verified`, `recovery.rewrite`, `recovery.re_retrieve`, `integrity.failed`) had no entry and fell back to generic gray styling | Rebuilt the map from the real event names emitted by `graph.py`/`analysis_service.py` |
| **Trace page never loaded data** | `TracePage.jsx` hardcoded `events={[]}` and never called the trace API despite the analysis `id` being available in the route | Wired it to `analysisService.trace(id)` via `useQuery` |
| **Generic error messages on login/register** | Axios's default `err.message` is `"Request failed with status code NNN"`, not the backend's actual JSON error message, so failed logins always showed a generic string instead of e.g. "Invalid email or password" | Added a response interceptor in `lib/api.js` that promotes `error.response.data.error.message` onto `err.message` |
| **Diagnosis never actually shown** | `PlaygroundPage.jsx` only displayed `diagnosis.failures` when `analysis.status === 'failed'` (pipeline crash), but the diagnosis populated above lives under `reliability.status === 'FAILED'` while `status` stays `'completed'` | Broadened the condition to cover both cases |
| **Wrong model name displayed** | `SettingsPage.jsx` hardcoded the LLM as `gemini-2.5-flash`; `models.yaml` actually configures `gemini-2.5-flash-lite` for the main LLM (`gemini-2.5-flash` is the verification model) | Corrected the displayed value |
| Stale doc comments | `ClaimResponse.state` and `EvidenceResponse.integrity_status` schema comments listed states that don't match what the code actually emits | Corrected to `SUPPORTED/CONTRADICTED/NEUTRAL` and `VERIFIED/CORRUPTED` |

Verified after this pass: 54/54 backend tests pass, `ruff`/`pyflakes` clean, frontend
`npm run build` and `npm run lint` both clean with zero warnings.

---

## Development

### Backend

```bash
cd apps/api
source .venv/bin/activate

# Run tests
pytest tests/ -v

# Lint
ruff check app/ tests/
ruff format app/ tests/

# Type check
mypy app/
```

### Frontend

```bash
cd apps/web
npm run dev       # Dev server with HMR at :5173
npm run lint      # ESLint check
npm run build     # Production bundle → dist/
```

---

## Reliability Pipeline States

```
Claim States:    SUPPORTED | CONTRADICTED | NEUTRAL
Failure Types:   RETRIEVAL_FAILURE | EVIDENCE_CONFLICT | LOW_COVERAGE
Recovery:        query_rewrite → re_retrieve → re_verify
Answer States:   Grounded Answer  |  ABSTAIN
```

Recovery is bounded by `max_recovery_attempts` (default: 2) to prevent infinite loops and token cost explosion.

---

## License

MIT — see [LICENSE](LICENSE)
