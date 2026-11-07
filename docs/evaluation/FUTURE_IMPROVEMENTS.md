# TrustRAG — Future Improvements

**Date:** 2026-11-07

## Deferred (P3)
- Promote 3B+ models (SmolLM3-3B, Llama-3.2-3B, gemma-3-4b) to interactive serving only after 16 GB+ host validation.
- Add per-source benchmark harness with measured latency/memory numbers (currently qualitative).
- Deeper browser QA of upload/indexing/chat/citations flows (requires authenticated seeded data).
- Performance profiling of hybrid retrieval on large KBs.

## Known follow-ups
- The `_is_effectively_identical_query` meta-token guard may over-reject short rewrites that happen to consist only of meta-vocabulary; consider requiring the rewrite to preserve original subject tokens.
- Responsiveness guard (`is_responsive_answer`) is token-overlap based; could be strengthened with embedding similarity for paraphrased answers.
- Deep browser QA of upload/indexing/chat/citations flows (requires authenticated seeded data).
- Per-source benchmark harness with measured latency/memory numbers.
