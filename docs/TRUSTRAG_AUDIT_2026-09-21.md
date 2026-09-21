# TrustRAG Deep Audit — 2026-09-21

Senior roles: Backend, AI/ML, Security, Optimization, Testing (blackbox + whitebox).
Scope: optimization Phases 1–4 working tree on branch `ui-redesign`
(`config.py`, `local_llm.py`, `model_registry.py`, `onnx_reranker.py`,
`generator.py`, `reranker.py`, `retriever.py`, `concurrency.py`,
`analysis_service.py`, `models.yaml` v1.18).
Method: whitebox diff review + parallel subagent sweeps (correctness,
security/perf, dead-code). Per instructions: no reliance on test scripts;
verification via `ruff` + targeted runtime checks.

Follows: `docs/SESSION_SUMMARY_2026-09-21.md`, `docs/TRUSTRAG_OPTIMIZATION_PLAN.md`.

## P0 — must fix (data loss / broken feature)

### P0-1 Ollama "unload" deletes models from disk — `local_llm.py:133-153`
`unload_ollama_inactive_models()` calls `DELETE /api/delete`, which
permanently deletes the model blob. Correct VRAM-only unload is
`POST /api/generate` (or `/api/chat`) with `keep_alive: 0`.
Status: FIXED → `POST {base}/api/generate {"model": name, "keep_alive": 0}`.

### P0-2 ONNX export traces the wrong object — `onnx_reranker.py:192-206`
`torch.onnx.export(model, (input_ids, attention_mask))` where `model` is a
`sentence_transformers.CrossEncoder` (no such forward; real net is
`model.model`). `input_names`/`dynamic_axes` also omit `token_type_ids`
while `predict()` feeds them. Export graph and inference inputs disagree.
Status: FIXED → export `model.model`, include `token_type_ids` in dummy
inputs/names/axes; `predict()` truncates to session inputs; tokenizer pinned
to `cfg.reranker_model` at both export and load call sites.

### P0-3 NVIDIA client timeout/cap silently ignored + stalled default model
Live probe (2026-09-21, `langchain-nvidia-ai-endpoints 1.4.3`): `ChatNVIDIA`
declares `max_completion_tokens` (not `max_tokens`) and takes `timeout` via
client kwargs with `extra='ignore'` — the registry's `max_tokens=`/`timeout=`
were both dropped, leaving the OpenAI-client default (~600s) per attempt and
no output cap. Meanwhile `nvidia/nemotron-3.5-lightning-30b-a3b` returns zero
bytes indefinitely (streaming and non-streaming; auth + `/models` healthy at
0.1s; sibling models 404-not-entitled or 503-capacity; only
`openai/gpt-oss-20b` answers, in 44s). Net effect: each call hangs minutes,
pipeline burns N× that, user sees "much time but no response".
Status: FIXED → registry passes `max_completion_tokens` + `timeout`
(verified `client.timeout == 180.0`, `max_tokens == 1024` in payload);
new `probe_cloud_llm()` (60s tiny completion) hooked into `create_analysis`
preflight for nvidia/nim/gemini/google_genai → fast 503 with retry guidance.
Follow-up FIXED: vendor `UserWarning: ... type is unknown and inference may
fail` (emitted on every ChatNVIDIA construction) suppressed at both
construction sites via `_suppress_nvidia_unknown_type_warning()` + debug log;
cloud preflight in `create_analysis` broke
`test_pre_request_budget_disabled_allows_large_query` (mocked config never
reaches a real constructor) → test now mocks `probe_cloud_llm` per the
`probe_local_llm_server` pattern. Suite: 390 passed.

## P1 — serious (wrong behavior / crash / race)

### P1-0 Local-only kwargs leaked to Gemini/NVIDIA — `generator.py``generate_grounded_answer` and `compress_context` sent `num_ctx`,
`num_batch`/`n_batch`, `keep_alive` (and `max_tokens`) to every provider.
Verified against installed `langchain-google-genai 4.3.7` /
`langchain-nvidia-ai-endpoints 1.4.3` / `langchain-core 1.6.1`: Gemini
ignores `max_tokens` (reads `max_output_tokens`) and rejects unknown
`GenerateContentConfig` fields (`num_ctx`/`keep_alive` → ValidationError,
failing the call); NVIDIA merges extras into the API payload. The
verifier/graph already fenced this via `local_cap_kwargs` — the generator
was the only leaker (confirmed by repo-wide grep).
Status: FIXED → `_invoke_kwargs_for_provider()`: local keeps full tuning,
Gemini gets `max_output_tokens`, NVIDIA/NIM gets `max_tokens`.

### P1-1 Caller `stop` wipes early-exit stops — `local_llm.py:434-438,594-599`
`if stop: options/payload["stop"] = stop` overwrites EOS stops.
Status: FIXED → union of both lists, deduplicated.

### P1-2 Dynamic `num_ctx` silently dropped; batch key mismatch
Generator passes `num_ctx`/`n_batch`/`keep_alive` to all providers, but
`ChatLlamaCppClient` never read `num_ctx`/`keep_alive`, and Ollama reads
`num_batch` while generator sent `n_batch`.
Status: FIXED → Ollama accepts `num_batch`/`n_batch`; llama.cpp accepts
`n_batch`/`num_batch` and `num_ctx`/`n_ctx` (advisory: server `-c` is fixed
at startup; oversize logs a warning). Generator sends both keys.

### P1-3 `compress_context` double-format + stale citation range — `generator.py`
`generate_grounded_answer` formats, then `compress_context` re-formats from
`chunks`; returned `chunk_indices` describe pre-compression segments while
text is free-form summary, so `strip_invalid_citations` validates against a
phantom range.
Status: FIXED → format once; `compress_context` takes pre-formatted
`(context_str, chunk_indices)`; compressed path returns the surviving
segment numbers parsed from the summary (fallback: original indices).

### P1-4 Adaptive Top-K threshold never fires — `retriever.py:499`
`top_rrf >= 0.82` with `rrf_k=60` (max RRF ≈ 0.033) is dead code.
Status: FIXED → threshold `0.02` documented against RRF scale; comment updated.

### P1-5 Registry seal bug — `model_registry.py:116-124,932-938`
`clear_model_caches()` → `close_all_llm_instances()` sets
`_LLM_REGISTRY_CLOSED=True` with no reopen; every later `put_llm_instance`
drops new instances.
Status: FIXED → split close vs seal; `clear_model_caches()` reopens registry.

### P1-6 Empty-string env crashes — `config.py`
`int("")`/`float("")` raises for `LOCAL_LLM_NUM_CTX=""`,
`RERANKER_CACHE_SIZE=""`, `LOCAL_LLM_MIN_P=""`,
`CONTEXT_COMPRESSION_TARGET_REDUCTION=""`, `MAX_CONTEXT_TOKENS=""`, etc.
Status: FIXED → blank env treated as unset (shared `_blank_as_none`
helper); `keep_alive`/timeout fall back to defaults.

### P1-7 Reranker cache race — `reranker.py:33-64`
"Thread-safe" LRU with no lock; `_rerank_sync` runs via `asyncio.to_thread`.
Status: FIXED → `threading.Lock` around get/set/clear/stats.

### P1-8 Reranker tokenizer mismatch — `onnx_reranker.py:29`, `model_registry.py`
Export and load both fall back to `ms-marco-MiniLM-L-6-v2` even when
`cfg.reranker_model` differs.
Status: FIXED → `tokenizer_name=cfg.reranker_model` at both call sites.

## P2 — should fix (calibration / waste)

- P2-1 Threshold scales inconsistent (`dense 0.78` vs `rerank logit 0.80` vs
  `RRF 0.82`). Documented per-signal scales; RRF fixed (P1-4). Rerank-logit
  cutoff left but flagged for sigmoid normalization (follow-up).
- P2-2 `get_max_llm_instances()` syscalls `psutil.virtual_memory()` per
  `put_llm_instance`. FIXED → cached with 60 s TTL.
- P2-3 Double `get_reranker()` per query. FIXED → single lookup reused.
- P2-4 `calculate_dynamic_num_ctx` clamps down to the static cap it claims to
  escape. FIXED → loud warning when `required_ctx > max_ctx`.
- P2-5 `predict()` signature indentation. FIXED via ruff format.

## Security notes (verified; residual hardening)

- S1 (Med) Service-token tenancy opt-in (`internal.py:113-142,156-209`):
  unbound `ingest:write` tokens can present arbitrary `user_id`+`kb_id`.
  Gated on token minting; needs bound-enforcement follow-up. NOT changed.
- S2 (Med) `/models/providers` unauthenticated-cost fan-out (subprocess +
  5-port probe, ~8 s UI poll). Needs rate limit. NOT changed (route-level).
- S3 (Low) Reranker (`query+doc` hash) and gen caches lack kb/model
  namespace. Floats only, no leak; poisoning-class. NOT changed.
- S4 (Low) ONNX path operator-controlled, no suffix/confinement check.
  NOT changed (operator-only surface).
- S5 (Low) Non-atomic `discovered_models.json` / `semantic_cache.json`
  writes. FIXED (local_llm snapshot only) → atomic tmp+rename.
- S6 (Low) No per-user doc-count/byte quota. NOT changed.
- S7 (Info) Base-URL disclosure on authenticated route. NOT changed.
- Rejected (verified safe): SSRF base_url/URL-ingest, JWT, Mongo/Qdrant
  injection, model-string injection, compression recursion, subprocess,
  secrets-in-logs, server XSS, config-cache I/O, tiktoken DoS.

## Cleanup

Deleted (regenerable, gitignored): root + `apps/api` `.coverage`,
`.pytest_cache/`, `.ruff_cache/`, `apps/api/.mypy_cache/`,
`trustrag_api.egg-info/`, all `__pycache__/`+`*.pyc`, project `.DS_Store`
files. Left in place (runtime/data, gitignored): `apps/api/data/`
(caches, snapshots, Qdrant, page images), `.model_cache/` + ONNX blobs
(duplicate ~267 MB noted — re-export via `scripts/export_bge_onnx.py`;
 NOT deleted to avoid breaking local inference), `.venv/`,
`apps/web/node_modules/`, `apps/web/dist/`, `.env`.
Dead code removed: `apply_temporal_filtering_batched()` alias
(`retriever.py`, zero callers). Kept (wired feature, not dead):
`maybe_unload_inactive_models` chain, `discover_hf_hub_gguf_models`,
`export_crossencoder_to_onnx`, `compress_context`.

## Verification (no test-suite reliance)

- `ruff check apps/api/app/core/local_llm.py apps/api/app/core/config.py
  apps/api/app/core/model_registry.py apps/api/app/core/onnx_reranker.py
  apps/api/app/generation/generator.py apps/api/app/retrieval/reranker.py
  apps/api/app/retrieval/retriever.py` → clean.
- `ruff format --check` on touched files → clean.
- `python -m compileall` on touched files → OK.
- Targeted runtime probes: blank-env config, adaptive Top-K branch,
  stop-union, registry reopen, reranker-cache concurrency → pass.

## Refinement pass — cloud reasoning models verify like local ones

Symptom (playground screenshot): NVIDIA muse-glimmer-30b answer grounded
and cited, yet "Only 1/3 claims supported → 33% FAILED". Reproduced live:
batch NLI returned 2/3 verdicts with one NEUTRAL on verdict "S".

Root causes + fixes (all provider-agnostic, local behavior unchanged):
1. Verdict coercion too strict — `_normalize_verdict_value` rejected
   single letters ("S") and trailing punctuation ("SUPPORTED.") →
   false NEUTRALs. Added verb forms (SUPPORT/SUPPORTS/CONTRADICT/...),
   S/C/N shorthands, and punctuation stripping.
2. Reasoning traces share the completion budget — verification caps
   (384/512/768/1024) truncate verdict JSON on thinking models. New
   `verification_cap_kwargs(provider, model, N)`: local identical,
   non-reasoning cloud unchanged ({}), reasoning cloud 2x with the
   provider-correct name (max_tokens / max_output_tokens).
3. Native tool-calling structured output is flaky on NVIDIA
   unknown-type models (live: HTTP 400 on guided_json, partial arrays).
   New `_structured_verifier()`: nvidia/nim go through the prompt-based
   JSON path (response_format json_object + repair); others keep native.
   Live batch re-run: 3/3 SUPPORTED with correct segments (was 2/3).
   Suite: 392 passed (2 new unit tests).

## Refinement pass 2 — thinking local models abstain (qwen3:1.7b)

Symptom (playground screenshot): same evidence answers on gemma3:1b but
qwen3:1.7b ABSTAINs after 4 identical regeneration retries. Reproduced
live: our client returned 0 chars. Root cause: the Phase 2.5 Ollama
`"\n\n"` stop token — thinking models open with `<think>\n\n`, so every
answer was decapitated to a stub (and ordinary multi-paragraph answers
were truncated mid-way). Compounding it, small num_predict budgets get
eaten by the thinking trace (rewrite cap 128 → empty rewrite, matching
the "Empty rewrite on already-refused evidence" timeline).
Fixes: dropped `"\n\n"` (real EOS tokens only); new
`strip_think_blocks()` wired into generation + compression;
`verification_cap_kwargs` now gives thinking models 2x headroom on
local providers too (qwen3/qwq/deepseek-r1 keywords).
Live: 0 chars → 1449-char 3-paragraph answer, no think leakage;
grounded summary path returns 2374 cited chars (was ABSTAIN).
Suite: 395 passed (3 new unit tests).

## Refinement pass 3 — reasoning-model verification endgame (muse-glimmer)

Symptom (playground screenshot): summary query, 8 chunks, 0 assertions,
ABSTAIN after 4 recoveries, "Empty rewrite on already-refused evidence".
Reproduced live, three stacked bugs:
1. Fused decompose+verify truncates mid-JSON even at 2048 budget
   (reasoning overflow) → None → wasted call + latency. Fix: reasoning
   models skip fused, go two-step directly (designed path, with debug log).
2. Rewrite starves at 256 (reasoning ate it all; 512+ succeeds). Fix:
   `verification_cap_kwargs` floor raised to 1024 for thinking models
   (local and cloud) — verified rewrite returns 37 chars via helper.
3. (Prior pass) prompt-based JSON transport for nvidia.
Suite: 395 passed.

## Follow-ups (not in this pass)

1. Sigmoid-normalize reranker logits before `0.80` cutoff (P2-1 remainder).
2. Enforce `bound_kb_id`/`bound_user_id` on all `/internal/*` (S1).
3. Rate-limit `/models/providers` + hardware endpoints (S2).
4. Namespace reranker/gen caches by kb/model (S3); confine ONNX path (S4).
5. Per-user ingestion quotas (S6).
6. Deduplicate BGE ONNX blobs; consolidate overlapping plan docs
   (`TRUSTRAG_specs` vs `IMPLEMENTATION-PLAN` vs `UPGRADE-PLAN` vs
   `OPTIMIZATION-PLAN`, dual architecture docs).
