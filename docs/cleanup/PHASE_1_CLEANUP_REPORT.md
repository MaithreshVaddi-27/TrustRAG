# TrustRAG — Phase 1 Cleanup Report

**Date:** 2026-11-08 · **Branch:** `ui-redesign`  
**Status:** Complete — all verified cleanup executed and validated.

---

## 1. Removed files

| Path | Type | Reason | Verification |
|---|---|---|---|
| `apps/web/public/styles/animations.css` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/styles/app-layout.css` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/styles/landing.css` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/styles/loaders.css` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/styles/materials.css` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/styles/typography.css` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-404.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-claims.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-conflicts.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-dashboard.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-evidence.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-knowledge-bases.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-mobile-dashboard.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-mobile-drawer.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-playground.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-settings.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `apps/web/public/audit-traces.png` | asset | dead, zero references | repo-wide grep: 0 hits |
| `scripts/calibrate_local_judge.py` | script | orphan, zero references | repo-wide grep: 0 hits |
| `scripts/prune_llm_cache.py` | script | orphan, zero references | repo-wide grep: 0 hits |

Estimated bundle/repo savings: ~5.4 MB (audit PNGs) + ~0.1 MB (dead CSS). Frontend `dist/` no longer ships these assets.

## 2. Removed dependencies

| Dependency | File | Reason |
|---|---|---|
| `dompurify` ^3.4.17 | `apps/web/package.json` | zero imports; `react-markdown` escapes by default |
| `htmlparser2` ^12.0.0 | `apps/web/package.json` | zero imports |

Removed via `npm uninstall`; `package.json` and `package-lock.json` updated. No import breakage (verified via grep before removal and tests/build after).

## 3. Code fixes

| File | Fix | Rule |
|---|---|---|
| `apps/api/app/rag/generation/generator.py` | Renamed `_FILLER_WORDS` → `_filler_words`; wrapped overlong prompt docstring | N806 + E501 |
| `apps/api/app/rag/verification/verdict.py` | Wrapped overlong docstring | E501 |
| `apps/web/src/components/landing/AnimatedPipeline.jsx` | Removed unused `scrollProgress` + `useMotionValue` import | no-unused-vars |
| `apps/web/src/components/landing/ProblemSolutionNarrative.jsx` | Removed unused `ShieldAlert`, `Check` imports | no-unused-vars |

All edits are minimal and behavior-preserving (variable rename is internal to one function; import/removal only deletes unused symbols; docstring wrapping changes no runtime text).

## 4. Validation results

### Backend (`apps/api`)

| Gate | Result |
|---|---|
| `ruff check app/ tests/` | **All checks passed** (0 errors) |
| `ruff format --check app/ tests/` | 3 pre-existing unformatted files (baseline, untouched: `analysis.py`, `test_eval_metrics.py`, `test_api_contract.py`) |
| `pytest` | **757 passed, 4 skipped** |
| Coverage | **78.67%** (gate 78%) — unchanged from baseline |

### Frontend (`apps/web`)

| Gate | Result |
|---|---|
| `eslint src --max-warnings 0` | **clean** (0 errors) |
| `vitest run` | **33 passed** (8 files) |
| `vite build` | **success** |

Pre-existing failures carried forward unchanged (reported separately, not regressions): the 3 backend unformatted files at baseline.

## 5. Contracts preserved

- No REST/LangGraph/Mongo/Qdrant route or schema changed.
- No authentication, database behavior, RAG algorithm, or evaluation contract altered.
- No production config changed; no dependency versions upgraded.
- No migrations, fixtures, fixtures, or model weights (`.model_cache/`) touched.
- No user data or existing Git changes discarded (untracked branch work in `docs/design/`, `docs/engineering/`, `screenshots/`, landing components left intact).

## 6. Artifacts produced

- `docs/cleanup/PHASE_1_REPOSITORY_AUDIT.md` — full pre-cleanup audit
- `docs/cleanup/PHASE_1_CLEANUP_REPORT.md` — this report
- `docs/cleanup/REMAINING_TECHNICAL_DEBT.md` — residual issues (see below)
