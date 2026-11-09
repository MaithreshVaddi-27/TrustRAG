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

from app.llm.model_registry import get_verification_model  # noqa: F401
from app.persistence.mongodb import get_collection  # noqa: F401
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
from app.rag.verification.pipeline.metrics import (  # noqa: F401
    _record_batch_total_failure,
    get_nli_metrics,
)
from app.rag.verification.pipeline.nli import (  # noqa: F401
    batch_verify_claims_nli,
    fused_decompose_verify,
    verify_claim_nli,
)
from app.rag.verification.pipeline.orchestrator import (  # noqa: F401
    execute_claim_verification,
    _is_small,
)
from app.rag.verification.pipeline.retrieval import (  # noqa: F401
    _persist_claim_evidence,
    retrieve_evidence_for_claim,
)
from app.rag.verification.verdict import is_refusal_answer  # noqa: F401
from app.rag.verification.meta import (  # noqa: F401
    _PREDICATE_VERBS,
    _filter_degenerate_claims,
    _fused_claims_cover_answer,
)
from app.rag.verification.pipeline.orchestrator import _is_meta_claim
from app.rag.verification.triple import extract_claim_triple_heuristic  # noqa: F401
from app.rag.verification.schemas import (  # noqa: F401
    BatchNLIVerdict,
    ClaimDecomposition,
    ClaimVerdict,
    FusedClaimVerdict,
    FusedDecomposeVerify,
    NLIVerdict,
)
from app.rag.verification.coercion import _normalize_verdict_value  # noqa: F401
from app.rag.verification.prompts import (  # noqa: F401
    DECOMPOSITION_PROMPT,
    DECOMPOSITION_PROMPT_SMALL,
    NLI_PROMPT_TEMPLATE,
    NLI_PROMPT_TEMPLATE_SMALL,
    BATCH_NLI_PROMPT_TEMPLATE,
    BATCH_NLI_PROMPT_TEMPLATE_SMALL,
    FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE,
)

__all__ = [
    "UNCHECKED_CLAIM_STATE",
    "_apply_cap_via_model_copy",
    "_await_nli_call",
    "_chunk_identity",
    "_nli_timeout_seconds",
    "_record_batch_total_failure",
    "_safe_object_id",
    "_structured_verifier",
    "batch_verify_claims_nli",
    "decompose_answer_to_claims",
    "execute_claim_verification",
    "fused_decompose_verify",
    "get_nli_metrics",
    "get_verification_model",
    "is_refusal_answer",
    "verify_claim_nli",
    "FusedClaimVerdict",
    "FusedDecomposeVerify",
    "get_collection",
    "_filter_degenerate_claims",
    "_PREDICATE_VERBS",
    "extract_claim_triple_heuristic",
    "_fused_claims_cover_answer",
    "_is_small",
    "_is_meta_claim",
    "_normalize_verdict_value",
    "DECOMPOSITION_PROMPT",
    "DECOMPOSITION_PROMPT_SMALL",
    "NLI_PROMPT_TEMPLATE",
    "NLI_PROMPT_TEMPLATE_SMALL",
    "BATCH_NLI_PROMPT_TEMPLATE",
    "BATCH_NLI_PROMPT_TEMPLATE_SMALL",
    "FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE",
    "NLIVerdict",
    "ClaimDecomposition",
    "ClaimVerdict",
    "BatchNLIVerdict",
    "BatchNLIVerdict",
]
