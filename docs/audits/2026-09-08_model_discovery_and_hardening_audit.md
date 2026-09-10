# TrustRAG Audit & Fix — Model Discovery, Validator Allowlist, and Hardening Pass

**Date:** 2026-09-08
**Branch:** `ui-redesign`
**Status:** Complete — all changes verified (141 backend tests, ruff-clean, frontend build/lint green)

---

## Root cause fixed: `Value error, Model is not enabled for provider 'llama_cpp'`

The Playground surfaced this error whenever a model installed *after* the static
`INSTALLED_*_LLMS` lists was selected — e.g. `SmoILM3-3B-GGUF:Q4_K_M`
(`SmolLM3-3B`) appeared in the discovery-driven UI dropdown, but the request
validator only allowed the static allowlist. Discovery and validation were out
of sync.

**Fix:** the validator's `AnalysisCreate` allowlist for `ollama`/`llama_cpp` now
unions the static lists with the **live discovery cache** (`merge_discovered_llms`),
so any model the UI offers is accepted. Security is preserved: local servers can
only ever serve weights already installed on disk; cloud/Ollama guards unchanged.

### Discovered-model pipeline

| Layer | Behavior |
|---|---|
| `scripts/discover_local_models.py` | Pre-backend CLI: `ollama list` + `llama-server --cache-list`, filters embedding names, seeds the in-process cache and writes `apps/api/data/discovered_models.json` |
| `app/core/local_llm.py` | `merge_discovered_llms` / `get_discovered_llms` (thread-safe cache), `save/load_discovery_snapshot`, `seed_local_model_discovery`; 4s CLI timeouts |
| `app/main.py` lifespan | `load_discovery_snapshot()` before serving the first request; `seed_local_model_discovery()` joins the background warmup with embedding load + hardware probe |
| UI Playground | `model-providers` query refetches every 8s; QueryPanel gains a refresh (`RotateCcw`) button beside the model selector; loading state disables it |
| UI Settings | Already auto-refreshes the provider list every 15s (unchanged) |

### Validator allowlist

- `apps/api/app/api/v1/schemas/analysis.py` — `ollama`/`llama_cpp` model fields
  accept `INSTALLED_*_LLMS ∪ get_discovered_llms(provider)`.
- Embedding models stay filtered during discovery (ollama/llama.cpp are LLM-only).

---

## Bug-fixing pass (this session)

1. **Divergent cache directories** (`semantic_cache.py`)
   `CACHE_DIR` used `parents[3]` (`apps/data/cache`) while `disk_cache.py` and
   `local_llm.py` used `parents[2]` (`apps/api/data/cache`). Fixed to `parents[2]`;
   all three caches now coalesce under `apps/api/data/`. Regression:
   `test_cache_directories_coalesce`.

2. **`_persist_cache` deque mutation race** (`semantic_cache.py`)
   Iterated `_SEMANTIC_CACHE` outside `_CACHE_LOCK`; a concurrent append/popleft
   could raise `RuntimeError: deque mutated during iteration`, silently swallowed
   by the broad `except`. Now snapshots `list(_SEMANTIC_CACHE)` under the
   (reentrant) lock before serializing.

3. **Empty-list `IndexError` guards** (`local_llm.py`)
   `check_ollama_status` / `check_llamacpp_status` used `all_llms[0]`/`combined[0]`
   unconditionally. Now guarded (`else ""`) so an operator-emptied static list
   cannot crash the endpoint.

4. **Embedding disk-cache cross-contamination** (`model_registry.py`, `disk_cache.py`)
   Disk cache keyed on `model:text` only; two providers serving the same model
   string but different vectors would collide on `embedding_cache.db`. Cache
   label is now `provider::model`. In-memory LRU stays per-provider/model because
   `get_embedding_model` is `lru_cache`-keyed by `(provider, model)`.

5. **`CachedEmbeddingsWrapper` thread-safety** (`model_registry.py`)
   The shared `OrderedDict` LRU was mutated from `asyncio.to_thread` threads and
   the event loop without a lock. Guarded `_lookup_mem`/`_store_mem` with a
   `threading.RLock` (reentrant, safe for nested callers).

6. **NLI segment misalignment after context pruning** (`generator.py`)
   `format_context_with_chunk_indices` formatted segments then ran the whole
   block through `prune_context_tokens`, which renumbered/merged/dropped
   `Segment N` headers — so the verifier's
   `context_chunk_indices[idx - 1] → evidence_id` mapping could point at the
   wrong evidence. Now pruning is **per-segment** and segments are kept whole
   against the char budget (never partially truncated), preserving
   number↔index↔evidence alignment. Regression:
   `test_context_segment_numbers_align_with_chunk_indices_under_truncation`.

### Reviewed and accepted as-is
- **SSRF posture** (`search_service.py`): strict origin allowlist + per-hop DNS
  revalidation + `follow_redirects=False` + manual redirect cap. Residual
  DNS-rebinding TOCTOU is bounded to allowlisted public origins. (Connection-time
  IP pinning remains a documented future hardening item.)

---

## Verification

```bash
cd apps/api
ruff check app tests          # All checks passed!
ruff format --check app tests  # 90 files formatted
python -m pytest tests -q --no-cov   # 141 passed, 22 warnings (pre-existing deprecations)

cd apps/web
npm run lint                  # clean (0 errors/warnings)
npm run test                  # 15 Vitest tests passed
npm run build                 # production bundle OK (~3.4s)
```

Frontend build splits into optimized vendor chunks (react-vendor 180 kB, etc.).

---

## Documentation updates (same day)

- `README.md` — badge/CI/test counts → 141; architecture tree now lists
  `scripts/` + `config/ports.yaml`; new "Pre-Backend Discovery Snapshot"
  subsection (#14); env table gains `TRUSTED_PROXY_IPS`, rate-limit overrides,
  `CACHE_DIR`; Docker section documents `uv sync --locked`; Option A adds the
  discovery step; cache/namespace notes in section #7.
- `.env.example` — documents `TRUSTED_PROXY_IPS` (already present), optional
  rate-limit ceilings, and `CACHE_DIR`.
- `.gitignore` — **fixed:** `apps/api/uv.lock` was globally ignored but the API
  `Dockerfile` runs `uv sync --locked` and `COPY pyproject.toml uv.lock .`; the
  lockfile is now explicitly un-ignored so the `docker-build` CI job can build.
- `CONTRIBUTING.md` — test counts refreshed (141 across 20 files).

---

## Next (not yet done)

1. ~~Run one controlled E2E with live Ollama/llama.cpp to watch the discovery
   snapshot + UI dropdown + validator accept the same model end-to-end.~~

### ✓ E2E verified (this session)

- **Servers**: `ollama serve` (11434) + `llama-server -hf ggml-org/SmolLM3-3B-GGUF:Q4_K_M` (8080) both live.
- **Discovery**: `scripts/discover_local_models.py` seeded 6 models → `apps/api/data/discovered_models.json`.
- **Backend startup**: loaded the snapshot pre-serve.
- **`GET /api/v1/models/providers`**: both local providers `connected: true`;
  `ggml-org/SmolLM3-3B-GGUF:Q4_K_M` listed (models + cache_models),
  `Impulse2000/smollm3:3b-q4_K_M` listed under ollama.
- **Validator**: `POST /api/v1/analyses` with
  `llm_model="ggml-org/SmolLM3-3B-GGUF:Q4_K_M"`/`Impulse2000/smollm3:3b-q4_K_M`
  now passes model validation — proceeds to KB lookup (404 `Knowledge Base
  not found`, expected) instead of `422 Model is not enabled for provider
  'llama_cpp'`. The original bug is gone.
- **Live generation**: SmolLM3-3B answers on llama.cpp (reasoning model —
  emits `reasoning_content` then final `content`; via `/v1/chat/completions`).

1. ~~Connection-time SSRF IP pinning for URL ingestion.~~

### ✓ SSRF IP pinning verified (this session)

- `apps/api/app/services/search_service.py`: `_PinnedAsyncNetworkBackend`
  dials the pre-validated public IP while httpcore still performs TLS with
  the original hostname (SNI/Host preserved). `fetch_document_from_url`
  builds a per-hop pinned client; redirects are re-resolved + re-checked.
- Tests: 3 new (`test_fetch_success_with_pinned_client`,
  `test_fetch_rejects_non_public_dns`,
  `test_pinned_backend_connects_to_validated_ip_only`); 14/14 in
  `test_search_mcp.py` pass.
- Live check: `https://en.wikipedia.org/wiki/Python` fetched 89,924 bytes
  through the pinned transport; `rebound.internal` redirect rejected.
- Full backend suite: **153 passed**, ruff check + format clean.

3. ~~Distinguish "retrieval outage" from "no evidence" in `retriever.py`.~~

### ✓ Retrieval outage vs no-evidence (this session)

- **Before**: `dense_search`/`sparse_search` swallowed every exception and
  returned `[]`, so a Qdrant/embedding outage was indistinguishable from an
  empty result — the graph reported RETRIEVAL_FAILURE/ABSTAIN ("no
  evidence") and burned recovery loops on dead infrastructure.
- **Now**: new `RetrievalOutageError` (`app/core/exceptions.py`); both
  searches raise it on infra failure (client/query/embedding) and return
  `[]` only for genuine empty results (incl. empty sparse reps);
  `retrieve_hybrid_chunks` propagates it (documented).
- **Graph**: `retrieval_node` catches it → `diagnosis_type =
  "RETRIEVAL_OUTAGE"` (new `DiagnosisType` value), user-facing "temporarily
  unavailable" message, `attempts = max_recovery_attempts` (no futile
  rewrites); `generation_node`/`verification_node` preserve the outage
  answer (never cached — verdict stays FAIL); `analysis_service` stores
  `status: failed` + `RETRIEVAL_OUTAGE` diagnosis + `analysis.outage` trace.
- **Other callers**: MCP `trustrag_search` returns an outage text instead of
  raising; `POST /internal/search` returns `{"results": [], "count": 0,
  "error": "retrieval outage: ..."}`.
- **Tests**: 6 new in `test_retrieval.py` (outage raise vs empty-list for
  dense/sparse/hybrid) + 3 in `test_agent.py` (node diagnosis, generation
  + verification preservation). Full suite 153 passed, ruff clean.

4. Add tenant-bound service tokens for `/internal/ingest/document`.
5. bcrypt password max length + JWT audience/issuer claims.