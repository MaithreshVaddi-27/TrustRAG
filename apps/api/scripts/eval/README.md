# TRUSTRAG — the evaluation package

Everything that measures **answer correctness** lives here, so the ground
truth and the harness that scores it are never separated, and a run is one
command.

| File | What it is |
|---|---|
| `eval_set.py` | The ground truth: a four-document corpus across four domains and **33 probes** — 27 answerable + 6 unanswerable. Both halves are scored, so accuracy cannot be bought by weakening verification: an answerable probe that stops being answered costs a point, and an unanswerable probe that starts being answered costs a point. |
| `eval_accuracy.py` | The harness: creates a knowledge base, uploads the corpus, waits for indexing, runs every probe through the **public API**, and reports answer accuracy, abstention accuracy, the false-abstention and false-answer lists, the mean latency, and the retrieval quality (Recall@K / Precision@K / MRR) of the evidence actually served. |
| `run_matrix.sh` | The matrix driver: runs the harness against every model configuration the project has measured — same corpus, same scoring — and restores the shipped configuration when it finishes, whatever happens. |

## Run it

```bash
cd apps/api

# One configuration (the shipped default):
bash scripts/eval/run_matrix.sh gemma3_1b

# The whole matrix (six configurations, roughly 40 minutes):
bash scripts/eval/run_matrix.sh
```

Each run writes `eval_accuracy_<label>.json` next to the scripts. The
harness talks to a **live backend** — start the stack first:

```bash
bash apps/api/scripts/start_local_services.sh
```

## The matrix

| Label | Model | What it varies |
|---|---|---|
| `gemma3_1b` | `gemma3:1b` | The shipped default |
| `gemma3_rerank` | `gemma3:1b` | The ONNX cross-encoder reranker ON |
| `gemma3_temp0` | `gemma3:1b` | Greedy decoding (`temperature: 0`) |
| `gemma3_ctx3` | `gemma3:1b` | Three context chunks instead of five |
| `qwen3_1_7b` | `qwen3:1.7b` | The deep-reasoning model, verifier thinking ON |
| `qwen3_nothink` | `qwen3:1.7b` | The deep-reasoning model with the **thinking control** — the shipped setting |

The last two need `DEEP_REASONING_MODE=true` on the server: the
specification forbids a deep-reasoning model in interactive serving, so the
API rejects it with HTTP 422 unless an operator opts in. `run_matrix.sh`
starts the server with the right environment for each configuration.

## What is *not* in here

The benchmark harnesses (`scripts/bench/bench_api.py`, `scripts/bench/bench_pipeline.py`,
`scripts/bench/analyze_quality.py`) and the verification harnesses
(`scripts/verify/validate_integration.py`, `scripts/verify/validate_resilience.py`) stay
one level up: they measure **latency, retrieval quality and behaviour**, not
answer correctness. The results of both kinds live in
`docs/backend/`.
