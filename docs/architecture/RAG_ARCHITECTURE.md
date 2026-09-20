# TrustRAG — System Architecture

Complete technical reference for the TrustRAG project.

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [RAG Pipeline Flow](#rag-pipeline-flow)
   - [Ingestion](#ingestion)
   - [Query Processing](#query-processing)
   - [Retrieval](#retrieval)
   - [Generation](#generation)
   - [Verification](#verification)
   - [Adaptive Recovery](#adaptive-recovery)
5. [Data Stores](#data-stores)
6. [Frontend Architecture](#frontend-architecture)
7. [Configuration](#configuration)
8. [Deployment](#deployment)

---

## Overview

TrustRAG is a trustworthy Retrieval-Augmented Generation system. It goes beyond a naive retrieve-and-generate pipeline by adding deterministic query routing, hybrid retrieval with Reciprocal Rank Fusion, cross-encoder reranking with early termination, grounded generation with inline citations, NLI-based claim verification, a trust verdict computation layer, and an adaptive recovery loop that retries with query rewriting or expanded retrieval when verification fails. A semantic response cache avoids redundant LLM calls for equivalent queries. A post-ingestion evidence integrity audit compares stored vectors against source records in MongoDB to detect drift.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI (async, Python 3.11+) |
| Agent orchestration | LangGraph (`StateGraph`) |
| Vector database | Qdrant (dense + sparse vectors, 384d) |
| Document store | MongoDB (async `motor`) |
| Embeddings | Local-only `BAAI/bge-small-en-v1.5` — PyTorch (`huggingface`) or ONNX Runtime (`onnx`, torch-free) |
| Reranking | CrossEncoder (sentence-transformers, off by default) |
| Generation | llama.cpp / Ollama (local, default) · Gemini / NVIDIA NIM (cloud, selectable) |
| Frontend | React 18, Vite 6, Tailwind CSS 3, `motion` |
| Container runtime | Docker Compose |

---

## Project Structure

```
TrustRAG/
├── apps/
│   ├── api/                          # Python backend
│   │   ├── app/
│   │   │   ├── main.py               # FastAPI app factory
│   │   │   ├── agent/
│   │   │   │   ├── graph.py          # LangGraph StateGraph + recovery loop
│   │   │   │   └── router.py         # Pre-retrieval deterministic query router
│   │   │   ├── api/v1/               # REST route handlers (auth, KBs, analyses, …)
│   │   │   ├── retrieval/
│   │   │   │   ├── retriever.py      # Hybrid dense+sparse search with RRF
│   │   │   │   └── reranker.py       # CrossEncoder reranking (off by default)
│   │   │   ├── generation/
│   │   │   │   └── generator.py      # Grounded answer generation + citations
│   │   │   ├── verification/
│   │   │   │   ├── verifier.py       # Claim decomposition + NLI verification
│   │   │   │   ├── verdict.py        # Trust verdict computation
│   │   │   │   └── integrity.py      # Evidence integrity audit (SHA-256)
│   │   │   ├── ingestion/
│   │   │   │   ├── pipeline.py       # Ingestion coordinator
│   │   │   │   ├── parser.py         # Multi-format parsing + OCR routing
│   │   │   │   ├── chunker.py        # Word-snapping windows (512/64)
│   │   │   │   ├── chunking_strategies.py  # Pluggable chunking strategies
│   │   │   │   └── sparse_vector.py  # BM25-style sparse weight generation
│   │   │   ├── core/
│   │   │   │   ├── config.py         # Settings + models.yaml loader
│   │   │   │   ├── model_registry.py # Model factory (embedding, verification, LLM)
│   │   │   │   ├── semantic_cache.py # Semantic response cache + context pruning
│   │   │   │   ├── local_llm.py      # Ollama + llama.cpp LangChain clients
│   │   │   │   ├── hardware.py       # Hardware detection + llama.cpp launch args
│   │   │   │   └── memory.py         # Conversation memory trimming
│   │   │   ├── db/
│   │   │   │   ├── qdrant.py         # Qdrant client + collection init
│   │   │   │   └── mongodb.py        # MongoDB client + indexes (`Collections`)
│   │   │   ├── services/
│   │   │   │   ├── analysis_service.py  # Analysis lifecycle + SSE tickets
│   │   │   │   ├── kb_service.py     # Knowledge base CRUD + snapshots
│   │   │   │   ├── auth_service.py   # Auth + JTI revocation
│   │   │   │   ├── experiment_service.py  # Experiment records
│   │   │   │   └── search_service.py # Web-search orchestration (SSRF-guarded)
│   │   │   └── mcp/                  # MCP server (`trustrag_*` tools) + client
│   │   ├── config/
│   │   │   └── models.yaml           # Model IDs, thresholds, tuning params (v1.15)
│   │   ├── tests/                    # Backend suite incl. `tests/eval/` harness
│   │   └── pyproject.toml
│   └── web/                          # React frontend
│       ├── src/
│       │   ├── pages/                # 12 routes (Landing … Settings, Trace, 404)
│       │   ├── components/
│       │   │   ├── landing/          # Landing page sections
│       │   │   └── workbench/        # QueryPanel, ResultsPanel, ClaimInspector, …
│       │   ├── services/             # Domain services (KB, analysis, auth, …)
│       │   ├── lib/                  # Central Axios client, labels, motion config
│       │   ├── store/                # Auth session store
│       │   ├── hooks/                # `useBackendHealth`, …
│       │   ├── layouts/              # App / auth layouts
│       │   └── styles/               # Per-page CSS
│       ├── e2e/                      # Playwright specs
│       └── package.json
├── docker-compose.yml                # api + web + qdrant (MongoDB + LLM on host)
├── config/
│   └── ports.yaml                    # Canonical port registry
└── docs/                             # Specs, architecture, security, eval, deploy
```

---

## RAG Pipeline Flow

```
User Query
    │
    ▼
┌─────────────────────────┐
│ Semantic Cache Check    │  cosine similarity ≥ 0.94 → skip generation
└────────────┬────────────┘
             │ miss
             ▼
┌─────────────────────────┐
│ Retrieval Node          │  hybrid dense + sparse → RRF → CrossEncoder rerank
└────────────┬────────────┘
             │ top-k chunks + evidence_ids
             ▼
┌─────────────────────────┐
│ Generation Node         │  grounded prompt → Gemini/local LLM → answer + citations
└────────────┬────────────┘
             │ answer
             ▼
┌─────────────────────────┐
│ Verification Node       │  decompose → NLI → compute verdict
└────────────┬────────────┘
             │
        ┌────┴────┐
        │ PASS?   │
        │         │
    yes ▼     no  ▼
   [END]   ┌─────────────────────────┐
           │ Recovery Node           │  strategy = rewrite | re_retrieve | regenerate
           └────────────┬────────────┘
                        │
                        ▼
                   back to Retrieval
                   (loop until PASS or max attempts)
```

### LangGraph State

```python
class AgentState(TypedDict):
    analysis_id: str
    user_id: str | None
    kb_id: str
    query: str
    current_query: str          # may differ after query rewrite
    answer: str | None
    chunks: list[dict]          # evidence segments
    evidence_ids: list[str]
    claims: list[dict]          # verified atomic claims
    attempts: int               # recovery loop counter
    verdict_status: str         # "PASS" | "FAIL"
    recovery_strategy: str | None
    reliability_score: float | None
    diagnosis_type: str | None
    diagnosis_failures: list[str]
    cache_hit: bool
    node_errors: list[dict]
```

---

### Ingestion

Pipeline (`app/ingestion/pipeline.py`) stages:

1. **Parse** — file type handler extracts raw text (PDF, DOCX, CSV, JSON, HTML, HTM, TXT, MD; scanned pages via RapidOCR-ONNX fallback)
2. **Chunk** — word-snapping windows; configurable `chunk_size` (default 512) and `chunk_overlap` (default 64); selectable `chunking_strategy`
3. **Embed** — per-chunk: dense vector (local BGE, torch or ONNX) + BM25-style sparse weights
4. **Index** — upsert points to Qdrant collection `kb_{kb_id}`
5. **Status update** — write `completed` / `failed` to MongoDB document record

A per-event-loop `Semaphore(1)` serializes ingestion jobs so concurrent uploads cannot starve the local embedding model.

---

### Query Processing

Router (`app/agent/router.py`) applies deterministic regex rules before any retrieval:

| Route | Trigger | Behavior |
|---|---|---|
| SIMPLE | Default; unsplittable input falls back here | Single-pass hybrid retrieval |
| TEMPORAL | Query names an explicit year (e.g. "in 2025") | Single call + `reference_time` (mid-year) for range filtering |
| COMPARISON | Markers (`vs`, `versus`, `compare`, "differences between") | Fan-out to sub-queries (≤2× base), merged via RRF |
| COMPLEX | Multi-`?` input | Deterministic per-question split, capped at `max_sub_queries: 3` |

The router is a pure function — no LLM call — so it adds zero latency. Partial branch outage degrades to surviving branches.

---

### Retrieval

Retriever (`app/retrieval/retriever.py`):

1. **Dense path** — embed query via local BGE, Qdrant `search` with cosine similarity
2. **Sparse path** — BM25-style client TF saturation + Qdrant server-side IDF (`Modifier.IDF`); `sparse_top_k: 0` disables this leg (current default — set `20` for full hybrid)
3. **Reciprocal Rank Fusion** — merge ranked lists: `score = Σ 1/(k + rank_i)` with `rrf_k: 60`, `fusion_top_k: 20` enforced
4. **CrossEncoder reranking** — `sentence-transformers` CrossEncoder on fused candidates (off by default; needs the `local-models` extra); depth cap `top_k: 20`
5. **Adaptive top-k** — returns fewer chunks when confidence is high, up to `max_context_chunks: 8` when confidence is low

Per-branch timeouts (45 s each) ensure one hung branch degrades gracefully instead of failing the whole query.

---

### Generation

Generator (`app/generation/generator.py`):

- System prompt enforces: ground every assertion in Context segments, never fabricate, address all sub-questions, end every factual sentence with an inline citation like `[Segment 3]`
- Prompt injection defense: treats Context section as untrusted raw data
- `strip_stray_abstain()` cleans trailing ABSTAIN tokens appended by small local models
- Produces structured `FormattedAnswer` with sections, citations, and confidence metadata

---

### Verification

Verifier (`app/verification/verifier.py`):

1. **Claim decomposition** — LLM breaks answer into atomic factual claims
2. **Meta-claim filter** — removes opinion/meta claims ("I believe…") that cannot be NLI-verified
3. **Batch NLI** — each claim scored against evidence segments as SUPPORTED / CONTRADICTED / NEUTRAL
4. **Verdict** (`app/verification/verdict.py`):
   - `VerdictStatus`: PASS or FAIL
   - `ReliabilityStatus`: TRUSTED / UNCERTAIN / FAILED / ABSTAINED
   - `DiagnosisType`: RETRIEVAL_FAILURE / OUTAGE / EVIDENCE_CONFLICT / LOW_COVERAGE / NONE
   - Thresholds from `models.yaml`: `minimum_evidence_coverage`, `maximum_contradiction_rate`, `abstain_below`

---

### Adaptive Recovery

Recovery node (`app/agent/graph.py:recovery_node`) cycles through strategies until verdict passes or `max_recovery_attempts` is exhausted:

| Strategy | Behavior |
|---|---|
| `query_rewrite` | LLM expands acronyms and terms targeting missing claims; sanitized before reuse |
| `re_retrieve` | Widens search parameters (more candidates); downgraded to `regenerate` if evidence already sufficient |
| `regenerate` | Retries generation on existing chunks without new retrieval |

The loop: `retrieval → generation → verification → (if FAIL) recovery → retrieval → ...`

Sanitization strips meta-prefixes ("Expanded Search Query:", "Rewritten Query:") and detects echoed instructions to prevent junk tokens from polluting retrieval.

---

## Data Stores

**Qdrant** — vector database
- Collection per knowledge base: `kb_{kb_id}`
- Each point: dense vector (384d BGE) + sparse weights + payload (chunk text, document ID, chunk index, OCR flags)
- Hybrid dense+sparse search; INT8 on-disk quantization; pre-IDF collections recreate on init

**MongoDB** — document store (`Collections` in `app/db/mongodb.py`)
- Collections: `users`, `knowledge_bases`, `documents`, `document_chunks`, `analyses`, `claims`, `evidence`, `recovery_runs`, `trace_events`, `experiments`, `feedback`, `revoked_tokens`, `stream_tickets`
- Tracks ingestion status, analysis results, claim verification results, recovery run history
- Evidence integrity audit compares SHA-256 hashes of served chunks against source `document_chunks` records

---

## Frontend Architecture

React 18 SPA with twelve routes:

| Route | Page | Purpose |
|---|---|---|
| `/` | LandingPage | Marketing / product overview |
| `/login`, `/register` | Auth pages | JWT login / account creation |
| `/dashboard` | DashboardPage | KBs, recent analyses, reliability at a glance |
| `/playground` | PlaygroundPage | Query interface + results viewer |
| `/knowledge-bases` | KnowledgeBasesPage | Upload documents, manage KBs, snapshots |
| `/evidence` | EvidencePage | Evidence segments + integrity status |
| `/claims` | ClaimsPage | Verified claims + verdicts |
| `/conflicts` | ConflictsPage | Source/claim disagreements |
| `/experiments` | ExperimentsPage | A/B tests and metrics |
| `/traces/:id` | TracePage | Pipeline timeline, timings, recovery events |
| `/settings` | SettingsPage | Provider, embedding, account preferences |

Key components:
- **QueryPanel** — input form with model/provider selector, streaming progress
- **ResultsPanel** — formatted answer with collapsible sections
- **ClaimInspector** — drill-down into individual verified claims with evidence links
- **EvidenceViewer** — raw evidence segments with integrity status
- **ExecutionTrace** — timeline of pipeline nodes executed, timings, recovery events
- **FormattedAnswer** — rendered markdown answer with inline `[Segment N]` citations

Motion system: `motion` package with shared config (`lib/motionConfig.js`), entrance/exit animations, layout transitions.

---

## Configuration

**`config/models.yaml`** — single source of truth for:
- Embedding model IDs and providers
- Verification model IDs and thresholds
- LLM model IDs, timeouts, context window sizes
- Retrieval parameters (top_k, chunk_size, overlap, RRF k)
- Recovery strategy priority order and max attempts
- Semantic cache similarity threshold

**`.env`** — secrets and deployment-specific values:
- `JWT_SECRET`, `MONGODB_URI`, `QDRANT_URL` (+ `QDRANT_API_KEY` for cloud)
- `GEMINI_API_KEY` / `NVIDIA_API_KEY` (only for cloud LLM providers), `TAVILY_API_KEY` (else DuckDuckGo)
- `EMBEDDING_PROVIDER`, `LLM_PROVIDER`, model/endpoint overrides (env wins over `models.yaml`)

**`config/ports.yaml`** — canonical port registry for all services (Qdrant, MongoDB, Ollama, llama.cpp, frontend dev server).

Settings class (`app/core/config.py`) merges `.env` → `models.yaml` into a typed `Settings` object via pydantic-settings. Business code never reads `os.environ` directly.

---

## Deployment

**Docker Compose** (`docker-compose.yml`) — orchestrates:
- `api` — FastAPI backend (port 8000, hot-reload bind mount, non-root runtime)
- `web` — React frontend, Node 22 dev server with HMR (port 5173)
- `qdrant` — Qdrant vector database (host 6335 → container 6333, persistent volume)

MongoDB and the LLM server (Ollama / llama-server) run on the **host**; the `api`
container reaches them via `host.docker.internal`.

**Hardware detection** (`app/core/hardware.py`):
- Auto-detects Apple Silicon Metal, NVIDIA CUDA, or CPU-only
- Generates optimal `llama-server` launch flags (GPU offload, flash attention, KV-cache quantization)
- Monitors system memory and adjusts context budgets to prevent OOM

**Local development** — all services run natively; `ports.yaml` ensures consistent port assignments across team members.

---

## Key Design Decisions

1. **Deterministic routing over LLM classification** — zero-latency, zero-cost query routing with no hallucination risk
2. **Hybrid retrieval (dense + sparse + RRF)** — dense captures semantic similarity; sparse captures exact keyword matches; RRF merges both without tuning weights
3. **Early termination in reranking** — stops scoring candidates once top result is confident enough, cutting latency 30-50% on easy queries
4. **NLI-based verification, not faithfulness scoring** — decomposes into atomic claims and uses a trained NLI model for objective support/contradiction classification
5. **Adaptive recovery loop** — retries with targeted query rewriting instead of blind regeneration; knows when to stop (max attempts, evidence already sufficient)
6. **Semantic cache with verification revalidation** — cached answers skip generation but still run retrieval + NLI to ensure claims and evidence are current
7. **Evidence integrity audit** — post-ingestion sha256 hash comparison detects vector drift or storage corruption
8. **Per-branch retrieval timeouts** — one slow retrieval path degrades to the other instead of failing the whole query
