# TrustRAG — Second-Pass Fixes & Validation

**Date:** 2026-11-07

## Fixes applied
1. `app/rag/generation/generator.py`: renamed `_FILLER_WORDS` → `_filler_words` (N806); split long prompt line (E501).
2. `app/rag/verification/verdict.py`: shortened docstring (E501).

## Validation
- `ruff check app/` → All checks passed.
- `pytest -q` → 757 passed, 4 skipped, coverage 78.71%.
- Frontend: `npm run lint` clean, `npm run build` succeeded.
- Browser QA: no console errors; all network 200.

## Deferred
- See FUTURE_IMPROVEMENTS.md (P3).
