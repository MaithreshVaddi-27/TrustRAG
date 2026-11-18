"""
TRUSTRAG — the evaluation package.

Everything that measures *accuracy* lives here, so that a run is one command
and the ground truth it is scored against is never separated from the
harness that scores it:

- ``eval_set``      — the ground truth: a four-document corpus and 33 probes
                      (27 answerable + 6 unanswerable).
- ``eval_accuracy`` — the harness: uploads the corpus, runs every probe
                      through the public API and scores answer accuracy,
                      abstention accuracy and the retrieval quality of the
                      evidence actually served.
- ``run_matrix.sh`` — the matrix driver: runs the harness against every
                      model configuration the project has measured, with the
                      same corpus and the same scoring, and restores the
                      shipped configuration when it finishes.

The benchmark harnesses (``bench_api``, ``bench_pipeline``,
``analyze_quality``) and the verification harnesses
(``validate_integration``, ``validate_resilience``) stay in ``scripts/``:
they measure latency, retrieval quality and behaviour, not answer
correctness.
"""

from __future__ import annotations

__all__ = ["eval_accuracy", "eval_set"]
