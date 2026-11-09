"""
TRUSTRAG — Claim verification pipeline: NLI verification.

Single-claim NLI, batch NLI, and fused decompose+verify operations.
Extracted from the flat ``verifier.py`` module into its own focused file.
"""

from __future__ import annotations

from typing import Any

from app.config import get_model_config
from app.llm.llm_ledger import invoke_counted
from app.llm.local_llm import is_small_model
from app.llm.model_registry import get_verification_model
from app.llm.providers.capabilities import verification_cap_kwargs
from app.observability.logging import get_logger
from app.rag.generation.generator import (
    format_context,
    neutralize_prompt_fences,
)
from app.rag.verification.pipeline.infra import (
    _structured_verifier,
)
from app.rag.verification.prompts import (
    BATCH_NLI_PROMPT_TEMPLATE,
    BATCH_NLI_PROMPT_TEMPLATE_SMALL,
    FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE,
    NLI_PROMPT_TEMPLATE,
    NLI_PROMPT_TEMPLATE_SMALL,
)
from app.rag.verification.schemas import (
    BatchNLIVerdict,
    FusedDecomposeVerify,
    NLIVerdict,
)

logger = get_logger(__name__)

__all__ = [
    "batch_verify_claims_nli",
    "fused_decompose_verify",
    "verify_claim_nli",
]


async def verify_claim_nli(
    claim: str,
    chunks: list[dict[str, Any]],
    provider: str | None = None,
    model: str | None = None,
    context_str: str | None = None,
) -> dict[str, Any]:
    """Perform NLI verification check on a single claim against evidence segments."""

    try:
        if context_str is None:
            context_str = format_context(chunks)

        model_obj = get_verification_model(provider=provider, model=model)
        cap = verification_cap_kwargs(
            provider or get_model_config().verification_provider, model, max_tokens=384
        )
        structured_nli = _structured_verifier(model_obj, provider, NLIVerdict, cap)

        prompt_str = (
            NLI_PROMPT_TEMPLATE_SMALL if is_small_model(model, provider) else NLI_PROMPT_TEMPLATE
        ).format(context_str=neutralize_prompt_fences(context_str), claim=claim)

        logger.debug("Running NLI verification for claim", claim_len=len(claim))
        response = await invoke_counted(structured_nli, [("human", prompt_str)])

        return {
            "verdict": response.verdict,
            "supporting_segments": response.supporting_segments,
            "explanation": response.explanation,
        }

    except Exception as exc:
        logger.error("NLI verification failed", claim=claim, error=str(exc))
        return {
            "verdict": "NEUTRAL",
            "supporting_segments": [],
            "explanation": "Verification could not be completed.",
        }


async def batch_verify_claims_nli(
    claims: list[str],
    chunks: list[dict[str, Any]],
    provider: str | None = None,
    model: str | None = None,
    context_str: str | None = None,
) -> dict[int, dict[str, Any]]:
    """Verify multiple claims simultaneously in a single structured call."""
    if not claims or not chunks:
        return {}

    if context_str is None:
        context_str = format_context(chunks)
    claims_list_str = "\n".join(f"{i}. {text}" for i, text in enumerate(claims, start=1))

    batch_prompt = (
        BATCH_NLI_PROMPT_TEMPLATE_SMALL
        if is_small_model(model, provider)
        else BATCH_NLI_PROMPT_TEMPLATE
    )
    prompt_str = batch_prompt.format(
        context_str=neutralize_prompt_fences(context_str), claims_list_str=claims_list_str
    )

    model_obj = get_verification_model(provider=provider, model=model)
    cap = verification_cap_kwargs(
        provider or get_model_config().verification_provider, model, max_tokens=768
    )
    structured_batch = _structured_verifier(model_obj, provider, BatchNLIVerdict, cap)

    try:
        logger.info("Executing batch NLI verification", claim_count=len(claims))
        response = await invoke_counted(structured_batch, [("human", prompt_str)])

        results: dict[int, dict[str, Any]] = {}
        for item in response.verdicts:
            results[item.claim_id] = {
                "verdict": item.verdict,
                "supporting_segments": item.supporting_segments,
                "explanation": item.explanation,
            }

        logger.info("Batch NLI verification complete", verified_count=len(results))
        return results

    except Exception as exc:
        logger.error("Batch NLI verification failed", error=str(exc))
        from app.rag.verification.pipeline.metrics import _record_batch_total_failure

        _record_batch_total_failure()
        raise


async def fused_decompose_verify(
    answer: str,
    chunks: list[dict[str, Any]],
    provider: str | None = None,
    model: str | None = None,
    context_str: str | None = None,
) -> list[dict[str, Any]] | None:
    """Decompose the answer AND verify each claim in a single structured call."""
    if not answer or not chunks:
        return None

    if context_str is None:
        context_str = format_context(chunks)

    prompt_str = FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE.format(
        context_str=neutralize_prompt_fences(context_str), answer=answer
    )

    model_obj = get_verification_model(provider=provider, model=model)
    cap = verification_cap_kwargs(
        provider or get_model_config().verification_provider, model, max_tokens=1024
    )
    structured_fused = _structured_verifier(model_obj, provider, FusedDecomposeVerify, cap)

    try:
        logger.info("Executing fused decompose+verify", answer_len=len(answer))
        response = await invoke_counted(structured_fused, [("human", prompt_str)])
        items = [
            {
                "claim": item.claim.strip(),
                "verdict": item.verdict,
                "supporting_segments": item.supporting_segments,
                "explanation": item.explanation,
            }
            for item in response.items
            if item.claim and item.claim.strip()
        ]
        logger.info("Fused decompose+verify complete", items=len(items))
        return items
    except Exception:
        logger.warning("Fused decompose+verify failed; two-step fallback advised")
        return None
