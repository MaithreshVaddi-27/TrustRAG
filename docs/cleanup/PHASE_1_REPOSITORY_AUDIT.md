# TrustRAG — Phase 1 Repository Audit

**Date:** 2026-11-08 · **Branch:** `ui-redesign` · **Role:** Principal Software Engineer  
**Scope:** Full repository audit before cleanup (discover + audit phases complete).

---

## 1. Repository map

| Layer | Location | Tech | Notes |
|---|---|---|---|
| Backend | `apps/api/` | FastAPI 0.115, Python 3.11–3.12 | 75 tracked source modules |
| Backend tests | `apps/api/tests/` | pytest | 69 tracked test files incl. `tests/eval/` |
| Frontend | `apps/web/` | React 18, Vite 6, Tailwind 3 | 95 tracked src files |
| Config | `config/ports.yaml`, `apps/api/config/models.yaml` | YAML | canonical port registry + model/source-of-truth |
| Scripts | `scripts/` | Python / shell | 13 tracked scripts |
| Docs | `docs/` | Markdown | architecture, audit, deployment, design, evaluation |
| CI | `.github/workflows/{ci,security}.yml` | GitHub Actions | full gate: lint, test, build, e2e, docker, compose |

## 2. Quality baseline (before changes)

| Gate | Tool | Result |
|---|---|---|
| Backend tests | `pytest` | **757 passed, 4 skipped**, coverage 78.67% (gate 78%) |
| Backend lint | `ruff check` | **3 errors** (`generator.py` N806, `generator.py` E501, `verdict.py` E501) |
| Backend format | `ruff format --check` | **5 unformatted files** |
| Frontend tests | `vitest run` | **33 passed** (8 files) |
| Frontend lint | `eslint` | **3 errors** (all in untracked landing files on `ui-redesign`) |
| Frontend build | `vite build` | success |

Pre-existing failures (not introduced by this cleanup):
- 3 backend files unformatted at baseline (`analysis.py`, `test_eval_metrics.py`, `test_api_contract.py`).
- `ci.yml` gate already required all jobs green; `typecheck_ratchet.sh` is wired into CI.

## 3. Verified dead code (zero references anywhere in repo)

### 3a. Frontend public assets (never committed clean on this branch)

| Asset | Count | Est. size | Evidence |
|---|---|---|---|
| `apps/web/public/styles/*.css` | 6 | ~0.1 MB | Zero imports/references; `index.html` and `src/index.css` only use `src/styles/` |
| `apps/web/public/audit-*.png` | 11 | ~5.4 MB | Zero code references; old audit screenshots |

Both were removed on a prior branch (`reliability-phase1`) but remain tracked on `ui-redesign`. Verified via repo-wide grep: no source, doc, or config references.

### 3b. Frontend dependencies

| Dep | Declared in | Evidence |
|---|---|---|
| `dompurify` ^3.4.17 | `apps/web/package.json` | Zero imports in `apps/web/src`; `react-markdown` escapes by default, no `dangerouslySetInnerHTML` |
| `htmlparser2` ^12.0.0 | `apps/web/package.json` | Zero imports in `apps/web/src` |

### 3c. Orphan Python scripts

| Script | Evidence |
|---|---|
| `scripts/calibrate_local_judge.py` | Repo-wide grep returns zero references (only its own file) |
| `scripts/prune_llm_cache.py` | Repo-wide grep returns zero references (only its own file) |

Kept (referenced): `run_ragas_eval.py` (imported by `tests/eval/test_ragas_runner.py`), `typecheck_ratchet.sh` (invoked by `.github/workflows/ci.yml`), `apply_ports.py` (CI port-drift check), `bootstrap.py`, `ensure_onnx_models.py`, `export_bge_onnx.py`, `setup.sh`, `start_local_llm.sh`, `start_mlx_server.sh`, `eval_provider.sh`, `run_baseline_eval.py`, `e2e_manual_verify.sh`.

## 4. Lint / format defects found

Backend (`apps/api`):
1. `app/rag/generation/generator.py:468` — N806 `_FILLER_WORDS` (module-level constant in function) + E501 line-too-long in generator prompt docstring.
2. `app/rag/verification/verdict.py:72` — E501 line-too-long in docstring.

Frontend (`apps/web`):
1. `components/landing/AnimatedPipeline.jsx:206` — `scrollProgress` assigned but never used.
2. `components/landing/ProblemSolutionNarrative.jsx:4` — `ShieldAlert`, `Check` imported but never used.

These untracked landing files blocked frontend lint (CI gate `max-warnings 0`).

## 5. Dependency & duplication analysis

Backend `pyproject.toml` dependencies were cross-checked against imports — all declared runtime deps are used. The `transformers` package is intentionally declared (tokenizer for ONNX bootstrap; torch-free at runtime). The optional `cloud` extra (`langchain-google-genai`, `tavily-python`) is opt-in and unused by default.

No circular imports detected across the 75 backend modules; every module has at least one importer or test mock.

Frontend: `@tanstack/react-query`, `axios`, `lucide-react`, `motion`, `recharts`, `date-fns`, `clsx`, `react-markdown` all have imports. Removed `dompurify`/`htmlparser2` (see 3b).

No duplicated service implementations found (each service module has a single implementation and its callers traced).

## 6. Stale / redundant documentation

Existing docs are current and consistent with code:
- `docs/TRUSTRAG_specs.md` — source of truth, up to date.
- `docs/audit/AUDIT_2026-10-03.md`, `docs/audit/FRONTEND_AUDIT_2026-11-04.md` — point-in-time audit reports, preserved as history.
- `docs/engineering/CODEBASE_CLEANUP_REPORT.md` and `FINAL_VALIDATION_REPORT.md` — describe cleanup performed on a *different* branch (`reliability-phase1`); not merged into `ui-redesign`. Their verified dead-asset removals are reproduced here on this branch.
- `docs/design/` and `docs/engineering/` are untracked on this branch (user's in-progress design work) — left untouched per constraints (do not discard existing Git changes / user work).

No stale documentation was removed in this phase.

## 7. Summary of audit findings (to be cleaned)

| # | Finding | Verdict | Action |
|---|---|---|---|
| 1 | `public/styles/*.css` (6) | REMOVE | deleted |
| 2 | `public/audit-*.png` (11) | REMOVE | deleted |
| 3 | `dompurify`, `htmlparser2` | REMOVE | uninstalled |
| 4 | `scripts/calibrate_local_judge.py` | REMOVE | deleted |
| 5 | `scripts/prune_llm_cache.py` | REMOVE | deleted |
| 6 | Backend N806 + 2× E501 | FIX | fixed |
| 7 | Frontend 3 unused-var/import errors | FIX | fixed |
| 8 | `ui/` components (PageHeader, Card, Badge) defined but unused | KEEP | additive new-component work on branch; not dead (referenced by index.js export surface) |

## 8. What was deliberately NOT touched

- `docs/design/`, `docs/engineering/`, `screenshots/`, untracked landing components (`AnimatedPipeline.jsx`, `ProblemSolutionNarrative.jsx`) — user's in-progress branch work; constraints prohibit discarding it.
- Backend API contracts, auth, DB behavior, RAG algorithms, evaluation contracts, production configs — all preserved.
- Migrations, fixtures, model weights (`.model_cache/`), user data — never deleted.
- Pre-existing uncommitted changes — preserved.
