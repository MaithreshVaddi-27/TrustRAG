# TRUSTRAG Repository Fix Plan

## Phase 1: P1 Fixes (Lint & CI Pipeline Restoration)
1. **Frontend Lint (AUD-01, AUD-02, AUD-03)**:
   - `apps/web/src/pages/ClaimsPage.jsx`: Remove unused `ClaimStateBadge` and `Filter`.
   - `apps/web/src/pages/ConflictsPage.jsx`: Remove unused `GitMerge`.
   - `apps/web/src/pages/DashboardPage.jsx`: Remove unused `FileText`.
   - Verification: Run `npm run lint` in `apps/web` (expect 0 errors, exit code 0).

2. **Backend Lint (AUD-04, AUD-05, AUD-06, AUD-07, AUD-08)**:
   - `apps/api/app/ingestion/sparse_vector.py`: Remove unused `re` and move `from app.ingestion.preprocessor import ...` to file top.
   - `apps/api/app/generation/generator.py`: Replace `getattr(item, "text")` with `item.text`.
   - `apps/api/app/agent/graph.py`: Replace `getattr(item, "text")` with `item.text`.
   - `apps/api/app/ingestion/preprocessor.py`: Convert `ZoneType` to `StrEnum` and replace ambiguous EN DASH `–` with standard `-`.
   - Verification: Run `ruff check app/ tests/` (expect zero errors).

---

## Phase 2: P2 Fixes (Type Safety, Security Headers, DB Indexing)
1. **Backend Formatting & Type Safety (AUD-09 to AUD-14)**:
   - Wrap long lines (>100 chars) in `evidence.py`, `knowledge_bases.py`, `verifier.py`, and `analysis_service.py`.
   - In `app/core/security.py`: Import `ExpiredSignatureError` and `JWTError` from `jose.exceptions`.
   - In `app/retrieval/retriever.py`: Satisfy typing for Qdrant client methods.
   - Verification: Run `mypy app/` and `ruff format --check app/`.

2. **Defensive Security Headers Middleware (AUD-15)**:
   - In `apps/api/app/main.py`: Add standard HTTP security headers middleware (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`).
   - Verification: Inspect curl response headers on `GET /api/v1/health`.

3. **Database Performance Indexing (AUD-16)**:
   - In `apps/api/app/db/mongodb.py`: Add `Collections.DOCUMENT_CHUNKS` index on `[("document_id", pymongo.ASCENDING)]`.
   - Verification: Restart app and verify log: `MongoDB indexes created/verified`.

---

## Phase 3: P3 Fixes (UI/UX A11Y & Documentation Sync)
1. **Frontend A11Y & User Experience (AUD-17, AUD-18)**:
   - In `PlaygroundPage.jsx` and `KnowledgeBasesPage.jsx`: Replace synchronous `alert()` with accessible inline dismissible error notification banners.
   - Verification: Run `npm run build` and test in browser.

2. **Documentation Alignment (AUD-19)**:
   - Update `TRUSTRAG_specs.md` and `README.md` to document:
     - Batch NLI Verification (reducing quota usage from N to 1 API call).
     - Document Zoning (`title`, `header`, `summary`, `body`, `metadata`).
     - Porter Stemmer & Lexical Analysis Pipeline.
   - Verification: Review markdown formatting and link integrity.
