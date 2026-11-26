"""
TRUSTRAG — Claim verification Pydantic schemas.

Structured-output mapping schemas for claim decomposition, NLI verdicts,
batch verification, and fused decompose+verify calls.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = [
    "BatchNLIVerdict",
    "ClaimDecomposition",
    "ClaimVerdict",
    "FusedClaimVerdict",
    "FusedDecomposeVerify",
    "NLIVerdict",
]


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
        default_factory=list,
        description=(
            "1-based index numbers of context segments containing "
            "supporting or contradicting evidence. Empty if NEUTRAL."
        ),
    )
    explanation: str = Field(
        default="",
        description=(
            "A brief factual explanation of why this verdict was "
            "chosen based on the context segments."
        ),
    )

    @field_validator("verdict", mode="before")
    @classmethod
    def _tolerate_verdict_aliases(cls, value: Any) -> Any:
        from app.rag.verification.coercion import (
            _normalize_verdict_value,
        )

        return _normalize_verdict_value(value)

    @field_validator("supporting_segments", mode="before")
    @classmethod
    def _tolerate_segment_shapes(cls, value: Any) -> Any:
        from app.rag.verification.coercion import (
            _coerce_segment_list,
        )

        return _coerce_segment_list(value)


class ClaimVerdict(BaseModel):
    """Schema for an individual claim verification inside a batch."""

    claim_id: int = Field(description="1-based index number of the claim matching input list.")
    verdict: Literal["SUPPORTED", "CONTRADICTED", "NEUTRAL"] = Field(
        description=(
            "SUPPORTED if context proves it, CONTRADICTED if context refutes it, "
            "NEUTRAL if insufficient."
        )
    )
    supporting_segments: list[int] = Field(
        default_factory=list,
        description=(
            "1-based index numbers of context segments containing supporting or "
            "contradicting evidence."
        ),
    )
    explanation: str = Field(
        default="",
        description="Brief factual explanation of the verdict.",
    )

    @field_validator("claim_id", mode="before")
    @classmethod
    def _tolerate_claim_id(cls, value: Any) -> Any:
        from app.rag.verification.coercion import (
            _coerce_claim_id,
        )

        return _coerce_claim_id(value)

    @field_validator("verdict", mode="before")
    @classmethod
    def _tolerate_verdict_aliases(cls, value: Any) -> Any:
        from app.rag.verification.coercion import (
            _normalize_verdict_value,
        )

        return _normalize_verdict_value(value)

    @field_validator("supporting_segments", mode="before")
    @classmethod
    def _tolerate_segment_shapes(cls, value: Any) -> Any:
        from app.rag.verification.coercion import (
            _coerce_segment_list,
        )

        return _coerce_segment_list(value)


class BatchNLIVerdict(BaseModel):
    """Schema for batch NLI verification across multiple claims in a single call."""

    verdicts: list[ClaimVerdict] = Field(
        description="List of verification verdicts for each numbered claim."
    )

    @model_validator(mode="before")
    @classmethod
    def _drop_unrecoverable_items(cls, data: Any) -> Any:
        from app.rag.verification.coercion import (
            _usable_batch_verdict_item,
        )

        if not isinstance(data, dict):
            return data

        raw = data.get("verdicts")
        if not isinstance(raw, list):
            for alias in (
                "verdicts",
                "verdict",
                "vericits",
                "results",
                "statements",
                "claims",
                "data",
                "items",
            ):
                candidate = data.get(alias)
                if isinstance(candidate, list):
                    raw = candidate
                    break

        kept: list[Any] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    usable = _usable_batch_verdict_item(item)
                    if usable is not None:
                        kept.append(usable)
                elif isinstance(item, str):
                    try:
                        parsed = __import__("json").loads(item)
                    except (ValueError, TypeError):
                        parsed = None
                    if isinstance(parsed, dict):
                        usable = _usable_batch_verdict_item(parsed)
                        if usable is not None:
                            kept.append(usable)
                    else:
                        pass  # drop unrecoverable items
                else:
                    pass  # drop unrecoverable items

        return {**data, "verdicts": kept}


class FusedClaimVerdict(BaseModel):
    """One atomic claim AND its verification, produced in a single call."""

    claim: str = Field(
        description=(
            "One atomic, self-contained factual assertion from the answer "
            "(pronouns resolved, no conversational filler, never about the "
            "question/asker/answering process itself)."
        )
    )
    verdict: Literal["SUPPORTED", "CONTRADICTED", "NEUTRAL"] = Field(
        description=(
            "SUPPORTED if context proves it, CONTRADICTED if context refutes it, "
            "NEUTRAL if insufficient."
        )
    )
    supporting_segments: list[int] = Field(
        default_factory=list,
        description="1-based index numbers of supporting/refuting segments.",
    )
    explanation: str = Field(
        default="",
        description="Brief factual explanation (under 15 words).",
    )

    @field_validator("verdict", mode="before")
    @classmethod
    def _tolerate_verdict_aliases(cls, value: Any) -> Any:
        from app.rag.verification.coercion import (
            _normalize_verdict_value,
        )

        return _normalize_verdict_value(value)

    @field_validator("supporting_segments", mode="before")
    @classmethod
    def _tolerate_segment_shapes(cls, value: Any) -> Any:
        from app.rag.verification.coercion import (
            _coerce_segment_list,
        )

        return _coerce_segment_list(value)


class FusedDecomposeVerify(BaseModel):
    """Decompose-then-verify in one structured call."""

    items: list[FusedClaimVerdict] = Field(
        description="Atomic claims from the answer, each with its NLI verdict."
    )
