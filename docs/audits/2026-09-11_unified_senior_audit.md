# TrustRAG — Unified Senior Audit (2026-09-11)

**Date:** 2026-09-11
**Auditors (acting roles):** Senior Frontend Developer · Senior Designer (Apple-design primary) · Senior Backend Developer · Senior AI/ML Engineer · Senior Security Engineer · Senior Optimization Engineer · Senior Testing Engineer (blackbox + whitebox)
**Scope:** Full stack, backend-first. `apps/api` (FastAPI + LangGraph RAG), `apps/web` (React 18 + Vite + Motion), config, Docker, docs.
**Status:** AUDITED · NO CODE CHANGED IN THIS PASS · 10 OLD AUDIT FILES SUPERSEDED AND DELETED (see §10)
**Frontend skill:** `apple-design` loaded and applied as primary lens (§3–§4). No redesign — scoped polish only, per skill utility rule.

> Supersedes everything under `docs/audits/` dated 2026-09-06 → 2026-09-10
> (`comprehensive_system_audit.md`, `SENIOR_AUDIT.md`,
> `2026-09-06_full_stack_working_now_audit.md`,
> `2026-09-07_backend_rag_correctness_audit.md`, `2026-09-07_security_audit.md`,
> `2026-09-07_embedding_removal_fix_audit.md`, `2026-09-07_performance_local_llm_audit.md`,
> `2026-09-07_work_status_and_next_steps.md`,
> `2026-09-08_model_discovery_and_hardening_audit.md`,
> `2026-09-10_senior_backend_ai_security_optimization_audit.md` incl. Rounds 1–11).
> History is preserved in git (`git log -- docs/audits/`); the working tree keeps one canonical audit: this file.

---

## 1. Executive summary

| Category | Critical | High | Medium | Low | Verdict |
|---|---|---|---|---|---|
| Backend correctness / RAM | 1 | 5 | 7 | 3 | Largest resident is **in-process BGE torch + embedded Qdrant + 16-slot LLM cache** — see §5, §7 |
| AI/ML + local-LLM load | 0 | 3 | 4 | 1 | Pipeline is safe (abstains, never hallucinates) but 3B verification is variable; refusal-gate + caps working |
| Security | 0 | 2 | 5 | 4 | No RCE/IDOR open; remaining risk is internet-exposure hardening (CORS, health recon, uploads, headers) |
| Frontend + Apple-design | 0 | 1 | 5 | 3 | Working screens kept; motion tokens drift from Apple values; one a11y defect (reduced-motion still springs) |
| Testing blackbox/whitebox | 0 | 1 | 3 | 1 | Backend ~191 + frontend 21 green per last audit; gaps in E2E + RAM/security regression |
| **TOTAL (fresh, de-duplicated)** | **1** | **12** | **24** | **12** | **All P0 runtime blockers from 09-06 stay fixed; nothing re-broke** |

**The one Critical (fresh): CRIT-RAM-1.** The API process still loads the full
sentence-transformers/torch BGE stack **in-process** at startup warmup (`main.py:158-167` →
`get_embedding_model()`), plus embedded Qdrant (`data/qdrant`), plus up to 16 cached LLM
clients (`model_registry.py:63`). On an 8 GB host this is the heat/hang root cause from
Rounds 5/6 — KV-quant flags and token caps cut *inference-server* RAM, but the *API-process*
floor (~1 GB torch + Qdrant mmap + pools) is untouched. Fix path is §7 (lazy/ONNX/sidecar),
not another prompt tweak.

---

## 2. What was re-verified as still fixed (no regression)

- LangGraph `graph.py` compiles; CRIT-1/CRIT-2 (dead `query_rewrite` branch) fixes intact.
- Retrieval datetime normalization, `None`-answer ABSTAIN, empty-prompt guard, 60 s retrieval budget intact.
- Semantic-cache namespacing by `embedding_model` + dim filter + KB-scoped invalidation on add/delete/rollback intact (`kb_service.py:158,179,226,474,536`).
- Stream-ticket ownership check intact (`analyses.py:166-183`).
- SSRF exact-host + DNS-answer validation + redirect revalidation; trusted-proxy rate limiting (`TRUSTED_PROXY_IPS`); provider/model allowlist; locked Docker builds (`uv sync --locked`); upload/URL rate limits + ingestion semaphore.
- Upload parse/chunk off event loop (`to_thread`); PyMuPDF close; word-boundary chunker; punctuation-insensitive dedup.
- Local-server offline 503 preflight, phantom-model prune, effective-engine persistence, refusal gate (`is_refusal_answer`), stray-ABSTAIN strip, sentence backstop, rewrite sanitizer, chunk pin + 422 mismatch guard, ports registry (`config/ports.yaml` + `scripts/apply_ports.py --check`).
- KV `q8_0` flags on Metal/CUDA, task token caps via `local_cap_kwargs()`, `TOKENIZERS_PARALLELISM=false`, single worker, `.env.example` Ollama server block.

---

## 3. Senior Designer + Senior Frontend (Apple-design primary)

Applied strictly where it earns its place (skill: warning-before-problem, critically-damped default, press-on-down, materials, type, reduced-motion). No gesture sheets/carousels exist — deliberately not invented. No haptics/audio (utility rule).

### HIGH-1 (a11y defect) — `SPRING_REDUCED` still springs
- **Where:** `apps/web/src/lib/motionConfig.js:22` — `SPRING_REDUCED = { type:'spring', damping:100, stiffness:400 }`.
- **Why wrong:** Apple-design §14 + skill: `prefers-reduced-motion: reduce` means **cross-fade/static, no slide/spring/parallax, drop overshoot**. A stiff spring is still vestibular motion.
- **Fix:** when reduced-motion matches, use `opacity 200ms ease, transform:none` (CSS media query already partially present — wire `MotionConfig reducedMotion="user"` + the CSS fallback as the single path).

### MEDIUM (frontend/design)
1. **Motion tokens drift from Apple values.** `SPRING_NORMAL {damping:22,stiffness:280}`, `SNAPPY {24,320}`, `BOUNCE {16,220}` are Motion stiffness/damping numbers, but comments claim Apple `damping ratio 1.0 / response 0.3–0.4`. They are not the same unit system. `SPRING_BOUNCE` on **hover lift** violates the skill (bounce only when the gesture carried momentum — flick/throw/drag-release; hover is not momentum). **Fix:** keep `bounce:0, duration:0.3–0.4` default; reserve bounce for drag-release/sheet; document the Motion↔Apple mapping in one comment.
2. **Press feedback incomplete.** Skill §1/§10: highlight on **pointer-down**, ~10 px hit padding, cancel-by-drag-away. `whileTap:0.95–0.98` + 150 ms ease-out exists on provider/prompt buttons, but generic buttons/inputs rely on CSS without `:active{transform:scale(.97);transition:100ms}`. **Fix:** one global `.btn-press:active` rule.
3. **Interruptibility not provable.** No `setPointerCapture`, no velocity history, no presentation-value re-target (skill §2–§5). Acceptable today (no draggable sheet/carousel) — **do not add** until such a component exists; then use springs + `project()` + velocity handoff, never CSS transitions/keyframes for the gesture.
4. **Materials risk stacking translucency.** `backdrop-blur` toolbars/sheets exist; skill §12 forbids light-translucent-on-translucent + demands context-aware shadow and scroll-edge fade instead of hard dividers. **Fix (2-day):** audit stacked panels, add `saturate(180%)` + bright top edge + heavier shadow over busy content.
5. **Type tracking is one-size.** Skill §15: negative tracking on display, ~0 on body, tight leading on headings, `rem`-based spacing for Dynamic Type. Current `tracking-tight` on headings only. **Fix:** `display{letter-spacing:-0.02em;line-height:1.05}` + body `1.5` + system-font-first (already mostly true).

### LOW (frontend)
- `lib/api.js:74-91` ticket flow is correct (no JWT in URL); 401 clears session — keep.
- JWT in web storage (authStore) remains XSS-sensitive — accept for local-first; move to httpOnly cookies only if internet-exposed (>2-day).
- `PlaygroundPage` chunk ~202 kB / `chart-vendor` ~393 kB — lazy-load charts (>2-day, P1 carried over).
- Vite proxy duplicate `/api` + `/api/v1/analyses` keys — harmless, dedupe opportunistically.

---

## 4. Frontend verdict (Apple-design)

Foundations present (press springs, blur materials, focus-visible ring, tabular-nums timestamps, compacted trace feed). **No P0 design blocker.** The single must-fix is HIGH-1 (reduced-motion). The rest is token hygiene, not a redesign.

---

## 5. Senior Backend (main focus)

### CRIT-RAM-1 — API-process floor: torch BGE + embedded Qdrant + 16 LLM clients (CONFIRMED, not fixed)
- **Where:** `main.py:158-167` warmup `get_embedding_model()` + `embed_query("warmup")` (loads ~1 GB torch/s-t at boot); `db/qdrant.py` embedded file mode (`data/qdrant`); `model_registry.py:63 @lru_cache(maxsize=16) get_llm`, `:169` + `:420 (maxsize=8)` embedding/registry caches.
- **Effect:** baseline RSS is dominated by web-process weight, before any inference. 16 LLM slots each pin an httpx pool + client object; combined with torch + Qdrant mmap this is what cooks 8 GB hosts (Rounds 5/6 heat).
- **Fix:** §7 UL-1…UL-6 (lazy-load / ONNX / sidecar / bounded registry with eviction+close). No behavior change to retrieval quality.

### HIGH backend (all confirmed present)
- **H-RAM-2 — `InMemoryCache` unbounded, keyed on never-repeated NLI prompts.** `model_registry.py:41-54` sets global `langchain.llm_cache = InMemoryCache()`. NLI prompts never repeat → cache only grows, never hits. **Fix:** scope cache to generation calls only, or key on `(query, chunk-hash)`, or bound size + TTL.
- **H-RAM-3 — Disk-cache N+1 writes.** `model_registry.py:338,355,375,398` call single-row `set_cached_embedding()` per vector (each opens/commits/closes SQLite + `PRAGMA journal_mode=WAL` in `_get_connection()`). `get_cached_embeddings_batch` reads batched but writes do not. **Fix:** batch `executemany` in one transaction (see §7 UL-4).
- **H-BE-4 — `get_memory_usage_mb()` reads lifetime peak, not current.** `core/memory.py:46-50` uses `ru_maxrss`. Guard `check_and_enforce_memory_guard()` therefore never sees drops and over/under-triggers. **Fix:** `psutil.Process().memory_info().rss` with `resource` fallback.
- **H-BE-5 — Self-heal reindex up to 10 k chunks in one shot.** `graph.py` self-heal embeds/upserts without batching or progress events. **Fix:** batches of 64–128 with trace progress (carried over, still open).
- **H-BE-6 — In-process SSE pub/sub breaks under multi-worker.** Correct for single worker (`--workers 1` pinned) but silently wrong if scaled. **Fix:** document single-worker constraint (done) + Redis bus only when workers>1 (deferred, correct).

### MEDIUM backend
1. `core/config.py:576,582,589` + `model_registry.py:565` `lru_cache(maxsize=1)` on settings — fine, no leak (immutable config). Keep.
2. `ingestion/preprocessor.py:634 @lru_cache(maxsize=32768) stem_word` — unbounded-until-32k distinct-word cache, no TTL; acceptable for English vocab but counts toward RSS. **Fix:** bound to 8–16 k or use stemming inline cache per-doc.
3. `ingestion/pipeline.py:127-137` batch embedding exists (good) — but batch size not tied to RAM tier; wire to hardware tier (lean 32 / standard 64 / plus 128).
4. `retriever.py` dense+sparse `gather` has 60 s budget (good) — keep; add per-branch timeout so one slow branch cannot consume the whole budget.
5. Lifespan `warmup_task = create_task(_async_warmup())` + `gather(embed, hw, discovery)` (`main.py:177-183`): three heavy startups contend on first boot; cancel-on-shutdown is correct. **Fix:** sequence `discovery → hw → embed` or gate embed warmup behind `HF_HUB_OFFLINE` readiness; log RSS before/after each.
6. `request_id_middleware` (`main.py:331-344`) trusts client `X-Request-ID` unbounded — see Security M-3.
7. `GZipMiddleware(minimum_size=1000)` + JSON serialization — fine; keep. Consider `orjson`-less direct Pydantic path already taken — keep.

### LOW backend
- `TOKENIZERS_PARALLELISM=false` set in Dockerfile only — also set in systemd/launchd docs for bare-metal runs.
- No `uvloop`/`httptools` pin — acceptable; measure before adding.
- `structlog` contextvars cleared per request — correct.
- `docs_url` disabled in production — correct.

---

## 6. Senior AI/ML

### HIGH AI/ML
1. **3B-model structured-JSON variance is the quality floor.** Rounds 6–8 mitigations (refusal gate, 512 decompose cap, rewrite guard, backstop sentences, sanitizer, neutral acronym example) are all sound and verified (191 backend / 21 frontend). Remaining variance is model capacity, not pipeline logic. **Next:** single structured call (decompose+verify fusion) or 4B default — both >2-day with eval.
2. **Batch-NLI total-failure design flaw fix is correct** (raise on total failure → budgeted individuals). Keep; add counter metric `nli.batch_total_failures`.
3. **`local_cap_kwargs()` provider matrix is correct** (caps local-only, `{}` for cloud). Keep; extend to self-heal batch size.

### MEDIUM AI/ML
- Recovery doubles `top_k` then caps generation at 8 — current `min(2×dense, ctx+16)` / `min(2×ctx, ctx+4)` is a good compromise; further cuts need recall eval.
- CrossEncoder rerank runs `to_thread` (good) but loads per-call — memoize encoder singleton per process (RAM-aware: one resident, not per-request).
- `is_refusal_answer()` 10-regex gate is conservative-by-design (misread bounded to FAIL→recovery). Keep; log gate hits for tuning.
- Chunk pin + dim guard (422) is the correct correctness-over-convenience trade. Keep.

### LOW
- Temperature-0 blind-retry avoidance is correctly implemented via short-circuits. Keep.

---

## 7. Senior Optimization — backend-first + ultra-low-RAM plan (web-grounded, 2026)

Researched 2026-09-11: FastAPI heap-bloat/leak patterns + fixes (bounded LRU, chunked upload streaming, lifespan-shared httpx pools, `tracemalloc`); 256 MB FastAPI proxy pattern (no torch in web process, stream tokens, single worker, slim image); FastAPI 0.140.x framework-memory refactors; mimalloc vs glibc fragmentation (5–6× RSS cut); uvicorn single-worker + Alpine + cache limits; GC tuning; KV-cache quantization (`q8_0` halves KV, `q4_0` quarters with quality/arch caveats, requires flash-attention, global per server, verify VRAM) — full citations in §11.

### What already applies (keep)
- Single worker, lifespan-shared local-LLM pools + shutdown close, `TOKENIZERS_PARALLELISM=false`, KV `q8_0` + FA on Metal/CUDA, `-c` as shared budget + serial semaphore (`LOCAL_LLM_MAX_CONCURRENCY=1`), `OLLAMA_MAX_LOADED_MODELS=1` + `NUM_PARALLEL=1` documented, task token caps, normalized cache keys, `malloc_trim` helper (`memory.py:21-38`).

### New ultra-low-RAM work (ordered by MB-per-effort)
| ID | Technique (source) | TrustRAG mapping | Effect |
|---|---|---|---|
| UL-1 | **Remove torch from web process** — proxy/remote-embed pattern (256 MB guide) | Lazy-import `sentence-transformers` inside function (already partially); next: ONNX BGE runtime **or** embed-sidecar service so `import torch` never fires in API workers | **~500–1000 MB** floor cut; biggest single win |
| UL-2 | **Bound every in-process cache** (heap-bloat guide) | `get_llm(maxsize=16)` → bounded registry (e.g. 4) with LRU eviction + `close()`; `InMemoryCache` → bounded/TTL or generation-only; `stem_word 32768` → 8 k | Stops slow RSS creep/OOM |
| UL-3 | **Chunked upload streaming** (eager-`file.read()` anti-pattern) | Stream `UploadFile.file` in 64 KiB–1 MiB chunks to disk; enforce per-entry inflation caps + magic bytes (also closes SEC-M) | Constant per-request RAM regardless of file size |
| UL-4 | **Batch SQLite writes in one txn** | Replace per-vector `set_cached_embedding` loop with `executemany` single-commit; keep `WAL` + `NORMAL` pragmas once per connection | Cuts connection churn + WAL pressure on ingest |
| UL-5 | **Current-RSS (psutil) + idle trim** | `memory.py` → `psutil` RSS; `trim_memory()` (gc + `malloc_trim`) on idle/post-ingest hook, not only on guard breach; set `MALLOC_ARENA_MAX=1`, `M_TRIM_THRESHOLD=64K` in Docker/systemd | Reclaims glibc-held pages; fixes guard accuracy |
| UL-6 | **KV + server flags verified live** | `OLLAMA_KV_CACHE_TYPE=q8_0` + `FLASH_ATTENTION=1`, `MAX_LOADED_MODELS=1`, `NUM_PARALLEL=1`, `-c 4096` shared, `-ctk/-ctv q8_0` + FA on llama-server; verify via `ollama ps` VRAM before/after (silent-fallback risk) | **~50% KV cut**; must restart server to take effect |
| UL-7 | **Allocator + image** (mimalloc; slim/Alpine; FastAPI ≥0.140) | Evaluate `mimalloc` (or jemalloc fallback) for PM/heavy-ingest; `python:slim` + multi-stage; bump FastAPI to ≥0.140.13 (framework-mem + SSE status fix) | 10–80 MB + fewer OOMs under burst |
| UL-8 | **Measure first** (`tracemalloc` + RSS probe) | Add `/health` RSS field (current, not peak) + dev-only `tracemalloc` middleware printing top-3 allocators per suspect route; boot/request RSS log in lifespan | Prevents blind optimization |

---

## 8. Senior Security (fresh pass)

### HIGH (open, internet-exposure blockers — local-dev acceptable)
- **SEC-H-A — CORS credentialed + wildcard platform regex.** `main.py:376` `allow_origin_regex` trusts any `vercel.app/netlify.app/pages.dev` subdomain with `allow_credentials=True` + `allow_headers=["*"]`. Any third-party deploy on those platforms is an allowed origin. **Fix:** explicit origins list; preview regex only behind env flag.
- **SEC-H-B — Public `/health` recon.** `health.py:29-61` unauthenticated returns `environment`, full `registry_status()` (providers/models), `hardware` profile, `supported_formats`. **Fix:** public `{status, version}` only; diagnostics behind auth.

### MEDIUM (open)
1. **M-1 `X-Request-ID` reflected/logged unsanitized** (`main.py:339-343`). Log-forgery/trace-confusion. **Fix:** validate `[A-Za-z0-9-]{1,64}`, else regenerate; truncate.
2. **M-2 Internal ingestion trusts caller tenant fields** (`internal.py:56-77` service-token model). **Fix:** bind service tokens to tenant scope; drop caller-selected `user_id/kb_id`.
3. **M-3 MCP stdio not tenant-scoped** (`mcp/server.py:171-238`). **Fix:** require service identity + allowed-KB scopes; gate startup behind explicit flag.
4. **M-4 Prompt-injection defense is instruction-only**, markers unescaped; pruning can weaken delimiters. **Fix:** keep delimiters intact during prune, label web evidence, output-policy filter.
5. **M-5 Upload validation suffix-only; no magic bytes / per-entry zip-bomb caps** (`knowledge_bases.py`, `parser.py`, `pipeline.py`). 20 MB compressed cap exists. **Fix with UL-3:** magic bytes + per-entry inflation cap + chunked stream.

### LOW / hygiene
- Compose exposes Mongo/Qdrant without prod TLS/auth — bind loopback / require creds in prod.
- Bcrypt 72 B cap + complexity — verified present; keep.
- `aud`/`iss` JWT claims + separate service secret — add when service tokens harden (with M-2).
- Avoid logging claim/doc text on failure paths — spot-check `verifier.py`/`generator.py` error logs.
- Frontend JWT in localStorage — httpOnly-cookie migration only if internet-exposed.

---

## 9. Senior Testing (blackbox + whitebox)

**Carried green:** backend ~191 pytest, frontend 21 vitest, ruff + eslint clean, Vite build green (per Round 10/11 reports; rerun §12 before release).

### Gaps (fresh)
- **HIGH T-1 — No live E2E with local inference in CI.** pytest never runs `lifespan` (missed P0-LOCAL-1 class). **Fix (2-day):** smoke job booting API + llama-server stub/Ollama mock → register→KB→ingest→analysis→claims/evidence→stream-ticket replay test.
- **MEDIUM:** (a) RAM regression tests — boot RSS ceiling, N-upload RSS delta, cache-eviction test for `get_llm`/InMemoryCache/stem cache; (b) security blackbox — suffix-domain bypass, decimal/hex/octal IP, private-DNS, redirect-to-private, spoofed `X-Forwarded-For`, arbitrary model reject, cross-tenant MCP/internal, health-leak assert; (c) whitebox — batch-write txn count, `psutil` RSS vs `ru_maxrss`, self-heal batch progress events.
- **LOW:** Playwright console-error check + reduced-motion emulation test (`prefers-reduced-motion` → opacity only).

---

## 10. Refactor / Update / Degrade-or-Remove map

| Area | File(s) | Action | Reason |
|---|---|---|---|
| **REFACTOR** | `core/model_registry.py:63,169,420` | Bounded model/client registry with eviction + `close()` | 16 LLM slots pin pools/RAM; user-influenced keys |
| **REFACTOR** | `core/model_registry.py:41-54` | Scope/bound `InMemoryCache` (gen-only or `(query,chunk-hash)` + TTL) | Unbounded growth on never-repeated NLI prompts |
| **REFACTOR** | `core/disk_cache.py` + call sites `:338,355,375,398` | Batch `executemany` writes, one txn; open pragmas once | N+1 SQLite churn on every ingest |
| **REFACTOR** | `core/memory.py:41-73` | `psutil` current RSS; idle/post-ingest `trim_memory()`; arena env | Peak-reading guard is inaccurate; glibc holds pages |
| **REFACTOR** | `agent/graph.py` self-heal | Batch 64–128 + progress trace events | 10 k-chunk one-shot RAM spike |
| **REFACTOR** | `api/v1/knowledge_bases.py`, `ingestion/parser.py`, `pipeline.py` | Chunked stream ingest + magic bytes + inflation caps | Constant-RAM uploads + zip-bomb defense |
| **REFACTOR** | `main.py:331-344,373-381` | Sanitize `X-Request-ID`; explicit CORS origins; `allow_headers` explicit | Log-forgery + wildcard-credentialed CORS |
| **REFACTOR** | `api/v1/health.py` | Split public vs authed health | Recon minimization |
| **REFACTOR** | `api/v1/internal.py`, `mcp/server.py` | Tenant-bound service tokens; MCP scopes + startup gate | Cross-tenant abuse |
| **UPDATE** | `web/src/lib/motionConfig.js` | Fix Apple mapping; `SPRING_REDUCED` → cross-fade; bounce only on momentum | Skill compliance + a11y |
| **UPDATE** | `web` global CSS | `:active{scale(.97)}` press rule; `tracking:-0.02em` display; material stacking audit | Apple §1/§12/§15 |
| **UPDATE** | `Dockerfile`, `.env.example`, deploy docs | `MALLOC_ARENA_MAX=1`, `TOKENIZERS_PARALLELISM` everywhere, Ollama KV block, FastAPI ≥0.140.13 | Ultra-low-RAM + framework-mem |
| **UPDATE** | `ingestion/pipeline.py`, `retrieval/reranker.py` | Tier-tied batch sizes; singleton CrossEncoder | RAM-proportional throughput |
| **DEGRADE (remove/demotion)** | `core/secrets_manager.py`, `core/context.py` leftovers | Already deleted 1332 lines in Round 8 — verify no reintroduction | Dead code = RAM + attack surface |
| **DEGRADE** | Legacy cloud-KB pins, `OCC-RAG-*` embedding ambiguity | Keep re-upload guidance; keep LLM-only Ollama/llama-server discovery | Prevents cross-space garbage queries |
| **DEGRADE** | `stem_word lru 32768` | Demote to 8 k or per-doc scope | Idle RSS creep |
| **DO NOT DEGRADE** | Recovery loop, refusal gate, backstop, 422 pin guard, ticket auth, allowlists | Keep all — they are the reliability story | Removing any reopens abstain/hallucination/spam bugs |

---

## 11. Recommended upgrades

### A. Doable in ≤2 days (no eval-gated behavior change)
1. HIGH-1 reduced-motion cross-fade + `MotionConfig reducedMotion="user"`; motion-token comment fix; global press rule. (Frontend)
2. `psutil` RSS + idle `trim_memory()` + `MALLOC_ARENA_MAX=1` + `TOKENIZERS_PARALLELISM` everywhere. (Backend/RAM)
3. Batch SQLite embed writes (`executemany`); `stem_word` bound to 8 k. (Backend/RAM)
4. `X-Request-ID` validate+truncate; split public/authed health; explicit CORS origins behind env flag. (Security)
5. Chunked-stream upload path + magic bytes + per-entry inflation caps (wired to existing 10/min limits). (Security/RAM)
6. Bound `get_llm` registry (e.g. 4 + eviction/close); `InMemoryCache` generation-only + TTL. (RAM)
7. Restart llama-server with Round-4 flags; set + **verify** `OLLAMA_KV_CACHE_TYPE=q8_0` + `FLASH_ATTENTION=1` via `ollama ps` VRAM; keep `-c 4096` + semaphore 1. (Ops — needs terminal)
8. E2E smoke (lifespan boot + ticket-replay) + RAM ceiling + security blackbox tests from §9 into CI. (Testing)
9. Tier-tied ingest batch sizes; CrossEncoder singleton; boot/request RSS logging + `/health.rss_mb` (current). (Perf)
10. This audit replaces 8 old files (done in this pass — §12).

### B. Needs >2 days (eval, migration, or architecture)
1. **Torch-out-of-web-process:** ONNX BGE runtime or embed-sidecar; parity eval on recall/latency; largest RAM win. (UL-1)
2. **Decompose+verify fusion** into one structured call; prompt-schema robustness eval on 3B/4B. (AI/ML)
3. **Redis SSE bus + multi-worker readiness** (only if workers>1 ever needed); else keep documented single-worker. (Backend)
4. **Tenant-bound service tokens + MCP scoping + JWT `aud/iss` + httpOnly-cookie frontend auth.** (Security)
5. **Output-policy filter + delimiter-preserving prune + web-evidence labeling** (prompt-injection depth). (Security/AI)
6. **mimalloc/jemalloc eval + Alpine/slim image + FastAPI ≥0.140 rollout** with load-test (k6) before/after. (Platform)
7. **Chart lazy-load + proxy-key dedupe + full type-scale retune** with design review. (Frontend)
8. **Mongo `cacheSizeGB:1` cap + Qdrant on-disk tuning + self-heal progress UX** on 8 GB hosts. (Ops)
9. **Automated red-team + hallucination stress suite** in CI. (Testing/Security)

---

## 12. Verification (run before release)

```bash
# backend
cd apps/api
ruff check app/ tests/ && ruff format --check app/ tests/
pytest tests/ -q --no-header --no-cov   # expect 191+ green (post-§11: more)
python3 -m py_compile app/agent/graph.py app/core/model_registry.py app/core/memory.py app/core/disk_cache.py

# frontend (Apple-design scope)
cd ../web
npm run lint            # 0 errors
npx vitest run          # 21 green (+ reduced-motion test after A.1)
npm run build           # success

# ports + RAM + security spot-checks
python scripts/apply_ports.py --check
curl -s http://localhost:8000/api/v1/health | jq '{status, version}'
# RSS (after B: current-RSS field)
ps -o rss= -p $(pgrep -f "uvicorn app.main") | awk '{printf "API RSS MB: %.1f\n",$1/1024}'
# CORS / headers
curl -si -X OPTIONS http://localhost:8000/api/v1/auth/login -H "Origin: https://evil.vercel.app" | head -20
curl -s http://localhost:8000/api/v1/health | jq '{environment, models, hardware}'
```

---

## 13. Web research grounding (ultra-low RAM, fetched 2026-09-11)

- FastAPI heap-bloat failure analysis (unbounded module-state, eager `file.read()`, request-object capture in BackgroundTasks, per-request `httpx.AsyncClient`) + lifespan-shared pool + `tracemalloc` middleware — DevStackTips 2026-08-22.
- 256 MB FastAPI AI proxy (no torch/transformers in web image, stream tokens, single worker, slim image, RSS probe on boot/requests) — DEV 2026-09-04.
- FastAPI 0.140.x framework-memory refactors (no flat dep-tree retention, targeted body derivation) + SSE status-code fix in 0.140.13 — jonathansblog 2026-09-08.
- Glibc fragmentation vs mimalloc (97% fragmentation overhead case; ~5–6× RSS cut with mimalloc) — Medium/Shreehari 2026-01-05.
- Uvicorn overhead (single-worker + Alpine + cache limits; worker RAM math; container cpu_count trap) — DEV romdevin 2026-04-15; LogicLoopTech workers guide 2026-02-04.
- Microservice lean guide (lazy imports, lifespan on-demand, GC tuning, slim deps; 110→38 MB case) — Medium/Bhagya 2025-08-11.
- KV-cache quantization: `q8_0` halves KV at negligible loss, `q4_0` quarters with arch-dependent quality + ~37% slowdown at 110 K; V-quant needs flash-attention (panic otherwise); silent f16 fallback; global per server; verify VRAM — openclawdc 2026-08-08; modelpiper 2026-04-14; kvcache-bench; NVIDIA DGX Spark thread 2026-03-31; SSDNodes Ollama quantization 2026-08-11.
- Lean ASGI (`saltare` Zig backbone: lazy TLS, `mallopt`, idle `gc.collect+malloc_trim`, body streaming, `sendfile`, cgroup-aware caps) — PyPI saltare v1.11.0 notes.

---

## 14. Files

**Added (this audit):** `docs/audits/2026-09-11_unified_senior_audit.md` (this file).
**Deleted (this audit):** the 10 superseded files listed in the header.
**Changed:** none — findings are recorded for the next implementation pass (§11A first).
