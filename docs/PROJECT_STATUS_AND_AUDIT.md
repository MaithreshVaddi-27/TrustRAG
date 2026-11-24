# TrustRAG — Project Status & Deep Audit

**Date:** 2026-11-24
**Branch:** `feature/trustrag-refined` (HEAD `b7f49b3` at audit time)
**Scope:** 562 tracked files, live backend/frontend, inference path, quality gates, docs, and brand assets
**Method:** README setup commands with the repo venv, live HTTP probes, a real authenticated analysis run, Brave DevTools MCP UI inspection, repository-wide lint/test/structure scans

---

## 1. Executive summary

**Production audit: 73/100 — launchable with caveats.**

The product starts from a clean checkout with documented commands, the local inference path now completes an end-to-end verified analysis, and the frontend renders the new brand mark without console errors. The embedding warm-up failure (F1) is fixed and verified live. Remaining caveats are a document-upload status mismatch, 28 pre-existing backend test failures, and unpushed commits.

Strengths, briefly: strict dark design system with one accent; claim-level NLI verification with evidence integrity; authentication on sensitive routes; no tracked secrets or runtime state; complete brand kit and usage docs.

---

## 2. Runtime verification performed

### 2.1 Services and setup

| Check | Result |
|---|---|
| `./scripts/setup/setup.sh` (README step 4, repo venv) | 14 checks passed, 0 need attention |
| MongoDB `:27017` | Listening (pre-existing process) |
| Ollama `:11434` | Started by `apps/api/scripts/start_local_services.sh` |
| API `:8000` | Started by the same script; `GET /api/v1/health` → `{"status":"ok","app":"TRUSTRAG","version":"0.1.0"}` |
| Frontend `:5173` | Started with `npm run dev`; HTTP 200 |
| `GET /api/v1/health/detailed`, `/models/providers` | `401 UNAUTHORIZED` — expected, routes are authenticated |
| Ollama direct inference | `gemma3:1b` replied `READY`; 1.7 s including model load |
| `.env` | Present; `JWT_SECRET` configured; never committed |

### 2.2 Full inference run

A real user was registered through the API, a knowledge base created, a small text document uploaded, and an analysis run polled to completion.

- **First run:** `status: failed` with `analysis.outage` → `retrieval.outage`. API log traced it to an ONNX embedding load failure inside the API process, despite `bootstrap.py` reporting both ONNX weights present and L2-verified. A direct venv call to `get_embedding_model()` succeeded.
- **After restarting the API:** the second run completed in about 9 seconds:
  - Answer: `The default request rate limit is 50 requests per second per tenant.`
  - Claims: 1 × `SUPPORTED`
  - Evidence: 1 × `VERIFIED`, retrieval score `0.849`
  - Trace: `analysis.started → retrieval.started → retrieval.self_heal_batch → retrieval.completed → generation.completed → claims.started → claims.verified → analysis.completed`
- `GET /analyses/{id}/detail` returned `verdict_status: null` and `reliability_score: null` even though the claim was verified.

### 2.3 Frontend (Brave DevTools MCP)

- Landing page loaded at `http://localhost:5173/`; accessibility snapshot shows the main landmark, heading, navigation, both CTAs, and the verification-ledger section.
- Screenshot confirmed the dark Obsidian theme, Chrome Silver type, Laser Crimson focal button, and the new Overlap mark in the navbar.
- Console: 3 messages, all Vite/React info or debug; **0 errors**.

### 2.4 Manual UI pass (Brave DevTools MCP)

Driven in the real browser against the live stack:

| Flow | Result |
|---|---|
| Sign out → register → redirect to dashboard | Passed; new account created through the form |
| Sign out → sign in with that account | Passed; redirected to dashboard |
| Knowledge bases → New collection | Passed; collection appeared with name and description |
| Upload `.txt` into the collection | Passed; document appeared, detail page shows `Indexed`, SHA-256 hash and vector space |
| Playground → run query | Passed; `100% TRUSTED`, 1 evidence chunk, 1 claim, grounded answer |
| Answer / Evidence / Claims / Trace tabs | All rendered; trace shows retrieval 182 ms, generation 2110 ms, then claims verified |
| Dashboard after the run | 1 KB, 1 document, 1 analysis, mean reliability 100%, 1 supported claim |
| Console across every step | 0 errors |

One minor UI observation: the document list badge still read `Indexing` after ingestion completed and only showed `Indexed` on the document detail page or after navigation. Added as I5.

---

## 3. Phase status

| # | Phase | Status | Evidence |
|---|---|---|---|
| 0 | Setup & structure | Green | 14/14 setup checks; 562 tracked files; naming audit found no scratch/space/unicode names; runtime state untracked |
| 1 | Runtime services | Green | MongoDB, Ollama, API and Vite all reachable; health OK |
| 2 | Ingestion & data | Amber | Upload returned 201 while the first ingestion failed internally; retry returned 409 |
| 3 | Retrieval | Amber | First query hit an embedding warm-up outage; later run scored 0.849 and used self-heal batching |
| 4 | Generation & NLI verification | Green | One SUPPORTED claim, one VERIFIED evidence, full trace |
| 5 | Reliability scoring | Amber | `verdict_status` and `reliability_score` null on a completed run |
| 6 | Frontend & brand | Green | Brave DevTools snapshot/screenshot, 0 console errors, lint clean, 82/82 tests |
| 7 | Quality gates | Amber | `ruff check .` clean; backend suite on this host (Python 3.11.15) 28 failed / 797 passed / 4 skipped, identical at unmodified HEAD; `docs/README.md` records 813 passed + 4 skipped in CI, so local/CI drift needs reconciling |
| 8 | Docs & handover | Green | README, DESIGN.md, dark-luxury docs, backend changelog, brand README and board all present |
| 9 | Security & operations | Amber | Auth on sensitive routes, secrets ignored, CI workflows present; remote CI status and rollback drill not checked |

---

## 4. Improvement backlog

### Fix — do first

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| F1 | P1 | Retrieval / ops | First embedding load in a fresh API process can fail with a retrieval outage, even with weights present | Make warm-up synchronous with a bounded retry, surface the underlying exception, and mark ingestion as failed rather than silently continuing |
| F2 | P1 | Ingestion API | `POST /documents` returned 201 while ingestion had failed; re-uploading the same file returned 409 | Return an ingestion status the client can poll, and allow re-ingest of a document whose ingestion failed |
| F3 | P1 | Quality gate | 28 backend tests fail on this checkout; identical count at unmodified HEAD, so pre-existing | Triage by module (verification, upgrade phases, hardware) and fix or quarantine with documented reasons |
| F4 | P2 | Git hygiene | `b7f49b3` is not pushed | Push when the owner is ready |

### Update

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| U1 | P2 | Reliability contract | Completed run has verified claims but null `verdict_status` / `reliability_score` | Define and document when the score is emitted; align the API schema and UI badge |
| U2 | P2 | README | Quickstart does not explain first-run embedding warm-up behaviour or the exact recovery step | Add a short "first run" note referencing `bootstrap.py` and the health endpoint |
| U3 | P3 | Ops docs | No rollback drill was performed in this audit | Add a short rollback verification to the deployment runbook |

### Refine

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| R1 | P2 | Error reporting | `ConfigurationError.detail` is capped at 300 chars and not exposed by the API | Add a correlation id or a safe debug field so warm-up failures are diagnosable |
| R2 | P3 | Landing content | `recall@K 0.963` is a static figure in the UI | Keep, but document provenance next to the number or link the methodology from it |
| R3 | P3 | API surface | `/api/v1/models/providers` requires auth, so anonymous health checks cannot see inference readiness | Add an unauthenticated readiness summary that exposes only provider status, not model details |

### Refactor

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| C1 | P3 | Memory utilities | `check_and_enforce_memory_guard` is documented in the backend changelog as having no production caller | Decide explicitly: wire it in or remove it with its tests |
| C2 | P3 | Tailwind naming | Legacy `cyan-400` classes still appear in `traceEvents.js`; they map to silver in `tailwind.config.js` | Replace with `silver-400` for naming consistency (no visual change) |
| C3 | P3 | Design docs | `docs/design/*.svg` concept boards still show the older "T" mark | Label them as historical or archive them; the canonical system is `docs/design/dark-luxury/` |

### Improve

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| I1 | P2 | E2E coverage | No CI-safe test covers register → KB → document → analysis with mocked embeddings | Add one deterministic smoke test to protect the launch-critical path |
| I2 | P2 | CI verification | Workflows exist (`.github/workflows/ci.yml`, `security.yml`) but remote run status was not checked | Check the latest run on the branch before any release |
| I3 | P3 | Responsive UI | Only desktop viewport was inspected in this audit | Add a 390 px / 320 px Playwright or Brave DevTools pass |
| I4 | P3 | Load/resilience | k6 smoke and resilience scripts were not run in this audit | Run them against the live stack before a public launch |
| I5 | P3 | Frontend | Document list badge stayed `Indexing` after ingestion finished; detail page was correct | Refresh the document row when ingestion reaches a terminal state |

---

## 5. Evidence checked

- README setup flow, port registry, `.env` key presence (values redacted), repo venv
- `apps/api/scripts/start_local_services.sh`, API log at `${TMPDIR}/trustrag_api.log`
- Live HTTP: `/api/v1/health`, `/health/detailed`, `/models/providers`, `/analyses/*`, `/claims`, `/evidence`, `/trace`, `/detail`
- Ollama `/api/tags` and `/api/generate` with the configured `gemma3:1b`
- Brave DevTools MCP: page snapshot, screenshot, console messages
- `ruff check .`, `npm run lint`, `npm test` (82/82), backend `pytest -q` and a stashed HEAD baseline
- Naming/structure scan of all 562 tracked paths; `git status`, `git log`, `git check-ignore`

## 6. Evidence missing

- Latest remote CI run status and deployment URL
- Mobile-viewport UI check, k6 load results, and resilience harness results
- Rollback drill on a staging environment
- Security scan output (`pip-audit`, `npm audit`) for this revision

## 7. Next action

Fix **F1** first: make embedding warm-up deterministic and surface its real error. Then address **F2** so ingestion failures are visible to clients, and **F3** to restore a green backend gate.

---

*This is an engineering triage document, not a compliance or security certification. Re-run the checks after each fix and update the phase table.*
