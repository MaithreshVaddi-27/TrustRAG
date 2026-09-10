"""
Pydantic schemas for Analysis runs, claims, and evidence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
        description="Web search provider: 'tavily', 'duckduckgo', or 'both'",
    )
    llm_provider: str | None = Field(
        default=None,
        description="Active LLM provider override ('ollama', 'llama_cpp', 'gemini', 'nvidia')",
    )
    llm_model: str | None = Field(
        default=None,
        description="Specific model identifier override (e.g. 'granite4.2:3b-q4_K_M')",
    )
    embedding_provider: str | None = Field(
        default=None,
        description=(
            "Active embedding provider override ('huggingface' only — "
            "embeddings are local-only; cloud and LLM-server providers are rejected)."
        ),
    )
    embedding_model: str | None = Field(
        default=None,
        description=(
            "Specific embedding model identifier override (e.g. 'BAAI/bge-small-en-v1.5')"
        ),
    )

    @model_validator(mode="after")
    def enforce_server_model_policy(self) -> AnalysisCreate:
        """Reject free-form provider/model IDs before they reach model loaders.

        Operator-managed environment overrides are trusted, but API callers may
        only select models exposed by this deployment. This prevents arbitrary
        Hugging Face downloads and unbudgeted cloud model invocations.
        """
        from app.core.config import get_model_config, get_settings
        from app.core.local_llm import get_discovered_llms

        cfg = get_model_config()
        settings = get_settings()

        provider = (self.llm_provider or cfg.llm_provider).lower()
        provider = {"llamacpp": "llama_cpp", "nim": "nvidia", "google_genai": "gemini"}.get(
            provider, provider
        )
        allowed_providers = {"ollama", "llama_cpp", "gemini", "nvidia"}
        if provider not in allowed_providers:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # Local providers use models discovered from the running server /
        # local cache (see local_llm.get_discovered_llms). A local server can only
        # serve weights already on disk, so discovery never opens an arbitrary
        # auto-download path — but it does let operators select freshly-installed
        # GGUFs that the /models dropdown already lists.
        allowed_llms = {
            "ollama": set(get_discovered_llms("ollama")),
            "llama_cpp": set(get_discovered_llms("llama_cpp")),
            "gemini": {
                "gemini-3.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
            },
            "nvidia": {
                "meta/llama-3.3-70b-instruct",
                "mistralai/mistral-large-2-instruct",
                "nvidia/llama-3.1-nemotron-70b-instruct",
            },
        }
        operator_llm_overrides = {
            "ollama": settings.ollama_model,
            "llama_cpp": settings.llamacpp_model,
            "gemini": settings.gemini_model,
            "nvidia": cfg.llm_model if cfg.llm_provider == "nvidia" else "",
        }
        if operator_llm_overrides.get(provider):
            allowed_llms[provider].add(operator_llm_overrides[provider])
        if provider in ("ollama", "llama_cpp") and not allowed_llms[provider]:
            # New-user path: nothing installed yet. Fail closed with the fix
            # instead of a bare "not enabled" rejection.
            raise ValueError(
                f"No {provider} models discovered on this host. Install one "
                "(e.g. 'ollama pull granite4.2:3b-q4_K_M' + 'ollama serve', or "
                "place a GGUF and run ./scripts/start_local_llm.sh), then refresh."
            )

        requested_llm_model = (
            self.llm_model
            or operator_llm_overrides.get(provider)
            or (cfg.llm_model_for(provider) if provider in ("ollama", "llama_cpp") else None)
        )
        if requested_llm_model and requested_llm_model not in allowed_llms[provider]:
            raise ValueError(f"Model is not enabled for provider '{provider}'")

        embedding_provider = (self.embedding_provider or cfg.embedding_provider).lower()
        if embedding_provider == "local":
            embedding_provider = "huggingface"
        allowed_embedding_providers = {"huggingface"}
        if embedding_provider not in allowed_embedding_providers:
            raise ValueError(
                "Unsupported embedding provider: "
                f"{embedding_provider} (embeddings are local-only; "
                "re-upload documents to re-index with 'huggingface')"
            )

        allowed_embeddings = {
            "huggingface": {
                "BAAI/bge-small-en-v1.5",
                "sentence-transformers/all-MiniLM-L6-v2",
            },
        }
        if cfg.embedding_provider == embedding_provider and cfg.embedding_model:
            allowed_embeddings[embedding_provider].add(cfg.embedding_model)

        requested_embedding_model = self.embedding_model or cfg.embedding_model
        if self.embedding_model and not self.embedding_provider:
            matching_providers = [
                candidate
                for candidate, models in allowed_embeddings.items()
                if requested_embedding_model in models
            ]
            if len(matching_providers) != 1:
                raise ValueError(
                    "Embedding model requires an explicit provider or a supported model ID"
                )
            embedding_provider = matching_providers[0]
        if requested_embedding_model not in allowed_embeddings[embedding_provider]:
            raise ValueError(f"Embedding model is not enabled for provider '{embedding_provider}'")
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
    status: str  # pending, running, completed, failed, abstained
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
