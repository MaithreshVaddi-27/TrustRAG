"""
TRUSTRAG — Claim decomposition and Natural Language Inference (NLI) verification.

Decomposes generated answers into atomic claims and verifies each claim
against candidate evidence chunks using structured output mappings.

This package re-exports the public surface:
- Core verification: execute_claim_verification, batch_verify_claims_nli
- Decomposition: decompose_answer_to_claims
- NLI: verify_claim_nli
- Schemas: ClaimDecomposition, ClaimVerdict, NLIVerdict, etc.
- Utilities: is_refusal_answer, get_nli_metrics
"""

from __future__ import annotations

from app.rag.verification.coercion import (
    _coerce_claim_id,
    _coerce_segment_list,
    _normalize_verdict_value,
    _usable_batch_verdict_item,
)
from app.rag.verification.meta import (
    _filter_degenerate_claims,
    _fused_claims_cover_answer,
    _is_meta_claim,
)
from app.rag.verification.pipeline.orchestrator import (
    UNCHECKED_CLAIM_STATE,
    batch_verify_claims_nli,
    decompose_answer_to_claims,
    execute_claim_verification,
    fused_decompose_verify,
    get_nli_metrics,
    is_refusal_answer,
    retrieve_evidence_for_claim,
    verify_claim_nli,
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
from app.rag.verification.triple import (
    extract_claim_triple_heuristic,
)

__all__ = [
    "BATCH_NLI_PROMPT_TEMPLATE",
    "BATCH_NLI_PROMPT_TEMPLATE_SMALL",
    "DECOMPOSITION_PROMPT",
    "DECOMPOSITION_PROMPT_SMALL",
    "FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE",
    "NLI_PROMPT_TEMPLATE",
    "NLI_PROMPT_TEMPLATE_SMALL",
    "UNCHECKED_CLAIM_STATE",
    "BatchNLIVerdict",
    "ClaimDecomposition",
    "ClaimVerdict",
    "FusedClaimVerdict",
    "FusedDecomposeVerify",
    "NLIVerdict",
    "_coerce_claim_id",
    "_coerce_segment_list",
    "_filter_degenerate_claims",
    "_fused_claims_cover_answer",
    "_is_meta_claim",
    "_normalize_verdict_value",
    "_usable_batch_verdict_item",
    "batch_verify_claims_nli",
    "decompose_answer_to_claims",
    "execute_claim_verification",
    "extract_claim_triple_heuristic",
    "fused_decompose_verify",
    "get_nli_metrics",
    "is_refusal_answer",
    "retrieve_evidence_for_claim",
    "verify_claim_nli",
]
