"""
TRUSTRAG — Claim decomposition and Natural Language Inference (NLI) verification.

Decomposes generated answers into atomic claims and verifies each claim
against candidate evidence chunks using structured output mappings.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.model_registry import get_verification_model
from app.db.mongodb import Collections, get_collection

logger = get_logger(__name__)


# ─── Pydantic Schemas for Structured LLM Mappings ─────────────────────────────


class ClaimDecomposition(BaseModel):
    """Schema to decompose text into atomic, checkable assertions."""

    claims: list[str] = Field(
        description="List of atomic, self-contained factual claims extracted from the text."
    )


class NLIVerdict(BaseModel):
    """Schema for claim NLI verification verdict."""

    verdict: Literal["SUPPORTED", "CONTRADICTED", "NEUTRAL"] = Field(
        description=(
            "SUPPORTED if context directly proves it. "
            "CONTRADICTED if context refutes it. "
            "NEUTRAL if context has insufficient info."
        )
    )
    supporting_segments: list[int] = Field(
        description=(
            "1-based index numbers of context segments containing "
            "supporting or contradicting evidence. Empty if NEUTRAL."
        )
    )
    explanation: str = Field(
        description=(
            "A brief factual explanation of why this verdict was "
            "chosen based on the context segments."
        )
    )


# ─── Verification Prompts ─────────────────────────────────────────────────────

DECOMPOSITION_PROMPT = """Decompose the provided text into a list of
atomic, self-contained factual assertions.
Each claim must be checkable independently and make sense without context
(substitute pronouns with actual names).
Exclude conversational fillers, greetings, and subjective opinions.
"""

NLI_PROMPT_TEMPLATE = """You are an expert Natural Language Inference (NLI) verifier.
Your task is to determine the verification status of the Claim below
based ONLY on the provided Context segments.

[CONTEXT]
{context_str}

[CLAIM]
{claim}

Strict Rules:
- SUPPORTED: The context explicitly contains details supporting the claim.
- CONTRADICTED: The context explicitly contains details directly refuting or denying the claim.
- NEUTRAL: The context does not contain enough information to support or contradict the claim.
"""


# ─── Pipeline Core Functions ──────────────────────────────────────────────────


async def decompose_answer_to_claims(answer: str) -> list[str]:
    """Decompose the generated answer into atomic claims using Gemini structured outputs."""
    if not answer or answer == "ABSTAIN":
        return []

    try:
        model = get_verification_model()
        structured_llm = model.with_structured_output(ClaimDecomposition)

        logger.info("Running answer claim decomposition", answer_len=len(answer))

        response = await structured_llm.ainvoke(
            [("system", DECOMPOSITION_PROMPT), ("human", f"Text to decompose:\n{answer}")]
        )

        claims = [c.strip() for c in response.claims if c.strip()]
        logger.info("Claims decomposed", count=len(claims))
        return claims

    except Exception as exc:
        logger.error("Claim decomposition failed", error=str(exc))
        # Fallback: treat full answer as a single claim if structured call fails
        return [answer] if len(answer.strip()) > 0 else []


async def verify_claim_nli(claim: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Perform NLI verification check on a single claim against retrieved evidence segments.

    Returns:
      {
        "verdict": "SUPPORTED" | "CONTRADICTED" | "NEUTRAL",
        "supporting_segments": [1-based indices],
        "explanation": "text explanation"
      }
    """
    try:
        # Format candidate segments
        from app.generation.generator import format_context

        context_str = format_context(chunks)

        model = get_verification_model()
        structured_nli = model.with_structured_output(NLIVerdict)

        prompt_str = NLI_PROMPT_TEMPLATE.format(context_str=context_str, claim=claim)

        logger.debug("Running NLI verification for claim", claim_len=len(claim))

        response = await structured_nli.ainvoke([("human", prompt_str)])

        return {
            "verdict": response.verdict,
            "supporting_segments": response.supporting_segments,
            "explanation": response.explanation,
        }

    except Exception as exc:
        logger.error("NLI verification failed", claim=claim, error=str(exc))
        # Default to NEUTRAL on exception for safety
        return {
            "verdict": "NEUTRAL",
            "supporting_segments": [],
            "explanation": f"Verification failed due to error: {exc!s}",
        }


async def execute_claim_verification(
    analysis_id_str: str, answer: str, chunks: list[dict[str, Any]], evidence_ids: list[ObjectId]
) -> list[dict[str, Any]]:
    """
    Decompose answer, execute NLI verifications, and save claims to MongoDB.

    Links claim records to the appropriate persisted Evidence object IDs.
    """
    analysis_id = ObjectId(analysis_id_str)
    claims_coll = get_collection(Collections.CLAIMS)

    # 1. Decompose answer into atomic assertions
    claims_texts = await decompose_answer_to_claims(answer)

    verified_claims = []

    # 2. Verify each claim
    for text in claims_texts:
        nli_res = await verify_claim_nli(text, chunks)

        # Resolve 1-based supporting segments list to MongoDB Evidence IDs
        supporting_evidence_ids = []
        for idx in nli_res["supporting_segments"]:
            # Make sure index falls within boundaries
            if 0 < idx <= len(evidence_ids):
                supporting_evidence_ids.append(evidence_ids[idx - 1])

        claim_doc = {
            "analysis_id": analysis_id,
            "text": text,
            "state": nli_res["verdict"],
            "explanation": nli_res["explanation"],
            "evidence_ids": supporting_evidence_ids,
            "created_at": datetime.now(UTC),
        }

        result = await claims_coll.insert_one(claim_doc)
        claim_doc["_id"] = result.inserted_id

        verified_claims.append(claim_doc)

    return verified_claims
