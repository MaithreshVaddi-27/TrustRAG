# QA Audit — TrustRAG ui-redesign

**Scope:** 18 test files + conftest.py at `apps/api/tests`, CI at `.github/workflows`, cross-referenced against `apps/api/app`.
**Test inventory:** 103 tests total. API layer (FastAPI TestClient): 15 tests (~15%) across test_auth, test_kb, test_analyses, test_experiments, test_health. Pure unit: 88 (~85%). **CI executes 23/103 (~22%).**

---

## Critical

**[Critical] ~~CI runs only 1 of 18 test files — 80 tests never gate merges~~** ✅ Fixed
- Location: `.github/workflows/ci.yml:72-74`
- Fix: Changed `pytest tests/test_config.py -v --no-header` → `pytest tests/ -v --no-header` — runs all 103 tests across 17 test files. All tests pass offline with mock-based dependency_overrides + dummy env vars.

## High

**[High] Five endpoint modules have zero test coverage** (Confirmed)
- Location: missing tests for `app/api/v1/models.py`, `conflicts.py`, `evidence.py`, `claims.py`, `documents.py` (GET)
- Evidence: Repo-wide grep for those route paths in tests returns a single match — `test_kb.py:128: client.delete(f"/api/v1/documents/{doc_id}")` (DELETE only). Untested: `models.py` GET /providers (:18), GET /hardware (:190), POST /memory/trim (:200); `conflicts.py` GET "" (:18); `evidence.py` GET "" (:19); `claims.py` GET "" (:19); `documents.py` GET /{doc_id} (:22).
- Impact: The entire trust/verification readout surface (conflicts, evidence, claims) — the product's differentiating feature — can 500 or return wrong data silently. The invalid-ObjectId `NotFoundError` branch in documents.py:44 is also untested.
- Recommendation: One test file hitting all 5 routers with mocked services; include GET /documents/{invalid-objectid} → 404 and POST /memory/trim → 200.

**[High] No E2E test of the core flow: upload → ingest → search → answer** (Confirmed)
- Location: missing: `app/api/v1/knowledge_bases.py:83` (`upload_document_endpoint`, `file: UploadFile = File(...)` at :86)
- Evidence: `grep -rn "UploadFile\|/upload" apps/api/tests/` returns zero matches. Upload endpoint, `kb_service.add_document` (kb_service.py:126), and their wiring to ingestion/search/agent are never exercised together.
- Impact: The single most important user journey is unverified end to end — multipart handling, chunking, embedding, upsert, and answer generation are only tested in isolated mocks; wiring bugs (wrong field names, missing await, serialization) escape to prod.
- Recommendation: One TestClient test: POST multipart to /knowledge_bases/{id}/documents with mocked Qdrant + embeddings, then POST the query endpoint, assert a non-error answer payload.

**[High] Positive-path bias: only one 4xx assertion in the entire suite, zero 5xx** (Confirmed)
- Location: `apps/api/tests/test_auth.py` (whole file), `apps/api/tests/test_kb.py:134-149`
- Evidence: Suite's only negative API test is the IDOR check in test_kb.py:134-149 (asserts 403). test_auth.py (3 tests) has zero negatives — no duplicate-register 409, no wrong-password 401, no invalid-token 401, no short-password 422. Only other negative tests: 5 pydantic ValidationError/KeyError tests in test_config.py:184-188 — the one file CI runs.
- Impact: Auth regressions (the security-critical path), expired/malformed JWT handling, and invalid-input handling are completely unguarded.
- Recommendation: 4 tests in test_auth.py: duplicate email → 409, wrong password → 401, garbage Authorization header → 401, 5-char password → 422. ~15 lines.

**[High] Zero frontend tests** (Confirmed)
- Location: `apps/web/package.json`
- Evidence: `scripts` = dev, build, preview, lint, lint:fix only. No vitest/jest/playwright/cypress in devDependencies; ci.yml runs only frontend-lint and frontend-build.
- Impact: Any UI logic regression (query state, SSE stream parsing, error rendering) ships undetected; build passing does not verify behavior.
- Recommendation: Add vitest with one smoke test per page component (renders + fires initial query hook), plus the test script to package.json.

## Medium

**[Medium] conftest.py has zero fixtures — every API test file rebuilds mock setup** (Confirmed)
- Location: `apps/api/tests/conftest.py` (20 lines, only `os.environ.setdefault` calls); duplicated in test_analyses.py:19-62, test_kb.py:19-47, test_experiments.py:19-32, test_auth.py, test_health.py
- Evidence: Each file re-defines mock user/KB documents and its own `dependency_overrides[get_current_user]` autouse fixture.
- Impact: Divergent mock shapes across files mask real schema drift; a user-model change requires editing 5+ files, so mocks silently rot.
- Recommendation: Hoist `mock_user_doc`, `mock_kb_doc`, and the auth dependency override into conftest.py as named fixtures.

**[Medium] Core modules with zero direct tests: rate_limiter, logging, exceptions, security, mongodb, qdrant, reranker, generator** (Confirmed)
- Location: missing: `app/core/rate_limiter.py` (15 lines), `app/core/logging.py` (103), `app/core/exceptions.py` (145), `app/core/security.py` (70), `app/db/mongodb.py` (300), `app/db/qdrant.py` (148), `app/retrieval/reranker.py` (83), `app/generation/generator.py` (150)
- Evidence: `grep -rn "rate_limiter\|reranker\|app.core.logging\|app.core.exceptions" apps/api/tests/` returns zero matches. mongodb/qdrant appear only as patch targets, never behavior-tested.
- Impact: Rate limiting (DoS protection) is entirely untested; security.py (70 lines of hashing/token logic) is only exercised transitively.
- Recommendation: Priority: 3 tests for rate_limiter (under/over limit, window reset), 2 for security.py (hash verify round-trip, bad token rejection).

**[Medium] test_local_llm health checks execute real subprocess, HTTP, and filesystem calls** (Confirmed)
- Location: `apps/api/tests/test_local_llm.py:62-78`
- Evidence: `check_ollama_status` runs `ollama list` via `asyncio.create_subprocess_exec` (local_llm.py:571-577, 4s timeout), an HTTP GET to `/api/tags` with 3s timeout (local_llm.py:644-652), and `discover_hf_hub_gguf_models` scans `~/.cache/huggingface/hub` (local_llm.py:620). Tests pass offline only because hardcoded lists (`primary_ollama_llms = ["granite4.2:3b-q4_K_M", ...]`, local_llm.py:655) are always merged into the result (:657-665).
- Impact: Slow, machine-dependent, side-effect-prone tests; assertions verify hardcoded constants rather than detection logic, so discovery code can break without failing tests. Also the blocker for enabling the full suite in CI.
- Recommendation: Patch `discover_ollama_cli_models` and the HTTP call in these tests; assert merge logic with controlled fake inputs.

**[Medium] sleep-based timing test in search suite** (Confirmed)
- Location: `apps/api/tests/test_search_mcp.py:155-158`
- Evidence: `def _hanging_call(...): time.sleep(1.0)` with `SEARCH_TIMEOUT_SECONDS` patched to 0.05
- Impact: Guaranteed 1s wall-clock delay per run; under a loaded CI runner the 0.05s timeout could race thread scheduling → occasional flakes.
- Recommendation: Drop the sleep to 0.2s (timeout is 0.05s, any delay > 0.05 works) or make it event-based.

**[Medium] test_health.py never tests the Qdrant-degraded branch** (Confirmed)
- Location: `apps/api/tests/test_health.py:19, 40`
- Evidence: Both tests patch `qdrant_health_check` with `return_value=True` (the second is the "degraded" test but only degrades Mongo).
- Impact: The Qdrant-degraded status path (partial-outage reporting) is dead code as far as tests are concerned.
- Recommendation: Add one test with `qdrant_health_check` returning False asserting the degraded payload.

**[Medium] Mock-the-mock patterns: agent, verification, and ingestion pipeline tests assert mock wiring, not logic** (Confirmed)
- Location: `apps/api/tests/test_agent.py` (all 8 tests patch retrieve_hybrid_chunks, rerank_candidate_chunks, audit_evidence_integrity, execute_claim_verification, get_verification_model); test_verification.py (mocks decompose + verify + verdict mapping); test_ingestion.py pipeline test asserts `upsert` called once / `update_one` twice
- Impact: These tests verify that mocks return what they were configured to return; a changed signature, wrong argument passed to a real dependency, or reordered pipeline step passes all tests. graph.py (764 lines) has only node-level mock tests, no compiled-graph flow test.
- Recommendation: One test running the compiled graph end-to-end with only the outermost boundaries mocked (LLM + vector store), asserting the final state dict.

**[Medium] Memory-guard test only exercises the trivially-healthy path** (Confirmed)
- Location: `apps/api/tests/test_hardware.py:53`
- Evidence: `check_and_enforce_memory_guard(max_rss_mb=100000.0)` — 100 GB, far above any threshold; degraded/critical branches never hit.
- Impact: The guard that protects production from OOM crashes has zero test evidence it ever triggers.
- Recommendation: Two tests: one just over the degrade threshold, one over critical, asserting the enforcement action.

## Low

**[Low] No type checking in CI** (Confirmed)
- Location: `.github/workflows/ci.yml` (jobs: backend-lint, backend-test, backend-config-validate, frontend-lint, frontend-build, ci-gate)
- Evidence: No mypy/pyright job; pyproject.toml does not configure them.
- Impact: Type regressions in the async codebase surface only at runtime.
- Recommendation: Add a mypy job on `app/` (non-strict initially).

**[Low] pip-audit first pass is report-only; one vuln permanently ignored** (Confirmed)
- Location: `.github/workflows/security.yml`
- Evidence: First invocation `|| true` (produces pip-audit-report.json artifact, never fails), second strict; both `--ignore-vuln PYSEC-2026-1325`.
- Impact: The strict gate is real, but the ignored vuln has no expiry comment/issue link, so it can silently outlive its justification.
- Recommendation: Add a `# TODO(issue-xyz, expires YYYY-MM-DD)` comment on the ignore.

**[Low] pytest-cov installed but no coverage measurement or gate anywhere** (Confirmed)
- Location: `apps/api/pyproject.toml` (`pytest-cov>=5.0.0`); ci.yml has no `--cov` flags
- Impact: Coverage is invisible, so gaps like the 5 untested endpoint modules can't be tracked or trended.
- Recommendation: Add `--cov=app --cov-report=term` to the CI pytest step (no threshold gate initially).

**[Low] Critical modules have token coverage: 2 retrieval tests, 1 integrity test** (Confirmed)
- Location: `apps/api/tests/test_retrieval.py` (2 tests), `apps/api/tests/test_integrity.py` (1 test)
- Evidence: Retriever's full RRF hybrid path gets 2 exact-score assertions; evidence integrity (SHA-256 audit, the anti-tamper guarantee) gets a single VERIFIED/CORRUPTED/missing triple in one test.
- Impact: Regressions in ranking logic or evidence hashing — both correctness-critical for a trust product — are barely guarded.
- Recommendation: 3 more retriever tests (empty index, single-source, tie-breaking) and 2 more integrity tests (tampered hash, missing file).

---

## QA Score: 3.5 / 10

**Justification:** The pure-unit tests that exist are genuinely good — test_preprocessor (11 precise text/zone/weighting tests), test_config (the only negative tests, including secret-scanning of models.yaml), and test_search_mcp's `sanitize_url` test (:122-149) is exemplary security coverage (javascript:/data:/file: URIs, SSRF private IPs, cloud metadata endpoints). But the score is dragged down by one structural failure: **CI gates on 22% of the suite** (23/23 of which is test_config.py), so the 85% of tests that do exist provide zero merge protection. Layered on top: 5 untested endpoint modules, no E2E of the core flow, one 4xx assertion in the whole suite, zero frontend tests, and mock-the-mock patterns in the agent/verification tests. The suite is better written than it is deployed — its value is currently ~1/4 realized.

## Top 5 quick wins (cheapest, highest value)

1. **ci.yml:74 → `pytest -v`** — one-line change gating all 103 tests (all mock-based and offline-passing except the 2 local_llm health tests; patch those per the Medium finding first). Biggest risk-reduction per character changed.
2. **Negative auth tests** (~15 lines in test_auth.py): duplicate register 409, wrong password 401, invalid token 401, weak password 422. Closes the security-path gap immediately.
3. **One router file for the 5 untested endpoints** (models/conflicts/evidence/claims/documents GET, all mocked): ~60 lines covering the entire trust-readout surface plus the invalid-ObjectId 404.
4. **Hoist shared fixtures into conftest.py** (user doc, KB doc, auth override): deletion-only refactor that unifies 5 files' mocks and makes every subsequent API test cheaper to write.
5. **Single E2E test: mocked upload → ingest → search → answer** — exercises knowledge_bases.py:83 (the only completely untested write path) plus the wiring between kb_service, pipeline, and search that no other test touches.
