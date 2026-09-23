# TrustRAG — UPGRADE Plan: Accuracy + Speed + Ultra-Low RAM + Local (any-params) & Cloud

> Scope: senior backend / AI-ML / security / optimization / testing review, 2026-09-21.
> Goal: good accuracy with better speed, works efficiently with **local models of any parameter size** AND cloud models, ultra-low RAM.
> Do NOT trust existing test scripts as-is — they are stale (see §6). Fix code first, then rewrite tests.

## 0. Implementation status (updated as fixes land)

| # | Item | Status | Files |
|---|------|--------|-------|
| 1 | Embedding default → ONNX + validator allows `onnx` | ✅ DONE | `config/models.yaml:66`, `schemas/analysis.py:131-144` |
| 2 | Reranker no-pad-cache + ONNX batch loop/threads/offline | ✅ DONE | `retrieval/reranker.py:238-249`, `core/onnx_reranker.py` |
| 3 | Cloud model IDs read from yaml (not hardcoded) | ✅ DONE | `core/config.py:363-380,527-544` |
| 4 | Pin-before-upsert + Mongo dedup + sparse raw text | ✅ DONE | `ingestion/pipeline.py` |
| 5 | Qdrant auto-delete gated behind `ALLOW_QDRANT_RECREATE=1` | ✅ DONE | `db/qdrant.py:90-130` |
| 6 | Generator re-raise + `EXTERNAL_UNAUDITED` + tiktoken key norm | ✅ DONE | `generation/generator.py`, `verification/integrity.py`, `agent/graph.py` |
| 7 | Internal caps + MCP caps + service `jti` denylist + `nvidia-smi` returncode | ✅ DONE | `api/v1/internal.py`, `mcp/server.py`, `api/deps.py`, `core/hardware.py` |
| 8 | ONNX embed chunk ≤32 + OCR dpi 300→200 | ✅ DONE | `core/onnx_embeddings.py`, `config/models.yaml` |
| 9 | Verify: `ruff check app/ tests/` clean; backend 397 passed (incl. `test_indexing_pipeline_execution` — stale mock fixed with `delete_many` AsyncMock, see §6) | ✅ DONE | tests |
| 10 | `mlx_base_url` from `ports.yaml` (was hardcoded) | ✅ DONE 2026-09-23 | `core/config.py:180-184` |
| 11 | `internal_ingest_url` SSRF validation (parity with public from-url) | ✅ DONE 2026-09-23 | `api/v1/internal.py:151-180` |
| 12 | CORS credentialed-wildcard: enumerate methods/headers | ✅ DONE 2026-09-23 | `main.py:419-430` |
| 13 | Parser: chardet 100KB slice + PDF size/page caps + pixel-cap OCR + chunked AV scan | ✅ DONE 2026-09-23 | `ingestion/parser.py` |
| 14 | Upload filename `[:255]` cap + allowlist doc drift (`api.github.com`) | ✅ DONE 2026-09-23 | `api/v1/knowledge_bases.py` |
| 15 | Pipeline: pin-before-Mongo + remove duplicate pin blocks + effective-model dim stamp | ✅ DONE 2026-09-23 | `ingestion/pipeline.py` |
| 16 | Mongo `create_index` batched ×5 (M0 throttle guard) | ✅ DONE 2026-09-23 | `db/mongodb.py` |
| 17 | Verify: `ruff check apps/api/app/` clean; backend 397 passed | ✅ DONE 2026-09-23 | tests |
| 18 | NLI per-call timeout (90s) + skip individual fallback on recovery attempts | ✅ DONE 2026-09-23 | `verification/verifier.py` |
| 19 | Query-vector cache dim-mismatch invalidation (re-embed, never serve stale) | ✅ DONE 2026-09-23 | `retrieval/retriever.py:115-155` |
| 20 | Adaptive thresholds unified on RRF units (`_is_high_confidence`) | ✅ DONE 2026-09-23 | `retrieval/reranker.py` |
| 21 | Internal routes rate-limited (`60/minute`) | ✅ DONE 2026-09-23 | `api/v1/internal.py` |
| 22 | `sparse_top_k: 0` kept (conscious): early-return makes it zero-cost; flip to 20 for exact-match recall at ~2× Qdrant cost | ✅ DECIDED 2026-09-23 | `retrieval/retriever.py:200-204`, `models.yaml:148` |
| 23 | Cache TTLs/VACUUM already present (disk 30d + VACUUM≥100, semantic 24h/500/20k chars) — no change | ✅ VERIFIED 2026-09-23 | `core/disk_cache.py`, `core/semantic_cache.py` |
| 24 | conftest resets settings/model caches + query cache; 9 regression tests | ✅ DONE 2026-09-23 | `tests/conftest.py`, `tests/test_upgrade_phases.py` |
| 25 | Verify: `ruff` clean; backend 406 passed (397 + 9 new) | ✅ DONE 2026-09-23 | tests |

## 0.1 Manual testing status (2026-09-21)

| Provider | Model tested | Result | Notes |
|----------|--------------|--------|-------|
| ollama | gemma3:1b | ✅ TRUSTED (score 1.0) | Fast, accurate, ~20s total |
| ollama | qwen3:1.7b | ⚠️ FAILED (score 0.0) | Hallucinated Apple/NLI claims; recovery loop triggered |
| llama_cpp | LFM2.5-1.2B-Q4_K_M | ⚠️ UNCERTAIN (score 0.5) | SHA-256 focused, missed verification flow; ~180s |
| gemini | (not tested) | ⏳ PENDING | Config fix applied (model_gemini in yaml) |
| nvidia | (not tested) | ⏳ PENDING | Config fix applied (model_nvidia in yaml) |
| MLX | (not tested) | ⏳ PENDING | Requires `mlx_lm.server --port 8090` |

**Processes stopped for manual continuation:**
- Backend: `uvicorn app.main:app --port 8000` (was running, stopped)
- llama.cpp router: `scripts/start_local_llm.sh --max 1` on :8080 (was running, stopped)
- ollama: running on :11434 (keep running)

**Known issues to investigate:**
1. qwen3:1.7b hallucinates unrelated claims (Apple, NLI models) — may need temperature=0 or different prompt
2. LFM2.5-1.2B verification fixates on SHA-256, misses NLI verification context — may need max_tokens cap increase
3. Recovery loop slow on llama_cpp (~180s) — consider provider-specific caps (§1.2.5)
4. `test_ingestion` mock stale — needs rewrite with `delete_many` + pin-check expectation

Config version: `models.yaml` v1.19. Resolution: `models.yaml` → `ports.yaml` → `.env` (env wins).

---

## 1. Model strategy: local any-params + cloud (practical matrix)

The backend already abstracts providers in `app/core/local_llm.py` (ollama / llama_cpp / mlx HTTP) + cloud (`llm_utils.py`: gemini / nvidia). Keep that split, fix routing:

### 1.1 Recommended tiers (accuracy vs speed vs RAM)

| Tier | LLM | Embeddings | Reranker | When |
|------|-----|------------|----------|------|
| Lean 8GB | 1–1.5B Q4 (`LFM2.5-1.2B-Q4_K_M`, `gemma3:1b`, MLX 1B-4bit) | ONNX BGE-small (torch-free) | ONNX MiniLM int8, top_k 10–12 | Dev, laptop, CI |
| Balanced 16GB | 3B Q4 (`granite-4.2-3b-Q4_K_M`, `SmolLM3-3B-Q4_K_M`, MLX 3B-4bit) | ONNX BGE-small | ONNX MiniLM int8, top_k 15–20 | Best local quality/cost |
| Quality / prod | Cloud `openai/gpt-oss-20b` (NIM, ~3s) or `gemini-flash-lite` + local ONNX embeddings | ONNX BGE-small (keep local — zero API cost, no space-mix risk) | ONNX MiniLM int8 or cloud | Production reliability |

Why: local 1.2B is 20–60 s/call and abstains/NEUTRALs often on multi-hop; 3B is ~1.5–2× slower but much better JSON discipline; cloud is 10–30× faster and handles full 8-chunk context + structured output natively. Embeddings stay local in all tiers (identical recall if ONNX export keeps L2-norm — verify `scripts/export_bge_onnx.py:163-166`).

### 1.2 Concrete changes (what → where)

1. **Default to ONNX embeddings** — `apps/api/config/models.yaml:66` `provider: huggingface` → `onnx`.
   Saves ~500–1000 MB RSS (torch + sentence-transformers never load). Keep `local-models` extra out of Docker (`apps/api/pyproject.toml:71-75`; runtime image is already torch-free by design — see `docker-compose.yml:65-66`). Pre-export at build: `python3 scripts/export_bge_onnx.py` → bake `apps/api/.model_cache/bge-small-en-v1.5.onnx` into image (today `onnx_model_path: ""` re-exports on every cold start; same for reranker `models.yaml:120-121`).
2. **Fix cloud model IDs ignored** — `app/core/config.py:363-367,527-531` hardcode `openai/gpt-oss-20b` / `gemini-3.5-flash-lite`, ignoring `llm.model_nvidia`, `llm.model`, `verification.model`. Editing yaml does nothing for cloud today.
   Fix: `return str(self._get("llm","model_nvidia",required=False) or "openai/gpt-oss-20b")` (same for gemini + verification twins).
3. **Compression only for cloud** — `models.yaml:224` `context_compression_enabled: true` doubles local cost (compression call ≈ generation call on the same 1.2B). Gate: enable when provider in (nvidia, gemini), disable for ollama/llama_cpp/mlx, or add `compression_provider: cloud` fallback.
4. **Turn sparse leg on or delete it** — `models.yaml:127` `sparse_top_k: 0` means dense-only: you lose exact acronym/number match but still pay for the sparse code path. Set `sparse_top_k: 20` (needs Qdrant sparse IDF config in `app/db/qdrant.py`) or remove dead code in `app/retrieval/retriever.py` + `app/ingestion/sparse_vector.py`.
5. **Per-tier caps** — small locals choke on 8 claims × 8 chunks. Add in `models.yaml`:
   ```yaml
   local_llm:
     num_ctx: 4096        # 8GB; 8192 on 16GB (see hardware.py:79-80); 16384 only 32GB+
   cost_controls:
     max_verification_claims: 5   # local; 8 for cloud
     max_context_chunks: 5        # local; 8 for cloud
   ```
   Wire provider-aware override in `app/agent/graph.py` + `app/verification/verifier.py` (skip individual-NLI fallback when `attempt>0` or local provider).
6. **Any-params support** — `app/core/hardware.py:77-82` already scales `-c/-np` by RAM; align `scripts/start_local_llm.sh:29 --max 4` with `models.yaml:250 max_loaded_models: 1` (4×3B-Q4 = OOM on 8GB → `--max 1` on lean). ✅ DONE 2026-09-22: launcher now derives `--max` from RAM (1/2/4) unless explicitly passed; 8 GB tier also dropped to `-np 1` (measured: `-np 2` halves each slot to 2048 ctx while the backend sends 4096 through one serial consumer). ✅ DONE 2026-09-22: Normalize tiktoken cache key (`app/generation/generator.py:63-83` keys raw GGUF id → unbounded dup `cl100k_base`; normalize to registry name else single key).
7. **Keep proven speed wins**: two-tier embed cache (mem LRU + SQLite batch, `model_registry.py:554-636`, `disk_cache.py:96-137`), semantic short-circuit (`semantic_cache.py:197-295`), `prune_context_tokens` (`semantic_cache.py:369-412`, 20–35% KV saving), fused decompose+verify (`models.yaml:99`), task-sized `max_tokens` (`local_llm.py:299-359`), `prompt_caching`/`num_keep=-1` (`local_llm.py:485-486,665`), deterministic query router (`models.yaml:134-136`), hardware profile TTL (`hardware.py:189-207`), `keep_alive=0` unload — never `/api/delete` (erases blob; `local_llm.py:137-147`).

---

## 2. Existing bugs & errors (fix before tuning)

### P0 — data corruption / silent wrong answers
- [ ] **Reranker early-exit poisons cache with fake 0.0** — `app/retrieval/reranker.py:233-243`: unscored tail padded `0.0` then ALL written to `_RerankerCache`. Future identical query-doc pairs return 0.0 unscored. Fix: only cache `uncached_indices[:processed]`.
- [✅ DONE] **Cloud yaml dead** — `app/core/config.py:363-367,527-531` was fixed; cloud model IDs now correctly read from `models.yaml` (verified: `llm_model_for('nvidia')` returns `openai/gpt-oss-20b` from yaml).
- [✅ DONE] **Qdrant fail-open on unreadable config** — `app/db/qdrant.py:80-130` now raises `VectorStoreError` with actionable message; test updated to expect fail-closed.
- [✅ DONE] **`init_kb_collection` deletes all vectors on upgrade** — `app/db/qdrant.py:110-118` auto `delete_collection` + recreate empty. Fix: raise `VectorStoreError("requires re-index")` behind `ALLOW_QDRANT_RECREATE=1`, never in request path.
- [✅ DONE] **Ingest mixes embedding spaces** — `app/ingestion/pipeline.py:142-275` embeds+upserts THEN checks KB pin. Fix: move pin check before `aembed_documents`; reject 422 on mismatch. In `app/retrieval/retriever.py:145-167` replace truncate/pad with `raise RetrievalOutageError("embedding space mismatch")`.
- [✅ DONE] **Mongo chunk duplicates on retry** — `app/ingestion/pipeline.py:118-139` `insert_many` with no unique guard (Qdrant upsert is idempotent, Mongo isn't). Fix: unique index `(document_id,chunk_index)` in `app/db/mongodb.py:245-250` + `delete_many({document_id})` before insert.
- [✅ DONE] **Async singletons leak / break on reload** — LLM clients now implement `aclose()` and are awaited on eviction/shutdown via async `close_all_llm_instances(seal=True)`. ✅ DONE 2026-09-22: LLM registry now properly awaits `aclose()` on eviction/shutdown.
- [✅ DONE] **Generation masks outages as ABSTAIN** — `app/generation/generator.py:765-768` blanket `except → "ABSTAIN"`. Fix: re-raise `ConfigurationError`/`LLMUnavailableError`; ABSTAIN only on empty content.
- [✅ DONE] **Web chunks bypass integrity audit + marked VERIFIED** — `app/agent/graph.py:467-492` appends after `audit_evidence_integrity`; `app/verification/integrity.py:40-42` marks no-`document_id` chunks `VERIFIED`. Fix: run web chunks through audit or tag `EXTERNAL_UNAUDITED`; never `VERIFIED` (UI presents it as cryptographically verified). Also cap audit input (~100) — `$or` query at `integrity.py:59` is unbounded.

### P1 — performance / correctness
- [✅ DONE] **Async singletons leak / break on reload** — LLM clients now implement `aclose()` and are awaited on eviction/shutdown via async `close_all_llm_instances(seal=True)`. ✅ DONE 2026-09-22: LLM registry now properly awaits `aclose()` on eviction/shutdown.

- [ ] **ONNX reranker ignores `batch_size`, single-threaded** — `app/core/onnx_reranker.py:59,88-116` tokenizes+infers all pairs at once; 20 candidates × fan-out 3 = seconds on CPU. Fix: loop `range(0,len(pairs),batch_size or 16)`; threads `os.cpu_count()` instead of default 1.
- [ ] **Sparse leg embeds filename/zone prefix** — `app/ingestion/pipeline.py:150-152,197`: `[file | ZONE]` prefix is right for dense, wrong for BM25 (filename dominates). Fix: `generate_sparse_vector(chunk["text"])`.
- [ ] **Verifier worst-case ~20 serial local calls vs 180 s node timeout** — `app/verification/verifier.py:1062-1174`, `app/agent/graph.py:767-782`: fused+decompose+batch×2+8 individual+3×(retrieval+NLI) on 1.2B exceeds `max_verification_time_seconds`. `wait_for` cancels mid-persist → recovery repeats. Fix: per-call (not whole-node) timeouts; §1.2.5 caps.
- [ ] **Adaptive thresholds in wrong units, never fire** — `app/retrieval/reranker.py:130,255` `dense>=0.78` (BGE cosine rarely that high), `rerank>=0.80` (cross-encoder logits unbounded, not 0-1); only RRF `>=0.02` (`retriever.py:490`) is live. Fix: unify on RRF units or `sigmoid()>=0.8`.
- [ ] **`torch.set_num_threads(1)` is process-global** — `app/core/model_registry.py:757-760` throttles every torch consumer. Fix: delete; use `OMP_NUM_THREADS` env before import (ONNX path needs no torch).
- [ ] **Query-vector cache no invalidation** — `app/retrieval/retriever.py:118-130` + `graph.py:1361-1369`: 1024-LRU no TTL, un-normalized key duplicates work, no dim check on hit. Fix: one normalized key fn; store `(dim,vec)`, invalidate on mismatch.
- [ ] **ONNX embeddings no internal batching** — `app/core/onnx_embeddings.py:83-108`: 128-vector self-heal batch tokenized at once → RAM spike. Fix: chunk ≤32.
- [ ] Minor: `hardware.py:55-70` ignores `nvidia-smi` returncode (adds `-ngl` on broken drivers — check `returncode==0`); `config.py:156` `mlx_base_url` hardcoded, ignores `ports.yaml`; `onnx_reranker.py:78-82` `local_files_only=False` breaks `HF_HUB_OFFLINE=1` (`main.py:113-115`); `mongodb.py:407` 30 parallel `create_index` can throttle M0 free tier (unique hash index may be missing → dup docs).

---

## 3. Security fixes (senior security engineer)

- [ ] **MCP server: zero auth** — `app/mcp/server.py:172-284,287-325`: any local process reads any KB, drives LLM with arbitrary `model`+`prompt` (SSRF/cost), enumerates KBs. Fix: service-token/socket-peer gate on `run_stdio_mcp_server`; require `user_id` + `get_kb(kb_id,user_id)` ownership check; allowlist model IDs; cap prompt length; rate-limit web tools. Clamp already at `:203` — extend to web tools `:182,187`.
- [ ] **Internal routes lack public-route guards** — `app/api/v1/internal.py:151-238`: `internal_ingest_url` has NO `validate_ingestion_url`/DNS/IP-pinning (public `from-url` in `knowledge_bases.py:265,273` does); `internal_search` `top_k` unbounded; `internal_verify_claims` unbounded lists → LLM cost DoS; no rate limits. Fix: reuse `validate_ingestion_url`+pinned fetch; `top_k=max(1,min(int(top_k),50))`; `claims[:20]`, evidence `t[:4000]`; add `@limiter.limit`.
- [ ] **Login lockout per-process + unbounded dict** — `app/services/auth_service.py:69-88` bypassed by multi-worker, memory-DoS-able. Fix: Mongo TTL collection (`failed_logins`, `expireAfterSeconds=login_lockout_seconds`) or `TTLCache(maxsize=10_000)`.
- [ ] **Rate limiter per-process memory** — `app/core/rate_limiter.py:67`, `app/main.py:388-390` (SlowAPI in-memory; bypassed multi-replica; internal/MCP surfaces unlimited). Fix: Redis `storage_uri` in prod or pin single replica; add limits to internal routes; assert `Retry-After`.
- [ ] **Service tokens unrevocable** — `app/api/deps.py:63-97` vs `:37` (user `jti` denylist-checked, service not; 24h TTL in `security.py:32`). Fix: denylist-check service `jti` too or shorten TTL + rotation; validate `permissions: list[str]`.
- [ ] **Ingestion AV/decompression fail-open** — `app/ingestion/parser.py:63-108,155-164,354-389`: 8KB EICAR-only scan, 16B magic check, `parse_pdf` full `stream.read()` + uncapped `get_pixmap(dpi=300)`. Fix: chunked full-stream scan or size cap pre-scan; `max_pages` + max render pixels; try/size-guard OCR render.
- [ ] **Upload CPU/RAM** — `app/api/v1/knowledge_bases.py:164,311`, `parser.py:238,273,317,339`: no filename length cap; `chardet` on full 20MB ×4. Fix: `filename[:255]`; detect on first 100KB.
- [ ] **CORS credentialed-wildcard** — `app/main.py:395-406` `allow_credentials + ["*"]` methods/headers; dev regex allows takeover-prone `*.vercel/netlify/pages`. Fix: enumerate methods/headers; restrict regex.
- [ ] Doc drift: `knowledge_bases.py:256-257` claims `github.com` allowed but `DEFAULT_URL_ALLOWLIST` (`search_service.py:52-63`) has only `api.github.com`/`raw.githubusercontent`. Align.
- Verified good (don't regress): bcrypt 72B (`security.py:28-50`), service↔user confusion blocked (`security.py:126,202`), XFF only trusted proxies (`rate_limiter.py:20-64`), page-image traversal-safe (`page_images.py:31,61-74` + `documents.py:38,81`), URL fetch per-hop allowlist+DNS+pin (`search_service.py:392-475`).

---

## 4. Ultra-low RAM playbook (what's done vs what to flip)

Already good — keep: ONNX runtime (`pyproject.toml:68` torch-free), Qdrant `on_disk + INT8 ScalarQuantization always_ram=False` (`qdrant.py:142-165`), KV `q8_0 + flash-attn` (`hardware.py:45,49,62-67`), tiered ingest batch 32/64/128 (`hardware.py:174-186`, `pipeline.py:157-161`), batched `aembed` + SQLite (`pipeline.py:161-187`, `disk_cache.py:140-176`), `malloc_trim` + RSS guard (`memory.py:30-47,83-100`), out-of-process LLM (HTTP only).

| # | Action | Where | Saving |
|---|--------|-------|--------|
| 1 | Default `embedding.provider: onnx`, prebuild ONNX into Docker | `models.yaml:66`, `Dockerfile`, `scripts/export_bge_onnx.py:30-115` | ~500–1000 MB |
| 2 | Pre-export reranker ONNX int8 at build; never runtime `torch.onnx.export` | `models.yaml:119-121`, `onnx_reranker.py:159-221` | cold-start s + RAM spike |
| 3 | `--max 1` on ≤8GB (now automatic via RAM-aware default); lazy (not eager) embedding warmup on lean | `scripts/start_local_llm.sh`, `main.py:159-163` | multi-GB OOM guard |
| 4 | OCR `dpi: 300→200`, `store_page_images: false` on lean; downscale PNG; `idle_trim_memory()` post-ingest | `models.yaml:170,175`, `parser.py:164-165`, `memory.py` | linear pages×chunks spike |
| 5 | TTL + size cap + `VACUUM` for `embedding_cache.db`, `semantic_cache.json` (cap `response` size, 24h TTL, skip persist when empty), `data/page_images/` retention | `disk_cache.py:33-40,52-176`, `semantic_cache.py:46-51,111-144` | unbounded disk/RAM growth |
| 6 | Shell-level: `export OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_FLASH_ATTENTION=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE=5m`; `MALLOC_ARENA_MAX=1 TOKENIZERS_PARALLELISM=false` | `.env.example:139-148`, shell before `ollama serve` | resident vs swappy on 8GB |
| 7 | Skip `optimum-intel` int8-embedding flag (`models.yaml:75-76 false`) until stub `model_registry.py:774-799` is real — ONNX default already captures the win | `models.yaml:75-76` | avoid half-wired path |

---

## 5. Accuracy-with-speed tweaks (no quality loss)

- Keep ONNX MiniLM int8 rerank (~1% ranking loss for 3–4× CPU) but fix batching (§2.P1) or the speedup is unrealized; keep `cache_size: 500`.
- Keep `max_chars: 3000` + 8 chunks on 4096 ctx for 8GB; raise to 6000 only with `-c 8192` (16GB tier).
- Keep INT8 Qdrant quantization (~1–3% recall drop, acceptable).
- Keep `chunk_size: 512/overlap: 64` — retune only with full re-index (boundaries change).
- Keep fused decompose+verify (1 NLI call, not 2) with classic two-step fallback.
- Don't chase `min_p/top_k` speculative knobs (`local_llm.min_p: 0.0, top_k: 0` = disabled) until P0/P1 fixed — they add variance without fixing the 20-call verification blowup.

---

## 6. Tests: why stale + rewrite order (do NOT rely on current scripts)

- `tests/conftest.py:1-37` only clears reranker cache — does NOT reset `get_settings`/`get_model_config` lru_cache (so `test_rate_limit.py:23-47` leaks by order), `_FAILED_LOGINS`, OCR engine, SlowAPI storage, or `dependency_overrides`.
- `test_auth.py:14,29-51`: `TestClient(app)` without lifespan → `@patch(connect_db/create_indexes)` is theater; `str _id`/`created_at` vs real `ObjectId`/`datetime`; dummy `$2b$12$DUMMY…` isn't valid bcrypt; no lockout/inactive/legacy-no-`jti`/service-at-`/me` coverage.
- `test_rate_limit.py:22-86`: mutates global settings, couples to `testclient` host string, unique-`X-Forwarded-For` bucket isolation breaks under Redis/starlette; upload/URL/internal untested; no `Retry-After`.
- `test_ingestion.py:99-145`: `assert update_one.call_count == 3` implementation-brittle; heavy mocks; ZERO negative tests (magic-byte, zip-bomb, EICAR, XXE/billion-laughs via `defusedxml`, oversized CSV, OCR fail-open).
- `pyproject.toml [tool.pytest.ini_options]`: `addopts=--cov… -v` slows every run; sync `TestClient` on httpx deprecation path — pin or move to `httpx.ASGITransport`.
- Rewrite order: (1) autouse fixture resetting settings/model caches, `_FAILED_LOGINS`, OCR engine, limiter storage, `dependency_overrides` in `conftest.py:27`; (2) `with TestClient(app)` / `dependency_overrides[get_current_user]`; (3) negative security tests (SSRF mocked-DNS, `..` → `resolve_page_image_path=None`, EICAR → `IngestionError`, zip-bomb, lockout N-fails, revoked 401, MCP unknown-tool + `top_k` clamp, internal caps); (4) regression tests for every P0 in §2 (cache-poison, pin-before-upsert, no-auto-delete, no-pad-cache).

---

## 7. Suggested execution order (smallest effort → biggest win)

1. `models.yaml:66` → `onnx` + prebuild ONNX embed+rerank into image (§4.1–2).
2. `reranker.py:233-243` no-pad-cache + `onnx_reranker.py` batch loop (§2).
3. `config.py:363-367,527-531` cloud IDs from yaml (§1.2.2).
4. `pipeline.py` pin-before-upsert + Mongo dedup + sparse uses raw text (§2).
5. `qdrant.py:110-118` no-auto-delete gate (§2).
6. `generator.py:765-768` re-raise config/outage; `integrity.py:40-42` EXTERNAL + `graph.py:467-492` audit web chunks (§2–3).
7. `internal.py` SSRF/caps/rate-limit + MCP auth + lockout/limiter backends (§3).
8. Tier caps (§1.2.5) + OCR/dpi + cache TTLs (§4.4–5).
9. Rewrite `conftest.py` + negative tests (§6), then `ruff + pytest -v --cov=app`, `npm run lint && npm test`, `k6 run load-test/smoke.js`.
