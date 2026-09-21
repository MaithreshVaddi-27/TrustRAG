# TRUSTRAG — Free Performance & Efficiency Guide

How to make TrustRAG faster and leaner **without spending anything**: no paid APIs, no bigger machines — only configuration, local-model choice, and caches that already exist in the codebase. Includes **MLX on Apple Silicon** as the fastest free inference path on Mac.

> Rule: measure before and after. Every change below is verifiable with
> `GET /api/v1/metrics`, `k6 run load-test/smoke.js`, and
> `python scripts/run_baseline_eval.py` (see [Measure first](#1-measure-first-free)).

---

## Table of Contents

1. [Measure first (free)](#1-measure-first-free)
2. [Biggest free wins (do these first)](#2-biggest-free-wins-do-these-first)
3. [LLM serving: pick the fastest free server per OS](#3-llm-serving-pick-the-fastest-free-server-per-os)
4. [MLX on Mac (Apple Silicon, free, fastest tok/s per watt)](#4-mlx-on-mac-apple-silicon-free-fastest-toks-per-watt)
5. [Retrieval & verification knobs (free trade-offs)](#5-retrieval--verification-knobs-free-trade-offs)
6. [Ingestion efficiency (pay once, never per query)](#6-ingestion-efficiency-pay-once-never-per-query)
7. [RAM diet for 8 GB machines (free)](#7-ram-diet-for-8-gb-machines-free)
8. [Concurrency & timeouts (free correctness + speed)](#8-concurrency--timeouts-free-correctness--speed)
9. [Storage & infra (free)](#9-storage--infra-free)
10. [What NOT to do (costs money or hurts)](#10-what-not-to-do-costs-money-or-hurts)
11. [Change checklist (copy/paste runbook)](#11-change-checklist-copypaste-runbook)

---

## 1. Measure first (free)

Never tune blind. All three instruments are already in the repo:

```bash
# A. Live counters (no auth): requests, latency, analyses by status,
#    recovery by strategy, claim verdicts, token estimates, budget rejections
curl -s http://localhost:8000/api/v1/metrics | grep trustrag_

# B. Load gate (~3k requests): 0% failed, p95 < 300ms is the bar
API_BASE_URL=http://localhost:8000 k6 run load-test/smoke.js

# C. Quality gate (proves speed didn't break answers): frozen 25-query set
python scripts/run_baseline_eval.py --email ... --password ... \
  --kb-id <KB_ID> --post-experiment
```

Record the snapshot-table row in `docs/evaluation/methodology.md` after each change. If a "speedup" moves coverage/support/abstention the wrong way, revert it — speed without trust is the thing TrustRAG exists to prevent.

---

## 2. Biggest free wins (do these first)

Ordered by impact per minute of effort. All are config-only.

### 2.1 Switch embeddings to ONNX (saves ~500–1000 MB RAM, faster cold start)

The torch process RSS floor dominates small hosts. The ONNX path is numerically identical (parity verified, max diff 0.000000).

```bash
# One-time export (needs torch locally, once)
python scripts/export_bge_onnx.py
cp apps/api/data/models/bge-small-en-v1.5.onnx apps/api/.model_cache/
```

```bash
# .env
EMBEDDING_PROVIDER=onnx
```

Files: `scripts/export_bge_onnx.py`, `apps/api/app/core/onnx_embeddings.py`, `apps/api/app/core/model_registry.py` (`onnx` branch). In Docker this is mandatory anyway (the image ships `onnxruntime` but no torch).

### 2.2 Keep both caches ON (they already are — don't turn them off)

| Cache | Where | Effect |
|---|---|---|
| SQLite embedding disk cache | `apps/api/app/core/disk_cache.py` (`CACHE_DIR`, default `apps/api/data/cache`) | Repeat/revision embeddings cost zero compute across restarts |
| Semantic answer cache | `apps/api/app/core/semantic_cache.py`, threshold `0.94`, flag `enable_response_caching` | Repeat questions skip the LLM **100%** and still re-verify |

Warm them once by ingesting your docs and asking your top questions — every repeat after that is nearly free.

### 2.3 Keep fused decompose+verify ON (halves NLI calls)

One structured call instead of decompose → batch. Default on; falls back to two-step automatically.

```bash
# .env — only touch to debug
FUSED_DECOMPOSE_VERIFY=1
```

File: `apps/api/app/verification/verifier.py`, kill-switch in `apps/api/config/models.yaml` (`verification.fused_decompose_verify`).

### 2.4 Use the smallest model that still verifies (free tok/s)

Per-call latency is dominated by the local LLM, and one analysis makes ~9 sequential calls. The default (`LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M`) is already the lean choice — don't "upgrade" to 7B+ on the same machine and expect it to go faster. Smaller + quantized + Metal/CUDA offload beats bigger every time for this pipeline. (On Mac, see [MLX](#4-mlx-on-mac-apple-silicon-free-fastest-toks-per-watt) — same logic, even faster.)

### 2.5 Set log level to WARNING outside debugging (free I/O)

```bash
# .env
LOG_LEVEL=WARNING
```

`structlog` JSON per request is not free on slow disks — `INFO`/`DEBUG` stays in dev.

---

## 3. LLM serving: pick the fastest free server per OS

| Host | Fastest free option | Why |
|---|---|---|
| Mac (Apple Silicon) | **MLX** (`mlx_lm.server`) | Native Metal, 4-bit weights, best tok/s per watt — see §4 |
| Mac (Intel) / fallback | llama.cpp (`./scripts/start_local_llm.sh`) or Ollama | llama-server vendors Metal/CUDA, no torch needed |
| Linux + NVIDIA | llama.cpp with CUDA offload, or Ollama | Same; CUDA auto-detected by `app/core/hardware.py` |
| Linux CPU-only | Ollama with a ≤3B Q4 model | Simplest ops; keep expectations modest |
| Windows + NVIDIA | Ollama app, or llama.cpp | CUDA auto-detected |

Rules that apply to **every** server:

- **Separate ports for local servers:** `llama-server` on **:8080**, `mlx_lm.server` on **:8090** — they can run simultaneously. Ollama on :11434 coexists with both.
- **Keep `LOCAL_LLM_MAX_CONCURRENCY=1`.** Local servers are serial (llama-server `-np 2`, Ollama queue, MLX single model). The backend serializes generations with a semaphore (`app/core/local_llm.py`); raising this without a parallel-capable server buys timeout cascades, not throughput.
- **Ollama on ≤8 GB** (shell env, before `ollama serve`):
  ```bash
  export OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_FLASH_ATTENTION=1
  export OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE=5m
  ```
- **llama-server flags are auto-tuned** by `app/core/hardware.py` (full GPU offload, q8_0 KV cache, context/concurrency by RAM tier) via `./scripts/start_local_llm.sh` — prefer the script over hand-rolled flags.

---

## 4. MLX on Mac (Apple Silicon, free, fastest tok/s per watt)

[MLX](https://github.com/ml-explore/mlx) is Apple's array framework for Apple Silicon; `mlx-lm` runs LLMs directly on the Metal GPU with 4-bit quantized weights — no CUDA, no torch, no API key, no cost. Its server speaks the **OpenAI chat protocol**, which is exactly what TrustRAG's `ChatLlamaCppClient` already speaks (`{base_url}/chat/completions` with `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stop`).

### 4.1 Requirements (free, but strict)

- Apple Silicon Mac (M1+). **Intel Macs cannot run MLX** — use llama.cpp/Ollama instead.
- macOS 14+, Python 3.10–3.12, ~2–5 GB free disk per model.

### 4.2 Install (one line, isolated so it can't touch your venvs)

```bash
# Option A: plain pip (Apple Silicon only)
pip install mlx-lm

# Option B: fully isolated via uv (no env to manage)
brew install uv
uvx --python 3.12 --isolated --from mlx-lm mlx_lm.server --help
```

### 4.3 Pick a model (free, `mlx-community` 4-bit instruct builds)

| Your Mac | Pick | Why |
|---|---|---|
| 8 GB RAM | `mlx-community/Llama-3.2-1B-Instruct-4bit` | Smallest; leaves room for embeddings + Qdrant + MongoDB |
| 16 GB+ RAM | `mlx-community/Llama-3.2-3B-Instruct-4bit` | Best quality/speed balance for the ~9-calls-per-analysis pipeline |
| 24 GB+ / Max | `mlx-community/Qwen3-4B-Instruct-4bit` class | Larger reasoning headroom; verify first |

Any `mlx-community/*-Instruct-4bit` model works — instruct-tuned and 4-bit are the two properties that matter for this pipeline (verification needs instruction-following; 4-bit keeps it resident).

### 4.4 Serve it (on :8090, alongside llama-server on :8080)

```bash
# Terminal 1 — start the OpenAI-compatible server (model downloads once, then cached)
mlx_lm.server \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --host 127.0.0.1 --port 8090 \
  --max-tokens 1024

# Verify (any non-empty model routing key works; the name must match --model)
curl http://127.0.0.1:8090/health
curl http://127.0.0.1:8090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mlx-community/Llama-3.2-3B-Instruct-4bit","max_tokens":50,
       "messages":[{"role":"user","content":"Say: MLX online."}]}'
```

> Server default `--max-tokens` is 512 — the backend always sends its own `max_tokens` (up to 1024), but set the flag anyway so ad-hoc clients get sane lengths.

### 4.5 Wire TrustRAG to it — Option A: zero code (recommended)

Because the MLX server is protocol-compatible, reuse the `llama_cpp` provider slot on its dedicated port. Task-sized output caps, the serial semaphore, and all budgets then apply automatically (`LOCAL_LLM_PROVIDERS` in `app/core/local_llm.py`).

```bash
# .env — MLX runs on :8090, llama-server on :8080; both can run simultaneously
LLM_PROVIDER=llama_cpp
LLAMACPP_BASE_URL=http://127.0.0.1:8090/v1
LLAMACPP_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit   # EXACT id from --model
```

```bash
# Terminal 2 — backend (unchanged)
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Smoke test end-to-end (register → KB → upload → analysis), then compare
# /metrics latencies against your llama-server baseline from §1.
```

> ✅ **Verified 2026-09-20** on an 8 GB Apple Silicon Mac (mlx-lm 0.31.3,
> `mlx-community/LFM2.5-1.2B-Instruct-4bit`): plain chat and
> `response_format: json_object` calls both OK; full pipeline (register → KB →
> upload → analysis) completed in ~15 s with verdict TRUSTED and 2/2 claims
> SUPPORTED. No code changes — `.env` only.

### 4.6 Wire TrustRAG to it — Option B: first-class `mlx` provider (change spec)

Do this if you want MLX and llama-server side by side (e.g. MLX for generation, llama-server for verification), or MLX-specific defaults. Files to touch — nothing else:

| # | File | Change |
|---|---|---|
| 1 | `apps/api/app/core/model_registry.py` | Add `"mlx"` to `LOCAL_LLM_PROVIDERS`; add `mlx` branches in `get_llm()` / `get_verification_model()` constructing the existing `ChatLlamaCppClient` with `base_url=settings.mlx_base_url` (protocol-compatible — no new client class) |
| 2 | `apps/api/app/core/config.py` | Add `MLX_BASE_URL` (default `http://127.0.0.1:8080/v1`), `MLX_MODEL` settings + `llm_model_for("mlx")` / `verification_model_for("mlx")` wiring |
| 3 | `apps/api/config/models.yaml` | Add `model_mlx` defaults under `llm:` and `verification:` (mirroring `model_llamacpp`) |
| 4 | `.env.example` | Document `MLX_BASE_URL` / `MLX_MODEL` + the :8080 conflict note |
| 5 | `apps/api/tests/test_config.py`, `test_local_llm.py` | Cover the new provider key, URL default, and cap application |
| 6 | `scripts/setup.sh` | Probe `:8080/health` shape for MLX vs llama-server in the services check (optional nicety) |

Estimated: ~60 lines + tests. No new dependencies (`httpx` path is reused).

### 4.7 MLX caveats (read before reporting "it doesn't work")

- **Model string must match exactly** — the server 404s otherwise (`v1/models` lists what's loaded). This is the #1 MLX wiring failure; `LLAMACPP_MODEL` must equal `--model`.
- **`response_format: json_object`** is sent on structured paths (fused verify). If verification degrades under MLX while plain generation is fast, check API logs for 400s and set `FUSED_DECOMPOSE_VERIFY=0` as the diagnostic split — then file the finding; per-request provider split (Option B) is the durable fix.
- **`cache_prompt` / `repeat_penalty`** are llama-server extensions — harmless elsewhere (ignored fields), and MLX has its own prompt cache (`--prompt-cache-size`, on by default).
- **Serial server** — keep `LOCAL_LLM_MAX_CONCURRENCY=1` (§3). MLX batch flags (`--decode-concurrency`, `--prompt-concurrency`) tune server-side batching, not client parallelism.
- **Never in Docker** — MLX is macOS/arm64-only; containers stay on the ONNX + llama-server/Ollama path.

---

## 5. Retrieval & verification knobs (free trade-offs)

All live in `apps/api/config/models.yaml` (`retrieval:`, `verification:`, `reliability:`). No code, no cost — but each trades speed for quality, so re-run §1C after touching them.

| Knob | Current | Faster direction | Cost of going faster |
|---|---|---|---|
| `sparse_top_k` | `0` (dense-only) | keep `0` | Lower recall on keyword/rare-term queries; set `20` for full hybrid (+~1–5 ms/query, needs re-index expectations) |
| `dense_top_k` / `fusion_top_k` | `20` / `20` | lower (e.g. 10) | Fewer candidates → faster rerank/context, but recall drops |
| `max_context_chunks` | `8` | lower (e.g. 5) | Shorter prompts → faster + cheaper generation, thinner evidence |
| `reranker.enabled` | `false` | keep `false` until calibrated | Enabling costs +40–400 ms/query AND needs torch (`local-models` extra); calibrate thresholds from the Hybrid-vs-Hybrid+Rerank ablation first |
| `query_router.enabled` | `true` | keep `true` | The router is regex (zero LLM cost) and *saves* calls on simple queries |
| `max_sub_queries` | `3` | lower (e.g. 2) | Cheaper fan-out, weaker comparison/complex coverage |
| `max_recovery_attempts` | `2` | `1` | Bounded worst-case latency; more abstentions on hard queries |
| `claim_retrieval` budget | `≤3` | lower | Fewer NEUTRAL→SUPPORTED flips |
| `chunk_size` / `chunk_overlap` | `512` / `64` | larger chunks, smaller overlap | Fewer vectors to search, coarser evidence spans |

---

## 6. Ingestion efficiency (pay once, never per query)

Ingest cost is offline — spend it wisely once instead of per query forever:

- **Chunking strategy matters once:** `sliding_window` (default) is cheapest and byte-stable. `semantic`/`layout_aware` cost more at ingest for better spans — pick per corpus, then **re-index once** and stop switching (every switch = full re-upload).
- **OCR:** RapidOCR fires only on pages with <50 native chars and fails open. If your corpus has no scans, disable it (`ingestion.ocr.enabled: false` in `models.yaml`) to skip the `~/.onnx` first-use download stall. If it has scans, **pre-warm**: ingest one scanned PDF right after deploy.
- **Upload size cap** (`max_file_size_mb: 20`, `max_total_tokens_per_doc: 200000`) is a free DoS guard — leave it.
- **Embedding cache warming:** the first ingest embeds everything; every later ingest of the same bytes hits `disk_cache` and costs ~zero. Don't wipe `apps/api/data/cache` between runs.

---

## 7. RAM diet for 8 GB machines (free)

In order of MB saved:

1. `EMBEDDING_PROVIDER=onnx` — removes torch entirely (~500–1000 MB). Biggest single item.
2. 1–3B Q4 local model (default 1.2B is already right-sized) + q8_0 KV cache (Ollama env or llama-server flags — both scripted; see §3).
3. `TOKENIZERS_PARALLELISM=false` + `MALLOC_ARENA_MAX=1` in `.env` — kills thread-pool/allocator bloat next to torch.
4. Qdrant embedded (`QDRANT_URL=local`) with INT8 on-disk vectors (already default per D-13) — 75% vector RAM saving, no server process.
5. Local MongoDB instead of Atlas M0 (no network, no sleep/wake stalls) for dev.
6. One resident model only (`OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_KEEP_ALIVE=5m`).

---

## 8. Concurrency & timeouts (free correctness + speed)

Already correct in code — these are "verify, don't change" items:

- `LOCAL_LLM_MAX_CONCURRENCY=1` serializes the ~9-calls-per-analysis pipeline against serial servers (Ollama queue, llama-server `-np 2`, MLX). Raise **only** with a parallel-capable server.
- Per-branch retrieval timeouts (45 s each, 60 s total in `app/retrieval/retriever.py`) degrade one hung branch to the other instead of failing the query.
- Pooled `httpx.AsyncClient` per endpoint (`app/core/local_llm.py`) reuses keep-alive across the call fan-out — already done, don't regress to per-call clients.
- Rate limits (`RATE_LIMIT_*_PER_MINUTE`) are local-friendly; raise them only behind single-NAT production proxies, never to "go faster" locally.

---

## 9. Storage & infra (free)

- **Qdrant:** `local` (embedded, in-process) for dev = zero ops, zero latency hop. Docker Compose server + volume for team demos. Cloud only when you need off-host persistence.
- **MongoDB indexes** are created idempotently on startup (`ensure_indexes` in `app/db/mongodb.py`) — nothing to do, don't hand-create.
- **Frontend:** `npm run build` + static CDN (Cloudflare Pages free tier) instead of running Vite dev in production.
- **Docker image** is torch-free by design — keep it that way (don't `pip install sentence-transformers` into the image; use the ONNX path).

---

## 10. What NOT to do (costs money or hurts)

- ❌ Bigger cloud LLM for "speed" — per-token cost on a ~9-call pipeline, and Gemini/NVIDIA add network latency per call. Local small models win on both.
- ❌ Enabling the reranker without the `local-models` extra — silent no-op in Docker that still costs code-path complexity; calibrate first.
- ❌ Raising `LOCAL_LLM_MAX_CONCURRENCY` on Ollama/llama-server/MLX — serial servers + parallel clients = timeout cascades.
- ❌ Cloud embeddings — removed for a reason (D-19): per-token cost inside the hot path plus cross-space contamination risk.
- ❌ Redis/Celery/K8s "for performance" — explicitly deferred (D-08) until *measured* queue/SSE pain. The in-process path is faster at this scale.
- ❌ Blanket OCR or larger chunks "for recall" without running the ablation — measure via §1C.

---

## 11. Change checklist (copy/paste runbook)

```bash
# 0. Baseline (write down metrics + methodology snapshot row)
curl -s http://localhost:8000/api/v1/metrics | grep trustrag_
API_BASE_URL=http://localhost:8000 k6 run load-test/smoke.js

# 1. .env free wins
EMBEDDING_PROVIDER=onnx
LOG_LEVEL=WARNING
TOKENIZERS_PARALLELISM=false
LOCAL_LLM_MAX_CONCURRENCY=1

# 2. Mac only: MLX instead of llama-server (see §4)
mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --host 127.0.0.1 --port 8080 --max-tokens 1024
# .env: LLM_PROVIDER=llama_cpp, LLAMACPP_BASE_URL=http://127.0.0.1:8080/v1,
#       LLAMACPP_MODEL=<exact --model id>

# 3. models.yaml: touch ONE knob at a time (§5 table), then:
python scripts/run_baseline_eval.py --email ... --password ... \
  --kb-id <KB_ID> --post-experiment
# 4. Copy the aggregate row into docs/evaluation/methodology.md. Never hand-edit JSON.
```

> History note: superseded tuning advice lives in git (`git log -- docs/`). This guide reflects `models.yaml` v1.15 and the code at HEAD.
