# TRUSTRAG — System Architecture

## Overview

TRUSTRAG is an AI reliability workbench that implements a closed-loop reliability and self-healing engine over Retrieval-Augmented Generation (RAG):

```
Query → Retrieve (Vector + BM25 + MCP Live Web) → Rerank (RRF) 
      → Grounded Generation (Gemini 3.5 Flash Lite) 
      → Propositional Claim Decomposition → NLI Claim Verification 
      → Evidence Integrity & Provenance Audit → Threshold Reliability Diagnosis 
      → Adaptive Recovery Loop (LangGraph StateGraph) 
      → Re-verify → Grounded Answer / Safe Abstention
```

The core portfolio differentiator is the **autonomous diagnosis → adaptive recovery loop**, not one-shot retrieval or generation alone.

---

## Component Map

```
React 18 + Vite (Port 5173)
    │
    │ REST /api/v1/... (Reverse Proxy) │ SSE /api/v1/analyses/{id}/stream
    ▼
FastAPI (Python 3.12, Default Port 8080)
    │
    ├─── app/core/         Settings, ModelRegistry, Logging, Security, Exceptions
    ├─── app/db/           MongoDB Atlas client (Motor async, connection pooling)
    ├─── app/ai/           LangChain / Gemini wrappers (LLM, 384d MRL embeddings)
    ├─── app/ingestion/    Document parsing, chunking, cryptographic hashing
    ├─── app/retrieval/    Dense + Sparse BM25 + Reciprocal Rank Fusion (RRF)
    ├─── app/mcp/          Model Context Protocol (MCP) Server & Dispatcher
    │       ├── tavily_search     → AI-curated RAG search with clean parsed snippets
    │       ├── duckduckgo_search → Zero-config, 100% free web search fallback
    │       └── hybrid_web_search → Parallel execution with URL deduplication
    ├─── app/services/     Search Service (SSRF sanitization, query boundaries)
    ├─── app/generation/   Grounded answer generation with multi-part coverage
    ├─── app/verification/ Propositional claim decomposition + NLI entailment
    ├─── app/integrity/    Cryptographic SHA-256 provenance & temporal audit
    ├─── app/reliability/  Reliability scoring engine & threshold diagnosis
    ├─── app/agent/        LangGraph stateful self-healing workflow
    └─── app/evaluation/   Experiment runner & benchmark metrics
         │
         ├─── Google Gemini API (via langchain-google-genai)
         │       LLM: gemini-3.5-flash-lite / gemini-2.5-flash-lite
         │       Embedding: models/gemini-embedding-001, 384-dim MRL (0 MB local GPU RAM)
         │
         ├─── Qdrant (Vector & Payload Store)
         │       Dense vector indexing + Payload filtering
         │
         └─── MongoDB (Operational Data Store)
                 Users, Knowledge Bases, Analyses, Claims, Evidence, Traces
```

---

## Model Context Protocol (MCP) Integration

TRUSTRAG adopts the open **Model Context Protocol (MCP)** specification to decouple agent reasoning from retrieval and external live grounding:

1. **MCP Server (`app/mcp/server.py`)**:
   - Exposes standardized JSON-RPC endpoints: `tools/list` and `tools/call`.
   - Built-in tools:
     - `tavily_search`: High-accuracy AI search tailored for RAG grounding.
     - `duckduckgo_search`: Free live search requiring zero API keys.
     - `hybrid_web_search`: Parallel execution across both engines with automatic URL deduplication.
2. **MCP Client Dispatcher (`app/mcp/client.py`)**:
   - Dispatches agent grounding requests through the standard MCP interface.
   - Converts web results into verified context segments with SHA-256 hashes and citation metadata.
3. **Defense-in-Depth Search Security (`app/services/search_service.py`)**:
   - Strict SSRF sanitization (`sanitize_url` rejects non-HTTP/HTTPS schemes and internal network probes).
   - Hard query boundary limits (`MAX_QUERY_LENGTH = 500`) and 8.0s timeout guards.

---

## LangGraph Self-Healing Workflow

```
       [START]
          │
          ▼
   [retrieval_node] ◄──────────────┐ (Adaptive Recovery Edge)
   (Dense + Sparse + MCP Web)     │
          │                        │
          ▼                        │
   [generation_node]               │
   (Context-bound synthesis)      │
          │                        │
          ▼                        │
   [verification_node]             │
   (Propositional NLI)             │
          │                        │
          ▼                        │
  [evaluation_node]                │
  (Check reliability thresholds)   │
          │                        │
     Pass or Fail?                 │
     ├── PASS ─────────────────────┼──────────┐
     │                             │          │
     └── FAIL (within max attempts) │          │
          │                        │          │
          ▼                        │          │
   [recovery_node] ────────────────┘          │
   - Reset stale state["answer"]              │
   - Adaptive strategy selection:             │
     * Query Rewrite (target missing claims)  │
     * Expanded Retrieval (top_k=40)          │
                                              │
     Max attempts reached?                    │
     ├── Thresholds met ──────────────────────┴──► [ANSWER]
     └── Low confidence / insufficient data ─────► [ABSTAIN]
```

**Guardrails:**
- Bounded strictly by `max_recovery_attempts` in `models.yaml`.
- State reset logic: `state["answer"] = None` and `state["claims"] = []` prevent stale abstentions from propagating when newly retrieved segments provide the missing facts.

---

## Frontend Architecture (`apps/web`)

1. **Split-Screen Telemetry Workbench (`PlaygroundPage.jsx`)**:
   - **Left Control Panel**: Fixed width (`md:w-[320px] lg:w-[360px] xl:w-[400px]`), scrollable input container, docked "Run Analysis" button.
   - **Right Telemetry Panel**: Flexible width (`flex-1 min-w-0`), independent scroll container.
2. **Executive Telemetry HUD (`PipelineTelemetryHUD.jsx`)**:
   - 4-stage live architecture tracker: `Hybrid Retrieval` → `Cross-RRF Fusion` → `Grounded Synthesis` → `Claim Entailment`.
   - Real-time status indicators (emerald check, pulsing cyan spinner, slate pending).
3. **Classy Markdown & GFM Table Renderer (`FormattedAnswer.jsx`)**:
   - Integrated with `react-markdown` and `remark-gfm`.
   - Custom typography for headers, bold tokens, glowing cyan list markers, and responsive dark glass data tables (`<table>`, `<thead>`, `<tbody>`).
4. **Dual-Channel Active Polling Resiliency**:
   - Employs Server-Sent Events (SSE) for sub-second event streaming.
   - Concurrently runs a 2-second background status polling watcher to guarantee immediate completion transitions even if browser SSE connections buffer.
5. **Open Knowledge JSON-LD Audit Dossier**:
   - One-click export button generating schema-compliant JSON-LD audit packages containing full cryptographic provenance, verified claims, and reliability scores.

---

## MongoDB Collections

| Collection       | Purpose                                                 |
|------------------|---------------------------------------------------------|
| `users`          | Accounts, hashed passwords (bcrypt 12 rounds)           |
| `knowledge_bases`| Multi-tenant KB metadata and user ownership             |
| `documents`      | Document metadata, cryptographic SHA-256 provenance     |
| `document_chunks`| Ingested text segments with positional metadata         |
| `analyses`       | Analysis runs, queries, status, reliability diagnostics |
| `claims`         | Propositional claims decomposed and verified per run    |
| `evidence`       | Retrieved chunks and web grounding citations            |
| `recovery_runs`  | History of adaptive self-healing actions                |
| `trace_events`   | Persistent audit log of all pipeline events             |
| `experiments`    | Evaluation experiment datasets and benchmark results    |
| `feedback`       | User feedback on synthesized answers                    |
