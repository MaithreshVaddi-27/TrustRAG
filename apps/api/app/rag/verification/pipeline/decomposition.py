"""
TRUSTRAG — Claim verification pipeline: decomposition.

Decomposes generated answers into atomic claims using structured outputs.
"""

from __future__ import annotations

from app.llm.llm_ledger import invoke_counted
from app.llm.local_llm import is_small_model
from app.llm.model_registry import get_verification_model
from app.llm.providers.capabilities import verification_cap_kwargs
from app.observability.logging import get_logger
from app.rag.verification.pipeline.infra import _structured_verifier
from app.rag.verification.prompts import DECOMPOSITION_PROMPT, DECOMPOSITION_PROMPT_SMALL
from app.rag.verification.schemas import ClaimDecomposition

logger = get_logger(__name__)

__all__ = ["decompose_answer_to_claims"]


async def decompose_answer_to_claims(
    answer: str, provider: str | None = None, model: str | None = None
) -> list[str]:
    """Decompose the generated answer into atomic claims using structured outputs."""
    if not answer:
        return []

    try:
        model_obj = get_verification_model(provider=provider, model=model)
        cap = verification_cap_kwargs(
            provider or "default", model, max_tokens=512
        )
        structured_llm = _structured_verifier(model_obj, provider, ClaimDecomposition, cap)

        logger.info("Running answer claim decomposition", answer_len=len(answer))

        decomp_prompt = (
            DECOMPOSITION_PROMPT_SMALL
            if is_small_model(model, provider)
            else DECOMPOSITION_PROMPT
        )
        response = await invoke_counted(
            structured_llm,
            [("system", decomp_prompt), ("human", f"Text to decompose:\n{answer}")],
        )

        claims = [c.strip() for c in response.claims if c.strip()]
        before = len(claims)
        claims = [
            c
            for c in claims
            if not c.strip().lower().startswith(("the user", "this is", "the question"))
        ]
        if len(claims) != before:
            logger.info("Filtered meta-claims about the query itself", dropped=before - len(claims))
        logger.info("Claims decomposed", count=len(claims))
        return claims

    except Exception as exc:
        logger.error("Claim decomposition failed", error=str(exc))
        return [answer] if len(answer.strip()) > 0 else []
