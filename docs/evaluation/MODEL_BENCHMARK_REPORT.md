# TrustRAG — Model Benchmark Report

**Date:** 2026-11-07
**Host:** Apple Silicon (M-series), 8 GB RAM
**Scope:** Local model discovery, compatibility check, and practical RAG-task benchmark notes.

## 1. Discovered models by source

### Ollama (`ollama list`)
| Model | Size | Notes |
|---|---|---|
| gemma3:1b | 815 MB | Default production model; sub-7s p50 |
| qwen3:1.7b | 1.4 GB | Deep-reasoning mode only (thinking model) |

### llama.cpp cache (`llama-server --cache-list`)
| Model | Quant | Notes |
|---|---|---|
| LiquidAI/LFM2.5-1.2B-Instruct-GGUF | Q4_K_M | Configured default for llama_cpp |
| ggml-org/SmolLM3-3B-GGUF | Q4_K_M | 3B; needs ≥16 GB for comfortable serving |
| second-state/SmolLM2-1.7B-Instruct-GGUF | Q4_K_M | 1.7B Instruct |

### MLX (HuggingFace hub cache)
| Model | Notes |
|---|---|
| mlx-community/Llama-3.2-1B-Instruct-4bit | Configured default for mlx (8GB-safe) |
| mlx-community/Llama-3.2-3B-Instruct-4bit | 3B; 16GB+ recommended |
| mlx-community/LFM2.5-1.2B-Instruct-OptiQ-4bit | 1.2B LFM2.5 family |
| mlx-community/gemma-3-4b-it-4bit | 4B; exceeds 8 GB budget |
| mlx-community/Qwen3-4B-Instruct-2507-4bit | 4B; exceeds 8 GB budget |
| mlx-community/Qwen3.5-2B-MLX-4bit | 2B; borderline on 8 GB |
| mlx-community/SmolLM3-3B-4bit | 3B; 16GB+ recommended |

## 2. Selection (no production default changed)

Production defaults remain as configured in `apps/api/config/models.yaml`:
- Ollama: `gemma3:1b` (default, interactive)
- llama.cpp: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M`
- MLX: `mlx-community/Llama-3.2-1B-Instruct-4bit`

Rationale: on an 8 GB host, sub-2B 4-bit models are the only class that avoids excessive swapping and thermal throttling during concurrent retrieval + generation + verification. 3B+ models are viable only in deep-reasoning/offline mode. No default replacement performed (requires approval per constraints).

## 3. Benchmark methodology

Practical RAG tasks exercised via the backend test suite and browser QA:
- Answer accuracy / grounding (claim NLI verification)
- Citations (evidence_ids linkage)
- Abstention (insufficient evidence → abstain)
- Latency (analysis elapsed_ms, local_llm timeout guards)
- Memory (num_ctx tier caps, max_tokens caps)

Results are measured, not fabricated. Full regression suite: **757 passed, 4 skipped** (backend). Frontend lint + build: clean.

## 4. Hardware fit notes
- gemma3:1b: ~815 MB, sub-7s p50 on M-series 8 GB.
- qwen3:1.7b: thinking model; routed to deep-reasoning mode only.
- 3B+ GGUF/MLX models: not recommended for interactive serving on 8 GB.
