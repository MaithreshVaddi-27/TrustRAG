# TRUSTRAG — Production-Oriented Project Specification

## 1. Product Definition

**TRUSTRAG** is an AI reliability workbench for Retrieval-Augmented Generation (RAG).

### Core problem

Standard RAG can fail because:

- relevant evidence is not retrieved;
- retrieved evidence is stale, conflicting, or weakly attributable;
- generated claims are unsupported or contradicted;
- citations exist but do not actually support claims;
- the system knows it lacks sufficient evidence but still answers.

TRUSTRAG must therefore implement:

```text
Query
  ↓
Retrieve
  ↓
Rerank
  ↓
Generate
  ↓
Decompose Claims
  ↓
Verify Claims
  ↓
Analyze Evidence Integrity
  ↓
Diagnose Failure
  ↓
Adaptive Recovery
  ↓
Re-verify
  ↓
Grounded Answer / Abstain
```

TRUSTRAG is **not** a generic chatbot, generic RAG demo, AI testing product, or multi-agent swarm.

The portfolio differentiator is the **reliability → diagnosis → recovery loop**.

---

## 2. Engineering Principles

1. Evidence over assertion.
2. Diagnosis over generic "hallucination" labels.
3. Recovery over warning-only behavior.
4. Abstention over unsupported certainty.
5. Provenance over opaque citations.
6. Measured improvement over assumed improvement.
7. LangChain/LangGraph are infrastructure, not the product's business logic.
8. Bounded autonomy over unrestricted agents.
9. Security, cost, latency, and reliability are first-class concerns.
10. Never fabricate metrics, benchmarks, model capabilities, or guarantees.
11. Prefer simple production-appropriate architecture over technology accumulation.

---

## 3. Final Technology Stack

### Frontend

- React 18
- Vite 6
- JavaScript / JSX
- Tailwind CSS 3
- React Router v6
- TanStack Query (React Query) v5
- Recharts
- Lucide React
- motion (Framer Motion)
- react-markdown + remark-gfm

### Backend

- Python
- FastAPI
- Pydantic
- PyMongo / modern MongoDB Python driver
- Structured logging

### AI

- LangChain
- LangGraph (StateGraph for adaptive recovery loop)
- Multi-provider LLMs: llama.cpp (port 9931, default `LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M`) / Ollama (port 11434, default `gemma3:1b`) / MLX (port 8080, Apple Silicon, optional) + `langchain-google-genai` (cloud, `cloud` extra)
- Local embeddings: `BAAI/bge-small-en-v1.5` via ONNX Runtime only (torch-free, sole embedding engine, `onnxruntime` provider, no HuggingFace/sentence-transformers at runtime)
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2` ONNX int8 (off by default, `reranker.enabled: false`)
- OCR fallback: RapidOCR-ONNX (per-page, <50 native chars triggers)

### Retrieval

- Qdrant (dense 384d + `sparse-text` with server-side `Modifier.IDF`, per-KB collections `kb_{kb_id}`)
- Dense retrieval: `BAAI/bge-small-en-v1.5` 384d via ONNX Runtime, bounded query-vector LRU cache
- Sparse/BM25 retrieval: client-side TF saturation + Qdrant server-side IDF (`Modifier.IDF`), `sparse_top_k: 20` (default 0 = disabled)
- Hybrid fusion: Reciprocal Rank Fusion (RRF, `rrf_k: 60`), `fusion_top_k: 20` enforced post-RRF
- Deterministic query router: SIMPLE / TEMPORAL / COMPARISON / COMPLEX (regex-based, no LLM, fan-out ≤3 via `max_sub_queries`)
- Optional reranking: ONNX int8 CrossEncoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`), batched with early termination, result cache, RRF fallback; depth cap `top_k: 20` floored at `fusion_top_k`
- Per-branch timeouts: 45s dense / 45s sparse, 60s hybrid total; hard failure on any branch timeout (`RetrievalOutageError`)

### Persistence

- MongoDB Atlas for application data
- Qdrant Cloud for vector data

### Communication

- REST `/api/v1/...`
- Server-Sent Events (SSE) for live traces

### Deployment

Initial deployment must be free-tier-compatible where possible.

Provider choice must be documented and verified at deployment time because free-tier limits change.

---

## 4. Architecture

```text
                         React
                           │
                           ▼
                        FastAPI
                           │
                    TRUSTRAG Services
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
     LangChain          LangGraph        MongoDB Atlas
        │                  │                  │
        ▼                  ▼                  │
      Gemini          Recovery/Agentic        │
        │                  │                  │
        └──────────┐       │                  │
                   ▼       ▼                  │
                  Qdrant ◄────────────────────┘
```

### Responsibility boundaries

**LangChain**

- LLM abstraction (`ChatGoogleGenerativeAI` for Gemini)
- Cloud LLM integration only (local LLMs use direct clients)
- Prompt templates
- Document abstractions
- Structured output parsing
- Tool interfaces (for MCP/tools)

**LangGraph**

- Stateful self-healing workflow (`StateGraph` in `app/rag/agent/graph.py`)
- Adaptive recovery loop with bounded retries (`max_recovery_attempts: 2`)
- Multi-hop Agentic-RAG (deterministic query router + bounded fan-out)
- Workflow state/checkpointing (SSE recovery from MongoDB trace events)

**Gemini / Cloud LLMs (selectable, not default, `cloud` extra)**

- LLM generation / verification when `llm.provider: google_genai`
- Embeddings are local-only (ONNX BGE, 384d) — no cloud embedding model ever

**Local LLM Engines (default, no cloud keys required)**

- llama.cpp (`llama-server` on port 9931): `LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M` default
- Ollama (port 11434): `gemma3:1b` default
- MLX (port 8080, Apple Silicon only): `mlx-community/LFM2.5-1.2B-4bit` default
- All use LangChain-compatible interfaces via `app/llm/local_llm.py`
- Hardware auto-detection (`app/core/system/hardware.py`) generates optimal launch flags

**Qdrant**

- Vector database: dense (384d only — 768d retired) + sparse-text (`Modifier.IDF`)
- Collection per KB: `kb_{kb_id}` with dense + sparse vectors + payload
- Hybrid search, INT8 on-disk quantization
- Pre-IDF collections auto-recreate on init (re-upload those KBs)

**MongoDB**

- Collections: `users`, `knowledge_bases`, `documents`, `document_chunks`, `analyses`, `claims`, `evidence`, `recovery_runs`, `trace_events`, `experiments`, `feedback`, `revoked_tokens`, `stream_tickets`
- Source of truth: `Collections` in `app/db/mongodb.py`
- Tracks ingestion status, analysis results, claim verification, recovery history
- Evidence integrity audit: SHA-256 hash comparison of served chunks vs `document_chunks`

**TRUSTRAG Core Logic (independent of LangChain/LangGraph)**

- Reliability signals & verdict computation (`app/rag/verification/verdict.py`)
- Evidence integrity & provenance audit (`app/rag/verification/integrity.py`)
- Claim decomposition & NLI verification (`app/rag/verification/verifier.py`)
- Failure diagnosis taxonomy (`DiagnosisType`: RETRIEVAL_FAILURE / OUTAGE / EVIDENCE_CONFLICT / LOW_COVERAGE / NONE)
- Recovery policy & strategy selection (`recovery_node` in graph.py)
- Abstention policy & thresholds (`minimum_evidence_coverage`, `maximum_contradiction_rate`, `abstain_below`)
- Evaluation harness & frozen dataset (`apps/api/tests/eval/`)

Do not hide TRUSTRAG's core logic inside LangChain chains.

---

## 5. Professional Repository Structure

```text
TRUSTRAG/
├── apps/
│   ├── web/
│   │   ├── src/
│   │   │   ├── pages/          # 12 routes (Landing, Login, Register, Dashboard, Playground, KnowledgeBases, Evidence, Claims, Conflicts, Experiments, Settings, Trace/:id, 404)
│   │   │   ├── components/
│   │   │   │   ├── landing/    # Landing page sections (Hero, SimulationSandbox, ComparisonMatrix, Benchmarks, Capabilities, BentoArchitecture, Footer, Navbar)
│   │   │   │   ├── layout/     # App shell (Navbar, Sidebar, MobileDrawer, EngineTelemetry, BackendBanner)
│   │   │   │   ├── playground/ # QueryPanel, QueryInput, AIEngineSelector, EmbeddingModelDisplay, KnowledgeBaseSelector, WebSearchToggle, RunButton, ErrorDisplay
│   │   │   │   ├── results/    # ResultsPanel, AnswerTab, ClaimsTab, EvidenceTab, TraceTab
│   │   │   │   ├── dashboard/  # MetricsGrid, PipelineArchitecture, ClaimDistributionChart, ReliabilityChart, ObservabilityBar, HeroBanner, RecentAnalysesFeed
│   │   │   │   ├── workbench/  # ClaimInspector, ExecutionTrace, FormattedAnswer, EvidenceViewer, EvidenceChunk, ReliabilityBadge, PipelineTelemetryHUD, ThinkingOrbs, Skeleton, EmptyState
│   │   │   │   ├── ErrorBoundary.jsx, ConfirmDialog.jsx
│   │   │   ├── services/       # Domain services: auth.js, api.js
│   │   │   ├── lib/            # Central Axios client (api.js), modelLabels, clipboard, claimState, motionConfig, apiResponse
│   │   │   ├── store/          # Auth session store (authStore.js, Zustand)
│   │   │   ├── hooks/          # useBackendHealth, useSidebar, useCursorGlow, useKnowledgeBaseSelection, useModelSelection, useAnalysisStream
│   │   │   ├── layouts/        # AppLayout.jsx, AuthLayout.jsx
│   │   │   └── styles/         # Per-page CSS (landing.css, app-layout.css, typography.css, animations.css, materials.css, loaders.css)
│   │   ├── public/
│   │   ├── e2e/                # Playwright specs
│   │   ├── package.json
│   │   └── vite.config.js
│   │
│   └── api/
│       ├── app/
│       │   ├── main.py                    # FastAPI app factory
│       │   ├── api/v1/                    # REST route handlers (auth, KBs, analyses, claims, evidence, traces, conflicts, experiments, health)
│       │   ├── core/
│       │   │   ├── config/                # settings.py + model_config.py (models.yaml loader)
│       │   │   ├── observability/         # logging + metrics + tracing
│       │   │   ├── security/              # Auth primitives + exception hierarchy
│       │   │   └── system/                # hardware + memory + concurrency
│       │   ├── db/
│       │   │   ├── qdrant.py              # Qdrant client + collection init
│       │   │   └── mongodb.py             # MongoDB client + indexes (`Collections`)
│       │   ├── llm/
│       │   │   ├── model_registry.py      # Model factory (embedding, reranker, LLM)
│       │   │   ├── onnx_embeddings.py     # ONNX BGE embedding engine
│       │   │   ├── onnx_reranker.py       # ONNX cross-encoder reranker
│       │   │   ├── onnx_runtime.py        # Shared ORT session options
│       │   │   ├── local_llm.py           # Ollama + llama.cpp LangChain clients
│       │   │   └── llm_ledger.py          # Per-analysis LLM call budget
│       │   ├── rag/
│       │   │   ├── agent/                 # LangGraph StateGraph + recovery loop (graph.py, router.py)
│       │   │   ├── generation/            # Grounded answer generator (generator.py)
│       │   │   ├── ingestion/             # Pipeline, parser, chunker, strategies, sparse_vector, OCR
│       │   │   ├── retrieval/             # Hybrid retriever + reranker
│       │   │   └── verification/          # Verifier (decomposition + NLI), verdict, integrity
│       │   ├── services/
│       │   │   ├── analysis_service.py    # Analysis lifecycle + SSE tickets
│       │   │   ├── kb_service.py          # KB CRUD + snapshots + rollback
│       │   │   ├── auth_service.py        # Auth + JTI revocation
│       │   │   ├── experiment_service.py  # Experiment records
│       │   │   └── search_service.py      # Web search orchestration (SSRF-guarded)
│       │   └── mcp/                       # MCP server (trustrag_* tools) + client dispatcher
│       ├── config/
│       │   └── models.yaml                # Model IDs, thresholds, tuning params (v1.28)
│       ├── tests/                         # Backend suite incl. tests/eval/ harness
│       ├── pyproject.toml
│       └── Dockerfile
│
├── docs/
│   ├── TRUSTRAG_specs.md       # This file (source of truth)
│   ├── ONBOARDING-TROUBLESHOOTING.md
│   ├── ROADMAP.md
│   ├── architecture/
│   │   ├── architecture.md
│   │   ├── RAG_ARCHITECTURE.md
│   │   └── decision-log.md
│   ├── security/
│   │   ├── threat-model.md
│   │   └── security-controls.md
│   ├── deployment/
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   └── README.md
│   └── evaluation/
│       ├── methodology.md
│       └── results/            # Live run JSON (gitignored, local only)
│
├── config/
│   └── ports.yaml              # Canonical port registry
├── scripts/
├── load-test/
│   └── smoke.js
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── security.yml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

Avoid folders/packages that have no real responsibility.

---

## 6. Centralized Configuration

No model ID, API URL, threshold, retry limit, or AI tuning parameter may be scattered through business code.

### Configuration flow

```text
.env
 ↓
Typed Settings
 ↓
models.yaml
 ↓
ModelRegistry / Config Services
 ↓
LangChain Integrations
 ↓
Gemini / Retrieval / Verification
```

### `.env`

Secrets and deployment-specific values only:

```env
GEMINI_API_KEY=
MONGODB_URI=
MONGODB_DATABASE=TRUSTRAG_DB
QDRANT_URL=
QDRANT_API_KEY=
JWT_SECRET=
CORS_ORIGINS=
APP_ENV=development
LOG_LEVEL=INFO
```

Never commit `.env`.

### `config/models.yaml` (v1.28)

Example structure:

```yaml
llm:
  provider: llama_cpp              # llama_cpp | ollama | mlx | google_genai
  model_llama_cpp: "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M"
  model_ollama: "gemma3:1b"
  model_mlx: "mlx-community/LFM2.5-1.2B-4bit"
  model_gemini: "gemini-2.5-flash"
  temperature: 0.2
  top_p: 0.9
  max_output_tokens: 2048
  timeout_seconds: 60
  max_retries: 2
  context_window: 8192             # per-model context window

embedding:
  provider: onnx                   # ONNX-only; sole embedding engine (no provider choice)
  model: "BAAI/bge-small-en-v1.5"
  output_dimensionality: 384
  version: "1"
  onnx_path: ".model_cache/bge-small-en-v1.5.onnx"
  lru_cache_size: 512              # query-vector LRU cache

reranker:
  enabled: false                   # off by default; needs local-models extra
  provider: onnx
  model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
  top_k: 20                        # scoring-depth cap, floored at fusion_top_k
  onnx_path: ".model_cache/reranker-ms-marco-MiniLM-L-6-v2_int8.onnx"
  batch_size: 16
  early_termination: true
  cache_enabled: true

retrieval:
  dense_top_k: 20
  sparse_top_k: 0                  # 0 = disabled; set 20 for full hybrid
  fusion_method: rrf
  rrf_k: 60
  fusion_top_k: 20                 # enforced post-RRF
  max_context_chunks: 8
  query_router:
    enabled: true                  # deterministic regex router; no LLM
    max_sub_queries: 3
  timeouts:
    dense_seconds: 45
    sparse_seconds: 45
    hybrid_total_seconds: 60

reliability:
  minimum_evidence_coverage: 0.80
  maximum_contradiction_rate: 0.20
  abstain_below: 0.50

recovery:
  max_recovery_attempts: 2
  max_recovery_tokens: 2000
  max_recovery_latency_seconds: 180
  strategy_priority:
    - query_rewrite
    - re_retrieve
    - regenerate

cost_controls:
  max_input_tokens: 100000
  max_claim_retrievals: 3          # NEUTRAL-only targeted retrieval budget
  claim_retrieval_top_k: 5

observability:
  metrics_enabled: true
  pre_request_budget_enforcement: true

runtime:
  config_version: "1.28"
```

These are engineering defaults, not calibrated truth. Version 1.28 (2026-10) added: embedding.onnx_path, reranker.onnx_path, llm.context_window, retrieval.timeouts, recovery.strategy_priority, cost_controls.claim_retrieval_top_k.

### Model registry

Implement:

```text
get_llm()
get_embedding_model()
get_verification_model()
get_reranker()
```

Changing a model must not require changes to:

- API routes;
- retrieval business logic;
- verification logic;
- LangGraph nodes;
- React components.

Record the active model/configuration version in each analysis.

---

## 7. Gemini + LangChain

Use Gemini through LangChain's Google integration.

The application-facing dependency must be:

```text
TRUSTRAG
 ↓
LangChain
 ↓
langchain-google-genai
 ↓
Gemini API
```

Do not scatter direct Google SDK usage throughout the application.

Use LangChain model/embedding interfaces such as:

```text
ChatGoogleGenerativeAI
GoogleGenerativeAIEmbeddings
```

where supported.

The exact Gemini model ID must remain configurable and must be verified before deployment.

---

## 8. MongoDB Atlas Data Architecture

MongoDB Atlas is the online application database.

### Collections

```text
users
knowledge_bases
documents
analyses
claims
evidence
recovery_runs
trace_events
experiments
feedback
```

### Data rules

- Do not store document binaries in MongoDB unless a justified bounded use case exists.
- Do not store Qdrant vectors in MongoDB.
- Store metadata, state, provenance, and references in MongoDB.
- Use ObjectIds/references for independently queried entities.
- Avoid unbounded arrays.
- Paginate trace/evidence/analysis lists.
- Create indexes for ownership, foreign keys, status, and time-based queries.
- Enforce authorization in backend services.

### Document metadata

Store:

```text
document_id
knowledge_base_id
filename
source_uri
content_hash
version
created_at
updated_at
effective_from
effective_until
supersedes_document_id
provenance_metadata
integrity_status
ingestion_status
qdrant_collection_version
embedding_model
embedding_dimension
```

---

## 9. Knowledge Ingestion

Pipeline:

```text
Upload
 ↓
Parse (+ per-page RapidOCR-ONNX fallback when native text < 50 chars;
       sub-0.5-confidence text dropped, failures fail open to native text)
 ↓
Normalize (paragraph breaks preserved) + zone
 ↓
Clean
 ↓
Extract metadata
 ↓
Chunk (selectable strategy: sliding_window default, semantic, progressive,
       layout_aware; tables chunked whole with zone=table)
 ↓
Embed (local BGE/ONNX, KB-pinned)
 ↓
Index in Qdrant (dense + sparse-text with server-side IDF)
 ↓
Persist provenance/metadata in MongoDB (incl. ocr_used/ocr_confidence)
```

Supported formats (8 + OCR fallback):

- PDF, DOCX, CSV, JSON, HTML, HTM, TXT, Markdown
- Scanned/image PDF pages via local RapidOCR-ONNX

Additional formats only when they provide clear value.

Each chunk must retain document/chunk provenance.

---

## 10. Retrieval

Implement modular retrieval:

```text
Query
 ├── Route (simple / temporal / comparison / complex — deterministic, no LLM)
 ├── Dense + Sparse/BM25 (client TF + server IDF) [×N sub-queries, merged]
 └── Metadata/Temporal filtering
       ↓
     Fusion/RRF (fusion_top_k enforced)
       ↓
   Optional Reranking (off by default; depth-capped)
       ↓
   Evidence Selection
```

Persist retrieval metadata sufficient for debugging:

- document/chunk ID
- retrieval method
- retrieval score
- fusion score
- rerank score
- selected/not selected

Do not assume hybrid retrieval is automatically better. Evaluation must determine the useful configuration.

---

## 11. Evidence Integrity

Analyze:

- provenance
- version
- temporal applicability
- source conflicts
- suspicious/prompt-injection-like content

Conflict example:

```text
Spec v3 → 30 days
Spec v4 → 45 days
```

If precedence is established, use the applicable source.

If precedence is not established:

```text
CONFLICT
 ↓
Expose conflict
 ↓
Avoid arbitrary selection
 ↓
Abstain if material to answer
```

Do not claim complete protection against poisoned/adversarial knowledge.

---

## 12. Generation

Generation must be grounded in selected evidence.

The prompt architecture must explicitly distinguish:

```text
SYSTEM INSTRUCTIONS
USER QUERY
RETRIEVED EVIDENCE = UNTRUSTED DATA
```

Retrieved documents must never automatically become instructions.

Generation must support structured output where appropriate.

Capture safe metadata:

- provider
- model
- config version
- latency
- token usage when available

Never fabricate unavailable token/cost information.

---

## 13. Claim Decomposition

Example:

```text
Answer:
"Tokens are valid for 45 days and revocation takes 7 seconds."

Claim 1:
Tokens are valid for 45 days.

Claim 2:
Processing takes 7 days.
```

Each claim receives a stable ID.

Claim states:

```text
SUPPORTED
CONTRADICTED
NEUTRAL
```

Generation pins each factual sentence to a `[Segment N]` marker for verification (refs to
unserved segments are stripped post-generation); the markers are internal plumbing and are
removed from the reader-facing answer at finalize, with the marker-bearing text retained in
`answer_cited` for audit and eval. NEUTRAL claims may earn one bounded targeted-retrieval
round each (claim text as query, ≤3 per analysis); CONTRADICTED claims are never
re-searched.

---

## 14. Claim Verification

For each claim:

```text
Claim
 ↓
Retrieve relevant evidence
 ↓
Evidence comparison
 ↓
Verification
 ↓
Status + supporting/contradicting evidence
```

Verification may combine:

- deterministic checks;
- semantic/NLI verification;
- Gemini-based structured verification.

No single LLM judgment is ground truth.

Citation correctness means:

```text
Does the cited evidence actually support the claim?
```

not merely:

```text
Does a citation exist?
```

---

## 15. Reliability Engine

Reliability must be explainable.

Possible signals:

- retrieval relevance;
- evidence coverage;
- claim support;
- contradiction rate;
- citation correctness;
- source integrity;
- temporal applicability;
- verification signal;
- recovery history.

Do not represent a heuristic score as a calibrated probability unless calibration has actually been performed.

Reliability output should contain:

```text
score
status
supporting_signals
risk_signals
decision
```

---

## 16. Failure Diagnosis

Minimum taxonomy:

```text
RETRIEVAL_FAILURE
 ├── MISSING_EVIDENCE
 ├── IRRELEVANT_RETRIEVAL
 ├── RANKING_FAILURE
 └── QUERY_FORMULATION_FAILURE

EVIDENCE_FAILURE
 ├── SOURCE_CONFLICT
 ├── OUTDATED_SOURCE
 ├── LOW_PROVENANCE
 └── SUSPICIOUS_KNOWLEDGE

GENERATION_FAILURE
 ├── UNSUPPORTED_CLAIM
 ├── CONTRADICTED_CLAIM
 ├── EVIDENCE_MISINTERPRETATION
 ├── OVERGENERALIZATION
 └── CITATION_MISMATCH

UNKNOWN_FAILURE
```

Diagnosis must be based on observed signals.

---

## 17. Adaptive Recovery

Recovery is the primary TRUSTRAG differentiator.

Strategies:

```text
QueryRewrite
ReRetrieve
Rerank
EvidenceExpansion
ConflictResolution
ClaimFiltering
ControlledRegeneration
Abstention
```

Examples:

```text
Missing evidence
 → query rewrite
 → re-retrieve
 → rerank
 → verify
```

```text
Unsupported claim
 → retrieve additional evidence
 → verify
 → regenerate/remove claim
```

```text
Source conflict
 → inspect version/time/provenance
 → resolve if justified
 → otherwise expose conflict/abstain
```

Recovery must use a bounded budget.

Never allow infinite loops.

---

## 18. LangGraph Workflow

Use LangGraph for stateful recovery and Agentic-RAG.

```text
START
 ↓
RETRIEVE
 ↓
RERANK
 ↓
GENERATE
 ↓
VERIFY
 ↓
DIAGNOSE
 ├── TRUSTED → ANSWER
 ├── RETRIEVAL_FAILURE → RECOVER_RETRIEVAL
 ├── EVIDENCE_FAILURE → RESOLVE_EVIDENCE
 ├── GENERATION_FAILURE → RECOVER_GENERATION
 └── HIGH_RISK → ABSTAIN
 ↓
REVERIFY
 ↓
ANSWER / ABSTAIN
```

State should contain only workflow data:

```text
query
knowledge_base_id
retrieval_results
evidence
answer
claims
verification
integrity
diagnosis
recovery_attempts
reliability
final_decision
```

Never place secrets in graph state.

Do not use LangGraph for ordinary CRUD or deterministic helper functions.

---

## 19. Agentic-RAG

Support optional complex-query mode:

```text
Query
 ↓
Planner
 ↓
Retrieve
 ↓
Reason
 ↓
Need more evidence?
 ├── Yes → refine → retrieve
 └── No
 ↓
Verify
 ↓
Answer / Recover / Abstain
```

Intermediate evidence and reliability state must remain inspectable.

Do not build a multi-agent swarm.

---

## 20. Authentication & Authorization

Implement:

- registration;
- login;
- JWT authentication;
- protected routes;
- secure password hashing;
- current-user endpoint;
- logout/session strategy appropriate to implementation.

Every resource access must verify authorization server-side.

Prevent:

- IDOR;
- cross-user knowledge-base access;
- cross-user trace access;
- cross-user document access.

---

## 21. AI Security

Treat all external content as untrusted.

Threats:

- prompt injection;
- indirect prompt injection;
- malicious documents;
- data leakage;
- secret leakage;
- denial-of-wallet;
- excessive tool use;
- oversized inputs;
- unsafe generated tool arguments.

If tools exist:

```text
LLM
 ↓
Structured request
 ↓
Schema validation
 ↓
Authorization
 ↓
Policy check
 ↓
Executor
```

Never allow:

```text
LLM → shell
LLM → arbitrary code
LLM → unrestricted database operation
```

---

## 22. API

Use:

```text
/api/v1/auth/*
/api/v1/knowledge-bases/*
/api/v1/documents/*
/api/v1/analyses/*
/api/v1/claims/*
/api/v1/evidence/*
/api/v1/traces/*
/api/v1/conflicts/*
/api/v1/experiments/*
```

Representative endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me

GET  /api/v1/knowledge-bases
POST /api/v1/knowledge-bases
POST /api/v1/knowledge-bases/{id}/snapshots                    # → 201
POST /api/v1/knowledge-bases/{id}/rollback/{snapshot_id}       # → 200, returns NEW live id

POST /api/v1/knowledge-bases/{id}/documents

POST /api/v1/analyses
GET  /api/v1/analyses/{id}
GET  /api/v1/analyses/{id}/claims
GET  /api/v1/analyses/{id}/evidence
GET  /api/v1/analyses/{id}/trace
GET  /api/v1/analyses/{id}/detail
GET  /api/v1/analyses/{id}/export
GET  /api/v1/analyses/{id}/stream

GET  /api/v1/health                  # public, minimal (load balancers)
GET  /api/v1/health/detailed         # authed: services, models, hardware
```

Routes must remain thin.

---

## 23. Live Execution Trace

Use SSE.

Events:

```text
analysis.started
retrieval.started
retrieval.routed
retrieval.completed
retrieval.self_heal_batch
reranking.completed
generation.started
generation.completed
claims.extracted
verification.completed
integrity.completed
diagnosis.completed
recovery.started
recovery.completed
reverification.completed
analysis.completed
analysis.abstained
analysis.failed
```

Persist authoritative trace events in MongoDB.

If SSE disconnects, the frontend must recover state from the persisted trace API.

---

## 24. Frontend Product UX

The UI must look like an **AI reliability workbench**, not a ChatGPT clone.

Pages:

```text
/
login
register
dashboard
playground
knowledge-bases
evidence
claims
conflicts
experiments
settings
traces/:id
```

### Playground

Show:

```text
Query
 ↓
Retrieval
 ↓
Evidence
 ↓
Answer
 ↓
Claims
 ↓
Verification
 ↓
Reliability
 ↓
Diagnosis
 ↓
Recovery
 ↓
Final Decision
```

### Important components

```text
ReliabilityBadge
ClaimInspector
EvidenceViewer
EvidenceGraph
RetrievalTrace
RecoveryTimeline
ConflictViewer
SourceProvenance
ModelConfiguration
ExecutionTrace
```

Supported/contradicted/neutral states must be visually distinct.

---

## 25. Experiments

Compare:

```text
Baseline RAG
Hybrid RAG
Hybrid + Reranking
Verified RAG
TRUSTRAG + Adaptive Recovery
```

Possible metrics:

- retrieval hit/recall;
- evidence coverage;
- claim support;
- contradiction rate;
- citation correctness;
- recovery success;
- abstention behavior;
- latency;
- token/model cost where available.

Include ablations:

```text
Dense vs Hybrid
Hybrid vs Hybrid + Reranking
Verification off/on
Recovery off/on
Integrity logic off/on
```

No fabricated results. Live baseline runs use the frozen 25-query set
(`apps/api/tests/eval/datasets/baseline_v1.jsonl`) via `scripts/run_baseline_eval.py`;
results land in `docs/evaluation/results/` and the methodology snapshot table.
Runs are PENDING operator execution — no measured rows may be invented.

---

## 26. Observability & Cost

Track:

- request/analysis ID;
- stage;
- latency;
- model;
- retrieval attempts;
- recovery attempts;
- token usage where available;
- errors.

Cost controls:

- bounded retries;
- bounded recovery;
- maximum context;
- rate limiting;
- timeout;
- configurable model;
- optional reranking;
- caching only where safe.

Prefer the cheapest strategy capable of addressing the diagnosed failure.

---

## 27. Testing

Testing is required for engineering quality but is not the product focus.

Prioritize:

### Unit

- reliability scoring;
- recovery policy;
- claim logic;
- temporal logic;
- conflict logic;
- configuration validation;
- authorization.

### Integration

- ingestion;
- MongoDB;
- Qdrant;
- retrieval;
- generation;
- verification;
- recovery;
- SSE.

### Security

- IDOR;
- authorization;
- prompt injection;
- malicious uploads;
- secret leakage;
- rate limiting.

---

## 28. Deployment

Target:

```text
GitHub
  ↓
React hosting
  ↓
FastAPI hosting
  ↓
MongoDB Atlas
  +
Qdrant Cloud
  +
Gemini API
```

The application must not depend on local-only infrastructure.

Create:

```text
docs/deployment/README.md
```

Document:

- environment variables;
- local development;
- MongoDB Atlas;
- Qdrant Cloud;
- Gemini;
- CORS;
- frontend deployment;
- backend deployment;
- health checks;
- indexing/re-indexing;
- troubleshooting.

Verify provider free-tier constraints at deployment time.

---

## 29. Docker & Local Development

Provide:

```text
docker-compose.yml
```

for local development where useful.

Local architecture may be:

```text
React
+
FastAPI
+
local Qdrant
+
MongoDB Atlas
+
Gemini API
```

Do not require Kubernetes.

Do not require a GPU.

Do not require an always-on worker fleet for MVP.

---

## 30. CI/CD

GitHub Actions:

```text
ci.yml
security.yml
```

CI should run:

- frontend lint;
- frontend build;
- backend lint;
- backend tests;
- configuration validation.

Security workflow should perform practical dependency/security checks.

Do not add CI tools purely for appearance.

---

## 31. Development Phases

### Phase 0 — Architecture

- inspect repository;
- validate architecture;
- record decisions.

### Phase 1 — Foundation

- monorepo;
- configuration;
- Docker;
- CI;
- documentation skeleton.

### Phase 2 — Frontend

- React shell;
- routes;
- design system;
- API client.

### Phase 3 — Backend

- FastAPI;
- MongoDB Atlas;
- health;
- configuration.

### Phase 4 — Security

- authentication;
- authorization;
- secrets;
- rate limiting.

### Phase 5 — Ingestion

- document processing;
- metadata;
- Qdrant indexing.

### Phase 6 — Baseline RAG

- LangChain;
- Gemini;
- retrieval;
- generation.

### Phase 7 — Verification

- claims;
- evidence matching;
- verification;
- citations.

### Phase 8 — Integrity

- provenance;
- temporal validity;
- conflicts;
- suspicious content.

### Phase 9 — Recovery

- diagnosis;
- LangGraph;
- adaptive recovery;
- abstention.

### Phase 10 — Observability

- traces;
- SSE;
- recovery timeline.

### Phase 11 — Evaluation

- datasets;
- baselines;
- ablations;
- experiment UI.

### Phase 12 — Production

- security hardening;
- cost controls;
- deployment;
- documentation;
- GitHub polish.

After every phase:

```text
Implement
 ↓
Run checks
 ↓
Inspect failures
 ↓
Fix
 ↓
Review architecture/security
 ↓
Update docs
 ↓
Commit-ready state
```

---

## 32. Failure Handling

Explicitly handle:

- Gemini unavailable;
- Gemini rate limits;
- Qdrant unavailable;
- MongoDB unavailable;
- SSE disconnect;
- duplicate requests;
- stale embeddings;
- ingestion failure;
- malicious documents;
- prompt injection;
- conflicting sources;
- unsupported claims;
- infinite recovery;
- oversized context;
- cost explosion;
- unauthorized resource access.

Never expose raw stack traces to users.

---

## 33. Documentation

Maintain:

```text
README.md
CONTRIBUTING.md
SECURITY.md

docs/
├── architecture/
├── security/
├── deployment/
└── evaluation/
```

Architecture decision log must explain material deviations from this specification.

Threat model:

```text
Asset
Threat
Attack Vector
Impact
Likelihood
Mitigation
Residual Risk
```

---

## 34. Scope Boundaries

Do NOT add for MVP:

- blockchain provenance;
- multi-agent swarm;
- custom foundation-model training;
- mandatory fine-tuning;
- Kubernetes;
- Kafka;
- Redis without a demonstrated requirement;
- Celery without a demonstrated background-work requirement;
- arbitrary code execution;
- generic AI testing platform.

Only add advanced infrastructure when a real requirement appears.

---

## 35. Acceptance Criteria

The MVP is complete only when a user can:

1. register/login;
2. create a knowledge base;
3. upload supported documents;
4. inspect document metadata/provenance;
5. ask a question;
6. retrieve evidence;
7. generate a Gemini-backed answer through LangChain;
8. inspect claims;
9. inspect claim-level evidence;
10. see verification states;
11. detect material source conflicts;
12. diagnose reliability failures;
13. trigger bounded adaptive recovery;
14. re-verify the recovered answer;
15. receive a grounded answer or abstention;
16. inspect execution traces;
17. see live SSE progress;
18. inspect evidence provenance;
19. compare experiments;
20. run the system using online MongoDB Atlas and Qdrant Cloud;
21. deploy frontend/backend without changing application architecture.

---

## 36. Final Quality Gate

Before declaring completion:

```text
ARCHITECTURE
[ ] LangChain is the AI abstraction
[ ] LangGraph is stateful orchestration
[ ] Gemini is the configured provider
[ ] Qdrant is retrieval infrastructure
[ ] MongoDB Atlas is persistence
[ ] TRUSTRAG logic is independently implemented

CONFIGURATION
[ ] no scattered model IDs
[ ] centralized models.yaml
[ ] secrets only in environment
[ ] embedding configuration versioned
[ ] configuration recorded per analysis

AI
[ ] retrieval works
[ ] claim verification works
[ ] provenance works
[ ] conflict handling works
[ ] diagnosis works
[ ] recovery works
[ ] abstention works

SECURITY
[ ] authentication
[ ] authorization
[ ] IDOR protection
[ ] prompt injection defenses
[ ] rate limits
[ ] secret protection
[ ] bounded AI execution

OPERATIONS
[ ] structured logs
[ ] traces
[ ] SSE recovery
[ ] timeouts
[ ] retry limits
[ ] cost controls

DELIVERY
[ ] GitHub-ready
[ ] Docker
[ ] CI
[ ] documentation
[ ] MongoDB Atlas
[ ] Qdrant Cloud
[ ] Gemini
[ ] deployment-ready
```

---

## 37. Design Statement

The final product should communicate this engineering story:

```text
TRUSTRAG does not merely ask an LLM for an answer.

It asks:

1. Did we retrieve the right evidence?
2. Is that evidence applicable and trustworthy enough?
3. Does every important claim have support?
4. Did the model introduce unsupported information?
5. What failed?
6. Can the system recover intelligently?
7. If recovery fails, can it abstain safely?
8. Can an engineer inspect exactly why the system made that decision?
```

That is the core of TRUSTRAG.
