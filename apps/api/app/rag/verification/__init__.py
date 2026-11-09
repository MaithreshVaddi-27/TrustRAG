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

from app.rag.verification.pipeline.orchestrator import (
    execute_claim_verification,
    batch_verify_claims_nli,
    fused_decompose_verify,
    decompose_answer_to_claims,
    verify_claim_nli,
    retrieve_evidence_for_claim,
    get_nli_metrics,
    is_refusal_answer,
    UNCHECKED_CLAIM_STATE,
)
from app.rag.verification.pipeline.decomposition import (
    decompose_answer_to_claims as _decompose_impl,
)
from app.rag.verification.pipeline.nli import (
    verify_claim_nli as _verify_nli_impl,
)
from app.rag.verification.schemas import (
    ClaimDecomposition,
    ClaimVerdict,
    NLIVerdict,
    FusedDecomposeVerify,
    FusedClaimVerdict,
    BatchNLIVerdict,
)
from app.rag.verification.prompts import (
    DECOMPOSITION_PROMPT,
    DECOMPOSITION_PROMPT_SMALL,
    NLI_PROMPT_TEMPLATE,
    NLI_PROMPT_TEMPLATE_SMALL,
    BATCH_NLI_PROMPT_TEMPLATE,
    BATCH_NLI_PROMPT_TEMPLATE_SMALL,
    FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE,
)
from app.rag.verification.verdict import (
    is_refusal_answer as _is_refusal_impl,
)
from app.rag.verification.coercion import (
    _coerce_claim_id,
    _coerce_segment_list,
    _usable_batch_verdict_item,
    _normalize_verdict_value,
)
from app.rag.verification.meta import (
    _filter_degenerate_claims,
    _is_meta_claim,
    _fused_claims_cover_answer,
)
from app.rag.verification.triple import (
    extract_claim_triple_heuristic,
)

__all__ = [
    # Core orchestration
    "execute_claim_verification",
    "batch_verify_claims_nli",
    "fused_decompose_verify",
    "decompose_answer_to_claims",
    "verify_claim_nli",
    "retrieve_evidence_for_claim",
    "get_nli_metrics",
    "is_refusal_answer",
    # Schemas
    "ClaimDecomposition",
    "ClaimVerdict",
    "NLIVerdict",
    "FusedDecomposeVerify",
    "FusedClaimVerdict",
    "BatchNLIVerdict",
    # Prompts
    "DECOMPOSITION_PROMPT",
    "DECOMPOSITION_PROMPT_SMALL",
    "NLI_PROMPT_TEMPLATE",
    "NLI_PROMPT_TEMPLATE_SMALL",
    "BATCH_NLI_PROMPT_TEMPLATE",
    "BATCH_NLI_PROMPT_TEMPLATE_SMALL",
    "FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE",
    # Internal utilities (re-exported for backward compat)
    "UNCHECKED_CLAIM_STATE",
    "_coerce_claim_id",
    "_coerce_segment_list",
    "_usable_batch_verdict_item",
    "_normalize_verdict_value",
    "_filter_degenerate_claims",
    "_is_meta_claim",
    "_fused_claims_cover_answer",
    "extract_claim_triple_heuristic",
]