# TrustRAG — Phase 1 Remaining Technical Debt

**Date:** 2026-11-08 · **Branch:** `ui-redesign`  
**Status:** Residual issues intentionally left for a future phase (or accepted).

---

## 1. Pre-existing issues (not introduced by this cleanup; reported separately)

### Backend format (3 files, baseline)

These files were already unformatted before Phase 1 and were left untouched because they are outside the verified changes I made:

- `apps/api/app/api/v1/schemas/analysis.py:107` — long `if` statement
- `apps/api/tests/eval/test_eval_metrics.py:209` — blank line / def formatting
- `apps/api/tests/test_api_contract.py:387` — multi-line `pathlib.Path` call

They do not fail `ruff check` (only `ruff format --check`), so CI lint passes. Reformatting them is cosmetic and optional.

### Backend coverage headroom

Coverage is **78.67%**, just 0.67 points above the 78% gate (`--cov-fail-under=78` in `pyproject.toml`). Any new backend work should add tests to stay above the floor.

### Frontend dependency advisory

`follow-redirects` (high) is transitive via `axios@^1.7.3`, already pinned. Deferred to the next `axios` bump; a forced `npm audit fix` risks dependency churn without a security regression to fix (pre-existing, documented in prior engineering report).

### Orphan scripts decision boundary

Removed verified-orphan `calibrate_local_judge.py` and `prune_llm_cache.py` (zero references).

Kept despite limited direct references, because they are wired into CI/tests:
- `scripts/run_ragas_eval.py` — imported by `apps/api/tests/eval/test_ragas_runner.py`
- `scripts/typecheck_ratchet.sh` — invoked by `.github/workflows/ci.yml` (mypy ratchet)
- `scripts/apply_ports.py` — CI port-registry drift check

No changes to CI were required by Phase 1.

---

## 2. Deliberately preserved (user's in-progress branch work — not touched)

Per constraints, existing Git changes and user work were never discarded:

- `apps/web/src/components/landing/AnimatedPipeline.jsx` (untracked)
- `apps/web/src/components/landing/ProblemSolutionNarrative.jsx` (untracked)
- `apps/web/src/components/ui/` (untracked): `Badge`, `Button`, `Card`, `PageHeader`, `index.js` — additive new-component surface; `PageHeader`/`Card`/`Badge` are defined but not yet imported by pages, which is intentional in-progress work
- `apps/web/src/styles/design-tokens.css` (untracked)
- `docs/design/` (untracked)
- `docs/engineering/` (untracked)
- `screenshots/` (untracked)

None of these block CI (frontend lint, tests, and build all pass with them present).

---

## 3. Design-system items (deferred, out of scope for Phase 1)

- Light theme — dark is canonical; tokens are ready (see `docs/design/ULTRA_PREMIUM_DESIGN_SYSTEM.md`).
- `ui/` components not yet wired into pages — additive only, no removal.

These are explicit out-of-scope for Phase 1 (no feature development / UI redesign / design-system changes).

---

## 4. Recommended follow-ups (not part of Phase 1)

| Item | Why | Suggested phase |
|---|---|---|
| Reformat the 3 baseline backend files | Cosmetic consistency | Next lint pass |
| Add backend tests to raise coverage above ~80% | Margin above 78% gate is thin | Next backend work |
| Resolve `follow-redirects` advisory on next `axios` bump | Supply-chain hygiene | Dependency maintenance |
| Wire `PageHeader`/`Card`/`Badge` into pages | Complete the additive component surface | Feature work |
| Re-run `scripts/apply_ports.py --check` after any port change | Keep canonical registry in sync | Ops |

---

## 5. Nothing left unverified

All Phase 1 success criteria met: clean repository (verified dead code removed), reduced duplication, consistent configuration, preserved functionality, passing checks, and residual issues documented above.
