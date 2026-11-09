"""
TRUSTRAG — Claim verification pipeline: shared infra.

Shared helpers used by every pipeline sub-module, kept here to avoid circular
imports between decomposition, NLI, retrieval, and orchestration.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.config import get_model_config, normalize_provider
from app.observability.logging import get_logger
from app.persistence.mongodb import Collections, get_collection
from app.llm.local_llm import is_small_model
from app.rag.generation.context import extract_citations
from app.rag.verification.meta import _is_meta_claim
from app.rag.verification.schemas import ClaimVerdict
from app.rag.verification.triple import extract_claim_triple_heuristic
from app.rag.verification.verdict import is_refusal_answer

logger = get_logger(__name__)

__all__ = [
    "UNCHECKED_CLAIM_STATE",
    "NLI_PER_CALL_TIMEOUT_SECONDS",
    "_apply_cap_via_model_copy",
    "_await_nli_call",
    "_chunk_identity",
    "_nli_timeout_seconds",
    "_safe_object_id",
    "_structured_verifier",
]

# ─── Sentinel ─────────────────────────────────────────────────────────────────
UNCHECKED_CLAIM_STATE = "UNCHECKED"

# ─── Per-call NLI timeout ────────────────────────────────────────────────────
NLI_PER_CALL_TIMEOUT_SECONDS = 90

_CLOUD_PROVIDERS = frozenset({"gemini"})


def _resolve_model_config():
    """Resolve get_model_config through app.core.config shim so patches land."""
    import sys

    core_cfg = sys.modules.get("app.core.config")
    if core_cfg is not None and hasattr(core_cfg, "get_model_config"):
        return core_cfg.get_model_config()
    return get_model_config()


def _nli_timeout_default() -> int:
    import sys

    shim = sys.modules.get("app.rag.verification.verifier")
    if shim is not None and hasattr(shim, "NLI_PER_CALL_TIMEOUT_SECONDS"):
        return int(shim.NLI_PER_CALL_TIMEOUT_SECONDS)
    return NLI_PER_CALL_TIMEOUT_SECONDS


def _nli_timeout_seconds() -> int:
    """Per-call NLI budget, scaled by provider."""
    try:
        cfg = _resolve_model_config()
        if normalize_provider(cfg.verification_provider) in _CLOUD_PROVIDERS:
            configured = int(getattr(cfg, "llm_timeout_seconds", 0) or 0)
            if configured > _nli_timeout_default():
                return configured
    except Exception:
        logger.debug("NLI timeout: falling back to default", exc_info=True)
    return _nli_timeout_default()


async def _await_nli_call(coro, *, what: str):
    """Await one NLI LLM call with a per-call timeout."""
    timeout_s = _nli_timeout_seconds()
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except TimeoutError:
        logger.warning("NLI call timed out", what=what, timeout_s=timeout_s)
        raise


def _structured_verifier(
    model_obj: Any,
    provider: str | None,
    schema: type,
    cap: dict[str, Any],
):
    """Build the structured-output verifier for the active provider."""
    norm = (provider or get_model_config().verification_provider or "").strip().lower()

    if norm in ("gemini", "google_genai"):
        return _apply_cap_via_model_copy(model_obj, cap).with_structured_output(schema)

    return model_obj.with_structured_output(schema, **cap)


def _apply_cap_via_model_copy(model_obj: Any, cap: dict[str, Any]) -> Any:
    """Return a copy of `model_obj` with output-cap fields applied."""
    if not cap:
        return model_obj
    fields = getattr(type(model_obj), "model_fields", None)
    if not fields:
        return model_obj
    applicable = {k: v for k, v in cap.items() if k in fields}
    if not applicable:
        return model_obj
    try:
        return model_obj.model_copy(update=applicable)
    except Exception:
        logger.debug("model_copy cap application failed", exc_info=True)
        return model_obj


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _chunk_identity(chunk: dict[str, Any]) -> tuple[str, Any, str]:
    """Stable dedup key for retrieved chunks across retrieval rounds."""
    return (
        str(chunk.get("document_id") or ""),
        chunk.get("chunk_index"),
        (chunk.get("text") or "")[:80],
    )


def _safe_object_id(value: Any) -> ObjectId | None:
    """Convert to ObjectId, returning None for missing/malformed ids."""
    if not value:
        return None
    try:
        return value if isinstance(value, ObjectId) else ObjectId(str(value))
    except Exception:
        logger.debug("Invalid ObjectId format: %s", value)
        return None
