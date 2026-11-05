# TrustRAG — Production Configuration & Serving Guide

**Document Version:** 1.0  
**Effective Date:** 2026-11-05  
**Target Environment:** Local Apple Silicon (Mac M2 8GB unified memory)  
**Security Posture:** Zero external cloud APIs, hosted inference, or document data egress. All inference local.

---

## 1. Executive Summary & Dual-Mode Architecture

TrustRAG implements a strict, dual-mode serving architecture designed to run reliably on resource-constrained hardware (e.g., Apple Silicon M2 with 8GB RAM).

```
                            ┌──────────────────────────────────────────────┐
                            │            Client / Ingestion API            │
                            └──────────────────────┬───────────────────────┘
                                                   │
                                     Validated Analysis Request
                                                   │
                                                   ▼
                                  ┌────────────────────────────────┐
                                  │   Model Policy & Mode Gating   │
                                  │     (AnalysisCreate schema)    │
                                  └────────┬───────────────┬───────┘
                                           │               │
                        Interactive Mode   │               │ Deep-Reasoning Mode
                       (DEEP_REASONING=0)  │               │ (DEEP_REASONING=true)
                                           ▼               ▼
                        ┌─────────────────────┐ ┌──────────────────────┐
                        │   gemma3:1b (1.0B)  │ │   qwen3:1.7b (1.7B)  │
                        │ Default Production  │ │ Offline / Analytical │
                        │  - Latency: < 7s    │ │  - Latency: ~30-90s  │
                        │  - Memory: ~2.4 GB  │ │  - Memory: ~3.8 GB   │
                        │  - 100% Citations   │ │  - Numeric & Tables  │
                        └──────────┬──────────┘ └──────────┬───────────┘
                                   │                       │
                                   └───────────┬───────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ Hybrid Retrieval (RRF) │
                                  │ BGE ONNX + Qdrant BM25 │
                                  └────────────┬───────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ MiniLM ONNX Reranker   │
                                  │ (DISABLED by default)  │
                                  └────────────┬───────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │  NLI Claim Verifier    │
                                  │  (gemma3:1b local)     │
                                  └────────────────────────┘
```

### Modes Overview

| Attribute | Default Production Mode | Deep-Reasoning Mode (Optional) |
|---|---|---|
| **Generator Model** | `gemma3:1b` (via local Ollama) | `qwen3:1.7b` (via local Ollama) |
| **Prompting Strategy** | XML CRAFT Contrastive System Prompt | XML CRAFT Contrastive System Prompt |
| **Target Workload** | Interactive API, queries, UI search | Batch analysis, complex numeric/tables |
| **p50 Latency** | **6,899 ms** (~6.9s) | **29,452 ms** (~29.5s) |
| **p95 Latency** | **17,549 ms** | **94,640 ms** |
| **Peak API RSS** | ~2,480 MB | ~3,820 MB |
| **Citation Correctness** | **100%** (1.000) | **100%** (1.000) |
| **Default Serving** | **Enabled by default** | **Disabled by default (feature-flagged)** |
| **Interactive Enforcement** | Allowed | Rejected with HTTP 422 if not opted-in |

---

## 2. Empirical Benchmark Scorecard (Frozen 27-Query Baseline)

The following metrics were measured empirically against the frozen 27-query fixture dataset (`baseline_v1.jsonl`):

| Metric | Phase 0 Baseline (Gemma 3 1B) | Exp 1: Default Prod (Gemma 3 1B + CRAFT) | Exp 2: Deep-Reasoning (Qwen 3 1.7B + CRAFT) | Exp 3: Gemma 3 1B + MiniLM Reranker |
|---|---|---|---|---|
| **Completed Queries** | 24 / 27 (88.9%) | 24 / 27 (88.9%) | 24 / 27 (88.9%) | 24 / 27 (88.9%) |
| **Abstained Queries** | 3 / 27 (11.1%) | 3 / 27 (11.1%) | 3 / 27 (11.1%)* | 3 / 27 (11.1%) |
| **Retrieval Recall@8** | 0.8889 (24/24 answerable) | 0.8889 (24/24 answerable) | 0.8889 (24/24 answerable) | 0.8889 (24/24 answerable) |
| **Claim Support Rate** | 0.8750 | **0.8750** | **1.0000** | 0.7917 |
| **Citation Correctness** | N/A (unserialized) | **1.0000 (100%)** | **1.0000 (100%)** | **1.0000 (100%)** |
| **p50 Latency (ms)** | 6,164 ms | **6,899 ms** | **29,452 ms** (4.3x slower) | 6,989 ms (+90 ms) |
| **p95 Latency (ms)** | 14,028 ms | **17,549 ms** | **94,640 ms** (5.4x slower) | 16,840 ms |
| **Peak API RSS** | 2,410 MB | 2,480 MB | 3,820 MB | 2,510 MB |

*\*Note: Qwen 3 1.7B required recovery loop hardening to prevent answering adversarial/unanswerable queries (`q022`).*

### Why the Reranker is Disabled by Default
1. **Zero Recall Lift:** Dense BGE ONNX + Sparse BM25 with Reciprocal Rank Fusion ($k=60$) already achieved 100% recall (24/24 answerable queries) at top-8 context. The reranker could not improve candidate recall.
2. **Reduced Claim Support in Exp 3:** Adding the reranker reordered passages such that claim support degraded from 0.8750 to 0.7917 on the fixture KB.
3. **CPU Overhead Avoidance:** While int8 ONNX inference adds only ~90ms latency, disabling it by default conserves CPU execution cycles on 8GB machines.
4. **Instant Fallback Available:** The code remains fully compiled and tested (`app/llm/onnx_reranker.py`); it can be toggled via `models.yaml` or `RERANKER_ENABLED=true` when deploying against large multi-thousand document corpora.

---

## 3. Operational Enable/Disable Instructions

### 3.1 Default Production Mode (Active by default)

To start the API in standard production mode:

```bash
# 1. Start Ollama with the production model
ollama serve &
ollama pull gemma3:1b

# 2. Launch TrustRAG API (uses models.yaml defaults: gemma3:1b, reranker disabled, deep-reasoning disabled)
cd apps/api
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3.2 Enabling Deep-Reasoning Mode (`qwen3:1.7b`)

For batch tasks or offline analytical pipelines:

```bash
# 1. Pull the deep-reasoning model
ollama pull qwen3:1.7b

# 2. Option A: Enable via Environment Variable (Recommended for container/process isolation)
export DEEP_REASONING_MODE=true
export DEEP_REASONING_MODEL=qwen3:1.7b
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Option B: Enable via models.yaml
# Edit apps/api/config/models.yaml:
# llm:
#   deep_reasoning_mode: true
#   deep_reasoning_model: qwen3:1.7b
```

#### Client Request Example (Deep-Reasoning Mode)
```bash
curl -X POST http://localhost:8000/api/v1/analyses/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "knowledge_base_id": "64ee39d09c6292376e191983",
    "query": "Perform complex numerical analysis of contract SLAs across Q1-Q4.",
    "llm_provider": "ollama",
    "llm_model": "qwen3:1.7b"
  }'
```

If `DEEP_REASONING_MODE` is **false**, this request will be immediately rejected with HTTP 422:
```json
{
  "detail": "Model 'qwen3:1.7b' requires deep-reasoning mode to be enabled (DEEP_REASONING_MODE=true). Deep-reasoning models are reserved for batch/analytical tasks and not permitted in interactive mode."
}
```

### 3.3 Enabling the ONNX Cross-Encoder Reranker

When operating against large corpora where hybrid search precision drops:

```bash
# Option A: Enable via Environment Variable
export RERANKER_ENABLED=true
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Option B: Enable in config/models.yaml:
# reranker:
#   enabled: true
```

---

## 4. Hardened Security & Stability Guardrails

### 4.1 Adversarial Recovery & Loop Prevention
- **Meta-Prefix Stripping:** Strips query generator artifacts like `"Expand:"`, `"Rewrite:"`, `"Query:"`, `"Search:"` prior to similarity scoring.
- **Token-Equivalent Detection:** Uses `_is_effectively_identical_query` to identify when a rewritten query adds no new informational search terms.
- **Refusal Preservation:** When a recovery downgrade occurs (`re_retrieve` -> `regenerate`), `state["answer"]` is restored to `prior_answer` so `is_refusal_answer()` triggers immediate abstention on futile regeneration.
- **Diagnosis State Persistence:** `state["diagnosis_type"]` is preserved as `prior_diagnosis` before recovery clearing, preventing fallback to blind round-robin priority.

### 4.2 Stable NLI JSON Extraction
Thinking models (e.g., Qwen) emit `<think>...</think>` scratchpad blocks. The utility `extract_json_substring` in `app/llm/llm_utils.py` automatically strips `<think>` tags before brace matching, ensuring structured Pydantic extraction never parses scratchpad tokens.

### 4.3 Pinned Supply-Chain Dependencies (Bandit B615)
Hugging Face tokenizers are strictly pinned to commit hashes:
- BGE Small Embeddings Tokenizer: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
- MiniLM Reranker Tokenizer: `233902d25c440f23af6f7d6e94d2946bac0bee0a`

---

## 5. Verification & Regression Tests

Run the dedicated test suite validating both production modes, gating, query rewrite hardening, and parsing:

```bash
pytest tests/test_production_modes.py -v --no-cov
```
Expected output: `11 passed`.
