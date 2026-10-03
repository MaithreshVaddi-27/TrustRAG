# Manual Live Evaluation — 2026-10-04

Live measurement of the frozen 27-query `baseline_v1` set against a running
stack. Raw per-query scores:
`results/manual_mlx_llama32_1b_1.28_20261003T140418Z.json` (gitignored).

## Setup

- **LLM**: MLX `mlx-community/Llama-3.2-1B-Instruct-4bit` via `mlx_lm.server`
  on `:8090` (`AI_PROVIDER=mlx`), Apple Silicon
- **Context**: `local_llm.num_ctx=8192`, server slot `-c 8192 -np 1`
- **Embeddings**: ONNX BGE-small-en-v1.5 (384d) · **Reranker**: ONNX MiniLM int8
- **Stores**: local MongoDB + embedded Qdrant (`QDRANT_URL=local`)
- **Corpus**: all 7 `tests/eval/fixtures/corpus/*` docs, `ingestion_status=completed`
- **Config**: v1.28 · caps balanced 8/8/3 · verdict gate coverage ≥0.80, contra ≤0.20
- Runner: `scripts/run_baseline_eval.py --config-name manual_mlx_llama32_1b`

## Aggregate results

| Metric | Measured |
|---|---|
| `recall@k` / `hit_rate@k` / `MRR` / `nDCG@k` (k=8) | **0.889** |
| `snippet_recall` | **0.852** |
| `evidence_coverage` | **0.111** |
| `claim_support_rate` | **0.057** (3 of 53 claims) |
| `contradiction_rate` | **0.000** |
| `citation_correctness` | n/a (abstentions excluded by design) |
| `abstention_rate` | **0.926** (25/27) |
| `outcome_match_rate` | 0.185 |
| latency p50 / p95 | **16.5s** / **115s** |

## By query class

| Class | n | Abstained | Claim support |
|---|---|---|---|
| factual | 14 | 13 | 1/36 |
| temporal | 3 | 3 | 1/3 |
| conflicting | 3 | 3 | 0/5 |
| adversarial | 5 | 4 | 1/5 |
| missing_evidence | 2 | 2 (both correct) | 0/4 |

Answered: q003 (factual, 1/1 supported), q021 (adversarial, 1/1 supported).

## Findings

1. **Retrieval is strong** (0.889 across all rank metrics; first gold hit at
   rank ~1). Hybrid + reranker work on this corpus.
2. **The 1B NLI verifier is the bottleneck.** Hand-verified case: generated
   claims copied retrieved text near-verbatim
   (*"Parental leave is granted for 6 months at full pay"* — word-for-word
   from `leave-policy.md`) yet all 4 claims scored NEUTRAL, twice plus
   recovery. Same pattern under Ollama `gemma3:1b` (spot-checked before the
   run): retrieval 4/4 segments, 0/4 supported.
3. **Fail-safe direction holds.** Zero contradictions and zero false supports
   in 27 queries — when uncertain, the system abstains rather than asserts.
4. **Latency tail is recovery-driven** (p95 115s): failed verifications burn
   full rewrite → re-retrieve → regenerate rounds before abstaining.

## Recommended levers (in order)

1. A 3B verifier (still local, far better NLI) — biggest expected gain.
2. NLI prompt tuning for 1B judges.
3. Only then consider relaxing the 0.80/0.20 gate — that trades safety for
   vanity metrics.

## Note

The 2026-09-19 snapshot in `methodology.md` predates the 8192-context and
RAM-tier changes; this file supersedes it as the current baseline.
