# Reliability Phase 1 — Implementation Results

**Date:** 2026-11-06
**Branch:** `reliability-phase1` (from `ui-redesign` @ `dbbadcb`)
**Scope implemented:** F-1, F-2, F-3, F-10 from `RELIABILITY_PHASE1_ABSTENTION_AUDIT.md`, plus the regression/integration tests. F-4/F-5/F-6/F-7/F-8/F-9 deliberately **not** implemented.
**Evaluation:** frozen `baseline_v1.jsonl` (27 queries, unchanged), frozen 7-document fixture corpus, new isolated KB `6aedcd0c40abe8cb2801c82e`, `gemma3:1b` via local Ollama, `config_version 1.29`, local-only execution.
**Artifact:** `docs/evaluation/results/trustrag_baseline_reliability_phase1_1.29_20261106T130113Z.json`

---

## 1. What changed

| Fix | File | Change |
|---|---|---|
| **F-1** | `app/rag/verification/verdict.py` | New `DiagnosisType.VERIFICATION_UNAVAILABLE`; `compute_verdict(..., unchecked=0)` — any unchecked claim forces `FAIL`, never `TRUSTED`; `verdict_from_state` counts them. |
| **F-1** | `app/rag/verification/verifier.py` | Removed the `attempt > 0 → fallback_budget = 0` disable. Claims that still cannot be verified are persisted as `UNCHECKED` (not `NEUTRAL`), with no evidence linkage. |
| **F-1** | `app/llm/llm_ledger.py` | New bounded counter: `nli_fallback_calls`, `max_nli_fallback_calls()` (derived: `max_individual_nli_fallback × (max_recovery_attempts+1)` = 24), `nli_fallback_exhausted()`, `record_nli_fallback_call()`. Inert without a ledger. |
| **F-1** | `app/rag/agent/graph.py` | `verification_node` counts `UNCHECKED`, passes it to `compute_verdict`, and reports it in the trace stats. |
| **F-2** | `app/rag/verification/verifier.py` | `BatchNLIVerdict` tolerates renamed top-level containers (`vericits`, `verdict`, `results`, `items`, `statements`, `claims`, `data`) and **drops** rows with no claim id or a template-placeholder verdict instead of raising. |
| **F-3** | `app/rag/verification/verifier.py` | `_filter_degenerate_claims` also drops colon-terminated label fragments, single-token claim fragments, and title-case heading lines (2–6 words, no terminal punctuation, **no predicate verb**). |
| **F-1** | `tests/eval/metrics.py` | `claim_summary` reports `unchecked` separately and excludes it from coverage; new `claim_unchecked_total` / `claim_verification_availability` / `claim_support_denominator_total`. |
| **F-1** | `app/api/v1/schemas/analysis.py`, `apps/web/.../ReliabilityBadge.jsx` | `UNCHECKED` documented/rendered as "Unverified" (never as Supported). |
| **F-10** | `tests/test_analyses.py`, `tests/test_wave2_cloud_resilience.py` | The 3 stale tests fixed: provider expectation read from config instead of hard-coded `llama_cpp`; `deep_reasoning_model` added to the 3 `_CfgStub`s. |
| — | `tests/test_reliability_phase1.py` (new), `tests/eval/test_eval_metrics.py` | 30 new regression/integration tests. |

Nothing else was touched: no model, dependency, config value, architecture, or dataset change. `baseline_v1.jsonl` md5 unchanged (`e3d9072699d00fb2178af09ba00a5fdd`).

---

## 2. Test results

```
targeted (tests/test_reliability_phase1.py + tests/eval/)   53 passed
full suite before this work                                 3 failed, 731 passed, 4 skipped
full suite after                                            757 passed, 4 skipped, 0 failed
coverage                                                    78.83% (floor 78%)
frontend                                                     npm run lint → clean (0 warnings)
```

The 26 new tests are: 6 verdict/UNCHECKED, 3 fallback-budget/bound, 7 batch-NLI tolerance, 2 degenerate-claim filters, 4 eval-metric, 1 end-to-end incident guard, plus the 3 F-10 fixes. One existing test (`test_execute_claim_verification`) needed its fixture changed from the placeholder strings `"Claim 1"/"Claim 2"` to assertion-shaped sentences — those placeholders are exactly the scaffolding class F-3 drops.

---

## 3. Frozen-baseline evaluation: Phase 1 vs Exp 1

All Exp-1 figures are the previously recorded experiment; Phase-1 figures are the new artifact above.

| Metric | Exp 1 (before) | Phase 1 (after) | Δ |
|---|---|---|---|
| Queries terminal | 27/27 | 27/27 | — |
| Retrieval recall@8 / hit / MRR / nDCG | 0.8889 | 0.8889 | identical |
| Snippet recall | 0.8519 | 0.8519 | identical |
| Completed | 21 | 20 | −1 |
| Abstained | 6 | 7 | +1 |
| Abstention rate | 0.2222 | 0.2593 | +0.037 |
| Outcome-match rate | 0.8889 | 0.8519 | −0.037 |
| **Unverified (UNCHECKED) claims** | **12 / 53 (22.6 %)** | **0 / 63 (0 %)** | **defect closed** |
| **Verification availability** | 0.774 | **1.000** | +0.226 |
| Claim support rate (delivered answers) | 1.0000 (41/41) | 1.0000 (48/48) | held |
| Contradiction rate | 0.0000 | 0.0000 | held |
| p50 latency | 6,899 ms | **5,145 ms** | −25 % |
| p95 latency | 17,149 ms | **15,903 ms** | −7 % |
| max latency | — | 18,809 ms | — |
| Peak API RSS | ~280 MB (Phase-0 monitor) | **281.3 MB** (468 samples @2 s) | flat |
| Citation correctness (syntactic) | 1.0000 (21 cites) | 1.0000 (15 cites) | held |
| Semantic citation quality | 0.5714 (12/21) | 0.5000 (11/22) | unchanged (F-5 deferred) |
| Degenerate claims stored | 10 (all on q022) | **0** | F-3 working |

### Per-query outcomes

| Query | Expected | Exp 1 | Phase 1 | Note |
|---|---|---|---|---|
| q001 | completed | completed | completed | grounded **but wrong fact** (backups vs 30 days) — RC-3, deferred |
| q003 | completed | abstained ✗ | abstained ✗ | unchanged (model refusal) |
| q004 | completed | completed | completed | 5 supported claims |
| q005 | completed | completed | completed | grounded, wrong fact (RC-3) |
| q006 | completed | abstained ✗ | abstained ✗ | **dataset label defect** (excluded per instruction) |
| q009 | completed | completed | completed | grounded, wrong fact (RC-3) |
| q016 | abstained | abstained ✔ | **abstained ✔** | preserved |
| q017 | abstained | abstained ✔ | **abstained ✔** | preserved |
| q020 | completed | completed | completed | grounded, wrong fact (RC-3) |
| q021 | completed | completed | **abstained ✗** | new — model variance, proven below |
| q022 | abstained | abstained ✔ | **abstained ✔** | preserved (and now with 0 garbage claims, not 10) |
| q024 | completed | abstained ✗ | **completed ✔** | **target false abstention fixed** — but delivers the wrong fact (RC-3) |
| q025 | completed | completed | **abstained ✗** | new — model variance, proven below |

### Acceptance against the stated conditions

| Condition | Result |
|---|---|
| `baseline_v1.jsonl` unchanged; q006 excluded from genuine false-abstention math | ✔ md5 verified; genuine false abstentions = q003, q021, q025 = 3/24 = 0.1250 |
| q016 / q017 / q022 abstention preserved | ✔ all three abstained |
| Never allow UNVERIFIED or degenerate claims to become TRUSTED | ✔ 0 UNCHECKED claims persisted; every UNCHECKED path forces `FAIL`; 0 degenerate claims stored |
| NLI fallback bounded, no retry loops / uncontrolled cost | ✔ per-round cap 8 **and** whole-analysis cap 24 (derived from config, ledger-scoped); measured worst case per run ≤ 2 batch + ≤8 individual calls per round; no UNCHECKED claims occurred, so no bound was reached |
| No model / config / architecture / dependency change | ✔ `models.yaml` untouched; config_version still 1.29; only the 4 approved fixes + tests |
| Regression & integration tests added | ✔ 26 new tests, all passing |

---

## 4. The fixed defect, and the one the fix exposed

**Verified closed (F-1/F-2):** Exp 1 stored 12 claims with *"Verification skipped: batch NLI unavailable…"* and reported them as LOW_COVERAGE. Phase 1 stored **zero** such claims, `verification_availability = 1.000`, and `q024` — the recorded false abstention — now completes with a real `SUPPORTED` verdict. A live check of the same batch call confirms the repair path now survives the model's `{"vericits": …}` output rather than raising twice.

**Newly visible (deferred F-4):** q024's delivered answer is *"Backups expire after 7 days and are then unrecoverable."* The claim is genuinely grounded in the served segment, so NLI and the grounding gate pass it — but it is not the answer to "How long does a deletion request take to complete?" (expected: 5 business days). The same class affects q001, q005, q009 and q020, so **4 of 19 scorable delivered answers are grounded-but-wrong**. The fixes converted one false abstention into a verified wrong answer; only F-4 (answer-responsiveness check) closes that, and it remains deferred by instruction. This is the single most important follow-up.

---

## 5. Regression analysis: q021 and q025 are model variance, not caused by the changes

Both new abstentions take the refusal-gate path (`generation.completed → recovery.regenerate → generation.skipped`, 0 claims) — a **generation-stage** decision. None of F-1/F-2/F-3 touches generation, the refusal gate, retrieval, or thresholds; they only affect claim classification, batch parsing, and verdict computation.

Direct evidence that the inputs were identical:

- **q025** served context, Exp 1: `thermal-runoff-study.txt 0.03279, retention-policy.md 0.03151, limits-2026.txt 0.01613, service-api.md 0.01562` → completed. Phase 1: **byte-identical** segments and scores → abstained.
- **q021** served context, Exp 1: `scratch-notes.txt 0.03279, service-api.md 0.03252, limits-2026.txt 0.03200, retention-policy.md 0.01562` → completed ("The token lifetime is 30 days…"). Phase 1: **byte-identical** → abstained.
- **q021 already abstained under `gemma3:1b` before these changes** — Exp 3 (16:04:42 UTC, `gemma3:1b` + ONNX reranker) stored an ABSTAINED outcome for it, i.e. this failure mode predates the branch.
- Re-running q021/q025/q003 through the API reproduced the abstention in ~3.0 s each (deterministic in this environment), and re-running q024 reproduced the completed-but-wrong answer.

Verdict: **no regression attributable to the implementation**; the run-to-run variance of `gemma3:1b` at temperature 0.2 on a 7-document corpus is itself a reliability finding (2 of 24 answerable queries flip), and it is the same class of non-determinism already documented across Exp 1/2/3 (`q026` and `q022` flipped between models).

---

## 6. Latency and memory

- p50 5,145 ms (Exp 1: 6,899 ms), p95 15,903 ms (Exp 1: 17,149 ms), max 18,809 ms — faster despite the extra verification work, on a fresh cold KB.
- Peak API RSS **281.3 MB** over 468 samples (2 s interval), matching the Phase-0/Exp-1 footprint (~280 MB) — no memory growth from the bounded fallback.
- LLM call pattern observed: 1 generation + 1 batch NLI per round on the healthy path; the individual fallback only fires when the batch is unusable, capped at 8 per round and 24 per analysis.

---

## 7. Recommendation

1. **Merge this branch** — the verification-availability defect is closed, the target false abstention is fixed, abstention behaviour on q016/q017/q022 is preserved, the full suite is green, and latency/memory are flat or better.
2. **Approve F-4 next.** Without it the pipeline now verifies wrong answers as confidently as right ones (4/19 delivered answers). This is the highest-severity remaining gap and the direct continuation of this work.
3. Track the model-variance false abstentions (q021/q025 class) as a separate item: either accept them as documented non-determinism of a 1B generator, or gate interactive mode behind a determinism/sampling policy.
