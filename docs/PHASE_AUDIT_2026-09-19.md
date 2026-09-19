# TRUSTRAG — Phase-by-Phase Verification Audit (2026-09-19)

Manual re-verification of every phase in `TRUSTRAG-UPGRADE-PLAN.md` (canonical
numbering) against the actual code. Method per phase: read the implementation,
run the phase's test files, confirm acceptance criteria. Full suite at end:
**381 passed**, `ruff check` clean, `ruff format` clean.

Live-stack note: only MongoDB is reachable in this environment (Qdrant :6335 and
llama-server :8080 are down, no Docker daemon). Everything verifiable offline
was verified; live runs stay operator pendings (same as prior sessions).

## Phase 0 — Baseline ✅ verified, no changes
- `apps/api/tests/eval/` (metrics + dataset validation, 18 tests green),
  frozen `datasets/baseline_v1.jsonl` (25 queries), 6-file fixture corpus,
  `scripts/run_baseline_eval.py` (`--help` works), `docs/evaluation/methodology.md`
  with ablation matrix. `docs/evaluation/results/` absent = no live run yet (expected).

## Phase 1 — Ingestion + OCR ✅ verified, no changes
- 44 tests green (`test_ocr`, `test_page_images`, `test_page_image_endpoint`, `test_ingestion`).
- Per-page routing (`should_ocr_page`, <50 native chars), sub-0.5-confidence drop,
  `ocr_used`/`ocr_confidence` plumbed page → chunk → Mongo + Qdrant in parser,
  pipeline, chunker, and all chunking strategies.

## Phase 2 — Chunking ✅ verified, no changes
- 25 tests green. Both ingest paths (`knowledge_bases.py:202,331`) chunk via
  `get_chunking_strategy().chunk()`; default `sliding_window` is byte-identical
  to the legacy path. Newline-preserving normalization, true semantic offsets,
  gap-free progressive, whole-table layout chunks all covered by tests.

## Phase 3 — Retrieval ✅ verified, no changes
- 34 tests green (`test_retrieval`, `test_reranker`, `test_sparse_bm25`, `test_qdrant`).
- BM25-style client TF + Qdrant `Modifier.IDF` with recreate-on-mismatch migration;
  `fusion_top_k` enforced post-RRF; reranker depth cap `max(reranker_top_k,
  fusion_top_k)`. Reranker stays `enabled: false` — Docker image lacks torch by
  design (accepted limitation, documented in `models.yaml`).

## Phase 4 — Query Handling ✅ verified, no changes
- 21 tests green (`test_router` 13 + `test_citations` 8). Deterministic
  SIMPLE/TEMPORAL/COMPARISON/COMPLEX routing, year→July-1 reference_time,
  bounded fan-out merged by RRF, SIMPLE path byte-identical single call.

## Phase 5 — Multi-Hop ⚠️ partial (kept, justified — no code change)
- Shipped: deterministic multi-`?` split (capped at 3) + comparison fan-out ×2
  with concurrent branches, partial-outage degradation, RRF merge.
- Deferred: dependent multi-hop chains (sub-question B needs A's answer) and
  LLM-planned decomposition. Reason: both plans gate this on a live-eval signal
  that the deterministic splitter is insufficient, and no live eval exists yet.
  Adding LLM planning now would violate the plan's own promotion rule. Revisit
  after Phase 12 live ablations.

## Phase 6 — Verification ✅ verified, no changes
- 34 tests green (`test_verification`, `test_integrity`, `test_semantic_cache`).
  Fused decompose+verify primary with two-step fallback, tolerant NLI parsing,
  NEUTRAL-only targeted claim retrieval (budget 3, CONTRADICTED never re-searched),
  inline `[Segment N]` citations with invalid-ref strip, claim→evidence linkage.

## Phase 7 — Trust + Provenance ✅ verified, no changes
- SHA-256 integrity audit gating chunks to VERIFIED/CORRUPTED, hash chain,
  `page_image_ref` OCR→image linkage, KB snapshots + rollback, version pins.

## Phase 8 — Adaptive Recovery ✅ re-verified, no changes
- `max_recovery_attempts: 2`, token (2000) + latency (180s) budgets,
  diagnose-then-act mapping, `RECOVERY_BUDGET_EXHAUSTED` abstention path.
  28 agent tests green.

## Phase 9 — Security ✅ re-verified, no changes
- 24-test red-team suite green (injection-as-data, tool-call non-execution,
  conflict→CONTRADICTED, stale/temporal path, OCR confidence gate, KB
  cross-tenant 403, token confusion rejected). JWT `iss`/`aud` enforced both
  token types, service-token `bound_kb_id`/`bound_user_id` enforced on internal
  ingest, login lockout (5/900s), EICAR + best-effort clamd AV hook on upload.

## Phase 10 — Speed + Production ✅ re-verified, no changes
- Dependency-free `core/metrics.py` counters + `GET /api/v1/metrics` exposition,
  tracing-middleware recording, pre-request `max_input_tokens` enforcement with
  kill-switch, per-analysis token/completion accounting, k6 extended with
  `/metrics` + `/analyses` checks (LLM-free). 7 metrics tests green.
  `models.yaml` v1.15.

## Phase 11 — Index Lifecycle ✅ verified, no changes
- Lifecycle tests green (in the 96-test agent/redteam/metrics/lifecycle/config
  batch): snapshot 201, rollback 200 with new live id, 409 on vector-less and
  foreign snapshots, OCR-preserving snapshot copies, Qdrant purge by
  `document_id` on delete.

## Phase 12 — Final Evaluation ⏳ harness verified, live runs pending
- Runner, frozen dataset, metrics, methodology ablation matrix all verified
  working offline. The four ablation families + baseline measurement require a
  live stack (Qdrant + LLM server + seeded KB) — operator pending, unchanged.

## Phase 13 — Deployment ✅ checklist verified, no changes
- Dead code removed (AmbiguityDetector gone, one historical comment left in
  `retriever.py:32`); `ruff check` + `format` clean; 381 unit tests green;
  `HEALTHCHECK` in Dockerfile + compose (public `/health`, authed
  `/health/detailed`); env-based config (`Settings` + `.env.example`); structured
  logs (structlog); `docs/deployment/DEPLOYMENT_GUIDE.md` covers health, ONNX,
  JWT, CORS, OCR pre-warm. k6/Playwright e2e need the live stack (operator pending).
- Note: repo-wide `mypy` uses `python_version = 3.11` while this machine's numpy
  stubs need 3.12+ to parse — local-env-only artifact (CI pins 3.11); new Phase 10
  module is mypy-clean under 3.12. No code change made.

## Gaps fixed during this audit
- 3 pre-existing test-lint issues (`test_agent.py` unused `cfg`, `test_redteam.py`
  import sort + blind `Exception` → `ValueError`). No production-code gaps found;
  all other phases verified as-is.
