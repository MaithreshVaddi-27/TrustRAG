# Analysis Service Test Gaps

> Generated 2026-09-28 from `pytest --cov=app.services.analysis_service --cov-report=term-missing`
> over the full suite (734 tests, 3 s run). **Coverage: 54% (327 stmts, 151 missed).**
>
> This is the lowest-covered core service in the API layer. The gaps are not random:
> they cluster into six behaviors that are executed on every real analysis run but
> only ever exercised live (the E2E script) or via heavier integration paths.

**File:** `apps/api/app/services/analysis_service.py` (~1,090 lines)

---

## 1. Coverage snapshot

| Region | Lines (missing) | What it does | Risk if untested |
|---|---|---|---|
| `_looks_like_scaffold_echo` | 67–79 | Detects prompt-echo / repetition-loop LLM output | Degenerate answers stored as real synthesis |
| SSE pub/sub primitives | 126–156 | `_subscribe` / `_unsubscribe` / `_publish_analysis_event` | Subscriber leak, missed events, `QueueFull` drop |
| Serializer datetime fallbacks | 194–195, 211–212, 232–233 | `doc.get(...) or now(UTC)` branches | `500` on documents missing timestamps |
| `create_analysis` dim-pin guard | 271–272 | Rejects KB pinned at a different embedding **dimension** | Wrong-dim queries hit Qdrant → garbage retrieval |
| LLM probe MLX branch | 320–324 | `mlx` base-URL resolution + probe provider tag | New-user onboarding probe silently wrong on MLX |
| `get_analysis` wrap | 391–392 | Converts driver exceptions → `NotFoundError` | Driver error leaks as 500 |
| Claims/evidence fetchers | 426–458 | `_fetch_claims`, `_fetch_evidence`, + ownership pre-checks | Wrong sort order / missing 403 on foreign reads |
| `_fetch_trace` tail | 466 | Serialize + return | — |
| `add_trace_event` | 500–514 | Mongo insert + SSE publish | Trace events silently lost |
| SSE heartbeat branch | 557–561 | Ping every 3 idle ticks | Proxies (Render/Cloudflare) kill idle streams |
| Pipeline: RETRIEVAL_OUTAGE | 628–661 | Outage stored as `failed` with user-safe message | Outage presented as "no evidence found" |
| Pipeline: ABSTAINED finalize | 676–713 | Abstention persisted + `analysis.abstained` event | Bare "ABSTAIN" token stored as the answer |
| Pipeline: scaffold trace + stub swap | 755–770 | `generation.degenerate` event, `_UNVERIFIED_ANSWER` swap | Degenerate stub ("The") shown as answer |
| Pipeline: exception handler | 814–863 | Classifies connect/not-found/timeout → user message | Raw exception text leaks to the client |
| Pipeline: `finally` trim | 867–868 | Post-run `memory_mod.trim_memory` | RAM growth across runs goes unnoticed |
| Cross-analysis reads | 875–990 | `list_all_user_evidence` / `_claims` / `_conflicts` (incl. legacy `analysis_id` fallback) | Auth-scope bug: evidence visible across users |
| Dossier plain format | 1068 | Non-JSON-LD export return | Export endpoint returns wrong shape |

Covered elsewhere (already tested, listed for completeness): `create_analysis`
happy path + embedding-model mismatch + no-models 422 (tests/test_analyses.py),
reads + ownership + malformed IDs (tests/test_analysis_reads.py), SSE terminal
events (tests/test_sse_outage.py), finalize grounding gate for TRUSTED/withheld
answers (tests/test_analyses.py:470–621), flow-level verdicts
(tests/test_analysis_pipeline_integration.py).

---

## 2. Recommended tests (priority order)

### P0 — correctness/security

1. **`test_cross_user_evidence_and_claims_are_scoped`** (875–916)
   Seed evidence for user A; assert `list_all_user_evidence(user_b)` returns `[]`.
   Same for claims. This is an auth boundary — currently only the analysis-level
   ownership is tested, not the cross-analysis evidence listing.
2. **`test_list_all_user_*_falls_back_to_analysis_ids`** (885–891, 910–916)
   Evidence doc with legacy shape (no `user_id`, only `analysis_id`) is still
   returned to its owner, and never to another user.
3. **`test_pipeline_failure_messages_do_not_leak_exception_text`** (814–863)
   Force `execute_agentic_rag_flow` to raise; parametrize over connect /
   not-found / timeout / generic. Assert `error_message` matches the safe
   template and never contains the raw exception string.
4. **`test_dim_mismatch_create_is_422`** (271–272)
   KB pinned at `384`, server config `768` → `InputValidationError`. The
   model-name mismatch guard is tested; the dimension guard is not.

### P1 — pipeline finalize paths

5. **`test_finalize_abstained_path`** (676–713)
   Verdict = ABSTAINED → status `abstained`, bare `"ABSTAIN"` replaced by the
   user-facing sentence, `analysis.abstained` event emitted, metric recorded.
6. **`test_finalize_retrieval_outage_path`** (628–661)
   `diagnosis_type == "RETRIEVAL_OUTAGE"` → status `failed`, `analysis.outage`
   event, reliability score 0. Complements the SSE-side test in test_sse_outage.py.
7. **`test_scaffold_echo_detection`** (64–80) — unit test, no DB:
   - `"<context>"` marker → True
   - same 40+ char sentence ×3 → True
   - normal multi-sentence answer → False
8. **`test_finalize_scaffold_echo_swaps_stub_and_status`** (755–770)
   Scaffold-echo answer + SUPPORTED claims → stored answer is
   `_UNVERIFIED_ANSWER`, status `abstained`, `generation.degenerate` event.

### P2 — SSE / pub/sub mechanics

9. **`test_pubsub_subscribe_unsubscribe_roundtrip`** (126–140)
   Subscribe twice, unsubscribe once → set has 1 queue; unsubscribe again → key deleted.
10. **`test_publish_reaches_all_subscribers_and_survives_full_queue`** (143–156)
    Full queue → warning logged, other subscribers still receive (no exception raised).
11. **`test_sse_heartbeat_after_idle`** (557–561)
    Publish nothing; assert a `ping` event yields after ~3 s and the generator
    eventually stops (bounded by the 360-tick loop with mocked timeout).
12. **`test_add_trace_event_persists_and_publishes`** (500–514)
    Insert asserted in mock collection; published payload carries the same event/data.

### P3 — serialization & misc

13. **`test_serializers_default_missing_timestamps`** (194–195, 211–212, 232–233)
    Docs without `created_at` / `timestamp` serialize without raising.
14. **`test_get_analysis_wraps_driver_errors_as_404`** (391–392)
    `find_one` raising a `pymongo` error → `NotFoundError` (HTTP 404), not 500.
15. **`test_claims_and_evidence_sorted_ascending`** (426–458)
    Out-of-order seeds come back sorted by `created_at` ascending (stable UI order).
16. **`test_dossier_plain_format`** (1068)
    `export_format="json"` returns `{analysis, claims, evidence}` flat shape.
17. **`test_mlx_probe_branch`** (320–324)
    `effective_llm_provider == "mlx"` → probe hits `settings.mlx_base_url` with
    `probe_provider="mlx"`.

---

## 3. Suggested fixture layout

```python
# tests/test_analysis_service_gaps.py (proposed name)
# Reuse existing patterns:
#   - tests/test_analysis_reads.py::user_id + _Cursor  → fake cursor over seeded docs
#   - tests/test_analyses.py finalize tests            → _fake_flow + _Sem + MagicMock coll
#   - tests/test_sse_outage.py                          → real sse_event_generator with queues
```

Notes:
- The pub/sub primitives are in-process (`_analysis_subscribers` module global),
  so tests must reset it in a fixture (`analysis_service._analysis_subscribers.clear()`).
- `run_analysis_pipeline` needs the same `_Sem` / coll-mock scaffolding as
  `test_finalize_*`; extract it into a shared fixture to avoid a third copy.
- Estimated effort: P0 ≈ 4 tests, P1 ≈ 4, P2 ≈ 4, P3 ≈ 5 → **~17 tests**, lifting
  this module from 54% to roughly 85%+ with mostly async unit tests (no network).

---

## 4. Verification

After adding the tests, confirm with:

```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_analysis_service_gaps.py -q
python -m pytest tests/ --cov=app.services.analysis_service --cov-report=term-missing -q
```

Target: `analysis_service.py ≥ 85%`, all P0/P1 lines above green.
