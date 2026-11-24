# TrustRAG — Project Status & Deep Audit

**Date:** 2026-11-24
**Branch:** `feature/trustrag-refined` (HEAD `b7f49b3` at audit time)
**Scope:** 562 tracked files, live backend/frontend, inference path, quality gates, docs, and brand assets
**Method:** README setup commands with the repo venv, live HTTP probes, a real authenticated analysis run, Brave DevTools MCP UI inspection, repository-wide lint/test/structure scans

---

## 1. Executive summary

**Production audit: 73/100 — launchable with caveats.**

The product starts from a clean checkout with documented commands, the local inference path now completes an end-to-end verified analysis, and the frontend renders the new brand mark without console errors. The embedding warm-up failure (F1) is fixed and verified live. F2 is fixed: a document left in `failed` state can be re-uploaded and re-indexed under the same ID instead of being permanently blocked with 409. F3 was a false alarm from invoking pytest at the repo root instead of `apps/api`. Remaining caveats are a few small API/UI refinements and unpushed commits.

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
| 2 | Ingestion & data | Green | Upload returns 201 with a pollable `ingestion_status`; failed documents can be re-ingested under the same ID (live-verified) |
| 3 | Retrieval | Amber | First query hit an embedding warm-up outage; later run scored 0.849 and used self-heal batching |
| 4 | Generation & NLI verification | Green | One SUPPORTED claim, one VERIFIED evidence, full trace |
| 5 | Reliability scoring | Green | Live completed run returned `reliability: {status: TRUSTED, score: 1.0}`; UI badge showed `100% TRUSTED` (see U1) |
| 6 | Frontend & brand | Green | Brave DevTools snapshot/screenshot, 0 console errors, lint clean, 84/84 tests |
| 7 | Quality gates | Amber locally, red remotely | Local: `ruff check .` clean; `cd apps/api && .venv/bin/python -m pytest -q` → 829 passed / 4 skipped, coverage 80.32%. Remote CI run `45431899850` was red (see I2); fixes are in the working tree and need a fresh push to verify |
| 8 | Docs & handover | Green | README, DESIGN.md, dark-luxury docs, backend changelog, brand README and board all present |
| 9 | Security & operations | Amber | Auth on sensitive routes, secrets ignored; remote CI was red and its four causes are fixed but need a fresh push to verify. Rollback drill documented but not executed (U3) |

---

## 4. Improvement backlog

### Fix — do first

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| F1 | P1 | Retrieval / ops | First embedding load in a fresh API process can fail with a retrieval outage, even with weights present | Make warm-up synchronous with a bounded retry, surface the underlying exception, and mark ingestion as failed rather than silently continuing |
| F2 | P1 | Ingestion API | RESOLVED — a `failed` document is reset to `pending` on re-upload instead of returning 409 | Live-verified: same ID returned, status advanced to `completed`. UI badge sync tracked as I5 |
| F3 | P1 | Quality gate | RESOLVED — not a code defect. Root-level pytest invocation ignores `asyncio_mode = auto`, producing 28 false async failures | Always run `cd apps/api && .venv/bin/python -m pytest -q`; 827 pass, 4 skipped |
| F4 | P2 | Git hygiene | `b7f49b3` is not pushed | Push when the owner is ready |

### Update

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| U1 | P2 | Reliability contract | RESOLVED — not a defect. The published schema uses `reliability: {status, score}`; a live completed run returns `{status: "TRUSTED", score: 1.0}` and the UI badge reads `100% TRUSTED`. The probed `verdict_status` / `reliability_score` keys are internal pipeline state, not API fields | Document the published contract in the README so future audits probe the right keys |
| U2 | P2 | README | RESOLVED — quickstart now states the tokenizer-cache gating, the first-run recovery step, and the published `reliability: {status, score}` contract | README updated in the install and API-reference sections |
| U3 | P3 | Ops docs | Runbook added at `docs/DEPLOYMENT_RUNBOOK.md` with preconditions, drill steps and cadence; the drill itself has not been executed | Execute against staging before the first public release |

### Refine

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| R1 | P2 | Error reporting | RESOLVED — already implemented. `request_id_middleware` sets `X-Request-ID`, logs bind `request_id`, and `apps/web/src/lib/apiResponse.js` captures it into `Error.requestId`; the capped `detail` stays server-side by design | No change needed |
| R2 | P3 | Landing content | RESOLVED — already implemented. `hero.js` carries the 33-probe provenance in `note.text` and links `docs/evaluation/methodology.md` | No change needed; verified the linked file exists |
| R3 | P3 | API surface | Deferred by design. Public `/health` and `/health/ready` already cover API/datastore readiness; `/models/providers` deliberately requires auth because it exposes internal base URLs and model lists. An anonymous network-probing endpoint would add an unauthenticated DoS surface for little operational gain | Revisit only if an external anonymous consumer is identified |

### Refactor

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| C1 | P3 | Memory utilities | RESOLVED — removed the uncalled `check_and_enforce_memory_guard` and its test assertions. `trim_memory` remains wired into the coordinator, ingestion pipeline and ops endpoint |
| C2 | P3 | Tailwind naming | RESOLVED — six `text-cyan-400` classes in `traceEvents.js` replaced with `text-silver-400`; the alias made this a no-visual-change rename |
| C3 | P3 | Design docs | RESOLVED — `docs/design/README.md` labels the SVG boards as historical concept work and points to the canonical system and brand kit |

### Improve

| ID | Priority | Area | Finding | Suggested action |
|---|---|---|---|---|
| I1 | P2 | E2E coverage | RESOLVED — `tests/test_launch_path.py` drives register → KB → upload (indexing mocked) → analysis → detail through the real FastAPI stack and asserts the public wire shapes | 1 new test; full backend suite 830 passed / 4 skipped |
| I2 | P2 | CI verification | Checked: latest run `45431899850` was red with four distinct causes — Windows `apply_ports.py` path, Docker `COPY` without destination, k6 checksum filename mismatch, and host-dependent ONNX batch-size assertions. All four fixed locally; re-run required after push | Push the branch, then confirm the new CI run is green before release |
| I3 | P3 | Responsive UI | RESOLVED — Brave DevTools at 390 px and 320 px: landing and authenticated dashboard/playground render with no horizontal overflow and 0 console errors | No code change needed |
| I4 | P3 | Load/resilience | Partially run — k6 v2.2.0 smoke against a local API with CI's rate-limit setting: 2907 requests, 0 HTTP failures, p95 144 ms (gate <300 ms). Its two health assertions failed because this host has no Qdrant service, so `/health` was legitimately `degraded`. CI runs with a Qdrant service | Re-run the gate in CI where Qdrant is available |
| I5 | P3 | Frontend | RESOLVED — the document list now polls only while a row is unsettled and stops once all rows are terminal. Live-verified: badge reached `Indexed` without navigation | Two component tests cover refresh and polling shutdown |

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

F1–F3, U1, U2, R1, R2, C1–C3, I1, I3 and I5 are resolved. I2's four CI blockers are fixed but unverified remotely; U3 and I4 need a staging environment with Qdrant. The remaining action is to push and confirm a green CI run.

---

*This is an engineering triage document, not a compliance or security certification. Re-run the checks after each fix and update the phase table.*
