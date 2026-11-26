"""
TRUSTRAG — the benchmark package.

Harnesses that measure *how the system behaves*, not whether its answers are
right:

- ``bench_api``        — black-box HTTP latency for the API surface.
- ``bench_pipeline``   — in-process stage latency for the RAG pipeline.
- ``bench_auth``       — the shared benchmark account (register or log in).
- ``analyze_quality``  — retrieval quality over the analyses a run produced.

Accuracy lives next door, in ``scripts/eval/``: the two answer different
questions and are scored differently.
"""

from __future__ import annotations

__all__ = ["analyze_quality", "bench_api", "bench_auth", "bench_pipeline"]
