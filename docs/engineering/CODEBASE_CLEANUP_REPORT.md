# TrustRAG — Codebase Cleanup Report

**Date:** 2026-11-07 · **Branch:** `reliability-phase1` · **Method:** `INVENTORY → TRACE → CLEAN → BUILD → BROWSER TEST → REFINE`

## 1. Inventory

- 350 tracked files (`git ls-files`): 51 backend test files, 30+ backend source modules, 33 frontend pages/components, 12 routes, 6 CSS modules.
- Baselines on arrival (no changes): backend **761 passed** (coverage 79.07% ≥ 78% gate), frontend **33 passed**, ESLint clean, Vite build OK, `dist/` 12 MB.

## 2. Classification (KEEP | REFACTOR | REMOVE | REPLACE)

| Finding | Verdict | Evidence | Action |
|---|---|---|---|
| `apps/web/public/styles/*` (6 files) | REMOVE | Zero references — `index.css` imports only `./styles/*` from `src/`; `index.html` has no `/styles/` link. 4 of 6 were byte-identical to `src/styles/`; 2 had diverged (missing `.text-editorial`/`.grain`). Dead weight that could silently drift. | Deleted via `git rm` (still in git history). |
| `apps/web/public/audit-*.png` (11 files, ~5 MB) | REMOVE | Zero code references (only hit was an unrelated `trustrag-audit-*.jsonld` download name in `ResultsPanel.jsx`). Old audit screenshots copied to `dist/` → **bundle bloat**. | Deleted via `git rm`; 4 fresh screenshots now live under `docs/design/screenshots/` (docs, not shipped). |
| `htmlparser2` dependency | REMOVE | `grep -rn htmlparser2 apps/web/src` → no imports. | `npm uninstall`; lockfile updated. |
| `dompurify` dependency | REMOVE | `grep -rn dompurify apps/web/src` → no imports; `react-markdown` escapes by default, no `dangerouslySetInnerHTML` path needs a sanitizer. | `npm uninstall`; lockfile updated. |
| All backend modules (`ocr.py`, `page_images.py`, `llm_utils.py`, `model_registry.py`, `onnx_*`, `auth_service.py`, …) | KEEP | Every module traced to importers or test mocks (e.g. `ocr` → `tests/test_ocr.py` + `conftest.py`; `llm_utils` → `local_llm.py`, `graph.py`, `generator.py`; `model_registry` → 6 callers). Nothing backend was dead. | No backend deletions. |
| 6 bespoke page headers (`Claims/Evidence/Conflicts/KB/Trace/Settings`) | REFACTOR | Same pattern, 6 copies of eyebrow pill + `h1` + description + CTA. | Consolidated into `src/components/ui/PageHeader.jsx`; all pages render identical copy through one component (see Design System doc). |
| `⚠` (U+26A0) emoji in `DashboardPage` error banner | REPLACE | Every other icon is Lucide; emoji breaks the icon system. | Replaced with `<AlertTriangle>` (Lucide). |
| `SettingsPage` status badge (`div` wrapper, no live region) | REFACTOR | Health status conveyed visually only. | Moved into `PageHeader` actions slot with `role="status" aria-live="polite"`. |

## 3. Architecture (no deletions beyond verified bloat)

- No REST/LangGraph/Mongo/Qdrant contract changed; `apps/api/` untouched.
- No dependency added; 2 dead frontend deps removed → `node_modules` −2 packages, zero test impact.
- New code is additive only: `src/styles/design-tokens.css`, `src/components/ui/{PageHeader,Card,Badge,index}`. No file renamed, no import path broken (alias `@/` unchanged).

## 4. Performance

| Metric | Before | After | Δ |
|---|---|---|---|
| `dist/` size | 12 MB | 6.7 MB | **−44%** (audit PNGs no longer shipped) |
| JS chunks | unchanged (logic identical) | unchanged | 0 |
| `node_modules` pkgs | baseline | −2 (`htmlparser2`, `dompurify`) | smaller install |

## 5. Validation (after each batch)

- Backend: `pytest -q` → **761 passed**, coverage 79.07%, `ruff check app/` → clean.
- Frontend: `vitest` → **33/33**, `eslint --max-warnings 0` → clean, `vite build` → success.
- E2E (Playwright, live API): **2/2** (route guard, register→login→dashboard, SEC-H1 revocation).
- Browser QA (Chromium, 12 routes + mobile viewport): **0 console errors**, **0 horizontal overflow**.

## 6. Deferred / out of scope

- `follow-redirects` high advisory (transitive via `axios`) — pre-existing, pinned by `axios@^1.7.3`; left for the next `axios` bump rather than forcing `npm audit fix` churn.
- No light theme shipped — see Design System doc (tokens laid, dark canonical).
