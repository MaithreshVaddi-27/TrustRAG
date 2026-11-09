"""
TRUSTRAG — Claim decomposition and Natural Language Inference (NLI) verification.

This module is now a backward-compatible re-export shim. The implementation has
been split into focused sub-modules under ``app/rag/verification/pipeline/``:

- ``app.rag.verification.pipeline.infra`` — shared helpers
  (_structured_verifier, _chunk_identity, etc.)
- ``app.rag.verification.pipeline.decomposition`` — decompose_answer_to_claims
- ``app.rag.verification.pipeline.nli`` — verify_claim_nli,
  batch_verify_claims_nli, fused_decompose_verify
- ``app.rag.verification.pipeline.retrieval`` — retrieve_evidence_for_claim,
  _persist_claim_evidence
- ``app.rag.verification.pipeline.metrics`` — get_nli_metrics,
  _record_batch_total_failure
- ``app.rag.verification.pipeline.orchestrator`` — execute_claim_verification

All public names are re-exported here so existing imports keep working.
"""

from __future__ import annotations

from app.llm.model_registry import get_verification_model
from app.persistence.mongodb import get_collection
from app.rag.verification.coercion import _normalize_verdict_value
from app.rag.verification.meta import (
    _PREDICATE_VERBS,
    _filter_degenerate_claims,
    _fused_claims_cover_answer,
)
from app.rag.verification.pipeline.decomposition import decompose_answer_to_claims
from app.rag.verification.pipeline.infra import (  # noqa: F401
    NLI_PER_CALL_TIMEOUT_SECONDS,
    UNCHECKED_CLAIM_STATE,
    _apply_cap_via_model_copy,
    _await_nli_call,
    _chunk_identity,
    _nli_timeout_seconds,
    _safe_object_id,
    _structured_verifier,
)
from app.rag.verification.pipeline.metrics import (
    _record_batch_total_failure,
    get_nli_metrics,
)
from app.rag.verification.pipeline.nli import (
    batch_verify_claims_nli,
    fused_decompose_verify,
    verify_claim_nli,
)
from app.rag.verification.pipeline.orchestrator import (
    _is_meta_claim,
    _is_small,
    execute_claim_verification,
)
from app.rag.verification.pipeline.retrieval import (  # noqa: F401
    _persist_claim_evidence,
    retrieve_evidence_for_claim,
)
from app.rag.verification.prompts import (
    BATCH_NLI_PROMPT_TEMPLATE,
    BATCH_NLI_PROMPT_TEMPLATE_SMALL,
    DECOMPOSITION_PROMPT,
    DECOMPOSITION_PROMPT_SMALL,
    FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE,
    NLI_PROMPT_TEMPLATE,
    NLI_PROMPT_TEMPLATE_SMALL,
)
from app.rag.verification.schemas import (
    BatchNLIVerdict,
    ClaimDecomposition,
    ClaimVerdict,
    FusedClaimVerdict,
    FusedDecomposeVerify,
    NLIVerdict,
)
from app.rag.verification.triple import extract_claim_triple_heuristic
from app.rag.verification.verdict import is_refusal_answer

__all__ = [
    "BATCH_NLI_PROMPT_TEMPLATE",
    "BATCH_NLI_PROMPT_TEMPLATE_SMALL",
    "DECOMPOSITION_PROMPT",
    "DECOMPOSITION_PROMPT_SMALL",
    "FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE",
    "NLI_PROMPT_TEMPLATE",
    "NLI_PROMPT_TEMPLATE_SMALL",
    "UNCHECKED_CLAIM_STATE",
    "_PREDICATE_VERBS",
    "BatchNLIVerdict",
    "ClaimDecomposition",
    "ClaimVerdict",
    "FusedClaimVerdict",
    "FusedDecomposeVerify",
    "NLIVerdict",
    "_apply_cap_via_model_copy",
    "_await_nli_call",
    "_chunk_identity",
    "_filter_degenerate_claims",
    "_fused_claims_cover_answer",
    "_is_meta_claim",
    "_is_small",
    "_nli_timeout_seconds",
    "_normalize_verdict_value",
    "_record_batch_total_failure",
    "_safe_object_id",
    "_structured_verifier",
    "batch_verify_claims_nli",
    "decompose_answer_to_claims",
    "execute_claim_verification",
    "extract_claim_triple_heuristic",
    "fused_decompose_verify",
    "get_collection",
    "get_nli_metrics",
    "get_verification_model",
    "is_refusal_answer",
    "verify_claim_nli",
]
