"""
Pydantic schemas for Analysis runs, claims, and evidence.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config.model_config import (
    SUPPORTED_LLM_PROVIDERS,
    get_model_config,
    normalize_provider,
)
from app.core.config.settings import get_settings

# Module-level imports (verified cycle-free): the AnalysisCreate validator
# resolves provider allowlists on every request, so keeping these at the top
# avoids per-call import lookups.
from app.llm import local_llm as _local_llm_mod


class AnalysisCreate(BaseModel):
    knowledge_base_id: str = Field(..., description="Target knowledge base")
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User question (max 2000 characters to bound token cost)",
    )
    enable_web_search: bool = Field(
        default=False,
        description="Whether to ground analysis using live web search via MCP",
    )
    web_search_provider: str = Field(
        default="both",
        description="Accepted for compatibility; web grounding is Tavily-only",
    )
    llm_provider: str | None = Field(
        default=None,
        description=("Active LLM provider override ('ollama', 'llama_cpp', 'mlx', 'gemini')"),
    )
    llm_model: str | None = Field(
        default=None,
        description="Specific model identifier override (e.g. 'granite4.2:3b-q4_K_M')",
    )

    @model_validator(mode="after")
    def enforce_server_model_policy(self) -> AnalysisCreate:
        """Reject free-form provider/model IDs before they reach model loaders.

        Operator-managed environment overrides are trusted, but API callers may
        only select models exposed by this deployment. This prevents arbitrary
        Hugging Face downloads and unbudgeted cloud model invocations.
        """
        cfg = get_model_config()
        settings = get_settings()

        provider = normalize_provider(self.llm_provider or cfg.llm_provider)
        if provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # Local providers use models discovered from the running server /
        # local cache (see local_llm.get_discovered_llms). A local server can only
        # serve weights already on disk, so discovery never opens an arbitrary
        # auto-download path — but it does let operators select freshly-installed
        # models that the /models dropdown already lists.
        allowed_llms = {
            "ollama": set(_local_llm_mod.get_discovered_llms("ollama")),
            "llama_cpp": set(_local_llm_mod.get_discovered_llms("llama_cpp")),
            "mlx": set(_local_llm_mod.get_discovered_llms("mlx")),
            # Cloud allowlists live in models.yaml (single source of truth) —
            # never hardcode model IDs here, or the next model release 422s
            # again (cf. gemini-3.8-flash).
            "gemini": set(cfg.supported_gemini_models),
        }
        operator_llm_overrides = {
            "ollama": settings.ollama_model,
            "llama_cpp": settings.llamacpp_model,
            "mlx": settings.mlx_model,
            "gemini": settings.gemini_model,
        }
        if operator_llm_overrides.get(provider):
            allowed_llms[provider].add(operator_llm_overrides[provider])
        if provider in ("ollama", "llama_cpp", "mlx") and not allowed_llms[provider]:
            # New-user path: nothing installed yet. Fail closed with the fix
            # instead of a bare "not enabled" rejection.
            start_hints = {
                "ollama": "'ollama pull granite4.2:3b-q4_K_M' + 'ollama serve'",
                "llama_cpp": "place a GGUF and run ./scripts/start_local_llm.sh",
                "mlx": "'pip install mlx-lm' then 'mlx_lm.server --model "
                "mlx-community/Llama-3.2-1B-Instruct-4bit' (Apple Silicon only)",
            }
            raise ValueError(
                f"No {provider} models discovered on this host. Install one "
                f"({start_hints[provider]}), then refresh."
            )

        requested_llm_model = (
            self.llm_model
            or operator_llm_overrides.get(provider)
            or (cfg.llm_model_for(provider) if provider in ("ollama", "llama_cpp", "mlx") else None)
        )
        if requested_llm_model and requested_llm_model not in allowed_llms[provider]:
            raise ValueError(f"Model is not enabled for provider '{provider}'")

        # Validate the EFFECTIVE model, not just the optional request field
        # (audit B-15). The old check returned early when `llm_model` was
        # omitted: for a cloud provider `requested_llm_model` is then None, so
        # no allowlist check ran at all and the resolved config default went
        # through unvalidated. Whatever model will actually be used must be in
        # the allowlist.
        effective_llm_model = requested_llm_model or cfg.llm_model_for(provider)
        if effective_llm_model and effective_llm_model not in allowed_llms[provider]:
            raise ValueError(
                f"Model '{effective_llm_model}' is not enabled for provider '{provider}'. "
                f"Allowed: {sorted(allowed_llms[provider]) or '(none discovered)'}."
            )

        # Apply the same allowlist to the resolved VERIFICATION model (audit
        # B-15). The verifier runs its own billed, long-timeout calls, and until
        # now nothing constrained which cloud model those calls could target —
        # an operator-set (or drifted) verification model would silently bill an
        # unbudgeted model that the generation allowlist already forbids.
        #
        # Only cloud providers are checked here. A local server can only serve
        # weights already on disk, so a local verification model is inherently
        # bounded — the same argument made for the generation model above.
        v_provider = normalize_provider(cfg.verification_provider)
        if v_provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(f"Unsupported verification provider: {v_provider}")
        if v_provider == "gemini":
            v_allowed = set(allowed_llms[v_provider])
            # An explicit env override is an operator decision, same trust level
            # as settings.<provider>_model above: honour it rather than 422.
            env_v_model = os.environ.get("GEMINI_VERIFICATION_MODEL") or os.environ.get(
                "VERIFICATION_MODEL"
            )
            if env_v_model:
                v_allowed.add(env_v_model)
            v_model = cfg.verification_model_for(v_provider)
            if v_model and v_model not in v_allowed:
                raise ValueError(
                    f"Verification model '{v_model}' is not enabled for provider "
                    f"'{v_provider}'. Allowed: {sorted(v_allowed)}."
                )
        return self


class ReliabilitySummary(BaseModel):
    score: float | None = None
    status: str = "PENDING"  # TRUSTED, UNCERTAIN, ABSTAINED, FAILED, PENDING


class DiagnosisSummary(BaseModel):
    type: str | None = None  # RETRIEVAL_FAILURE, EVIDENCE_FAILURE, etc.
    failures: list[str] = []


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    user_id: str
    knowledge_base_id: str
    query: str
    # Actual values written by analysis_service: pending, processing, completed,
    # failed, abstained. There is no "running" — poll until the status leaves
    # pending/processing. (This comment is rendered in /docs, so it is part of the
    # published contract.)
    status: str
    answer: str | None = None
    reliability: ReliabilitySummary
    diagnosis: DiagnosisSummary
    created_at: datetime
    config_snapshot: dict[str, Any] | None = None
    web_search_enabled: bool = False
    web_search_provider: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None


class ClaimResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    analysis_id: str
    text: str
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    state: str  # SUPPORTED, CONTRADICTED, NEUTRAL
    explanation: str | None = None
    evidence_ids: list[str] = []
    created_at: datetime


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    analysis_id: str
    text: str
    document_id: str
    filename: str | None = None
    url: str | None = None
    retrieval_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    method: str | None = None  # dense, sparse, hybrid
    integrity_status: str | None = None  # VERIFIED, CORRUPTED
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    created_at: datetime


class TraceEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event: str
    timestamp: datetime
    data: dict[str, Any] = {}
