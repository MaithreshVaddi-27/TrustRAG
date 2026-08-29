# TRUSTRAG — Evaluation Methodology

## Principles

1. No fabricated results. All metrics must come from actual system runs.
2. Measure improvement — not assumed improvement.
3. Ablations must isolate single variables.
4. Baselines must be fair comparisons (same data, same query set).

---

## Experiment Configurations (Phase 11)

| Configuration | Description |
|--------------|-------------|
| `baseline_rag` | Dense retrieval only + Gemini generation. No verification, no recovery. |
| `hybrid_rag` | Dense + BM25 hybrid/RRF + Gemini generation. No verification. |
| `hybrid_rerank` | Hybrid + cross-encoder reranking + Gemini generation. No verification. |
| `verified_rag` | Hybrid + reranking + claim verification. No adaptive recovery. |
| `trustrag_full` | Full TRUSTRAG: hybrid + reranking + verification + diagnosis + recovery + abstention. |

---

## Metrics

| Metric | Definition | Source |
|--------|-----------|--------|
| `retrieval_hit_rate` | Fraction of queries where relevant evidence was retrieved in top-k | Human / automated labels |
| `evidence_coverage` | Fraction of claims with at least one supporting evidence chunk | TRUSTRAG claim verification |
| `claim_support_rate` | Fraction of claims verified as SUPPORTED | TRUSTRAG claim verification |
| `contradiction_rate` | Fraction of claims verified as CONTRADICTED | TRUSTRAG claim verification |
| `citation_correctness` | Fraction of citations that actually support the cited claim | TRUSTRAG citation check |
| `recovery_success_rate` | Fraction of initially-failing analyses that recovered successfully | Recovery logs |
| `abstention_rate` | Fraction of queries where the system abstained | Analysis status |
| `latency_p50` | Median end-to-end analysis latency (ms) | Trace events |
| `latency_p95` | 95th percentile analysis latency (ms) | Trace events |

---

## Ablation Plan

| Ablation | Variable Isolated |
|----------|-----------------|
| Dense vs Hybrid | Retrieval method (sparse BM25 off/on) |
| Hybrid vs Hybrid+Reranking | Reranking contribution |
| Verification off vs on | Claim verification value |
| Recovery off vs on | Adaptive recovery value |
| Integrity logic off vs on | Evidence integrity analysis value |

---

## Query Dataset

Minimum viable evaluation set:
- 20+ queries with known ground-truth answers
- Queries spanning: factual, temporal (outdated evidence), conflicting sources, missing evidence
- At least 5 adversarial: queries designed to trigger failures

---

## Reporting

All experiment results are stored in the `experiments` MongoDB collection.
Results are displayed in the Experiments page of the UI.
Results must include: configuration, query, metrics, timestamps, config_version.
