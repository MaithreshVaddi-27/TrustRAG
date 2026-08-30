# TRUSTRAG — System Architecture

## Overview

TRUSTRAG is an AI reliability workbench that implements a structured reliability loop over RAG:

```
Query → Retrieve → Rerank → Generate → Decompose Claims → Verify Claims
      → Analyze Evidence Integrity → Diagnose Failure → Adaptive Recovery
      → Re-verify → Grounded Answer / Abstain
```

The portfolio differentiator is the **diagnosis → recovery loop**, not retrieval or generation alone.

---

## Component Map

```
React (Vite + Tailwind)
    │
    │ REST /api/v1/...  │  SSE /api/v1/analyses/{id}/stream
    ▼
FastAPI (Python 3.11)
    │
    ├─── app/core/         Settings, ModelRegistry, Logging, Exceptions
    ├─── app/db/           MongoDB Atlas client (Motor async)
    ├─── app/ai/           LangChain wrappers (LLM, embeddings)
    ├─── app/ingestion/    Document parsing, chunking, indexing
    ├─── app/retrieval/    Dense + Sparse + Hybrid fusion + Reranking
    ├─── app/generation/   Grounded answer generation (Gemini via LangChain)
    ├─── app/verification/ Claim decomposition + evidence verification
    ├─── app/integrity/    Provenance, temporal validity, conflict detection
    ├─── app/reliability/  Reliability scoring engine
    ├─── app/recovery/     Failure diagnosis + adaptive strategy selection
    ├─── app/workflows/    LangGraph stateful workflow (main RAG loop)
    └─── app/evaluation/   Experiment runner + metrics
         │
         ├─── Google Gemini API (via langchain-google-genai)
         │       LLM: gemini-3.5-flash-lite / gemini-2.5-flash-lite (configurable)
         │       Embedding: models/gemini-embedding-001, 384-dim MRL (0 MB GPU RAM)
         │
         ├─── Qdrant (vector store)
         │       Dense + Sparse/BM25 + Hybrid/RRF retrieval
         │
         └─── MongoDB Atlas (application data)
                 All metadata, state, traces, analyses
```

---

## LangGraph Workflow (Phase 9)

```
START
  ↓
RETRIEVE          ← dense + sparse + hybrid fusion
  ↓
RERANK            ← optional cross-encoder reranking
  ↓
GENERATE          ← grounded answer via Gemini
  ↓
VERIFY            ← claim decomposition + evidence matching
  ↓
DIAGNOSE
  ├── TRUSTED              → ANSWER
  ├── RETRIEVAL_FAILURE    → RECOVER_RETRIEVAL (query rewrite / re-retrieve)
  ├── EVIDENCE_FAILURE     → RESOLVE_EVIDENCE (conflict resolution / expansion)
  ├── GENERATION_FAILURE   → RECOVER_GENERATION (claim filtering / regeneration)
  └── HIGH_RISK            → ABSTAIN
        ↓
      REVERIFY
        ↓
      ANSWER / ABSTAIN
```

**Bounded by:** `max_recovery_attempts` in `models.yaml`. No infinite loops.

---

## Data Flow (Retrieval → Answer)

```
User Query
    │
    ├─ Dense Embedding (sentence-transformers, local)
    │      └─ Qdrant dense vector search
    │
    ├─ Sparse/BM25 (Qdrant built-in)
    │
    └─ Hybrid Fusion (RRF)
           │
           ├─ Optional Reranking (cross-encoder)
           │
           └─ Evidence Selection (top-k chunks)
                  │
                  └─ Gemini Generation (grounded prompt)
                         │
                         ├─ Claim Decomposition
                         ├─ Claim Verification
                         ├─ Evidence Integrity Analysis
                         ├─ Reliability Scoring
                         ├─ Failure Diagnosis
                         ├─ Adaptive Recovery (if needed)
                         └─ Grounded Answer / Abstention
```

---

## Configuration Architecture

```
.env (secrets)
    ↓
Pydantic Settings (app/core/config.py)

config/models.yaml (model IDs, thresholds, tuning)
    ↓
ModelConfig (app/core/config.py)
    ↓
ModelRegistry (app/core/model_registry.py)
    get_llm()              → ChatGoogleGenerativeAI
    get_embedding_model()  → HuggingFaceEmbeddings
    get_verification_model() → ChatGoogleGenerativeAI
    get_reranker()         → CrossEncoder (or None)
```

No model ID appears outside `models.yaml` and `model_registry.py`.

---

## MongoDB Collections

| Collection       | Purpose                                         |
|------------------|-------------------------------------------------|
| `users`          | Accounts, hashed passwords                      |
| `knowledge_bases`| KB metadata, ownership                          |
| `documents`      | Document metadata, provenance, integrity status |
| `analyses`       | Analysis runs, query, status, config snapshot   |
| `claims`         | Decomposed claims per analysis                  |
| `evidence`       | Retrieved evidence metadata                     |
| `recovery_runs`  | Recovery attempt history                        |
| `trace_events`   | SSE trace persistence                           |
| `experiments`    | Experiment configurations and results           |
| `feedback`       | User feedback on analyses                       |

---

## Security Architecture

See [security-controls.md](../security/security-controls.md) for full controls.

Key boundaries:
- Retrieved documents are always `UNTRUSTED DATA` — never auto-promoted to instructions
- JWT protected all routes (except `/health`, `/auth/*`)
- CORS locked to configured origins
- Rate limiting on all public endpoints
- Authorization checked server-side per resource (IDOR prevention)
