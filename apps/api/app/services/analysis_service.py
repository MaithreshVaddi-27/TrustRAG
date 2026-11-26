"""
TRUSTRAG — Analysis runs, claims, evidence, and execution trace service.

This module is now a backward-compatible re-export shim. The implementation has
been split into focused sub-modules under ``app/services/``:

- ``app/services/pipeline.py`` — create_analysis, run_analysis_pipeline, reads,
  trace events, SSE, serialization helpers
- ``app/services/claims_evidence.py`` — user-level claim/evidence/conflict reads
- ``app/services/pipeline.py`` — prompt-echo / repetition-loop detection
- ``app/services/sse.py`` — in-process SSE pub/sub
- ``app/services/analytics.py`` — analysis dossier export

All public names are re-exported here so existing imports keep working.
"""

from __future__ import annotations

from app.config import get_model_config
from app.persistence.mongodb import get_collection
from app.services.analytics import (
    export_analysis_dossier,
)
from app.services.claims_evidence import (
    list_all_user_claims,
    list_all_user_conflicts,
    list_all_user_evidence,
    list_analysis_claims,
    list_analysis_evidence,
)
from app.services.kb_service import get_kb
from app.services.pipeline import (
    _SCAFFOLD_MARKERS,
    _UNVERIFIED_ANSWER,
    _fetch_claims,
    _fetch_evidence,
    _fetch_trace,
    _looks_like_scaffold_echo,
    _presentable_answer,
    _record_completed,
    add_trace_event,
    create_analysis,
    get_analysis,
    get_analysis_claims,
    get_analysis_detail,
    get_analysis_evidence,
    get_analysis_trace,
    list_analyses,
    memory_mod,  # noqa: F401  — re-export shim; patched by tests via svc.memory_mod.trim_memory
    run_analysis_pipeline,
    serialize_analysis,
    serialize_claim,
    serialize_evidence,
    serialize_trace,
    sse_event_generator,
    strip_citation_markers,
    verdict_from_state,
)
from app.services.pipeline import (
    _UNVERIFIED_ANSWER as _UNVERIFIED_ANSWER_DEGENERATE,
)
from app.services.pipeline import (
    _looks_like_scaffold_echo as _looks_like_scaffold_echo_degenerate,
)
from app.services.sse import (
    _analysis_subscribers,
    _publish_analysis_event,
    _subscribe_to_analysis,
    _subscribers_lock,
    _unsubscribe_from_analysis,
)

__all__ = [
    "_SCAFFOLD_MARKERS",
    "_UNVERIFIED_ANSWER",
    "_UNVERIFIED_ANSWER_DEGENERATE",
    "_analysis_subscribers",
    "_fetch_claims",
    "_fetch_evidence",
    "_fetch_trace",
    "_looks_like_scaffold_echo",
    "_looks_like_scaffold_echo_degenerate",
    "_presentable_answer",
    "_publish_analysis_event",
    "_record_completed",
    "_subscribe_to_analysis",
    "_subscribers_lock",
    "_unsubscribe_from_analysis",
    "add_trace_event",
    "create_analysis",
    "export_analysis_dossier",
    "get_analysis",
    "get_analysis_claims",
    "get_analysis_detail",
    "get_analysis_evidence",
    "get_analysis_trace",
    "get_collection",
    "get_kb",
    "get_model_config",
    "list_all_user_claims",
    "list_all_user_conflicts",
    "list_all_user_evidence",
    "list_analyses",
    "list_analysis_claims",
    "list_analysis_evidence",
    "run_analysis_pipeline",
    "serialize_analysis",
    "serialize_claim",
    "serialize_evidence",
    "serialize_trace",
    "sse_event_generator",
    "strip_citation_markers",
    "verdict_from_state",
]
