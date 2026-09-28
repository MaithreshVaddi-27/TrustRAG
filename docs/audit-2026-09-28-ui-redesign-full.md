# TrustRAG Full Audit — ui-redesign @ 0367a6d (2026-09-28)

- **Branch:** `ui-redesign` ONLY (no work on main/production-deploy)
- **Commit:** `0367a6d` (after `git pull --ff-only`, stash conflict resolved by keeping upstream)
- **Prior audits reviewed:** `docs/backend-audit-2026-09-27.md`, `docs/backend-audit-2026-09-28-ingestion.md`, `docs/STATUS-2026-09-27-embedding-cleanup.md`, `docs/ROADMAP.md`, `docs/architecture/decision-log.md`
- **Method / skills used:** `systematic-debugging` (reproduce-first), `verification-before-completion`, `requesting-code-review` checklist, `gstack-qa` / `gstack-review` gates, `design-taste-frontend` + `high-end-visual-design` for premium bar
- **Scope:** entire `apps/api` + `apps/web`, ONNX-only model enforcement, Mac/Linux/Windows parity, dead-code/unused-code sweep

## Status tracker (update as fixes land)

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| H1 | CRITICAL | HTML `<meta>` latches extractor off → every real HTML ingests as empty (`parser.py:323-344`) | ✅ FIXED 2026-09-28 — set-based `_ignored` (script/style only), repro passes (head-meta, mid-body-meta, script/style still stripped) |
| H2 | CRITICAL | ClamAV positive swallowed by own `except Exception` → malware indexed (`parser.py:418-426`) | ✅ FIXED 2026-09-28 — narrow except to connection failures + `return`, verdict raised outside `try`; fake-ClamAV FOUND repro now raises `IngestionError` |
| M1 | MEDIUM | DOCX decompression-bomb guard ratio-only, no absolute ceiling → 132x RSS amplification | ✅ FIXED — 256MB absolute ceiling in `check_decompression_bomb` + per-member bound in `parse_docx`; ceiling breach raises operator-facing message |
| M2 | MEDIUM | `layout_aware` chunk `character_offset` does not index page text → provenance wrong after chunk 0 | ✅ FIXED — blocks recorded as raw-line spans, exact page substring chunked, offsets rebased by `block_base`; table rows joined with `\n` (no more fabricated `\| a \| \| b \|` rows); verified 0 mismatches |
| M3 | MEDIUM | `ProgressiveChunkingStrategy` no step guard → 507x chunk blowup on bad overlap | ✅ FIXED — chunker-style guarded step (full-window fallback, single warning per page) + startup rejection in `get_model_config()` (`overlap >= size` → ValueError); degenerate case 99490 → 272 chunks |
| M4 | MEDIUM | `character_offset` points at stripped whitespace, not chunk start | ✅ FIXED — `start + leading_ws` in `chunker.py` + same rule in progressive strategy; verified 0 mismatches across 5 window configs |
| M5 | MEDIUM | Ingestion semaphore keyed by `id(event_loop)` → docs wedge in `processing` forever | ✅ FIXED — `WeakKeyDictionary` keyed by loop object + lock (same pattern as `core/concurrency.py`); acquire moved inside failure handler that marks doc `failed` instead of stranding `processing` |
| L1 | LOW | OCR `min_confidence` skipped when RapidOCR returns no per-line score | ✅ FIXED — `confidence is None` with non-empty lines now drops text (fail-closed, auditable `used=True`) |
| L2 | LOW | `parse_pdf` re-wraps own `IngestionError`, losing limit message | ✅ FIXED — `except IngestionError: raise` passthrough in `parse_pdf` AND `parse_docx` (same shape; preserves M1 bomb messages) |
| ONNX-1 | HIGH | Reranker still has torch `CrossEncoder` fallback path — embeddings are ONNX-only, reranker is not fully | ✅ DECIDED + ENFORCED — `use_onnx=true` (default) now fails closed to RRF order with actionable message, never silent torch weights; explicit `use_onnx=false` keeps PyTorch opt-in; `models.yaml` comment updated |
| DOC-1 | LOW | Stale `EMBEDDING_PROVIDER=onnx\|huggingface` refs (cleanup follow-up still present) | ✅ FIXED — `TRUSTRAG_specs.md` now `framework: onnxruntime / provider: onnx`; `ROADMAP.md` #16 annotated (sole engine since 2026-09-27); `decision-log.md` left as dated historical record |
| FE-1 | LOW | `console.error/warn` in 5 frontend files — verified as intentional error logging (PlaygroundPage, SettingsPage, main.jsx, ErrorBoundary, ResultsPanel, AppLayout), no debug leftovers | ✅ VERIFIED OK |
| XP-1 | MEDIUM | Cross-platform: no hardcoded POSIX paths; `.gitattributes` LF normalization; `memory.py`/`hardware.py` carry darwin/linux/Windows branches | ✅ CI WIRED — new `cross-platform` job (windows-latest + macos-latest): backend import/config smoke + frontend lint/test/build, gated in `ci-gate` |
| T-ISO | HIGH | `test_create_analysis` failed on any machine with `AI_PROVIDER` in local `.env` (config `load_dotenv` at import beats test defaults) — suite not hermetic | ✅ FIXED — conftest strips provider/model override vars at import AND per-test before cache clear; full suite 664 passed (was 663+1) |
| VITEST-ENV | MEDIUM | Frontend `vitest` unusable on Node 20 (`webidl.util.markAsUncloneable`, undici@8/jsdom@30 need Node ≥ 22) | ✅ CONFIRMED ENV-ONLY — `engines: >=22` already pinned, CI uses Node 22; verified 33/33 green on local Node 22.23.3 |
| UI-A11Y | MEDIUM | 6 icon-only buttons exposed `title` only (unreliable AT announcement); `h-screen` breaks on mobile browser chrome | ✅ FIXED — `aria-label` mirrors added; `h/min-h-screen` → `dvh` with `supports-` fallback on 5 layout roots |
| UI-COPY | LOW | 2 em-dash prose tells in Playground copy | ✅ FIXED — rewritten without em-dashes (placeholder `—` for empty data kept: standard typography, not a tell) |
| L-1 | HIGH | Same 3B model recommended for every RAM tier (only remaining user-visible defect in prior audit) | ✅ FIXED — lean ≤8.5GB → 1B class (`granite-4.0-h-1b` / `gemma3:1b` alt); standard → 3B granite; high → 3B granite + SmolLM3-3B alt; regression test `test_tiers_recommend_different_llm_weights` pins it |
| B-18 | MEDIUM | `ChatNVIDIA` has no langchain-level `max_retries` | ✅ DECIDED: NO RETRY — adding it without capping Gemini raises spend on the pricier provider; transient 5xx already classified by `probe_cloud_llm` + short-circuited via `LLMUnavailableError` (B-5/B-6). No code change. |

## ONNX-only enforcement (user requirement: "only ONNX to run models")

- ✅ Embeddings: `get_embedding_model()` is ONNX-only (`model_registry.py:561`), `BAAI/bge-small-en-v1.5` single engine, no provider env, no per-request override. Frontend sends no embedding fields. Verified.
- ✅ OCR: `rapidocr_onnxruntime` only. Verified.
- ⚠️ Tokenizers: `transformers.AutoTokenizer` used in `onnx_embeddings.py:75`, `onnx_reranker.py:82,189` — tokenizer-only, no weights, no torch model. Acceptable, not a violation.
- ❌ Reranker fallback: torch `CrossEncoder` still importable at `model_registry.py:673-705`. `hardware.py:114` imports torch only for device probe (with torch-free fallback per B-1 fix). Decision needed: keep pinned CPU fallback or delete for strict ONNX-only.
- dépass: `onnxruntime` + `rapidocr-onnxruntime` are the only model runtimes on the happy path.

## Cross-platform (Mac / Linux / Windows)

- Paths: no hardcoded POSIX-only paths in `apps/api/app` or `apps/web/src` beyond standard `/tmp` usage in tests; `pathlib` used in config/disk_cache.
- Binaries: `onnxruntime` ships wheels for all three OSes; `rapidocr_onnxruntime` likewise. No platform-gated imports found in happy path.
- Remaining: full `pytest` + `vitest` + `vite build` must pass on each OS in CI; Windows path-length + file-lock behavior for disk_cache/Qdrant untested locally.

## Dead-code / unused-code sweep

- 2026-09-27 cleanup deleted ~873 lines (exceptions, experimentation flags, semantic_cache, stale models.yaml keys). Verified present in tree.
- No new `TODO/FIXME/HACK` markers in `apps/` (grep clean).
- `docs/config/ports.yaml` duplicate noted in backend audit §Open decisions — re-check before delete (deletion needs explicit go-ahead, left untouched).

## Fix order (critical first)

1. H1 + H2 (this commit) with regression tests
2. M5 (wedged docs — data-loss class)
3. M1 (DoS amplification)
4. M2 + M4 (provenance correctness — core differentiator)
5. M3, L1, L2
6. ONNX-1 decision + DOC-1 cleanup

## Verification log (2026-09-28 final — all findings fixed)

- H1 repro: head-`<meta>` body text recovered, mid-body `<meta>` keeps both sides, script/style still stripped — PASS
- H2 repro: fake ClamAV `FOUND` verdict now raises `IngestionError` instead of "daemon unavailable" — PASS
- M4 check: 0 offset mismatches across 5 window configs (was 353) — PASS
- M2 check: 0 layout_aware offset mismatches incl. table chunks — PASS
- M3 check: degenerate `overlap=512/size=512` on 100KB page → 272 chunks (was 99,490) — PASS
- M1 check: `check_decompression_bomb` raises operator-facing message past 256MB absolute ceiling — PASS
- Targeted `pytest` (ingestion/chunking/ocr/concurrency/config): 89 passed
- Full backend `pytest`: **663 passed, 1 failed** — `test_analyses.py::test_create_analysis` expects default `llm_provider == llama_cpp`, env returns `ollama`. Pre-existing/env-dependent (provider auto-detect), untouched by this change; needs confirm on clean CI runner.
- `ruff check` + `ruff format --check` on `app/`: clean
- Frontend `vite build`: green (3.14s)
- Frontend `eslint --max-warnings 0`: clean
- `scripts/apply_ports.py --check`: exit 0
- Frontend `vitest`: 8 unhandled errors, all `webidl.util.markAsUncloneable is not a function` (undici/jsdom vs Node v20.19 env mismatch). Pre-existing — zero `apps/web` changes in this work; needs CI runner with pinned Node.
- `uv.lock` churn from local uv version reverted (twice) — not part of this fix
- Cross-platform: `.gitattributes` LF normalization present; `memory.py`/`hardware.py` carry darwin/linux/Windows branches; ONNX + RapidOCR wheels exist for all three OSes; full per-OS CI still required

## Second pass (2026-09-28, same branch)

- Test hermeticity fix → full backend **664 passed** (zero failures)
- Frontend on Node 22.23.3: lint clean, **33/33 vitest green**, build green
- UI premium pass (Redesign-Preserve, trust-first dials 4/3/5): motion story already complete (MotionConfig + per-file reduced-motion gates verified); added aria-labels, dvh viewport stability, copy touch-ups
- L-1 tiered recommendations + regression test (18/18 hardware tests green)
- B-18 resolved as no-change (cost); cross-platform CI job added + YAML validated + `ci-gate` wired

---
*All tracked findings are fixed and verified locally (macOS). Remaining: CI run on push (Ubuntu + Windows + macOS matrix) as final proof.*
