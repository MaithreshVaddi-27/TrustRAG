"""
TRUSTRAG — lightweight metrics (backward-compatible re-export shim).

`app.core.observability.metrics` is the legacy import path.  The canonical
module now lives at ``app.observability.metrics``; both names must share the
same in-memory counters, so this shim imports and re-exports everything from
the canonical location rather than duplicating the state.
"""

from __future__ import annotations

from app.observability.metrics import *  # noqa: F401, F403
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
