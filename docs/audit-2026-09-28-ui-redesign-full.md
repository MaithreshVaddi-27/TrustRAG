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
| M1 | MEDIUM | DOCX decompression-bomb guard ratio-only, no absolute ceiling → 132x RSS amplification | ⬜ OPEN |
| M2 | MEDIUM | `layout_aware` chunk `character_offset` does not index page text → provenance wrong after chunk 0 | ⬜ OPEN |
| M3 | MEDIUM | `ProgressiveChunkingStrategy` no step guard → 507x chunk blowup on bad overlap | ⬜ OPEN |
| M4 | MEDIUM | `character_offset` points at stripped whitespace, not chunk start | ⬜ OPEN |
| M5 | MEDIUM | Ingestion semaphore keyed by `id(event_loop)` → docs wedge in `processing` forever | ⬜ OPEN |
| L1 | LOW | OCR `min_confidence` skipped when RapidOCR returns no per-line score | ⬜ OPEN |
| L2 | LOW | `parse_pdf` re-wraps own `IngestionError`, losing limit message | ⬜ OPEN |
| ONNX-1 | HIGH | Reranker still has torch `CrossEncoder` fallback path (`model_registry.py:673-705`, `onnx_reranker.py:188-189`) — embeddings are ONNX-only, reranker is not fully | ⬜ OPEN (needs product decision: ONNX-only reranker or pinned fallback) |
| DOC-1 | LOW | Stale `EMBEDDING_PROVIDER=onnx\|huggingface` refs in `TRUSTRAG_specs.md:335`, `ROADMAP.md:32`, `decision-log.md:364-386` (cleanup follow-up listed in STATUS file, still present) | ⬜ OPEN |
| FE-1 | LOW | `console.error/warn` in 5 frontend files — verified as intentional error logging (PlaygroundPage, SettingsPage, main.jsx, ErrorBoundary, ResultsPanel, AppLayout), no debug leftovers | ✅ VERIFIED OK |
| XP-1 | MEDIUM | Cross-platform: no `rg`, hardcoded `/tmp`, backslash, or `C:\` paths found; `pathlib`/`os.path` usage needs full Windows CI run to confirm | ⬜ NEEDS CI VERIFY |

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

## Verification log (2026-09-28 checkpoint)

- H1 repro: head-`<meta>` body text recovered, mid-body `<meta>` keeps both sides, script/style still stripped — PASS
- H2 repro: fake ClamAV `FOUND` verdict now raises `IngestionError` instead of "daemon unavailable" — PASS
- `pytest -k "parser or ingestion or malware or html or clamav or eicar"`: 19 passed
- Full backend `pytest`: 663 passed, 1 failed — `test_analyses.py::test_create_analysis` expects default `llm_provider == llama_cpp`, env returns `ollama`. Unrelated to ingestion change (provider auto-detect depends on local installs); recorded as pre-existing/env-dependent, needs confirm on clean CI runner.
- `ruff check` + `ruff format --check` on `parser.py`: clean
- `uv.lock` churn from local uv version reverted — not part of this fix

---
*Next: M5 → M1 → M2/M4 → M3 → L1/L2 → ONNX-1 decision → DOC-1. Do not push until full `pytest`, `vitest`, `ruff`, `vite build` are green on CI.*
