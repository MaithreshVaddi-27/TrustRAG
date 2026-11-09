"""
TRUSTRAG — observability capability package.

Re-exports from the canonical submodules so ``app.observability`` behaves as a
single package:

- ``app.observability.logging`` — configure_logging, get_logger, scrub_secret_values
- ``app.observability.metrics`` — record_http_request, record_analysis_created,
  record_analysis_completed, record_recovery_attempt, record_verification_claims,
  record_tokens_estimated, record_budget_rejection, estimate_tokens,
  reset_for_tests, snapshot, render_prometheus
- ``app.observability.tracing`` — init_tracing, tracing_middleware
"""

from __future__ import annotations

from app.observability.logging import (  # noqa: F401
    configure_logging,
    get_logger,
    scrub_secret_values,
)
from app.observability.metrics import (  # noqa: F401
    estimate_tokens,
    record_analysis_completed,
    record_analysis_created,
    record_budget_rejection,
    record_http_request,
    record_recovery_attempt,
    record_tokens_estimated,
    record_verification_claims,
    render_prometheus,
    reset_for_tests,
    snapshot,
)
from app.observability.tracing import (  # noqa: F401
    init_tracing,
    tracing_middleware,
)

__all__ = [
    "configure_logging",
    "get_logger",
    "scrub_secret_values",
    "estimate_tokens",
    "record_analysis_completed",
    "record_analysis_created",
    "record_budget_rejection",
    "record_http_request",
    "record_recovery_attempt",
    "record_tokens_estimated",
    "record_verification_claims",
    "render_prometheus",
    "reset_for_tests",
    "snapshot",
    "init_tracing",
    "tracing_middleware",
]
