"""
TRUSTRAG — Claim verification pipeline: metrics.

NLI batch-failure counters. Extracted from the flat ``verifier.py`` module
into its own focused file.
"""

from __future__ import annotations

import threading

from app.observability.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "_record_batch_total_failure",
    "get_nli_metrics",
]

_NLI_METRICS_LOCK = threading.Lock()
_NLI_BATCH_TOTAL_FAILURES = 0


def _record_batch_total_failure() -> None:
    global _NLI_BATCH_TOTAL_FAILURES
    with _NLI_METRICS_LOCK:
        _NLI_BATCH_TOTAL_FAILURES += 1


def get_nli_metrics() -> dict[str, int]:
    """Return NLI verification counters (batch_total_failures)."""
    with _NLI_METRICS_LOCK:
        return {"batch_total_failures": _NLI_BATCH_TOTAL_FAILURES}
