# TrustRAG — Future Improvements

**Date:** 2026-11-16
**Status:** open items, with what each is waiting on.

## Deferred (P3)

- Promote 3B+ models (SmolLM3-3B, Llama-3.2-3B, gemma-3-4b) to interactive
  serving only after 16 GB+ host validation.
- ~~Add per-source benchmark harness with measured latency/memory numbers.~~
  **Done (B4)** — `apps/api/scripts/eval_accuracy.py` measures six model
  configurations against a 33-probe ground truth (27 answerable + 6
  unanswerable), reporting answer accuracy, abstention accuracy, Recall@K,
  Precision@K, MRR and mean latency. Results in
  [`backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md`](../backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md)
  §4.10.
- Deeper browser QA of upload/indexing/chat/citations flows (requires
  authenticated seeded data). Partly covered by
  `apps/api/scripts/validate_integration.py`, which walks the whole flow
  through the frontend's own proxy — but it does not drive the browser UI.
- Performance profiling of hybrid retrieval on large knowledge bases.

## Known follow-ups

- The `_is_effectively_identical_query` meta-token guard may over-reject
  short rewrites that happen to consist only of meta-vocabulary; consider
  requiring the rewrite to preserve original subject tokens.
- Responsiveness guard (`is_responsive_answer`) is token-overlap based; it
  could be strengthened with embedding similarity for paraphrased answers.
- **The mypy backlog — 30 errors in 10 modules.** The ratchet ceiling is
  committed at 30, so CI fails only on *new* errors; the backlog itself is
  untouched. Each fix can ratchet the ceiling down by one. The ratchet
  script is `scripts/typecheck_ratchet.sh` and the ceiling is
  `apps/api/mypy-error-ceiling.txt`.
- **Embedding int8 recall is still unmeasured.** Only the fp32 export exists
  locally (`apps/api/.model_cache/bge-small-en-v1.5.onnx`, 134 MB). Producing
  an int8 export is a separate job with its own risk — the config itself
  warns that 1 % clipping can drop the true nearest neighbour at the
  reranker boundary.

## Open decisions (the operator's call)

- **DECISION-006 — the default model.** The shipped default (`gemma3:1b`)
  answers **37 %** of answerable questions with **83 %** abstention accuracy.
  `qwen3:1.7b` answers **93 %** with **100 %** abstention accuracy, at **4.3×**
  the latency (5.0 s → 21.5 s). It is not the default because
  `models.yaml` marks it deep-reasoning-only — which the specification
  forbids for interactive serving — and because the deployment `.env` pins
  `OLLAMA_MODEL=gemma3:1b`. Both are policy, not technology.
