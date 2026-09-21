# TrustRAG Ultra-Low RAM & High-Speed Inference Optimization Plan

## Context
The TrustRAG project uses local LLMs (Ollama, llama.cpp, MLX) for inference. Currently, several optimization flags exist in `models.yaml` (kv_cache_quantization, flash_attention, prompt_caching, adaptive_top_k) but they are **not wired into the actual client code**. The user wants ultra-low RAM usage and maximum inference speed.

## Current State Analysis

### What's Already Done
- ✅ Hardware-aware concurrency semaphore (2/4/8 based on RAM)
- ✅ Connection pooling with keep-alive (30s)
- ✅ Configurable num_ctx, num_batch, keep_alive via models.yaml
- ✅ Semantic cache (500 entries, 5min TTL)
- ✅ Context pruning (20-35% reduction via `prune_context_tokens`)
- ✅ Reranker early termination & adaptive top-k
- ✅ Bounded LLM registry (max 4 instances, LRU eviction)

### What's Missing (Optimization flags in models.yaml NOT used)
- `optimization.kv_cache_quantization: "q4_0"` - Not passed to llama.cpp/Ollama
- `optimization.flash_attention: true` - Not passed to llama.cpp
- `optimization.prompt_caching: true` - Only for llama.cpp, not Ollama
- `optimization.adaptive_top_k: true` - Not implemented in retriever/generator

## Recommended Optimization Plan

### Phase 1: Wire Existing Optimization Flags (Immediate - Low Risk) ✅ COMPLETED

#### 1.1 Pass KV Cache Quantization to llama.cpp ✅ DONE
**File:** `apps/api/app/core/local_llm.py` - `ChatLlamaCppClient._agenerate()`
**Action:** Add `kv_cache_quantization` from config to llama.cpp payload
```python
# llama.cpp supports: "cache_type_k": "q4_0", "cache_type_v": "q4_0"
payload["cache_type_k"] = cfg.kv_cache_quantization
payload["cache_type_v"] = cfg.kv_cache_quantization
```

#### 1.2 Pass Flash Attention Flag to llama.cpp ✅ DONE
**File:** `apps/api/app/core/local_llm.py` - `ChatLlamaCppClient._agenerate()`
**Action:** Add `flash_attention` from config
```python
payload["flash_attention"] = cfg.flash_attention
```

#### 1.3 Enable Prompt Caching for llama.cpp ✅ DONE
**File:** `apps/api/app/core/local_llm.py` - `ChatLlamaCppClient._agenerate()`
**Action:** Made `cache_prompt` configurable via `cfg.prompt_caching`

#### 1.4 Add Optimization Config Properties to ModelConfig ✅ DONE
**File:** `apps/api/app/core/config.py`
**Action:** Added properties to read optimization section with env overrides
```python
@property
def kv_cache_quantization(self) -> str:
    value = self._get("optimization", "kv_cache_quantization", required=False)
    env_val = os.environ.get("KV_CACHE_QUANTIZATION")
    return env_val if env_val is not None else str(value or "q4_0")

@property
def flash_attention(self) -> bool:
    value = self._get("optimization", "flash_attention", required=False)
    env_val = os.environ.get("FLASH_ATTENTION")
    if env_val is not None:
        return env_val.strip().lower() in ("1", "true", "yes", "on")
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")

@property
def prompt_caching(self) -> bool:
    value = self._get("optimization", "prompt_caching", required=False)
    env_val = os.environ.get("PROMPT_CACHING")
    if env_val is not None:
        return env_val.strip().lower() in ("1", "true", "yes", "on")
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")

@property
def adaptive_top_k(self) -> bool:
    value = self._get("optimization", "adaptive_top_k", required=False)
    env_val = os.environ.get("ADAPTIVE_TOP_K")
    if env_val is not None:
        return env_val.strip().lower() in ("1", "true", "yes", "on")
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")
```

#### 1.5 Enable Prompt Caching for Ollama ✅ DONE
**File:** `apps/api/app/core/local_llm.py` - `ChatOllamaClient._agenerate()`
**Action:** Added `num_keep` for Ollama prefix caching (Ollama's equivalent of prompt caching)

### Phase 2: Ultra-Low RAM Optimizations (High Impact)

#### 2.1 Dynamic Context Sizing (Token-Aware) ✅ DONE
**Files:** 
- `apps/api/app/generation/generator.py` - Added `calculate_dynamic_num_ctx()` and `count_tokens()` using tiktoken
- `apps/api/app/core/config.py` - No additional config needed (uses existing `local_llm_num_ctx`)

**Action:** Replaced fixed 3000 char budget with token-aware budgeting using tiktoken:
- Calculate actual token count of context + system prompt + query
- Dynamically adjust `num_ctx` per request based on actual needs
- Reserve tokens for generation (max_tokens + safety margin)

#### 2.2 Aggressive Model Registry Eviction ✅ DONE
**File:** `apps/api/app/core/model_registry.py`
**Action:** 
- Reduced `_MAX_LLM_INSTANCES` from 4 to 2 for low-RAM systems
- Added `get_max_llm_instances()` that dynamically adjusts based on available RAM:
  - ≤8GB: 1 instance
  - ≤16GB: 2 instances  
  - 32GB+: 4 instances

#### 2.3 ONNX Quantization for Reranker ✅ DONE
**Files:**
- `apps/api/app/core/onnx_reranker.py` - NEW: ONNXCrossEncoder class with int8 quantization
- `apps/api/app/core/model_registry.py` - Updated `get_reranker()` to use ONNX when available
- `apps/api/app/core/config.py` - Added `reranker_use_onnx` and `reranker_onnx_model_path` properties
- `apps/api/config/models.yaml` - Added `use_onnx: true` and `onnx_model_path` config

**Action:** 
- Convert CrossEncoder to ONNX (int8) for 3-4x CPU speedup
- Auto-export from PyTorch if ONNX model doesn't exist
- Fallback to PyTorch if ONNX unavailable
- Configurable via `reranker_use_onnx` flag

#### 2.4 Context Compression Before LLM Call ✅ COMPLETED
**Files:**
- `apps/api/app/generation/generator.py` - Added `compress_context()` function with hierarchical summarization
- `apps/api/app/core/config.py` - Added `context_compression_enabled`, `context_compression_target_reduction`, `max_context_tokens` properties
- `apps/api/config/models.yaml` - Added context compression config section

**Action:**
- Implemented hierarchical summarization for long contexts
- Uses smaller/faster model to compress context before main generation
- Added `max_context_tokens` config (separate from `max_context_chunks`)
- Target reduction: 50% (configurable 40-60% range)
- Auto-skips for small contexts (< 1000 tokens)

#### 2.5 Speculative Decoding / Early Exit 🔄 PENDING
**File:** `apps/api/app/core/local_llm.py`
**Action:**
- For llama.cpp: enable `n_predict` streaming with early stop on EOS
- Add `min_p` / `top_k` sampling for faster generation
- Implement "draft model" pattern if multiple models available

### Phase 3: Inference Speed Optimizations

#### 3.1 Batch Prompt Processing ✅ DONE
**File:** `apps/api/app/core/local_llm.py`
**Action:**
- `n_batch` parameter already added and configurable via `local_llm_num_batch` (default 512)
- Passed to llama.cpp payload for prompt processing batch size

#### 3.2 Reduce Reranker Overhead ✅ PARTIAL
**File:** `apps/api/app/retrieval/reranker.py`
**Action:**
- Early termination already implemented with configurable thresholds
- ONNX quantization implemented (see 2.3)
- Reranker result caching per query 🔄 PENDING

#### 3.3 Parallel Retrieval with Adaptive Fan-out ✅ DONE
**File:** `apps/api/app/retrieval/retriever.py`
**Action:**
- Implemented `adaptive_top_k` from config to reduce `fusion_top_k` when confidence high (RRF score > 0.82)
- Already uses async gather for dense + sparse in parallel

#### 3.4 Connection Pool Optimization ✅ DONE
**File:** `apps/api/app/core/local_llm.py` - `_shared_http_client`
**Action:**
- Added `httpx.Limits(max_keepalive_connections=5, max_connections=10)` 
- Added `keepalive_expiry=30.0` for local servers

### Phase 4: Memory Pressure Mitigation

#### 4.1 Model Offloading for Inactive Models ✅ COMPLETED
**Files:**
- `apps/api/app/core/local_llm.py` - Added `unload_ollama_inactive_models()`, `unload_llamacpp_inactive_models()`, `unload_inactive_models_for_provider()`, `maybe_unload_inactive_models()`
- `apps/api/app/core/config.py` - Added `local_llm_model_unload_enabled`, `local_llm_model_unload_timeout`, `local_llm_max_loaded_models` properties
- `apps/api/config/models.yaml` - Added model offloading config section

**Action:**
- Call Ollama `/api/ps` to check loaded models, unload unused via `/api/delete`
- For llama.cpp: reports current model (restart needed to change)
- Added periodic check with configurable timeout (`model_unload_timeout`)
- Configurable max loaded models (default 1 for lowest RAM)

#### 4.2 Embedding Model Quantization ✅ COMPLETED
**Files:**
- `apps/api/app/core/model_registry.py` - Added int8 quantization support in `get_embedding_model()`
- `apps/api/app/core/config.py` - Added `embedding_quantization` and `embedding_quantized_model_path` properties
- `apps/api/config/models.yaml` - Added `quantization: false` and `quantized_model_path: ""` config

**Action:**
- Uses OpenVINO (optimum-intel) for int8 quantization when available
- Falls back to PyTorch dynamic int8 quantization on CPU
- Configurable via `embedding_quantization` flag (default: disabled/opt-in)
- Path to pre-quantized model via `embedding_quantized_model_path`

## Critical Files Modified

| Priority | File | Changes |
|----------|------|---------|
| 1 | `apps/api/app/core/config.py` | Added optimization config properties + context compression config |
| 1 | `apps/api/app/core/local_llm.py` | Wired kv_cache_quantization, flash_attention, prompt_caching, num_keep, n_batch |
| 2 | `apps/api/app/generation/generator.py` | Token-aware context budgeting + context compression |
| 2 | `apps/api/app/core/model_registry.py` | Aggressive eviction, ONNX support |
| 3 | `apps/api/app/core/onnx_reranker.py` | NEW: ONNXCrossEncoder with int8 quantization |
| 3 | `apps/api/app/retrieval/reranker.py` | ONNX integration |
| 3 | `apps/api/app/retrieval/retriever.py` | Adaptive top-k implementation |
| 4 | `apps/api/config/models.yaml` | Added all optimization config options |

## Verification Strategy

1. **Unit Tests:** Run full test suite (390 tests) - must pass ✅
2. **Memory Profiling:** 
   - `python -m pytest tests/test_local_llm.py -v` 
   - Monitor RSS with `psutil` during inference
3. **Latency Benchmarks:**
   - Time `generate_grounded_answer` with various context sizes
   - Compare before/after for each phase
4. **Integration Test:**
   - Run full analysis pipeline with local model
   - Verify answer quality unchanged (no regression)
5. **Config Validation:**
   - Test all env overrides work
   - Verify models.yaml changes picked up without restart (cache clear)

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| KV cache quantization | Medium - may affect quality | Test with q4_0, q8_0, fp16; default q4_0 |
| Flash attention | Low - llama.cpp handles gracefully | Only enable if supported by build |
| Dynamic context | Medium - token counting adds overhead | Cache tiktoken encoder; use fast path |
| ONNX reranker | Medium - model conversion needed | Keep fallback to PyTorch; feature flag |
| Aggressive eviction | Low - registry already handles | Configurable threshold |
| Context compression | Low - optional, falls back | Auto-skip for small contexts |

## Implementation Status Summary

| Phase | Task | Status |
|-------|------|--------|
| 1.1 | KV Cache Quantization → llama.cpp | ✅ DONE |
| 1.2 | Flash Attention → llama.cpp | ✅ DONE |
| 1.3 | Prompt Caching → llama.cpp | ✅ DONE |
| 1.4 | Optimization Config Properties | ✅ DONE |
| 1.5 | Prompt Caching → Ollama (num_keep) | ✅ DONE |
| 2.1 | Dynamic Context Sizing (tiktoken) | ✅ DONE |
| 2.2 | Aggressive Model Registry Eviction | ✅ DONE |
| 2.3 | ONNX Quantization for Reranker | ✅ DONE |
| 2.4 | Context Compression Before LLM | ✅ DONE |
| 2.5 | Speculative Decoding / Early Exit | 🔄 PENDING |
| 3.1 | Batch Prompt Processing (n_batch) | ✅ DONE |
| 3.2 | Reduce Reranker Overhead | ✅ PARTIAL |
| 3.3 | Parallel Retrieval + Adaptive Fan-out | ✅ DONE |
| 3.4 | Connection Pool Optimization | ✅ DONE |
| 4.1 | Model Offloading for Inactive Models | ✅ DONE |
| 4.2 | Embedding Model Quantization | ✅ DONE |

## Next Steps (Priority Order)

1. **Phase 2.5 - Speculative Decoding / Early Exit** - Add `min_p` sampling and early stop on EOS for llama.cpp (already wired in config, needs client implementation)
2. **Phase 3.2 - Reranker Result Caching** - Cache reranker results per query to avoid re-scoring (cache infrastructure exists, needs integration)

## Configuration Options (models.yaml v1.17)

```yaml
optimization:
  kv_cache_quantization: "q4_0"                 # q4_0, q8_0, fp16 (saves 50-75% context VRAM)
  flash_attention: true                         # Computes attention in SRAM tiles (O(N) memory)
  prompt_caching: true                          # Reuses KV cache for static prompt prefixes
  adaptive_top_k: true                          # Selects top 3-4 chunks if RRF > 0.82
  context_compression_enabled: true             # Enable hierarchical summarization
  context_compression_target_reduction: 0.5     # Target: 50% of original size
  max_context_tokens: 8000                      # Hard token budget before LLM call

local_llm:
  num_ctx: 4096                                 # Context window (tokens)
  num_batch: 512                                # Prompt processing batch size
  keep_alive: "5m"                              # Model keep-alive duration

reranker:
  use_onnx: true                                # Enable ONNX int8 acceleration
  onnx_model_path: ""                           # Auto-generated if empty
```

## Environment Variable Overrides

All config options support env overrides:
- `KV_CACHE_QUANTIZATION`
- `FLASH_ATTENTION`
- `PROMPT_CACHING`
- `ADAPTIVE_TOP_K`
- `CONTEXT_COMPRESSION_ENABLED`
- `CONTEXT_COMPRESSION_TARGET_REDUCTION`
- `MAX_CONTEXT_TOKENS`
- `LOCAL_LLM_NUM_CTX`
- `LOCAL_LLM_NUM_BATCH`
- `LOCAL_LLM_KEEP_ALIVE`
- `RERANKER_USE_ONNX`
- `RERANKER_ONNX_MODEL_PATH`

---

**Last Updated:** 2026-09-21  
**Config Version:** 1.17  
**Test Status:** 390 tests passing