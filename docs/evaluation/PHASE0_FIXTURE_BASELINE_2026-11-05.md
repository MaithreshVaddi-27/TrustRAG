# Phase 0 Fixture Baseline — 2026-11-05

## Scope and decision

This report covers exactly one fresh authenticated end-to-end baseline. It uses the frozen 27-query `baseline_v1.jsonl` dataset and the seven-document fixture corpus in an isolated evaluator-owned knowledge base.

The earlier partial run, which stopped after nine queries, is **explicitly excluded** from every number in this report. It has no complete result artifact and must not be used for comparison.

No model, dependency, fixture document, or runtime configuration was changed during the fresh run. No ablations were run.

## Reproducibility

| Item | Value |
|---|---|
| Timestamp | 2026-11-05T14:16:37.167601+00:00 |
| Dataset | `apps/api/tests/eval/datasets/baseline_v1.jsonl` |
| Dataset size | 27 queries: 14 factual, 3 temporal, 3 conflicting, 2 missing-evidence, 5 adversarial |
| Fixture corpus | 7 completed-ingestion documents from `apps/api/tests/eval/fixtures/corpus/` |
| Isolated knowledge base | `6aec8b8514772d6c3cc8c597` |
| Evaluator account | `6aec8b8514772d6c3cc8c596` |
| Server configuration version | `1.28` |
| Generation and verification | local Ollama `gemma3:1b` |
| Embeddings | ONNX `BAAI/bge-small-en-v1.5`, 384 dimensions |
| Retrieval | dense + sparse/BM25, RRF fusion, `top_k=8` |
| Reranking | unavailable at runtime: missing ONNX artifact; deterministic RRF fallback used |
| Web search | disabled |

Run from the repository root after starting the already-configured local services and authenticating the dedicated evaluator:

```bash
python -I scripts/run_baseline_eval.py \
  --email "$EVALUATOR_EMAIL" \
  --password "$EVALUATOR_PASSWORD" \
  --kb-id 6aec8b8514772d6c3cc8c597 \
  --top-k 8 \
  --output /tmp/trustrag-phase0/phase0_fixture_gemma3_1b_rrf_1.28_20261105T141637Z.json
```

Credentials are intentionally not recorded. Use a new isolated evaluator account and knowledge base for a clean repeat.

## Artifact and contract audit

The raw artifact is `/tmp/trustrag-phase0/phase0_fixture_gemma3_1b_rrf_1.28_20261105T141637Z.json`.

| Check | Result |
|---|---|
| Artifact SHA-256 | `ff9a0eb7bbc73fe6af05ff2f5a41a2d98588a879d4c66ab845ce1efe43492992` |
| Dataset coverage | 27 expected / 27 actual / 27 unique |
| Missing IDs | none |
| Unexpected IDs | none |
| Duplicate IDs | none |
| Terminal outcomes | 27 / 27 |
| Terminal status split | 26 completed, 1 abstained, 0 failed |
| Runner timeouts | 0 |
| Artifact-contract violations | 0 |
| Empty actual responses | 0 |
| Empty retrieved-context lists | 0 |

Every record has exactly the corrected evaluation artifact fields:

```json
{
  "user_input": "<frozen dataset query>",
  "response": "<actual served response>",
  "retrieved_contexts": ["<actual served evidence text>"],
  "reference": "<dataset reference keywords>"
}
```

The audit also checked that every `user_input` exactly matches its frozen dataset query. The response and contexts were fetched from the analysis-detail API, not reconstructed from gold snippets or reference keywords. The `reference` field is intentionally the dataset's evaluation reference, not a substitute for retrieved context.

A separately preserved trace/claim/evidence summary is `/tmp/trustrag-phase0/complete-run-detail-summary.json` (SHA-256 `2c74ca8c2b372e8fea4ec9ad45197bfe1d1919e16b429071a207ee16efd83799`).

## Measured aggregate

| Metric | Measured value |
|---|---:|
| Recall@8 | 0.8889 |
| Hit rate@8 | 0.8889 |
| MRR@8 | 0.8889 |
| nDCG@8 | 0.8889 |
| Snippet recall | 0.8519 |
| Evidence coverage | 0.9630 |
| Claim support rate | 1.0000 |
| Contradiction rate | 0.0000 |
| Abstention rate | 0.0370 (1/27) |
| Outcome-match rate | 0.9259 (25/27) |
| Latency minimum | 3,753 ms |
| Latency p50 | 6,164 ms |
| Latency p95 | 12,726.1 ms |
| Latency maximum | 17,517 ms |
| Peak API RSS during complete workload | 279.84 MB |
| API RSS after workload sample | 276.12 MB |

The peak RSS is the workload monitor's maximum over the complete run. It is not the API's startup-warmup measurement.

## Outcomes, recovery, verification, and citations

### Outcome mismatches

Two expected abstentions completed instead:

| Query | Expected | Actual | Observed behavior |
|---|---|---|---|
| `q016` | abstained | completed | Answered the employee parental-leave policy although the question specified contractors, which are not covered by the fixture. |
| `q022` | abstained | completed | Answered a garbled query with a token-lifetime claim. |

The sole correct abstention was `q017`, an unsupported question about the publisher's founder. It completed bounded recovery, recorded `RETRIEVAL_FAILURE`, and abstained rather than guessing.

### Retrieval and verification signals

- Zero-recall records: `q016`, `q017`, and `q022`.
- `q017` is the only record with recovery events. Its persisted trace contains two bounded recovery cycles, including rewrite and re-retrieve events.
- Claim records: 41 `SUPPORTED`, 0 `CONTRADICTED`, 0 `NEUTRAL`.
- The all-supported claim result does not establish correct abstention behavior: `q016` and `q022` each have a supported claim despite being expected to abstain.
- No analysis was left pending or processing. The evaluator account had 36 terminal analyses after the run: 27 from this fresh run plus 9 from the earlier interrupted run.

### Citation measurement unavailable

`citation_correctness` is `null`, `citations_evaluated` is `0`, and all 27 `cited_segments` arrays are empty. The current run therefore cannot support a citation-correctness claim. This is a measurement failure, not a zero score.

The artifact preserves actual responses and contexts, but their responses lacked `[Segment N]` references. Investigate the answer-citation finalization/serialization path before treating citation correctness as an evaluable baseline metric.

## Preserved evidence

| Evidence | Location |
|---|---|
| Complete raw baseline artifact | `/tmp/trustrag-phase0/phase0_fixture_gemma3_1b_rrf_1.28_20261105T141637Z.json` |
| Complete runner log, exit code 0 | `/private/tmp/claude-501/-Users-maithresh-Downloads-TrustRAG/7d98ebda-26a3-4088-8d28-c6249b3936dc/tasks/bzefcyc2d.output` |
| Detail audit summary | `/tmp/trustrag-phase0/complete-run-detail-summary.json` |
| Complete-run memory monitor result | `api_peak_rss_mb=279.84` |
| Interrupted-run log, excluded | `/tmp/trustrag-phase0/baseline.log` |
| Evaluator terminal-status snapshot | `/tmp/trustrag-phase0/analyses-after-complete-run.json` |

## Blockers and next experiment

1. **Reranking unavailable:** the expected ONNX reranker artifact is absent. Do not report reranker metrics and do not download it without approval.
2. **RAGAS unavailable:** `ragas` and `openai` packages are absent, and no local judge is configured. Do not fabricate RAGAS scores or install dependencies without approval.
3. **Citation measurement unavailable:** no served segment references reached the artifact.
4. **Grounding gate gap:** `q016` and `q022` completed when the evaluation contract expected abstention.

### Recommendation, pending approval

Run **one focused, non-model-changing citation-and-abstention integrity investigation** before any performance or retrieval ablation. First reproduce and trace only `q016`, `q022`, and one citation-bearing expected-completed query against the same fixture KB. The experiment should identify whether the issue is in answer finalization, citation serialization, or the grounded-abstention decision. Do not change configuration, models, dependencies, or corpus until that diagnosis is reviewed and approved.
