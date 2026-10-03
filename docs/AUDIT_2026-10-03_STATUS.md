# AUDIT 2026-10-03 — Fix Status (branch `ui-redesign`)

Source of truth: `docs/AUDIT_2026-10-03.md`. Every item below was **verified against
the current code before changing it** — nothing was fixed on the audit's word alone.
"Where it says X, code says Y" is recorded for the items that did not match.

Last verified: backend `697 passed`, coverage `78.9%` (gate 78), ruff clean,
ruff-format clean, mypy ratchet 48/48, frontend `eslint` clean, `vite build` OK.

---

## Phase 1 — CRITICAL (all 27 items)

| # | Finding | Status | Evidence / change |
|---|---|---|---|
| P1-1 | `cfg.flash_attention` → `AttributeError` on every default-provider call | **fixed** | Added `ModelConfig.flash_attention` (`model_config.py`) with `FLASH_ATTENTION` env override. Confirmed first: the property genuinely did not exist. |
| P1-2 | Pipeline + LLM client take the same non-reentrant semaphore → self-deadlock | **fixed** | Removed the pipeline-level `async with sem` in `run_analysis_pipeline` + the now-unused import. Per-call LLM permit is the only gate. |
| P1-3 | ONNX sessions rebuilt per call (no cache anywhere) | **fixed** | `model_registry` now holds lock-guarded singletons for `get_embedding_model()` / `get_reranker()`, keyed on `(model, resolved_path, …)`; `clear_onnx_caches()` for tests. |
| P1-4 | "Hybrid" retrieval was dense-only (`sparse_top_k: 0`) | **fixed** | `sparse_top_k: 20`. RRF is genuinely two-leg now; `_is_high_confidence` reachable. |
| P1-5 | All evidence text stored lowercased → citations not verbatim | **fixed** | `normalize_text` no longer lowercases/expands; that moved to index time in `lexical_analyze`. Stored chunks are verbatim, so SHA-256 now attests source bytes. Also fixes N-7 (HEADER zone was unreachable). |
| P1-6 | Small-model prompt emits `[2]`, extractor only matched `[Segment N]` | **fixed** | `_CITATION_RE = r"\[(?:Segment\s+)?(\d+)\]"`; small prompt example now `[Segment 2]`. |
| P1-7 | `max_analysis_seconds: 120` < one LLM timeout (180) → recovery unreachable | **fixed** | `600`, with a comment explaining it is now ≥ round-1 + one retry. |
| P1-8 | OCR failures ingested as empty pages, reported `completed` | **fixed** | Parser tracks `ocr_attempted/ocr_failed` per page → chunker → document record (`ocr_pages_attempted/failed`) → `ingestion_status: "degraded"` + message. |
| P1-9 | ~750 MB of page PNGs retained for a 500-page scan | **fixed** | Pipeline drops `page_image_png` refs as soon as they are persisted; peak is one page. |
| P1-10 | OCR at 200 DPI (below the accuracy floor) | **fixed** | `dpi: 300`. |
| P1-11 | NLI unsound: attacker text and claim in one `<context>` block | **partially fixed** | (a) NLI prompts split into `<premise>` (untrusted, classify-only) / `<hypothesis>`; the generator prompts use the same framing and the user message fence is now `<premise>`. (b) alias table documented + test-locked as symmetric-by-count, unknown → NEUTRAL. (d) both CONTRADICTED regimes documented at the call site. **(c) the ≥200-pair adversarial eval set is still missing** — it needs a labelled dataset and a measurement, not a patch. |
| P1-12 | `internal_search` had no tenant check → cross-tenant read | **fixed** | Now calls the shared `enforce_service_tenant()`; 403 on binding mismatch. |
| P1-13 | Token mint never set bindings → M-2 guard was a no-op | **fixed** | `generate_service_token_endpoint` accepts `bound_kb_id` / `bound_user_id` and passes them through. |
| P1-14 | 5 cloud-egress paths violate on-prem | **fixed (code)** | `langchain-google-genai` + `tavily-python` moved to a `cloud` extra (the Docker image no longer installs either); LangSmith now needs `TRUSTRAG_TRACING=1` *in addition to* the key; Google Fonts CDN removed from `index.html`; the Cloudflare `og:url` removed. k6 download is checksum-verified. |
| P1-15 | CI `cross-platform` imported 7 non-existent modules → gate permanently red | **fixed** | Paths corrected to `app.rag.*`, `app.llm.*`, `app.core.system.*`, `../../scripts/apply_ports.py`. |
| P1-16 | Named volume shadowed the documented `docker cp` bake | **fixed** | Bind-mount `./apps/api/.model_cache:/app/.model_cache:ro`; the `model_cache` volume is gone. |
| P1-17 | Healthcheck passed while Mongo/Qdrant were down | **fixed** | `GET /api/v1/health/ready` returns 503 when degraded; compose healthcheck targets it. |
| P1-18 | In-flight analyses orphaned forever on restart | **fixed** | Startup reaper in the lifespan marks `processing` → `failed` with a retry message. |
| P1-19 | No rate limiting anywhere; lockout is an account-DoS primitive | **fixed** | `slowapi` + global 60/min, `/auth/register` 3/hour, `/auth/login` 5/min, 429 handler. Lockout is now keyed on `(email, client IP)` and **escalates exponentially**. |
| P1-20 | Upload parsed + chunked before the ownership check | **fixed** | `await kb_service.get_kb(...)` is the first statement in `_ingest_content`. |
| P1-21 | `localStorage` token + no CSP | **partially fixed** | Strict CSP added to `security_headers_middleware`. **Still open:** the token is still in `localStorage`; moving it to a cookie changes the auth flow (CSRF surface) and is a product decision, not a patch. |
| P1-22 | Collapsed sidebar rendered every label as a permanent tooltip | **fixed** | Tooltip gated on `group-hover` / `group-focus-within` + `opacity-0`. |
| P1-23 | Settings fabricated diagnostics when the API failed | **fixed** | `healthUnknown` / `providersError` drive explicit `Unknown` states for system status, both stores, version, arch, engine, LLM and verifier. |
| P1-24 | Hardcoded superlatives that are false regardless of state | **fixed** | `100% Grounded`→`Evidence-linked`; `High Trust` derived (≥75/≥50); `0.0% Hallucination Leakage`→`Abstain-safe`; `0 MB Local GPU Weights (Pure Cloud)`→`0 bytes leave your network`; `Zero Hallucination Leakage`→`Abstain-safe by design`; footer claim removed. |
| P1-25 | a11y blockers on data-critical surfaces | **partially fixed** | Claim expand is a real `<button aria-expanded aria-controls>`; comparison `<tr>` is focusable with Enter/Space; `slate.500/600` remapped in `tailwind.config.js`; `prefers-contrast` remap extended to 600; `aria-live` on trace + badge; 4 search inputs labelled; focus ring consolidated from 3 definitions to 1. **Still open:** modal focus trap / restore (Escape + initial focus + restore are in), ConfirmDialog is new. |
| P1-26 | `get_reranker()` downloaded + exported a PyTorch model inside a request | **fixed** | The block is deleted. The request path is read-only and fails closed to RRF with an actionable log. |
| P1-27 | Collection dimension was a full HTTP round-trip per dense query | **fixed** | Memoized per collection. |

---

## Phase 2 — NEEDED

### Retrieval & RAG
| # | Status | Note |
|---|---|---|
| N-1 | open | `apply_temporal_filtering` still re-reads the document set per retrieval. |
| N-2 | open | `_reference_time_for_query` still maps any year to July 1. |
| N-3 | open | Reranker failure still returns an unranked slice that bypasses `_adaptive_top_k_slice`. |
| N-4 | open | Unscored candidates are still padded with `0.0` and sorted in. |
| N-5 | open | `early_termination_confidence` / `score_gap_threshold` still compared against raw logits. |
| N-6 | open | RRF ties still break on dict insertion order. |
| N-7 | **fixed** | Consequence of P1-5: `normalize_text` no longer lowercases, so zone detection sees real casing. |
| N-8 | open | `is_table_line` still treats >3 spaces as a table row. |
| N-9 | open | `top_k_override` still scales both legs. |

### LLM
| # | Status | Note |
|---|---|---|
| N-10 | open | Local providers still have zero retries; HTTP errors still become `ConfigurationError`. |
| N-11 | open | No circuit breaker. |
| N-12 | open | `add_trace_event` is still awaited without a try/except. |
| N-13 | open | No seed is sent. |
| N-14 | open | `extract_final_answer` still falls back to the raw unscrubbed answer. |
| N-15 | open | `_is_meta_claim` is still a keyword blocklist. |
| N-16 | open | `extract_json_substring` still uses `rfind`. |
| N-17 | open | `cache_type_k/v/flash_attention` still sent in the request body. |

### OCR
N-18 … N-23 all **open**. P1-8/9/10 fixed the *reporting* and *cost* problems; the
accuracy gaps (printability-based scan detection, per-line confidence, language
config, table structure, deskew, injection screening) still need work and are
the right subject for a follow-up pass with real scanned fixtures.

### Verification & verdict
| # | Status | Note |
|---|---|---|
| N-24 | open | Uncalibrated thresholds. |
| N-25 | open | UNCERTAIN is still stored as `completed` with an abstention message. |
| N-26 | open | Targeted claim retrieval is still serial. |
| N-27 | open | The two no-op `if` blocks at `verifier.py:1162` remain. |
| N-28 | **fixed** | `attempt` is now in the evidence dedup key. |

### Backend / API
| # | Status | Note |
|---|---|---|
| N-29 | open | `/api/v1/metrics` is still unauthenticated. |
| N-30 | open | `/health` still does live probes per hit. |
| N-31 | **fixed** | `AuthorizationError` on a foreign KB → `NotFoundError`. |
| N-32 | open | `create_kb_snapshot` is still an N+1 insert loop. |
| N-33 | **fixed** | `count_documents` probe removed; the `analysis_id` fallback is now reached only when the `user_id` query returns nothing, and it is scoped to the caller's analyses. |
| N-34 | **fixed** | Conflicts merge → sort → paginate once instead of paging each source separately. |
| N-35 | **fixed** | `list_kb_documents` takes `limit`/`skip` (cap 500). |
| N-36 | **fixed** | `list_kbs` paginates and logs the 500-row truncation. |
| N-37 | **fixed** | `RequestValidationError` handler returns `loc: msg` — never the submitted value, so the password-echo path is closed while actionable messages survive (a test asserts the real message is still returned). |
| N-38 | **fixed** | Compose sets `QDRANT__SERVICE__API_KEY` and the matching `QDRANT_API_KEY` on both sides. |
| N-39 | **fixed** | `_scrub_sensitive` recurses one level into dict/list values. |
| N-40 | **fixed** | `detail=str(exc)` removed from the ObjectId-parse paths (4 sites). |
| N-41 | **fixed** | `str(exc)[:200]` replaced with a stable `PROVIDER_UNREACHABLE` code; the detail is logged. |
| N-42 | open | CORS `allow_origin_regex` still accepts any subdomain of the preview hosts (dev/staging only). |
| N-43 | **fixed** | `_looks_like_scaffold_echo` now catches the failure modes the marker list missed (all CRAFT fence tokens, prompt section headings, and a phrase repeated to the token cap) and is covered by 9 new tests. |

### Reliability & performance
| # | Status | Note |
|---|---|---|
| N-44 | open | `get_system_memory_info()` still reports host RAM under a cgroup limit. |
| N-45 | open | `_cache_time` still leaks into the profile response. |
| N-46 | **fixed** | Added `{analysis_id, created_at}` on claims + evidence and `{document_id, page}` on chunks. |
| N-47 | **fixed** | Qdrant payload indexes for `document_id`, `knowledge_base_id`, `chunk_index`, `integrity_status`. |
| N-48 | **fixed** | `get_model_config()` and `_load_ports_yaml()` are mtime-cached; live reload preserved. |
| N-49 | **fixed** | Self-heal stamps `self_healed_at` on the KB and skips a repeat heal within an hour. |
| N-50 | **fixed** | SSE subscriber queues bounded at 256, so the overflow path is real. |
| N-51 | **partially fixed** | Stream tickets carry `worker_pid`; a cross-worker consume returns 409 with a retry message instead of a silent 6-minute hang. |
| N-52 | open | `estimate_tokens` is still `len//4`. |
| N-53 | **fixed** | INT8 quantization gated behind `retrieval.quantization.enabled`, default **off**. |
| N-54 | open | CPU work still uses the default executor. |
| N-55 | open | Cancelled `to_thread` work still burns CPU. |
| N-56 | open | Error classification is still substring-based. |
| N-57 | open | Recovery-run insert still sits outside the try. |
| N-58 | open | `max_recovery_tokens` still can't fire. |
| N-59 | open | Web-chunk position bound still assumes list parity. |
| N-60 | open | `except TypeError` around `insert_many` still wrong. |
| N-61 | open | Evidence ids still rely on positional alignment. |
| N-62 | open | Sentence join still collapses newlines. |
| N-63 | **fixed** | `is_cloud = prov == "gemini"`. |
| N-64 | **fixed** | Compose sets `MLX_BASE_URL` to the host's :8090. |
| N-65 | open | ORT provider binding is still implicit. |
| N-66 | open | `is_small_model` is still a name heuristic. |

### Frontend
| # | Status | Note |
|---|---|---|
| N-67 | **fixed** | Model `<select>` has an explicit "No models discovered" option. |
| N-68 | **fixed** | Suspense moved per-route; navigating no longer blanks the shell. |
| N-69 | **fixed** | ResultsPanel is `overflow-visible md:overflow-hidden`. |
| N-70 | **fixed** | Fallback polling reads `traceEventsRef.current`, not a stale closure. |
| N-71 | **fixed** | `clearTimeout` moved to `finally`. |
| N-72 | **partially fixed** | `SimulationSandbox` timers are tracked and cleared on unmount and on re-run. |
| N-73 | **fixed** | One threshold: 75 everywhere (chart line, badge, card copy, status pill). |
| N-74 | **fixed** | Landing benchmark bar widths now match their values. |
| N-75 | **fixed** | Register → login failure routes to `/login?registered=1`; "already registered" says to sign in. |
| N-76 | **fixed** | Health and providers share one query key each; polls are 30 s. |
| N-77 | **fixed** | New `ConfirmDialog` replaces `window.confirm` (KB delete, doc remove, logout). |
| N-78 | **fixed** | Poll intervals 5 s (analyses) / 15 s (claims, conflicts) / 30 s (KBs). |
| N-79 | **fixed** | Trace rows keyed by `event-timestamp`. |
| N-80 | **fixed** | Rank comes from the unfiltered array. |
| N-81 | **fixed** | Shared `normalizeScore()`; a 0–100 response no longer renders 7400%. |
| N-82 | **fixed** | 30 s re-render tick so "Synced x ago" advances. |
| N-83 | **fixed** | Press feedback wrapped in `prefers-reduced-motion: no-preference`. |
| N-84 | **fixed** | `aria-label` on the 4 search inputs. |
| N-85 | **fixed** | Inline `ErrorBoundary` deleted; the component version is used. |
| N-86 | **fixed** | `:focus-visible` defined once. |
| N-87 | **fixed** | `hover:scale-102` → `hover:scale-[1.02]` (3 sites). |
| N-88 | open | Claims/evidence/conflicts are not virtualized. |
| N-89 | **fixed** | `maxLength={2000}`. |
| N-90 | **fixed** | Fake "5s elapsed" progress replaced with a real spinner. |
| N-91 | **fixed** | `axios` split into its own `http-vendor` chunk. |

### DevOps
| # | Status | Note |
|---|---|---|
| N-92 | **fixed** | Same fix as P1-15. |
| N-93 | **fixed** | `--cov-fail-under=78` ratchet. |
| N-94 | **fixed** | mypy now runs in CI via a ratchet that fails only on *new* errors. |
| N-95 | **fixed** | `pip-audit` audits the exported `uv.lock` graph, not `pip freeze`. |
| N-96 | open | `backend-test` still uses `pip install -e ".[dev]"` while Docker uses `uv sync --locked`. |
| N-97 | **fixed** | k6 archive checksum-verified before extraction. |
| N-98 | **partially fixed** | `mem_limit`/`cpus`/`pids_limit`/`no-new-privileges`/log rotation on all three services; `stop_grace_period: 400s` on api. Mongo is still a host service. |
| N-99 | **fixed** | `curl -fsS localhost:6333/readyz`. |
| N-100 | open | `--reload` still in the default compose command. |
| N-101 | **fixed** | `apps/api/.dockerignore`. |
| N-102 | **fixed** | `timeout-minutes` on all jobs; permissions narrowed to `contents: read` except `docker-build`. |
| N-103 | **fixed** | New `compose-smoke` CI job: `docker compose config` + boot + readiness probe. |
| N-104 | **fixed** | `passlib[bcrypt]` removed (nothing imported it; it raises on bcrypt 5). |

---

## Phase 3 — LATER

| # | Status | Note |
|---|---|---|
| L-1 / A-37 | **fixed** | `evidence_budget_chars()` — lean 3000 / balanced 6000 / cloud 12000, derived from `tier_caps`. |
| L-2 / A-38 | **fixed** | `num_ctx_for(model, provider)` with `local_llm.num_ctx_by_model` override; `calculate_dynamic_num_ctx` uses it. |
| L-3 | **fixed** | Small models get the 1024-token floor on verification caps. |
| L-4 | open | Reasoning-model ∩ small-model routing unchanged. |
| L-5 | **fixed** | Fallback ceiling no longer below the claim ceiling (test re-locked). |
| L-6 | **fixed** | `depth_cap` scales with tier instead of always 20. |
| L-7 | **fixed** | Covered by the L-3 floor. |
| L-8 | open | `rrf_k` not swept. |
| L-9 | open | Hash-collision domain still 1M. |
| L-10 | open | `extract_ngrams` still unreachable. |
| L-11 | open | Same as N-24. |
| L-12 | open | `_detect_embedding_dim` still falls back to 384. |
| L-13 | open | Embeddings not defensively normalized. |
| L-14 | open | Redundant double batching in ingestion. |
| L-15 | open | `chunks[:100]` audit bound still silent. |
| L-16 | open | Two unselectable chunking strategies remain. |
| L-17 | open | `sparse_avg_len_tokens` still a guess. |
| L-18 | **removed** | `context_compression_*` keys deleted — no consumer ever existed. |
| L-19 | open | Reranker still not warmed. |
| L-20 | **fixed** | Follows from P1-3: the warmup is no longer discarded. |
| L-21 | **fixed** | `reranker.py` reads `reranker_batch_size_effective`. |
| L-22 | open | `nvidia-smi` still spawned per profile. |
| L-23 | open | No-running-loop path still returns an uncached semaphore. |
| L-24 | **fixed** | Single `q4_0` default. |
| L-25 | open | MCP stdio loop still deprecated. |
| L-26 | open | `trustrag_list_kbs` still unbounded. |
| L-27 | **fixed** | `req_id` initialized before the loop body. |
| L-28 | **fixed** | `LLMUnavailableError` docstring no longer names Gemini. |
| L-29 | **fixed** | Stale "URL-ingest route" docstring removed. |
| L-30 | open | `X-Response-Time` still returned to anonymous callers. |
| L-31 | open | SSE ticket still lands in access logs. |
| L-32 | open | Animated `maxHeight` still used. |
| L-33 | **fixed** | `TabIndicator` re-measures on resize. |
| L-34 | open | Smooth auto-scroll still unconditional. |
| L-35 | open | Memory bar still has no `role="progressbar"`. |
| L-36 | **fixed** | `aria-live="polite"` on the trace stream and the reliability badge. |
| L-37 | **fixed** | Redundant `transition` on the spring-driven `motion.aside`. |
| L-38 | open | `animate-float` + `hover:scale-105` still fight. |
| L-39 | open | `class="dark"` retained. |
| L-40 | **partially fixed** | Cloudflare `og:url` removed; no `noindex` on authenticated routes. |

---

## IMPROVEMENTS

**refine (R-1 … R-30)** — R-2, R-5, R-6, R-7, R-9, R-10, R-12, R-13, R-14, R-15,
R-17, R-21, R-24, R-25, R-26, R-28, R-29, R-30 fixed. R-3/R-4 duplicate R-2's
neighbouring work; R-8's 2 duplicate sites are now 1; R-11, R-16, R-18, R-19, R-20,
R-22, R-23, R-27 open or absorbed.

**refactor (F-1 … F-14)** — F-1 done (one `enforce_service_tenant`), F-2 done,
F-4 done, F-5 done, F-6 done (`VerdictBadge`, `ClaimStateBadge` is an alias),
F-7 partially (trust tokens now drive the badge), F-8 done (`lib/claimState.js`),
F-9 done, F-10/F-11/F-12/F-13/F-14 open.

**small change (S-1 … S-33)** — S-1, S-2, S-3, S-4, S-5, S-6, S-7, S-8, S-9, S-10,
S-11, S-12, S-13, S-14, S-16, S-17, S-18, S-19, S-20, S-21, S-22, S-23, S-24, S-25,
S-26, S-27, S-28, S-30, S-31, S-32 fixed. S-15, S-29, S-33 open.

---

## Constraint verification

| Constraint | Before | Now |
|---|---|---|
| **C-1** NVIDIA removed except CUDA | code clean, 8 stale doc refs | **met** — all 8 doc references fixed; `decision-log.md` amended append-only. |
| **C-2** ONNX-only | runtime torch in the serving path | **met** — V-1/V-2/V-3 removed. Gaps that remain (int8 embedding export, ORT provider logging, version pins) are quality, not violations. |
| **C-3** large **and** small models | not met | **largely met** — tiered evidence budget, per-model `num_ctx`, small-model output caps, tier-scaled rerank depth, symmetric fallback ceiling. `L-4` remains. |
| **C-4** inference speed + accuracy | not met | **met** — ONNX session caching, mtime config cache, memoized collection dim, enabled hybrid leg, verbatim evidence, 300 DPI OCR, gated quantization. |
| **C-5** fully offline | 5 violations | **met in code** — cloud SDKs behind an extra, tracing behind explicit opt-in, no font CDN, k6 checksum-verified. `P1-21` (token storage) is not an egress path. |

---

## DEAD CODE

| Item | Status |
|---|---|
| `styles/{dashboard,playground,auth,knowledge-bases,evidence,claims,conflicts,settings,trace,components}.css` (1,568 lines) | **deleted** — verified class-by-class against every JSX/JS file; the only live rule in `trace.css` (`.trace-event`) already exists in `index.css`. |
| `styles/tokens.css` | **deleted** — the audit called it "make it load-bearing or delete"; the only live `var()` uses have identical inline fallbacks, and its values disagreed with Tailwind on 5 tokens. |
| `.btn-danger`, `.code-block`, `.reliability-*` in `index.css` | kept (`btn-danger` now used by `ConfirmDialog`). |
| `Collections.FEEDBACK` | **deleted.** |
| `internal_health` | **deleted** — reported healthy unconditionally; `/health/ready` is the real probe. |
| `passlib[bcrypt]` | **deleted** (N-104). |
| duplicate `.bg-cyber-grid` | **deleted** from `animations.css` (landing variant is the one in use). |
| orphan scripts | kept: `e2e_manual_verify.sh` is referenced by the execution plan as the nightly-E2E source, `eval_provider.sh` by the troubleshooting runbook. |
| `context_compression_*` config keys | **deleted** (L-18). |

---

## TESTING

| # | Status |
|---|---|
| T-1 … T-4 | open — needs real OCR fixtures and real ONNX models wired into the suite. |
| T-5 | open — the two prompt-routing twins are still guarded by source inspection. |
| T-6 | open — the eval harness still has no runner. |
| T-7 | open — full journey E2E not written. |
| T-8 | **fixed** — `tests/test_cross_tenant_scoping.py` (5 tests) covers `/evidence`, `/claims`, `/conflicts` on both the `user_id` and legacy `analysis_id` paths. Verified it has teeth: removing the tenant filter makes it fail. |
| T-9 | open. |
| T-10 | **fixed** — `tests/test_degenerate_output.py` (9 tests). |
| T-11 | open. |
| T-12 | open. |
| **Mock-theater items** | `test_verification.py`'s Gemini-arms are still framed against a provider that now needs the `cloud` extra. |
| **Backend total** | 681 → **697** passed, coverage 78.2% → 78.9%. |
| **Frontend** | lint clean, build OK. `npm test` needs Node 22 (host has 20; jsdom fails to load). |

---

## Explicitly not done

- **P1-11c** — a labelled ≥200-pair adversarial NLI eval set. This needs a dataset
  and a measurement run; writing thresholds before it would be theatre.
- **P1-21 (token storage)** — moving the JWT out of `localStorage` changes the
  auth model and the CSRF surface. That is a product decision.
- **N-18…N-23 (OCR depth)** — accuracy work that should be done against real
  scanned fixtures, not from a reading of the code.
- **N-88 / virtualization**, **L-1x perf tail** — real work, not risk-of-regression
  one-liners; left for a focused pass.
- **N-96** (`pip install -e` vs `uv sync --locked` in `backend-test`) — switching CI
  to `uv` changes the whole job's shape; the coverage and mypy ratchets give partial
  protection until it is done properly.
