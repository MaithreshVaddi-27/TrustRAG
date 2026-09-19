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
| Web framework | FastAPI (async, Python 3.12) |
| Agent orchestration | LangGraph (`StateGraph`) |
| Vector database | Qdrant (dense + sparse vectors) |
| Document store | MongoDB |
| Embeddings | ONNX BGE (local), OpenAI text-embedding-3-small (cloud) |
| Reranking | CrossEncoder (sentence-transformers) |
| Generation | Google Gemini, Ollama (local), llama.cpp (local) |
| Frontend | React 18, Vite 6, Tailwind CSS 4, Framer Motion 12 |
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
│   │   │   ├── retrieval/
│   │   │   │   ├── retriever.py      # Hybrid dense+sparse search with RRF
│   │   │   │   └── reranker.py       # CrossEncoder reranking
│   │   │   ├── generation/
│   │   │   │   └── generator.py      # Grounded answer generation + citations
│   │   │   ├── verification/
│   │   │   │   ├── verifier.py       # Claim decomposition + NLI verification
│   │   │   │   ├── verdict.py        # Trust verdict computation
│   │   │   │   └── integrity.py      # Evidence integrity audit
│   │   │   ├── ingestion/
│   │   │   │   ├── pipeline.py       # Ingestion coordinator
│   │   │   │   ├── chunker.py        # Character-based chunking
│   │   │   │   ├── chunking_strategies.py  # Pluggable chunking strategies
│   │   │   │   └── sparse_vector.py  # Sparse keyword weight generation
│   │   │   ├── core/
│   │   │   │   ├── config.py         # Settings + models.yaml loader
│   │   │   │   ├── model_registry.py # Model factory (embedding, verification, LLM)
│   │   │   │   ├── semantic_cache.py # Semantic response cache + context pruning
│   │   │   │   ├── local_llm.py      # Ollama + llama.cpp LangChain clients
│   │   │   │   ├── hardware.py       # Hardware detection + llama.cpp launch args
│   │   │   │   └── memory.py         # Conversation memory trimming
│   │   │   ├── db/
│   │   │   │   ├── qdrant.py         # Qdrant client + collection init
│   │   │   │   └── mongodb.py        # MongoDB client
│   │   │   ├── services/
│   │   │   │   ├── kb_service.py     # Knowledge base CRUD
│   │   │   │   └── search_service.py # Search orchestration
│   │   │   ├── api/                  # REST route handlers
│   │   │   └── mcp/                  # MCP server + client
│   │   └── config/
│   │       └── models.yaml           # Model IDs, thresholds, tuning params
│   └── web/                          # React frontend
│       ├── src/
│       │   ├── components/
│       │   │   ├── Layout/           # AppLayout, Sidebar, Header
│       │   │   ├── Playground/       # QueryPanel, ResultsPanel
│       │   │   ├── KnowledgeBase/    # KB upload, management UI
│       │   │   └── shared/           # Button, Card, Skeleton, etc.
│       │   ├── pages/                # LandingPage, PlaygroundPage, DashboardPage, KnowledgeBasesPage
│       │   ├── hooks/                # useQuery, useKnowledgeBase
│       │   ├── lib/                  # API client, animations, motionConfig
│       │   └── styles/               # Tailwind config, global CSS
│       └── index.html
├── docker-compose.yml
├── config/
│   ├── models.yaml
│   └── ports.yaml
└── docs/
    └── RAG_ARCHITECTURE.md           # This file
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

1. **Parse** — file type handler extracts raw text (PDF, DOCX, TXT, etc.)
2. **Chunk** — character-based splitting with word-boundary snapping; configurable `chunk_size` (default 1000) and `chunk_overlap` (default 200)
3. **Embed** — per-chunk: dense vector (ONNX BGE or OpenAI) + sparse keyword weights
4. **Index** — upsert points to Qdrant collection `kb_{kb_id}`
5. **Status update** — write `completed` / `failed` to MongoDB document record

A per-event-loop `Semaphore(1)` serializes ingestion jobs so concurrent uploads cannot starve the local embedding model.

---

### Query Processing

Router (`app/agent/router.py`) applies deterministic rules before any retrieval:

| Route | Trigger | Behavior |
|---|---|---|
| SIMPLE | < 8 words, no temporal/comparison markers | Single-pass retrieval |
| TEMPORAL | time-related keywords (e.g. "latest", "2024") | Adds temporal filter to retrieval |
| COMPARISON | comparison markers ("vs", "compare", "difference") | Fan-out to sub-queries, merge via RRF |
| COMPLEX | ≥ 8 words, multiple noun phrases | Expanded retrieval with broader search params |

The router is a pure function — no LLM call — so it adds zero latency.

---

### Retrieval

Retriever (`app/retrieval/retriever.py`):

1. **Dense path** — embed query via ONNX BGE, Qdrant `search` with cosine similarity
2. **Sparse path** — generate sparse keyword weights, Qdrant `search` with sparse vectors
3. **Reciprocal Rank Fusion** — merge both ranked lists: `score = Σ 1/(k + rank_i)` with configurable `k` (default 60)
4. **CrossEncoder reranking** — `sentence-transformers` CrossEncoder on fused candidates; early termination when top candidate confidence ≥ 0.85 and score gap ≥ 0.15
5. **Adaptive top-k** — returns fewer chunks when confidence is high, up to `max_context_chunks` when confidence is low

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
- Each point: dense vector (384-d or 1536-d) + sparse keyword weights + payload (chunk text, document ID, chunk index)
- Supports hybrid dense+sparse search natively

**MongoDB** — document store
- Collections: `knowledge_bases`, `documents`, `analyses`, `document_chunks`, `recovery_runs`, `conversation_history`
- Tracks ingestion status, analysis results, claim verification results, recovery run history
- Evidence integrity audit compares sha256 hashes of stored vectors against source `document_chunks` records

---

## Frontend Architecture

React 18 SPA with four main routes:

| Route | Page | Purpose |
|---|---|---|
| `/` | LandingPage | Marketing / product overview |
| `/playground` | PlaygroundPage | Query interface + results viewer |
| `/dashboard` | DashboardPage | Analytics, usage stats |
| `/knowledge-bases` | KnowledgeBasesPage | Upload documents, manage KBs |

Key components:
- **QueryPanel** — input form with model/provider selector, streaming progress
- **ResultsPanel** — formatted answer with collapsible sections
- **ClaimInspector** — drill-down into individual verified claims with evidence links
- **EvidenceViewer** — raw evidence segments with integrity status
- **ExecutionTrace** — timeline of pipeline nodes executed, timings, recovery events
- **FormattedAnswer** — rendered markdown answer with inline `[Segment N]` citations

Motion system: `framer-motion` with configurable spring physics (`motionConfig.ts`), entrance/exit animations, layout transitions.

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
- `GEMINI_API_KEY`, `OPENAI_API_KEY`
- `MONGODB_URI`, `QDRANT_URL`
- `EMBEDDING_PROVIDER`, `AI_PROVIDER` (override models.yaml defaults)

**`config/ports.yaml`** — canonical port registry for all services (Qdrant, MongoDB, Ollama, llama.cpp, frontend dev server).

Settings class (`app/core/config.py`) merges `.env` → `models.yaml` into a typed `Settings` object via pydantic-settings. Business code never reads `os.environ` directly.

---

## Deployment

**Docker Compose** (`docker-compose.yml`) — orchestrates:
- `api` — FastAPI backend (port 8000)
- `web` — React frontend served by nginx (port 3000)
- `qdrant` — Qdrant vector database (port 6333)
- `mongodb` — MongoDB (port 27017)
- `ollama` — Ollama inference server (port 11434)

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
