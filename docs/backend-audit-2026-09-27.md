# TrustRAG Backend Audit — Bugs, RAM, Model Portability, Test Gaps

- **Date:** 2026-09-27
- **Branch:** `ui-redesign` @ `c6a14d0`
- **Scope:** `apps/api` (backend), `apps/web` (frontend tests), `apps/web/e2e`, CI
- **Method:** four independent parallel audits (RAM/memory, local-model portability, cloud-model path, test-coverage gaps), followed by direct re-verification of every CRITICAL/HIGH claim by the author against the running source and installed packages.
- **Test baseline at audit time:** 431 passed, 32.7s, **70% coverage** (8185 statements, 2464 missed), 0 skipped / 0 xfail.

## Evidence legend

| Tag | Meaning |
|---|---|
| **VERIFIED** | Re-checked by the author against the source and/or the installed package at audit time. Reproduced where noted. |
| **EVIDENCE** | Read directly from source by a subagent; the claim follows from the code but was not independently re-run. |
| **NEEDS-RUNTIME** | Plausible failure mode that requires a live model / GPU / cloud key to confirm. Do not treat as a proven defect. |

Findings marked **VERIFIED** were checked against the exact line numbers quoted. Line numbers refer to `ui-redesign` @ `c6a14d0`.

---

# Status

Remediation tracker. **Waves 1 and 2 are complete, plus the five Wave 4/5 items in `1bc7b00` and a further round covering B-8 (upload/URL-ingest), B-11 (lifespan), B-15 (effective-model allowlist + canonical provider), and B-18 (`top_p` / `max_completion_tokens`).** Wave 3 and the residual items below are not started. All work is on `ui-redesign`; `1bc7b00` is committed, the second round is **uncommitted**.

Test suite: **431 → 619 backend passed (+188)**, **25 → 33 frontend passed (+8)**, backend coverage **70% → 75%** (8543 statements, 2135 missed). `ruff check` / `ruff format` clean, `scripts/apply_ports.py --check` clean. `app/main.py` 50% → **78%**; `onnx_embeddings.py` 48% → near-complete; `onnx_reranker.py` 29% → near-complete.

## Wave 1 — complete

| ID | Severity | Status | What changed |
|---|---|---|---|
| **B-1** | CRITICAL | ✅ **Fixed & measured** | Torch no longer imported on the ONNX path. Added torch-free `detect_accelerator()` / `_nvidia_smi_available()` / `_nvidia_vram_gb()`; `detect_hardware_profile()` uses it. `get_optimal_torch_device()` kept for the PyTorch `CrossEncoder` fallback, which genuinely needs it. Collapsed the duplicated `nvidia-smi` probe in `get_llamacpp_launch_args()`. **Verified: RSS delta 0.0 MB, `torch` absent from `sys.modules`, profile output identical.** |
| **B-2** | HIGH | ✅ **Fixed** | `verification_cap_kwargs` now returns the per-call cap for cloud with each client's real parameter name (`max_output_tokens` for Gemini, `max_tokens` for NVIDIA). Unknown providers still get `{}`. Removes the 512-token truncation and the silent 3-call fallback. |
| **B-3** | HIGH | ✅ **Fixed** | Gemini caps ride on the model via pydantic `model_copy`, not on the `with_structured_output` call. (`bind()` returns a `RunnableBinding`, which has no `with_structured_output`.) Local and NVIDIA paths untouched. |
| **B-6** | HIGH | ✅ **Fixed** | `probe_cloud_llm` now classifies 401/403 (credential), 429 (quota), 5xx, and unreachable separately; logs `exc_info` + status + error type; and reuses a recent success for 60 s so a burst of analyses pays one probe. |
| **B-19** | LOW | ✅ **Fixed** | Both tautological tests replaced. `execute_mcp_tool` gained 5 real tests (`_internal=True`, empty content → `None`, JSON parse, raw-text fallback, error propagation). The source-text lint became a behavioural prompt assertion. |
| **T-3** | — | ✅ **Added** | `test_build_agent_graph_has_expected_topology` — pins the workflow, including `recovery → retrieval`, and asserts `recovery → generation` does **not** exist. Plus a singleton-cache test. |
| **T-10** | — | ✅ **Added** | `FormattedAnswer.test.jsx` — 8 tests: GFM tables, inline vs fenced code, `[Segment N]` preservation, and two XSS guards. |

## Wave 2 — complete

| ID | Severity | Status | What changed |
|---|---|---|---|
| **B-5** | HIGH | ✅ **Fixed** | New `app/core/llm_outage.py` classifies vendor SDK and transport failures into `LLMUnavailableError`. `_execute_with_fallback` short-circuits with a terminal `LLM_OUTAGE` diagnosis, exhausts the recovery budget, and returns an answer that explicitly says this is *not* a finding of insufficient evidence. Ordinary errors pass through untouched. |
| **B-17** | MEDIUM | ✅ **Fixed** | Cloud client construction wrapped → key-free `ConfigurationError`. Added value-level credential scrubbing (`AIza…`, `nvapi-…`, `sk-…`, `hf_…`, `Bearer …`); the previous scrubber matched key *names* only and so missed credentials embedded in exception text. |
| **B-4** | HIGH | ✅ **Fixed** | New `app/core/llm_ledger.py`: a `ContextVar` ledger per analysis counting LLM calls, input/output tokens, and per-model breakdown. `invoke_counted` wraps all 10 provider call sites. New `cost_controls.max_llm_calls_per_analysis: 24` caps **cloud tiers only**. Enforced at the node boundary (`RECOVERY_BUDGET_EXHAUSTED`) and inside the per-claim NLI fallback loop — the largest cost multiplier. The vacuous pre-request guard now reads a separate, reachable `max_query_tokens: 400`. |
| **B-16** | MEDIUM | ✅ **Fixed** | Cloud providers bypass the RAM-derived LRU entirely and are never evicted, so `aclose()` cannot hit an in-flight billed request. Local eviction still works and now prefers evicting other local clients. |

## Selected Wave 4 / 5 items — complete

These were chosen for product impact rather than to clear the list mechanically. The ~28 shape-only test cleanups were deliberately skipped as low leverage, and Wave 3 (local portability) was deferred because it needs validation on real hardware.

| ID | Severity | Status | What changed |
|---|---|---|---|
| **B-9 / T-1** | MEDIUM | ✅ **Fixed** | **The highest-value gap in the audit.** New `tests/test_analysis_pipeline_integration.py` (7 tests) runs `execute_agentic_rag_flow` for real, mocking **only** the external boundaries — LLM client, vector search, Mongo. `generator.py`, `verifier.py`, `verdict.py`, the graph topology, and the state machine all execute as production code. Covers: a grounded PASS with linked evidence, evidence persistence, CONTRADICTED → FAIL, and empty-KB → ABSTAIN. **Verified to have teeth**: replacing `generate_grounded_answer` with a stub makes 3 of the 7 fail, which nothing in CI previously did. |
| **B-10** | MEDIUM | ✅ **Fixed** | New `tests/test_api_contract.py` (11 tests) pins the OpenAPI *wire* contract. Notably, the wire schema uses `id`/`status`/`reliability` where the internal graph state uses `_id`/`verdict_status`/`reliability_score`, so the snapshot targets the document the frontend consumes. |
| **B-7** | HIGH | ✅ **Fixed** | Context compression now defaults to `off`. It issues a *second* full LLM call on the same model, so firing by default doubled cloud generation cost in a narrow band where it helped least (128K–1M windows vs a ~3000-char formatted cap). Also added `context_compression_min_tokens: 6000` and fixed the output budget: the cap is the budget to *write* the summary, not the size wanted — capping at exactly the target truncated summaries mid-sentence. |
| **B-13** | MEDIUM | ✅ **Fixed** | `nvidia_base_url` was dead config: it only took effect when `load_dotenv` happened to export the env var, so a mounted secret, a programmatic override, or a self-hosted gateway was silently ignored. Now read from config/env and passed explicitly to `ChatNVIDIA`. |
| **B-14** | MEDIUM | ✅ **Fixed** | Provider aliases are normalised before the context-window lookup, so `google_genai`/`nim` no longer fall through to the 4096 local default. The "evidence will be truncated" warning is now emitted only for local providers (the only ones that receive `num_ctx`); cloud gets an informational line instead of a false alarm. |

## Corrections to this audit

Three findings were wrong and have been corrected in place or above:

- The RAM figure: `ru_maxrss` is **bytes** on macOS, not KB. Real delta is **176.9 MB**, not ~181 GB.
- The endpoint count is **46** v1 routes (**22** untested), not "18 of 51" — the original table double-counted.
- The error envelope is nested: `{"error": {"code", "message"}}`, not a flat `{code, message}`.
- B-7's claim that the compression gate skipped the `nim` alias was **wrong**; the alias is handled. The real defects were the default, the budget, and the threshold.
- B-13's claim that `NVIDIA_BASE_URL` was read from the environment by the NVIDIA client was **wrong**; `ChatNVIDIA` does not read it, which is precisely why the config was inert.

## New regression tests

`test_wave2_cloud_resilience.py` (47), `test_analysis_pipeline_integration.py` (7), `test_api_contract.py` (11), `FormattedAnswer.test.jsx` (8), plus additions to `test_hardware.py`, `test_local_llm.py`, `test_verification.py`, `test_agent.py`, `test_search_mcp.py`, `test_metrics.py`.

Three guards are **meta-tests** that keep the other guards from going vacuous — keep them if you edit these suites:
- `test_torch_trap_actually_has_teeth` — the B-1 import trap raises `BaseException`, because `get_optimal_torch_device()`'s `except Exception` would otherwise swallow it.
- `test_pre_request_query_budget_is_not_vacuous` — asserts `max_query_tokens` stays strictly below what the 2000-char schema cap allows. This caught a real mistake: the first value (500) reproduced the original dead-code bug exactly.
- `test_generation_gutted_would_fail_this_file` — asserts the graph still calls the real generator.

## Not started

| Wave | IDs | Theme |
|---|---|---|
| **3** | L-1 … L-12 | Local-model portability: per-tier model recommendations, per-model context window, llama.cpp flags, adaptive timeouts, local provider tests. **Needs hardware validation.** |
| **5 (rest)** | B-18 (`ChatNVIDIA` has no `max_retries`) | NVIDIA lacks a langchain-level retry; adding it without capping Gemini would increase spend, so this needs a cost decision |
| **2** | T-2 | ~28 shape-only tests. The ones that could let a real regression through are fixed (hardware profile coherence, tier→batch-size mapping, auth status codes); the rest are low-leverage `assert x is not None` cleanups. |
| **3** | L-1 … L-12 | Local-model portability. **Blocked on a product decision** (which models to recommend per RAM tier) and on hardware validation. |

### Known follow-ups

- **L-1 is the only remaining user-visible defect** (the same 3B model recommended for every RAM tier). It needs a product decision, not a code change.
- **B-12, B-8, B-11, T-8 are resolved.** `app/services/analysis_service.py` remains the least-covered service, but its authorization path is now pinned by tests that fail if the ownership check is removed.
- **L-1** (the same 3B model recommended for every RAM tier) is user-visible and still open; it needs a product decision on which models to recommend.
- Adding a generic `openai_compatible` provider would need a new `langchain-openai` dependency — deliberately not added without agreement.

## Incidental

`config/ports.yaml` was at one point moved to `docs/config/`, which broke 4 tests and — more seriously — made `config.py:59` silently return `{}`, so the app would have booted on wrong default ports. It has been restored. **`docs/config/` still exists and is untracked**; if relocating it is intentional it needs coordinated changes to `config.py`, `scripts/apply_ports.py`, and the docs.

---

# Part 1 — Confirmed bugs

## B-1 · CRITICAL · The "torch-free" ONNX path still imports Torch on every ingest (VERIFIED, 176.9 MB measured)

The embedding stack was deliberately converted to ONNX Runtime so that the API would not need PyTorch. A Torch import survives on the hot ingest path, costing **~177 MB RSS** on a project whose stated goal is ultra-low RAM.

**Chain (all VERIFIED by reading):**

1. `apps/api/app/ingestion/pipeline.py:190-192` → `get_ingest_embed_batch_size()`
2. `apps/api/app/core/hardware.py:203-212` → `get_cached_hardware_profile()`
3. `apps/api/app/core/hardware.py:230` → `detect_hardware_profile()`
4. `apps/api/app/core/hardware.py:243` → `device = get_optimal_torch_device()` — **unconditional, no accelerator guard**
5. `apps/api/app/core/hardware.py:118` → `import torch`

`get_optimal_torch_device()` exists only to pick a device for a Torch-based embedder that no longer exists. Its own docstring at `hardware.py:30-31` states the design intent explicitly:

> `llama-server` vendors its own Metal/CUDA backends (no torch dependency), so detection here uses platform probes, not torch.

The code contradicts its own stated contract.

**Measured (VERIFIED, reproduced on this host):**

```
baseline:            14.4 MB
after import torch: 191.2 MB
DELTA:              176.9 MB
```

`torch 2.14.0` is installed in the API environment, so the import succeeds and the memory is really allocated. Note that on a host *without* Torch the import raises and is swallowed at `hardware.py:128` — which is precisely why this has gone unnoticed: the cost is invisible in CI and only appears on developer laptops and production hosts that happen to have Torch installed.

**Fix:** make the accelerator probe Torch-free. `detect_hardware_profile()` should determine `device` from platform probes that do not import Torch (the same approach the module already uses for memory at `hardware.py:134-194`), and `get_optimal_torch_device()` should either be deleted or reduced to a lazy, Torch-only helper that is never on the ingest path. Suggested guard: if no caller needs a Torch device, drop the `device = get_optimal_torch_device()` line from `detect_hardware_profile()` entirely and derive `device` from `platform.system()` + a Metal/CUDA capability probe.

**Expected saving:** ~177 MB RSS during ingestion; ~177 MB resident for the lifetime of the process once imported.

---

## B-2 · HIGH · `verification_cap_kwargs` never applies the per-call cap to cloud models → guaranteed JSON truncation (VERIFIED by reading)

`apps/api/app/core/local_llm.py:340-361` returns the task-sized output cap for verification calls. The final branch is:

```python
if norm in LOCAL_LLM_PROVIDERS:
    return {"max_tokens": int(max_tokens)}
return {}          # <-- every non-local provider falls here
```

`LOCAL_LLM_PROVIDERS` covers Ollama / llama.cpp / MLX only. Gemini and NVIDIA therefore get `{}`, and the cap falls back to the instance default `verification.max_output_tokens: 512` (`config/models.yaml:107`).

But the caller asks for **different, larger** budgets per call:

| Call site | Requested tokens | Cloud actually gets |
|---|---|---|
| `verifier.py:694-696` (per-claim NLI) | 384 | 512 |
| `verifier.py:758-760` (batch NLI) | 768 | **512 — truncated** |
| `verifier.py:820-822` (fused decompose+verify) | 1024 | **512 — truncated** |

The fused call serialises decomposition *plus* verdicts for up to `cost_controls.cloud_tier.max_verification_claims: 8` claims. That does not fit in 512 tokens. The result is mid-JSON truncation, `fused_decompose_verify` returns `None` at `verifier.py:840-842`, and the code falls back to the two-step path.

**Impact:** every cloud verification pays **3 billed calls instead of 1** on the common path, and produces a worse result than the local path on identical inputs. This is the single largest cloud cost defect in the codebase.

**Fix:** return the per-call cap for cloud providers too, using the provider-correct parameter name — `max_output_tokens` for `gemini`/`google_genai`, `max_tokens` for `nvidia`/`nim` (the name-mapping discipline already present at `local_llm.py:351-358`).

---

## B-3 · HIGH · Gemini reasoning models would crash every verification call (VERIFIED mechanism, LATENT — no current model id triggers it)

`apps/api/app/verification/verifier.py:81` passes the cap dict straight into LangChain:

```python
if norm not in ("nvidia", "nim"):
    return model_obj.with_structured_output(schema, **cap)
```

`app/core/local_llm.py:356-357` returns a non-empty cap for Gemini whenever `is_reasoning_model(model)` is true (`{"max_output_tokens": N}`).

**VERIFIED against the installed package** (`langchain-google-genai 4.4.0`):

```
VERIFIED LINE: msg = f"Received unsupported arguments {kwargs}"
VERIFIED LINE: raise ValueError(msg)
```

`ChatGoogleGenerativeAI.with_structured_output` raises `ValueError` on *any* unexpected kwarg. So the moment a Gemini model id matches `REASONING_MODEL_KEYWORDS` (`local_llm.py:319-328`: `glimmer`, `gpt-oss`, `reasoning`, `deepseek-r1`, `r1-`, `qwen3`, `qwq`, `think`), every decomposition and NLI call raises.

**Why it is latent, not live (VERIFIED):** I cross-checked every currently-allowed model against the keyword list:

```
GEMINI  gemini-3.8-flash                              reasoning=False
GEMINI  gemini-3.5-flash-lite                         reasoning=False
GEMINI  gemini-2.5-pro                                reasoning=False
... (7 Gemini ids, all reasoning=False)
NVIDIA  openai/gpt-oss-20b                             reasoning=True  ['gpt-oss']
```

No Gemini id matches today. The bug is a landmine: adding any Gemini `-thinking` model id turns every cloud verification into a guaranteed `ValueError` → `decompose_answer_to_claims` falls back to `[answer]` → all claims become NEUTRAL → verdict `FAIL` forever, with no error surfaced.

**Related live finding (VERIFIED):** `openai/gpt-oss-20b` is the **default** NVIDIA verification model (`models.yaml:70-73` / `105`) **and** matches `gpt-oss` → `is_reasoning_model` is permanently `True` for it. It therefore always skips the fused fast path (`verifier.py:1010-1012`) and receives 2× caps. NVIDIA verification carries an unflagged 2–3× cost premium on the default cloud configuration.

**Fix:** never forward caps to `with_structured_output`. Bind them on the model first: `model_obj.bind(**cap).with_structured_output(schema)`. Separately, reconsider whether `gpt-oss` should be classified as a reasoning model for *verification*, where zero-temperature direct answers are wanted.

---

## B-4 · HIGH · `pre_request_budget_enforcement` and `max_recovery_tokens` are both vacuous (VERIFIED)

**Pre-request budget is dead code (VERIFIED):**
- `config/models.yaml:218` sets `cost_controls.max_input_tokens: 100000`, commented *"Hard limit per LLM call AND pre-request query budget"*.
- `app/api/v1/schemas/analysis.py:15-20` caps `AnalysisCreate.query` at `max_length=2000` characters.
- `app/services/analysis_service.py:246-247` compares `estimate_tokens(query_text) > cfg.max_input_tokens`.

2000 characters is at most ~500–700 tokens. A 100 000-token ceiling can never be exceeded. The guard is unreachable, and the comment claiming it is a "Hard limit per LLM call" is false — it is checked against the **query string only**, never against assembled prompt or completion tokens.

**Recovery budget is also vacuous (EVIDENCE):**
- `config/models.yaml:203` `max_recovery_tokens: 2000`; `app/agent/graph.py:1070` estimates `len(current_query)//4 + 100` ≈ 110 tokens per round → ~220 across a whole run, never approaching 2000.
- `graph.py:994-997` compares `recovery_latency_ms`, which is only measured *inside* `recovery_node`'s `finally` (`graph.py:1065-1071`) — not for the retrieval/generation/verification work it is meant to bound.

**Net effect: nothing bounds cloud spend.** A single analysis costs roughly probe(1) + compression(1) + generation(1) + fused-or-fallback(1–3), per round, × up to 3 rounds ≈ **12–20 billed calls** with no ceiling.

**Fix:** add a real per-analysis LLM ledger (count calls and output tokens at the LLM wrapper), and abort the graph with a terminal `RECOVERY_BUDGET_EXHAUSTED` diagnosis when a cloud tier is exceeded. Make the latency budget accumulate per node, not per recovery strategy.

---

## B-5 · HIGH · Dead credential / exhausted quota is reported to the user as "insufficient evidence" (EVIDENCE)

- `app/generation/generator.py:807-810` re-raises non-domain exceptions.
- `app/agent/graph.py:139-158` catches **everything** and converts it to `verdict_status=FAIL` plus a recovery round.
- `analysis_service.py:620-640` then surfaces `abstained` — *"the retrieved evidence did not support a grounded response"*.

A revoked `GEMINI_API_KEY`, a 403, or an NVIDIA 429 `RESOURCE_EXHAUSTED` therefore burns up to 3 full recovery rounds against the live API and terminates with a confidently wrong diagnosis. The verifier side is quieter still: `verifier.py:711-717` converts every exception to NEUTRAL, silently deflating the trust score with no error recorded at all.

**Fix:** classify vendor SDK exceptions (`google.api_core.exceptions`, `openai`, `aiohttp`) into `LLMUnavailableError` and let them short-circuit the graph with a terminal `LLM_OUTAGE` diagnosis, mirroring the existing `RetrievalOutageError` fast path at `graph.py:272-296`.

---

## B-6 · HIGH · `probe_cloud_llm` is a billed call on every analysis and hides the real error (EVIDENCE)

`analysis_service.py:286-289` calls it unconditionally for every cloud-backed analysis. `local_llm.py:869-881` constructs a client and issues a real `"Reply with the word OK."` completion with an 8-token cap — one billed request per analysis, on top of the ~4–6 pipeline calls.

Worse, `local_llm.py:892-896` catches **every** exception and raises a generic `"is not reachable"` 503. A 401, 403, or quota-exceeded is reported as unreachability. Line 893 logs the warning **without the exception**, so the true cause never reaches the log at all. It also probes only the analysis model, never the verification model.

**Fix:**
1. `logger.warning(..., exc_info=True)` so the cause is recorded.
2. Branch on status: 401/403 → `ConfigurationError`; 429 → 429 with `Retry-After`; 5xx/timeout → 503.
3. Cache probe success per `(provider, model)` for ~60 s so a burst of analyses pays one probe.
4. Probe the verification model as well.

---

## B-7 · HIGH · Cloud context compression is ON by default and silently doubles generation cost (EVIDENCE)

`config/models.yaml:251-252`:
```yaml
context_compression_enabled: true
context_compression_provider: "cloud"
```

`generator.py:679-699` then makes an **extra full LLM call per generation round** using the *same expensive cloud model*. Two further defects compound it:
- The compression output cap is the *target* size (`generator.py:316` passes `max_tokens=target_tokens`), so the summary is routinely truncated mid-sentence.
- `generator.py:353-355` swallows any failure and silently returns the original context — you pay twice and sometimes get a degraded summary.

With `max_chars=3000` in `format_context_with_chunk_indices` (`generator.py:567`), compression only fires above ~1000 tokens: a narrow band where it costs the most and helps least.

**Fix:** default `context_compression_provider: "off"`; skip when the formatted context is already within budget; give the compression call its own headroom; never fail silently. Also note `nim` is skipped entirely by the hardcoded provider tuple at `generator.py:679-690` despite being an accepted alias.

---

## B-8 · MEDIUM · Route-level test gaps (was 22 of 46 endpoints; now 20)

`app/api/v1/` contains exactly **46** route decorators (author-verified by counting `@router.<method>` across the 12 routers), plus `/metrics` in `app/main.py`. **22 of the 46** had no route-level test at the time of the audit; 2 of the heaviest are now covered (see RESOLVED below), leaving **20**. Full inventory in Part 5.2. The two heaviest untested paths are `POST /knowledge-bases/{id}/documents` (`knowledge_bases.py:157-228`, 72 statements — the primary user-facing write path, including **all** of the 413/415/422 branches) and `POST /knowledge-bases/{id}/documents/from-url` (`knowledge_bases.py:264-359`, the SSRF-guarded ingest path).

Also untested: the four read endpoints the workbench calls on every finalize (`/analyses/{id}`, `/claims`, `/evidence`, `/trace`, `/detail` at `analyses.py:110-165`) — including `/trace`, which is the polling fallback when SSE drops.

**RESOLVED (upload + URL-ingest).** `apps/api/tests/test_kb_upload.py` (15 tests) now covers both heavy handlers: 201 happy paths asserting the document record is written *and* the chunker is invoked (a missing background task is the silent "stored but never searchable" failure); content-hash stability for de-duplication; path-traversal and NUL stripping in the client-supplied filename; the 415 unsupported-extension branch; the 413 streaming size guard; cross-tenant (403) and missing-KB (404) refusals via the real `kb_service.get_kb` ownership check; the full SSRF matrix (`127.0.0.1`, `169.254.169.254` cloud metadata, `file://`, `[::1]`); fetch-failure reporting; and the remote-oversize cap. All 15 pass.

**Remaining:** the five `/analyses/{id}` read endpoints (`analyses.py:110-165`), including `/trace`.

---

## B-9 · MEDIUM · E2E suite passes while generation is completely broken (VERIFIED)

`apps/web/e2e/auth.spec.js` contains 2 tests, both auth. Its own docstring (lines 11-12) states *"no LLM, embedding, or Qdrant collection is required."* CI starts the backend with `AI_PROVIDER=ollama` but **never starts an Ollama service** (`.github/workflows/ci.yml`, e2e job) — and the suite passes anyway.

The reason is that it only ever touches:
- `GET /api/v1/health` → `health.py:43`, a **static liveness check** that never touches the LLM, Qdrant, or the graph;
- a static `<h1>` heading on the dashboard.

There is no `POST /analyses`, no upload, no KB selection, no wait for `verdict_status`, and no assertion on `answer`, `claims`, or `reliability_score`.

**Therefore: you could delete `generator.py`, `retriever.py`, or the entire LangGraph and both Playwright tests plus the k6 smoke would still pass.** Nothing in CI exercises generation. The only real guard is `scripts/run_baseline_eval.py` against a live LLM — and that is **not wired into CI** (no match in `ci.yml`); its six output files in `docs/evaluation/results/` are from manual runs on 2026-09-19.

---

## B-10 · MEDIUM · No API contract test exists (VERIFIED)

There is no reference to `openapi` anywhere in `apps/api/tests/`. Renaming or removing any field in `AnalysisResponse`, `KBResponse`, `ClaimResponse`, `EvidenceResponse`, or the `{code, message}` error envelope would pass CI silently. `schemas/analysis.py` and `schemas/kb.py` report 98%/100% only because they are pure `BaseModel` declarations with no behavioural code.

---

## B-11 · MEDIUM · `app/main.py` lifespan is entirely untested (VERIFIED, 0% for `79-259`)

`app/main.py` is at 50% coverage with the **entire** startup path uncovered: settings validation, ONNX preflight, database connect, index creation, and every exception handler (`main.py:298-414`). No test ever runs startup. A missing `JWT_SECRET` or a failed index creation would not be caught by any test.

**RESOLVED (lifespan).** `apps/api/tests/test_lifespan.py` (5 tests) drives the real `lifespan` context manager with only the heavy externals stubbed, and asserts the decisions that matter: startup completes and yields (the server actually served); `connect_db` precedes `create_indexes`; all three shutdown steps (LLM pool close, client-instance close, DB disconnect) run; a missing ONNX embedding-weight file produces an **error** log naming bootstrap (not a warning — every query 500s without it); `HF_TOKEN`/`HUGGING_FACE_HUB_TOKEN` are exported to the child-process environment; `LANGCHAIN_TRACING_V2` is forced off for strict offline operation; and a `get_settings` failure is reported as the first-run `.env` trap rather than surfacing as a bare pydantic error. All 5 pass; `app/main.py` rose from 50% to **78%**.

**Remaining:** the exception handlers (`main.py:298-414`).

---

## B-12 · MEDIUM · `execute_agentic_rag_flow` and `build_agent_graph` are 100% untested (VERIFIED)

`app/agent/graph.py:1351-1454` (the module's public entrypoint, ~115 statements) and `graph.py:1309-1334` (graph topology) have zero coverage. `test_agent.py:11-18` already imports and patches everything needed, so this is a **choice, not a structural constraint** — the tests are a copy-paste from `test_agent.py:66-88` away.

Consequence: a mis-wired edge (e.g. recovery looping into retrieval when it should terminate) is invisible to the entire suite.

---

## B-13 · MEDIUM · Cloud `nvidia_base_url` is dead config, blocking self-hosted endpoints (EVIDENCE)

`config.py:208-212` defines `settings.nvidia_base_url`, but `_create_llm` never passes `base_url` to `ChatNVIDIA` (`model_registry.py:233-241`). It only works because `load_dotenv` (`config.py:40-41`) exports `NVIDIA_BASE_URL` into the process environment, where `langchain_nvidia_ai_endpoints` reads it. Any other configuration path — a Kubernetes secret mounted as a file, a programmatic override — is silently ignored. There is also no TLS-verification escape hatch for a self-hosted gateway.

**This directly blocks the "any OpenAI-compatible cloud endpoint" goal.**

**Fix:** pass `base_url=settings.nvidia_base_url` explicitly, and add a general `openai_compatible` provider that accepts an arbitrary base URL.

---

## B-14 · MEDIUM · Hardcoded cloud context windows are inert and produce false warnings (EVIDENCE)

`generator.py:131-137` hardcodes `gemini: 1000000`, `nvidia: 128000`. The values are consumed **only** for local `num_ctx` (`generator.py:45-55` excludes cloud) and for logging — they never clamp a cloud prompt. Worse, the dict has no `google_genai` or `nim` key, both of which are accepted provider aliases (`schemas/analysis.py:55-57`), so those fall through to `cfg.local_llm_num_ctx` (4096) and log a spurious *"Context overflows provider window; evidence will be truncated"*.

**Fix:** move the window into `models.yaml` per model id, key by normalized provider alias, and drop the warning for providers where the value is unused.

---

## B-15 · MEDIUM · Cloud allowlist has a hole when `llm_model` is omitted (EVIDENCE)

`schemas/analysis.py:100-106`: when the caller omits `llm_model` and there is no operator override, `requested_llm_model` is `None` and **no allowlist check runs at all** (lines 100-104 explicitly exclude cloud providers). The cross-provider case *is* correctly blocked (provider=nvidia + `gemini-3.8-flash` → 422). But `config.py:531-535` lets `GEMINI_VERIFICATION_MODEL` set an arbitrary model id that `verification_model_for` uses verbatim with **no allowlist check anywhere**.

**Fix:** validate the *resolved effective* model against `cfg.supported_*_models`, and apply the allowlist to the resolved verification model too.

**RESOLVED (both halves).** `apps/api/app/core/config.py` gained a canonical `normalize_provider()` plus a `SUPPORTED_LLM_PROVIDERS` set, so aliases (`nim`, `google_genai`, `llamacpp`, …) resolve consistently. `AnalysisCreate` now validates the **effective resolved model** even when the request omits `llm_model`, and the same allowlist is applied to the resolved **verification** model — the verifier runs its own billed, long-timeout calls, and nothing previously constrained which cloud model those calls could target, so a drifted verification model could bill a model the generation allowlist already forbids. Local providers are deliberately exempt (a local server can only serve on-disk weights), and an explicit `GEMINI_VERIFICATION_MODEL` / `VERIFICATION_MODEL` env override is honoured as an operator decision, matching the existing `settings.<provider>_model` trust level. `analysis_service.py` persists the **canonical** provider name. Covered by normalization / effective-model / verification-allowlist / env-override / cross-provider tests in `tests/test_wave2_cloud_resilience.py` (57 pass in that file).

**Remaining:** `app/services/analysis_service.py` is still the lowest-covered service at **40%**.

---

## B-16 · MEDIUM · Cloud clients are closed mid-request by the RAM-based LRU (EVIDENCE)

`model_registry.py:118-153` bounds the registry to 1/2/4 instances based on `psutil.virtual_memory()`, and `_schedule_close` (`model_registry.py:292-302`) fires `aclose()` on eviction — potentially on a client with an in-flight, **paid** cloud HTTP request. RAM-based sizing is meaningless for cloud, where the connection is cheap.

**Fix:** exempt cloud providers from the eviction/close path, or set `max_instances = 4` (never close) for gemini/nvidia.

---

## B-17 · MEDIUM · API keys can reach the logs via client-construction exceptions (EVIDENCE)

`model_registry.py:233-241` (ChatNVIDIA) and `252-260` (ChatGoogleGenerativeAI) are unguarded. If pydantic validation fails on the client, `str(exc)` includes `input_value=` — the API key. That string flows to `graph.py:140` (`logger.error(..., error=str(exc), exc_info=True)`).

The structlog scrubber at `app/core/logging.py:20-40` matches on **key names only**, so a credential embedded in a *value* is never redacted. `main.py:370-395` correctly keeps raw traces off the wire, so this is a **log-side** exposure, not an HTTP one.

**Fix:** wrap client construction in `try/except` → `ConfigurationError("...invalid credentials...")`; add a value-level scrubber for `AIza[0-9A-Za-z_-]{35}` and `nvapi-[A-Za-z0-9_-]+`.

---

## B-18 · LOW/MEDIUM · Provider asymmetries that silently change behaviour (EVIDENCE)

- `model_registry.py:233-241`: `ChatNVIDIA` receives **no `top_p`** — sampling silently differs from the local path (`model_registry.py:193/205/219`).
- `local_llm.py:358,879` and `generator.py:59` pass `max_tokens` to `ChatNVIDIA`, which emits a `DeprecationWarning` per call; the field is `max_completion_tokens`.
- **VERIFIED:** `ChatNVIDIA` has **no `max_retries` field at all**, so NVIDIA relies solely on the app's own retries while Gemini gets both langchain's and the app's — a double-retry path on the more expensive provider.
- `analysis.py:55-57` normalizes the provider alias for the allowlist, but `analysis_service.py:259` persists the **un-normalized** value, so downstream provider switches see two spellings.
- `local_llm.py:843,881`: `asyncio.wait_for(..., 60)` cancels an HTTP request Gemini may already be generating — **cancelled requests are not free**.

**RESOLVED (4 of 5 sub-items).** Fixed: (1) NVIDIA now receives the configured `top_p`, matching the local path; (2) NVIDIA generation **and** verification now use `max_completion_tokens` instead of the deprecated `max_tokens` (Gemini and local keep their own correct names); (3) the canonical provider is persisted, so downstream sees one spelling; (4) the per-call NLI timeout in `verifier.py` is now **provider-aware** — local keeps the 90s guard that defends against a hung local socket, while cloud defers to the configured `llm.timeout_seconds` (180s). The 90s cap existed to stop a dead local server from eating the whole verification budget; applying it to a billed cloud request cancelled generation the provider had already started, and a cancelled Gemini/NVIDIA request is still billed. The floor is one-directional: a misconfigured short cloud timeout can never shorten the local guard. Regression tests cover the token-parameter names per provider, NVIDIA `top_p` propagation, the cloud/long and local/short timeout selection, and the floor.

**Remaining:** `ChatNVIDIA` still has **no `max_retries` field**, so NVIDIA has no langchain-level retry while Gemini gets both langchain's and the app's — a double-retry path on the more expensive provider. Left open deliberately: adding retries to NVIDIA without also capping Gemini would *increase* spend.

---

## B-19 · LOW · Two tests are tautological (VERIFIED)

1. `tests/test_search_mcp.py:126-133` patches `app.mcp.client.handle_tool_call` — the *only* callee of `execute_mcp_tool` (`client.py:30`). It asserts only that a hardcoded JSON string parses. The real call passes `_internal=True`; the mock accepts any signature, so a broken internal-auth path would still pass. It would also pass if `execute_mcp_tool` were `return json.loads(handle_tool_call(...))` regardless of arguments. `client.py:38-43` is uncovered, confirming the dispatch is untested.
2. `tests/test_agent.py:534-540` asserts `"Internal Revenue Service" not in inspect.getsource(recovery_node)` — a lint on source text, not behaviour.

A further ~28 tests are shape-only (e.g. `test_hardware.py:22-25` `assert dev in ("cuda","mps","cpu")` would pass if the function always returned `"cpu"`; `test_hardware.py:85-96` would pass with `trim_memory(): return None`). Full list in Part 5.4.

---

# Part 2 — RAM optimization

Ordered by value. B-1 is the only one that is both large and certain.

| # | Action | Saving | Confidence | Effort |
|---|---|---|---|---|
| RAM-1 | **Remove the Torch import from `detect_hardware_profile()`** (B-1) | **~177 MB** | **VERIFIED, measured** | S |
| RAM-2 | Exempt cloud providers from LRU eviction/close (B-16) | avoids peak duplication; prevents mid-request churn | EVIDENCE | S |
| RAM-3 | `onnx_embeddings.py` (20% coverage) — verify session is single-instance and inputs are freed per batch | unknown, likely 50–150 MB at peak | NEEDS-RUNTIME | M |
| RAM-4 | `onnx_reranker.py` — cap `max_length`/batch on cross-encoder path (`retrieval/reranker.py:246-256`) | 20–80 MB peak | EVIDENCE | S |
| RAM-5 | `semantic_cache.py` — bound the in-memory similarity scan (`94-120`) and enforce TTL pruning (`275-293`) | scales with cache size | EVIDENCE | S |
| RAM-6 | `disk_cache.py` — verify LRU eviction (`181-210`) is actually running; no test covers it | unbounded growth | EVIDENCE | S |
| RAM-7 | `pipeline.py:202-214, 297-303` — background `index_parsed_chunks` embeds without the tier batch cap applied on the async path | peak during ingest | EVIDENCE | M |
| RAM-8 | `analysis_service.py:744-1041` — trim between finalize/aggregation stages | peak during finalize | EVIDENCE | M |

**Do not attempt RAM-3 … RAM-8 blind.** RAM-1 is measured and free. The rest need a profile on a real host first — the highest-value next step is a `tracemalloc` / `psutil` peak-RSS trace across one ingest and one analysis, captured on the target hardware tier.

**Structural note:** `get_ingest_embed_batch_size()` exists solely to size batches by RAM tier (`hardware.py:197-212`). That is the right idea, but it is currently the *only* consumer of the hardware profile on the ingest path, and it is what drags Torch in. Fixing B-1 by making the probe Torch-free preserves the tier logic and its memory benefit — do not simply delete the batch-size function.

---

# Part 3 — Local model accessibility

The project must work efficiently with local models of **arbitrary parameter size**, from sub-1B to 70B+, quantized or not, on CPU-only and accelerated hosts.

## 3.1 Blocking / high-value

| ID | Sev | Location | Finding |
|---|---|---|---|
| L-1 | HIGH | `hardware.py:270-288` | **The same 3B model is recommended for every RAM tier.** `lean_cpu`, `standard_cpu`, and `high_performance` all return `ibm-granite/granite-4.2-3b-GGUF:Q4_K_M`. The tier system varies `max_batch_size` and `max_concurrency` but never the model. An 8 GB host and a 64 GB host get identical advice, so a user with headroom is needlessly served a 3B model. The tier ladder should map to genuinely different model sizes. |
| L-2 | HIGH | `config/models.yaml:257+` | **`local_llm.num_ctx: 4096` is a single global constant** conflated across four concerns: server launch flags, provider request options, tier selection, and the dynamic context calculation. A 128K-context model is launched at 4096; a small model that cannot hold 4096 is launched anyway. Context window must be per-model-id, probed from the server, and validated. |
| L-3 | HIGH | `local_llm.py` | **Context-window validation is absent.** Nothing verifies the model's real `n_ctx` before sending a prompt. Combined with L-2, a request that exceeds the true window is silently truncated by the server. |
| L-4 | HIGH | `generator.py:131-137` | Cloud and local share one hardcoded context dict; the local branch is the only consumer, and the values are not model-specific. |
| L-5 | MEDIUM | `local_llm.py:622-707, 861-894` | **Streaming (`chat_stream`) and `chat()` are untested** (61% module coverage). These are the two functions every local generation goes through. |
| L-6 | MEDIUM | `local_llm.py:1014-1050` | **MLX path is untested** and macOS-only, so CI never exercises it. MLX is a primary local backend on Apple Silicon. |
| L-7 | MEDIUM | `local_llm.py` | **llama.cpp launch flags** are derived from total RAM only (`hardware.py:100-104`: `-c 4096/-np 1`, `-c 8192/-np 2`, `-c 16384/-np 4`) with no model-size or quantisation awareness. A 70B Q4 model needs far more `-c` headroom and a smaller `-np` than a 3B. |
| L-8 | MEDIUM | `local_llm.py` | **Ollama request options are not model-aware.** `num_ctx`/`num_predict` are not read back from the running model, so a user who set `OLLAMA_CONTEXT_LENGTH` differently from the config gets the config's value. |
| L-9 | MEDIUM | `local_llm.py:843,881` | **Timeouts are fixed, not adaptive.** `asyncio.wait_for(..., 60)` will kill a legitimately slow 70B CPU generation on first token, then again on a long completion. Local inference latency scales with model size; the timeout must too. |
| L-10 | MEDIUM | `local_llm.py` | **Provider discovery does not report model context or quantisation**, so the frontend/API cannot tell the user what was actually loaded. |
| L-11 | LOW | `local_llm.py` | Stop-token handling differs across the three local providers and is untested for all three. |
| L-12 | LOW | `model_registry.py:118-153` | LRU sizing by RAM is reasonable for local but the *close* path (`_schedule_close`) can evict a model that is about to be reused, paying a full reload. |

## 3.2 Local-model acceptance criteria

A local backend should be considered "working" only if all of these hold. Use these as the black-box tests in Part 5.

1. Given a served model id, the effective context window is **read from the server**, not assumed from config.
2. `num_ctx` sent to the server equals the probed window.
3. A prompt longer than the window is **rejected or explicitly truncated with a visible signal** — never silently mangled.
4. Recommended model in `/models/hardware` **differs across RAM tiers**.
5. llama.cpp launch flags scale with **model size and quantisation**, not RAM alone.
6. Timeouts scale with model size; a slow-but-progressing generation is not killed.
7. Streaming works identically for Ollama, llama.cpp, and MLX.
8. Switching providers mid-process does not leak the previous model (RAM-2).

---

# Part 4 — Cloud model accessibility

The project must work with Gemini, NVIDIA NIM, and any OpenAI-compatible cloud endpoint.

## 4.1 Blocking / high-value

| ID | Sev | Location | Finding |
|---|---|---|---|
| C-1 | HIGH | `local_llm.py:359-361` | Cloud verification output cap is never applied → 512-token truncation → 3 billed calls instead of 1. (B-2) |
| C-2 | HIGH | `verifier.py:81` | `with_structured_output(**cap)` → `ValueError` for any reasoning-classified Gemini model. Latent landmine. (B-3) |
| C-3 | HIGH | `graph.py:139-158` | Dead key / exhausted quota → 3 recovery rounds → false "insufficient evidence" abstention. (B-5) |
| C-4 | HIGH | `local_llm.py:892-896` | `probe_cloud_llm` swallows all errors, logs without the exception, and bills a call per analysis. (B-6) |
| C-5 | HIGH | `models.yaml:214,218` | No working cloud spend guard; `max_input_tokens` is dead code. (B-4) |
| C-6 | HIGH | `models.yaml:251-252` | Cloud context compression on by default → silent 2× generation cost. (B-7) |
| C-7 | MEDIUM | `config.py:208-212` | `nvidia_base_url` is dead config — **blocks self-hosted / OpenAI-compatible endpoints**. (B-13) |
| C-8 | MEDIUM | `schemas/analysis.py:100-106` | Allowlist is skipped when `llm_model` is omitted; verification model is never allowlisted. (B-15) |
| C-9 | MEDIUM | `models.yaml:77,111` + `graph.py` | **Worst-case wall time ≈ 36 minutes.** 3 rounds × 4 nodes × 180 s `wait_for`. No total-analysis deadline. `asyncio.wait_for` on the graph entrypoint would fix this. |
| C-10 | MEDIUM | `local_llm.py:1108-1121` | Explicit batch-NLI retry **compounds** langchain's own `max_retries: 1` on Gemini — double retry on the expensive provider. |
| C-11 | MEDIUM | `analysis_service.py:497-513` | **SSE dies at 360 ticks** (`while no_event_ticks < 360`, 1 s ticks) and heartbeats do **not** reset the counter. On cloud, a node legitimately runs 180 s with no events, so the stream closes mid-run and the UI silently falls back to polling. Reset on heartbeat, or drive termination off an absolute deadline. |
| C-12 | MEDIUM | `model_registry.py:233-241` | No `top_p` for NVIDIA → silent sampling divergence from local. (B-18) |
| C-13 | MEDIUM | `analysis_service.py:286-289` | The 60 s blocking probe happens in `POST`, so the client sees nothing for up to 60 s before the analysis even starts. Move probing into the pipeline behind a trace event. |

## 4.2 Already handled correctly (do not regress)

These were explicitly checked and are sound:

- **No key material in any endpoint, log key-name, or trace event.** `/health`, `/health/detailed`, `/models/providers`, `/metrics`, `registry_status()`, and the export dossier all expose **booleans or counters only**. Keys travel in headers (`x-goog-api-key` / `Authorization: Bearer`), never query strings, so httpx/aiohttp error strings cannot contain them. `model_registry.py:229-230, 246-250` name the *env var*, never the value.
- **Per-provider parameter-name discipline is real and consistent.** `generator.py:35-59` and `local_llm.py:301-361` correctly keep `num_ctx`/`keep_alive`/`max_tokens` away from cloud models.
- **Gemini gets native `json_schema` structured output** (`verifier.py:81`) — genuinely better than the local prompt+regex path.
- **Cross-provider model/allowlist mismatch is rejected** (`analysis.py:105-106`), sourced from `models.yaml` via `config.py:553-567` — no hardcoded ids in code.
- **Cloud allowlists are narrow** (3 NVIDIA, 7 Gemini) — good blast-radius control.
- **Raw SDK exceptions never reach the client.** `main.py:277-395` returns fixed bodies for every handler.
- **Correct status codes:** `LLMUnavailableError` → 503, `ConfigurationError` → 503.
- **`strip_think_blocks` / `extract_final_answer` / `strip_invalid_citations`** (`generator.py:369-485`) keep reasoning traces and hallucinated `[Segment N]` refs out of NLI input on cloud reasoning models.
- **Rate limiting, query cap, bounded claims/retrieval/fallback budgets, and the futile-regeneration guard** (`graph.py:683-697`) apply equally to cloud.

## 4.3 Cloud-model acceptance criteria

1. A 429/401/403 terminates the analysis with a named diagnosis (`LLM_OUTAGE`), never as `abstained`.
2. Cloud verification uses **one** fused call, not three.
3. A burst of N analyses pays **one** connectivity probe, not N.
4. Total analysis wall time has a hard deadline; the SSE stream cannot expire before the terminal event.
5. Total billed calls per analysis is counted and capped; exceeding the cap aborts with a clear reason.
6. `nvidia_base_url` (and a generic OpenAI-compatible base URL) is honoured from any configuration source.
7. The effective cloud model — including the verification model — is allowlist-validated.
8. No credential value ever appears in a log line, including inside an exception string.

---

# Part 5 — Test coverage

Baseline: **431 passed, 70% coverage, 0 skipped.** The suite is *not* a smoke test — roughly 30 of 431 tests are weak and 2 are tautological, but the core RAG logic (graph nodes, retrieval, generation, verification, router) is genuinely well-tested at unit level. The real problems are (a) the top-level entrypoint and startup path have zero coverage, (b) the two heaviest write endpoints have zero coverage, and (c) nothing in CI exercises generation end to end.

## 5.1 Coverage — worst offenders

| File | % | Worst uncovered areas |
|---|---|---|
| `core/onnx_embeddings.py` | **20%** | `40-48, 68-97, 101-129, 133-153, 170-275` — the entire ONNX session/embed/tokenize path. Only the engine *name* is asserted. |
| `core/llm_utils.py` | **20%** | `36-71, 98-166` — token budgeting / context trimming. |
| `db/mongodb.py` | **29%** | `82-158, 207-447` — connection lifecycle, index creation, and every real query helper. All tests inject `MagicMock()` collections, so the real Mongo query code never runs. |
| `core/experimentation.py` | **33%** | `52-74, 162-195, 208-289, 358-454` — flag evaluation, assignment, exposure logging. |
| `core/logging.py` | **35%** | `49-98` — the whole structlog config. |
| `core/onnx_reranker.py` | **39%** | `110-158, 188-265` — ONNX cross-encoder scoring. |
| `services/analysis_service.py` | **39%** | `381-443, 455-517, 578-667, 744-1041` — finalize, aggregation, claim/evidence reads. |
| `api/v1/knowledge_bases.py` | **43%** | `157-228, 264-359` — the entire upload and URL-ingest handler bodies. |
| `main.py` | **50%** | `79-259` — the **entire lifespan**. Plus every exception handler `298-414`. |
| `api/deps.py` | **54%** | `73-105, 127-133` — `get_current_user`; every test overrides this dependency. |
| `api/v1/internal.py` | **64%** | `118-151, 217-233, 258-268` — ingest/verify/claim handler bodies. |
| `mcp/server.py` | **64%** | `378-414` — the entire stdio JSON-RPC loop. |
| `core/hardware.py` | **60%** | `68-89, 156-182, 251-288` — accelerator probe, GPU launch args, recommendations. |
| `core/local_llm.py` | **61%** | `622-707, 861-894, 1014-1050` — streaming, `chat()`, MLX. |
| `agent/graph.py` | **68%** | `1312-1334, 1351-1454` — `build_agent_graph` and `execute_agentic_rag_flow`, both fully untested. |
| `core/model_registry.py` | **69%** | `226-273, 546-564, 610-630` — `get_llm`, ONNX embedding load. |

## 5.2 BLACKBOX gaps — 22 of 46 endpoints have no route-level test

| Endpoint | Tested? | What to add |
|---|---|---|
| `GET /analyses/{id}` | ❌ | 200 shape + 404 cross-user |
| `GET /analyses/{id}/claims` | ❌ | 200 + 404 |
| `GET /analyses/{id}/evidence` | ❌ | 200 + 404 |
| `GET /analyses/{id}/trace` | ❌ | 200 — **this is the SSE polling fallback** |
| `GET /analyses/{id}/detail` | ❌ | 200 — the single-round-trip finalize payload the UI uses on every run |
| `GET /claims` | ❌ | 200 + 404 |
| `GET /conflicts` | ❌ | 200 + 404 |
| `GET /documents/{id}` | ❌ | 200 + 404 |
| `GET /evidence` | ❌ | 200 + 404 |
| `DELETE /knowledge-bases/{id}` | ❌ | 204 + 403 + 404 |
| `GET /knowledge-bases/{id}/documents` | ❌ | 200 + 404 |
| `POST /knowledge-bases/{id}/documents` | ❌ | **201 + 400/415 bad extension + 413 oversize + 404 cross-user + assert `background_tasks.add_task(index_parsed_chunks, ...)` fired** |
| `POST /knowledge-bases/{id}/documents/from-url` | ❌ | **400 SSRF rejection + 201 + 404** |
| `GET /experimentation/flags` | ❌ | 200 |
| `GET /models/hardware` | ❌ | 200 + tier assertions (see L-1) |
| `POST /models/memory/trim` | ❌ | 200 |
| `POST /internal/tokens` | ❌ | 201 + 4xx |
| `POST /internal/ingest/document` | ❌ body | 201 + 4xx |
| `POST /internal/search` | ❌ | 200 |
| `POST /internal/verify/claims` | ❌ | 200 + 4xx |
| `GET /internal/health` | ❌ | 200 |
| `GET /internal/status` | ❌ | 200 |

The remaining 24 are covered at route level. `POST /internal/ingest/url` is a partial: the handler is exercised only by a direct function call in `test_upgrade_phases.py`, never through the route.

**Untested error paths:**
- **4xx:** no test asserts 404 for *any* of the read endpoints above.
- **413/415/422 on upload:** zero coverage of file-size, extension-allowlist, and empty-file branches.
- **5xx:** no test asserts that the `main.py` exception handlers return the documented `{"code","message"}` envelope. `core/exceptions.py` shows 100% only because it is class definitions.

## 5.3 WHITEBOX gaps — untested branch → concrete test to add

| Module | Untested branch | Recommended test |
|---|---|---|
| `agent/graph.py:1309-1334` | graph topology | `test_build_agent_graph_has_expected_nodes_and_edges` — assert node set == {retrieval, generation, verification, recovery} and that `should_recover` is the conditional edge |
| `agent/graph.py:1340-1454` | **public entrypoint, 100% untested** | `test_execute_agentic_rag_flow_registers_analysis_and_returns_terminal_state`; `..._persists_trace_events`; `..._bubbles_node_error_as_failed_analysis` |
| `agent/graph.py:444-460` | empty-KB short-circuit | `test_retrieval_node_empty_kb_short_circuits_without_rerank` |
| `agent/graph.py:176-226` | regenerate reuse + `re_retrieve` widening | `test_retrieval_node_re_retrieve_doubles_top_k_when_evidence_thin`; `..._skips_widening_when_chunks_sufficient` |
| `agent/graph.py:500-515` | MCP web-search grounding | `test_retrieval_node_web_search_failure_does_not_abort_retrieval` |
| `verification/verifier.py:84-92` | timeout → node error | `test_verification_timeout_records_node_error_and_forces_regenerate` |
| `verification/verifier.py:1027-1032, 1207-1256` | NLI provider exception → NEUTRAL | `test_nli_provider_error_degrades_claims_to_neutral` |
| `core/local_llm.py:622-707, 861-894` | streaming + `chat()` | `test_ollama_stream_yields_incremental_deltas`; `test_llamacpp_chat_returns_content` |
| `core/local_llm.py:1014-1050` | MLX provider | `test_mlx_chat_uses_mlx_generate` |
| `core/model_registry.py:226-273` | unknown provider | `test_get_llm_raises_actionable_error_for_unknown_provider` |
| `core/model_registry.py:546-564, 610-630` | ONNX load + dim mismatch | `test_get_embedding_model_raises_on_dim_mismatch` |
| `core/semantic_cache.py:94-120` | similarity scan + threshold edge | `test_check_semantic_cache_below_threshold_returns_none`; `..._ignores_zero_vector_entries` |
| `core/semantic_cache.py:275-293` | TTL / prune | `test_expired_entry_is_not_returned` |
| `core/hardware.py:68-89` | accelerator probe | `test_detect_accelerator_reports_none_on_cpu_only_host` — **and assert `torch` is not in `sys.modules` after calling `detect_hardware_profile()`** (regression test for B-1) |
| `core/hardware.py:156-182` | GPU launch args (CI is Linux CPU, so only the CPU branch is covered) | `test_llamacpp_gpu_args_include_nlayers_and_split_mode` |
| `retrieval/reranker.py:246-256` | cross-encoder path | `test_rerank_uses_cross_encoder_when_enabled` |
| `retrieval/retriever.py:163-184` | RRF with one leg dead | `test_rrf_fusion_with_only_dense_leg_preserves_order` |
| `ingestion/pipeline.py:202-214, 297-303` | background `index_parsed_chunks` | `test_index_parsed_chunks_embeds_dense_and_sparse` |
| `ingestion/preprocessor.py:448-552` | ~30 lexical/n-gram branches | `test_lexical_analyze_handles_punctuation_only_and_emoji_tokens` |
| `services/search_service.py:147-199` | result normalization/merge | `test_normalize_drops_results_without_url_or_content` |
| `mcp/server.py:373` | unknown tool | `test_handle_tool_call_rejects_unknown_tool_name` |
| `mcp/server.py:378-414` | stdio JSON-RPC loop | `test_stdio_server_answers_tools_list_and_tools_call` |
| `api/deps.py:73-105` | real `get_current_user` (always overridden) | `test_get_current_user_raises_401_without_token`; `..._for_inactive_user` |
| `main.py:79-259` | lifespan | `test_lifespan_creates_indexes_and_validates_config`; `test_lifespan_fails_fast_without_jwt_secret` |

## 5.4 Tests that lie (assert shape, not behaviour)

**Tautological:**
1. `test_search_mcp.py:126-133` — patches the sole callee of the function under test. (B-19)
2. `test_agent.py:534-540` — asserts on `inspect.getsource()` text, not behaviour.

**Weak — would pass against a gutted implementation:**
3. `test_hardware.py:22-25` — `assert dev in ("cuda","mps","cpu")`; passes if the function always returns `"cpu"`.
4. `test_hardware.py:72-83` — asserts key presence only; a profile of `{"max_concurrency": 1}` for every host passes.
5. `test_hardware.py:85-96` — `trim_memory()` called bare, asserts only that RSS is a float ≥ 0. Passes with `trim_memory(): return None`.
6. `test_disk_cache.py:41`, `test_page_images.py:28,66`, `test_semantic_cache.py:51,59` — `assert x is not None` as the primary assertion.
7. `test_health.py:49-57` — `assert status_code in (401, 403)`; cannot detect an auth-regression code change.
8. `test_analyses.py:353,359` — same `(401, 422)` / `(401, 400)` problem.
9. `test_integrity.py` — real assertions, but a hand-rolled `MagicMock` cursor; switching `find()` to `aggregate()` would break production code and still pass.
10. `test_upgrade_phases.py:345` — `assert sc._MATRIX_CACHE is not None`; holds for a plain-`dict` stub.
11. `test_redteam.py:168,237` — `assert result is not None` inside a red-team suite.

**Genuinely meaningful (would catch real regressions):** `test_agent.py:22-38` (should_recover budget), `:255-270` (refusal gate), `:410-500` (self-heal batching — asserts real `embed_documents.call_count == 2` and `find.assert_called_once()`, i.e. genuine anti-N+1), `:766-800` (outage fast path); `test_router.py:127-160` (fan-out partial outage); `test_generation.py:22-88` (byte-stable context ordering, dedup); `test_retrieval.py:315-372` (outage vs. empty); `test_claim_retrieval.py:135-161`; `test_disk_cache.py:74-99`; `test_analyses.py:341-384` (SSE ticket single-use + ownership). **These ~8 tests carry the suite.**

## 5.5 Frontend — 25 tests / 7 files for 33 components + 13 pages

- **26 of 33 `.jsx` files have no test.**
- **`components/workbench/FormattedAnswer.jsx` (123 lines, uses `ReactMarkdown` + `remarkGfm`) has ZERO tests.** This is the component that renders the actual product output. A broken citation renderer, a dropped marker, or an HTML-passthrough regression ships silently.
- **SSE happy path is untested.** `lib/api.test.js:63-77` covers only `openAnalysisStream` *failure* recovery (valuable). Untested: message parsing, terminal/`done` event, keep-alive/ping handling, `onComplete` firing, event→state mapping, auto-reconnect.
- **`PlaygroundPage.test.jsx` mocks `analysisService: {}`** — the entire submit → poll → render path is untested. No test asserts a query is sent or that results render.
- `components/ErrorBoundary.jsx` — untested, and it is the app's last line of defence.
- All 12 non-Playground pages untested; `App.jsx` route table untested (nothing asserts which routes exist or are guarded).
- No coverage config, no MSW/nock — every test hand-mocks `@/services/api`, so **no frontend test exercises a real request/response shape.** A backend schema change is caught nowhere.

## 5.6 E2E — 2 auth tests only

See **B-9**. Proof that it passes while generation is broken: the suite touches only `GET /health` (static) and a static dashboard heading. Delete `generator.py`, `retriever.py`, or the whole graph and it still passes.

**Root cause is missing infrastructure, not missing ambition:** `tests/eval/fixtures/corpus/*.txt` already exists, and the polling/status API already exists. There is simply no Playwright `global-setup` that registers a user, creates a KB, uploads the corpus, and asserts a completed analysis.

## 5.7 Missing test infrastructure

- **`app/agent/graph.py` is fully mockable today.** `test_agent.py:11-18` imports the node functions and patches every dependency. The 68% coverage is **choice, not constraint.**
- **`tests/conftest.py` provides only env defaults and a cache-clearing fixture.** There is **no shared `client` fixture** (each file builds its own `TestClient`), **no `auth_user` fixture** (each file hand-rolls `dependency_overrides`), **no mock-collection factory**, and **no graph/LLM fixture**. This duplication is the main reason route coverage is low.
- **No ONNX / llama-server fixture.** `onnx_embeddings.py` (20%) and `onnx_reranker.py` (39%) are untested because nothing injects a fake `onnxruntime.InferenceSession`. A `monkeypatch` fixture returning a fixed `(1, 384)` array would unlock ~160 statements in ~30 lines.
- **0 skipped / 0 xfail / 0 `skipif` anywhere.** Nothing is gated off. CI *does* require the e2e job — the problem is that e2e does not test generation.

## 5.8 Prioritized test additions (value per hour)

| # | Addition | Est. | Why it pays |
|---|---|---|---|
| 1 | E2E that actually analyses: register → create KB → upload `tests/eval/fixtures/corpus/*.txt` → `POST /analyses` → assert `verdict_status == completed`, non-empty `answer`, `len(claims) > 0`, `0 <= reliability_score <= 1` | 2–3h | **The only test that fails when generation breaks.** Corpus and polling API already exist. |
| 2 | `test_execute_agentic_rag_flow_*` (3 tests over `graph.py:1340-1454`) | 1.5h | 115 uncovered statements on the public entrypoint; mocks already exist. |
| 3 | `test_build_agent_graph_topology` | 15 min | Cheapest coverage-per-hour in the repo; catches a mis-wired edge nothing else can see. |
| 4 | `test_kb_upload.py` — `POST /knowledge-bases/{id}/documents` | 2h | 72 uncovered statements on the primary write path; 413/415/422 all untested. |
| 5 | `test_analyses_finalize.py` — the five read endpoints | 1.5h | Closes 5 endpoints; natural home for a first contract assertion. |
| 6 | `test_contract.py::test_openapi_response_schemas_stable` | 1h | The only thing that catches a response-schema change. |
| 7 | `test_api_auth_deps.py` — real `get_current_user` | 1.5h | Every existing test *bypasses* the auth chokepoint via `dependency_overrides`. |
| 8 | `test_onnx_fakes.py` — fake `InferenceSession` fixture | 3h | Unlocks ~160 statements; would catch a padding/normalisation bug that silently degrades every embedding. |
| 9 | `test_verifier_degradation.py` — timeout + NLI error paths | 1h | Reliability fallbacks are the product's pitch; the failure branches ship untested. |
| 10 | `FormattedAnswer.test.jsx` — GFM table, marker styling, `<script>` not executed, code fence | 1h | The one component that shows the product's output, at 0%. |

**Two free fixes:** delete-or-rewrite `test_search_mcp.py:126-133`; add `client` + `auth_user` fixtures to `conftest.py` so #4/#5/#7 stop re-implementing setup.

---

# Part 6 — Prioritized remediation plan

## Wave 1 — high value, low risk, all verifiable now ✅ COMPLETE

| ID | Action | Why first |
|---|---|---|
| B-1 | Make the hardware probe Torch-free | **177 MB measured.** Contradicts the module's own documented contract. |
| B-2 | Return the per-call output cap for cloud | 3 billed calls → 1 on every cloud verification. |
| B-3 | Bind caps on the model instead of into `with_structured_output` | Removes a latent total-failure landmine. |
| B-6 | Log `exc_info` + branch on status code + cache the probe | Stops per-analysis billing and restores diagnosability. |
| T-10 | `FormattedAnswer.test.jsx` | 1h, closes the product's main renderer at 0%. |
| T-3 | `test_build_agent_graph_topology` | 15 min, catches mis-wiring. |
| B-19 | Fix/delete the two tautological tests | Free integrity. |

## Wave 2 — correctness of the cloud failure story ✅ COMPLETE

| ID | Action |
|---|---|
| B-5 | Map vendor SDK exceptions → `LLMUnavailableError` → terminal `LLM_OUTAGE` diagnosis. |
| B-17 | Guard client construction + add a value-level credential scrubber. |
| B-4 | Real per-analysis LLM call/token ledger; abort on cap. |
| B-16 | Exempt cloud from LRU eviction/close. |

## Wave 3 — local-model portability (not started)

| ID | Action |
|---|---|
| L-1 | Make `/models/hardware` recommend genuinely different models per RAM tier. |
| L-2/L-3 | Per-model context window, probed from the server; validate before sending. |
| L-7 | Model-size/quantisation-aware llama.cpp flags. |
| L-9 | Model-size-aware timeouts. |
| T-8 | Fake-ONNX fixture; T-5/L-5/L-6 tests for the three local providers. |

## Wave 4 — close the structural test gaps

| ID | Action |
|---|---|
| B-9 | Wire the E2E analysis path (the single highest-value test in the repo). |
| T-1,T-2,T-4,T-5 | E2E + `execute_agentic_rag_flow` + upload + finalize-read + contract tests. |
| B-10 | OpenAPI snapshot test. |
| B-11 | Lifespan/startup tests. |
| B-12 | Graph topology tests. |

## Wave 5 — cleanup

B-7 (compression default), B-8/B-14/B-15 (allowlist + context windows), B-13 (`nvidia_base_url` + generic OpenAI-compatible provider), B-12 provider asymmetries (`top_p`, `max_completion_tokens`, alias normalization, adaptive timeouts), plus the ~28 shape-only tests.

**Rounds 2-5.** B-8 upload + URL-ingest (15 tests), B-11 lifespan (5 tests), B-15 effective-model allowlist + canonical provider persistence, B-18 `top_p` + `max_completion_tokens` + **provider-aware NLI timeout** (local 90s guard vs. billed cloud at the configured 180s), and B-15's verification-model allowlist. Three stale `tests/test_local_llm.py` assertions that encoded the pre-B-18 NVIDIA `max_tokens` name were updated to match the intentional change.

**Rounds 3-5.** B-12 (10 tests: graph topology, compiled singleton, initial state, semantic-cache gates, async-embed fallback, ledger teardown). B-11 remainder (24 tests: all 15 exception handlers + request-ID middleware) plus a fix so unhandled 500s echo `X-Request-ID`. B-8 remainder (21 tests: the five `/analyses/{{id}}` read routes and their authorization). T-8 (16 tests: fake-ONNX-session coverage of both engines) plus a fix for the hardcoded 384 empty-batch width. T-2 (strengthened hardware-profile and auth-status assertions).

Every new test was mutation-checked: broken edge map, fail-open verdict default, over-broad cache store, removed ownership check, removed ONNX chunking, ignored reranker `batch_size`, uniform tier batch sizes, decoupled `usage_pct`, zeroed RSS — each was confirmed to fail the intended test.

---

## Appendix — what was verified vs. what needs a live environment

**Verified by the author (source + installed package + measurement):** B-1 (incl. 176.9 MB measurement), B-2, B-3 (mechanism + latency classification), B-4 (pre-request half), B-8 (46 v1 routes counted directly, 22 untested), B-9, B-10, B-11, B-12, B-19, the **431 passed / 70% / 8185 stmts / 2464 missed** baseline (re-run, 33.46s), the absence of skips, `langchain-google-genai` 4.4.0 `ValueError` on unexpected kwargs, `ChatNVIDIA` lacking both `max_retries` and `max_completion_tokens`, and the reasoning-keyword cross-check for all 7 Gemini + 3 NVIDIA ids.

**Verified by execution (fix + regression test, all passing):** B-1 through B-11, B-13, B-14, B-16, B-17, B-19, the **619 passed / 75% / 8543 stmts / 2135 missed** result (re-run, 38.67s), and the frontend **33 passed** in 8 files. The B-8 route tests exercise the real SSRF validator and the real `kb_service` ownership check rather than mocking them; the B-11 tests drive the real `lifespan` context manager.

**Code-evidence only (not re-run):** B-4 recovery half, B-12 (`execute_agentic_rag_flow` — still 100% untested, so its *absence* of a defect is not established), B-18's residual `ChatNVIDIA` `max_retries` gap, C-7 through C-13, and all of Part 3. These follow directly from the cited lines but were not independently reproduced.

**Requires a live environment to confirm:** any timeout/backoff behaviour (needs slow or failing endpoints); actual memory for RAM-3 … RAM-8 (needs a peak-RSS profile on the target hardware tier); MLX behaviour (needs Apple Silicon); real cloud error codes and billing (needs live keys). Do not report these as proven defects without that evidence.
