# TRUSTRAG — Execution Plan (what to do first, what comes later)

Companion to `PRODUCTION_AUDIT_OPTIMIZATION.md` (the *what/why*) — this is the *when/in what order*.
Status legend: ✅ done · 🔶 open · ⏳ scheduled.

## Phase 1 — FIRST (correctness of configuration; this pass) ✅

1. ✅ Audit: secret scan, hardcoded-ID scan, ONNX/RAM review, dep-usage scan
   (with one false positive caught by verification: `motion`/`recharts` ARE used).
2. ✅ Fix C-1/C-2/C-3: `models.yaml` is now the sole source — resolvers fail fast, engines
   resolve defaults from config, no silent literal pins.
3. ✅ Fix C-4: tests env-first (`setdefault`), synthetic keys labeled, helper uses config.
4. ✅ Remove NVIDIA NIM + DuckDuckGo + URL-ingest dangling surfaces end-to-end.
5. ✅ Fix boot blockers: page-image chain, query cache, reranker, timeouts, EICAR,
   DOCX/HTML parsers, dead-credential classification, sanitize hardening.
6. ✅ Verify: backend 680 passed + ruff/format clean + app boots; frontend lint +
   vitest (33) + build green.
7. ✅ Commit locally (you push when ready).

## Phase 2 — NEXT (production hardening, in order) 🔶

1. O-1: integration tests for `analysis_service.py` create/finalize (see
   `ANALYSIS_SERVICE_TEST_GAPS.md`, 17-test plan).
2. O-2: Redis-backed rate limiting for multi-worker prod (`SLOWAPI_STORAGE_URI`).
3. U-1: per-host-class `ONNX_*` / Ollama env profiles (lean ≤8 GB values in the audit doc).
4. U-4: nightly live E2E in CI (`scripts/e2e_manual_verify.sh` + Mongo service).

## Phase 3 — LATER (premium polish, only after Phase 2 is green) ⏳

1. U-3: Apple-design spring micro-interactions + token-stream rendering in Playground.
2. U-5: `_DEFAULTS` sync test locking `local_llm.py` / `hardware.py` mirrors to `models.yaml`.
3. O-3: `model_validate` serialization cleanup (~80 lines).

## Standing rules (every phase)

`READ → PLAN → BUILD → VERIFY → FIX → DOCUMENT → NEXT` · never continue with known failures ·
`models.yaml` for IDs/params · `.env` for secrets · record `config_version` per analysis ·
bump `runtime.config_version` on any `models.yaml` value change.
