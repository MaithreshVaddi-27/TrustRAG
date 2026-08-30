"""
TRUSTRAG API — core settings.

Reads from environment (via .env) and from config/models.yaml.
Business code must import from this module — never read env vars directly.

Separation of concerns:
  .env          → secrets, deployment-specific values (GEMINI_API_KEY, URIs, etc.)
  models.yaml   → model IDs, thresholds, tuning parameters, retrieval config
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Paths ────────────────────────────────────────────────────────────────────

# apps/api/ root (one level above app/)
_API_ROOT = Path(__file__).resolve().parents[2]
_MODELS_YAML_PATH = _API_ROOT / "config" / "models.yaml"


def _load_models_yaml() -> dict[str, Any]:
    """Load and parse config/models.yaml. Fails loudly on missing/malformed file."""
    if not _MODELS_YAML_PATH.exists():
        raise FileNotFoundError(
            f"models.yaml not found at {_MODELS_YAML_PATH}. "
            "This file must exist — it is the centralized config registry."
        )
    with _MODELS_YAML_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"models.yaml must be a YAML mapping. Got: {type(data)}")
    return data


# ─── Settings ─────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """
    Application settings.

    Values come from environment variables (or .env file).
    Model/AI configuration is read from models.yaml via model_config property.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    app_name: str = "TRUSTRAG"
    app_version: str = "0.1.0"

    # ── Security ──────────────────────────────────────────────────────────────
    jwt_secret: str
    jwt_expiry_minutes: int = 60
    cors_origins: str = "http://localhost:5173"

    # ── Hugging Face ──────────────────────────────────────────────────────────
    hf_token: str = ""  # Optional read-only token to prevent download rate-limits

    # ── Google Gemini ──────────────────────────────────────────────────────────
    gemini_api_key: str

    # ── MongoDB Atlas ──────────────────────────────────────────────────────────
    mongodb_uri: str
    mongodb_database: str = "trustrag_db"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""  # Empty string = no auth (local dev)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_analyses_per_minute: int = 10
    rate_limit_auth_per_minute: int = 20

    # ── Model Configuration Overrides (env takes precedence over models.yaml) ──
    gemini_model: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_MODEL", "LLM_MODEL"),
        description="Override primary LLM model ID in .env",
    )
    gemini_verification_model: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_VERIFICATION_MODEL", "VERIFICATION_MODEL"),
        description="Override verification LLM model ID in .env",
    )
    gemini_embedding_model: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_EMBEDDING_MODEL", "EMBEDDING_MODEL"),
        description="Override embedding model ID in .env",
    )
    embedding_dim: int | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_DIM", "EMBEDDING_DIMENSIONALITY"),
        description="Override embedding dimensionality in .env",
    )

    # ── Derived: parsed CORS list ─────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Validation ────────────────────────────────────────────────────────────
    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters. "
                'Generate with: python -c "import secrets; print(secrets.token_hex(64))"'
            )
        return v

    @field_validator("app_env")
    @classmethod
    def valid_app_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}, got '{v}'")
        return v

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v_upper

    @model_validator(mode="after")
    def production_must_have_qdrant_key(self) -> Settings:
        if self.app_env == "production" and not self.qdrant_api_key:
            raise ValueError("QDRANT_API_KEY must be set in production")
        return self

    def is_production(self) -> bool:
        return self.app_env == "production"

    def is_development(self) -> bool:
        return self.app_env == "development"


# ─── Model config (from models.yaml) ─────────────────────────────────────────


class ModelConfig:
    """
    Typed access to models.yaml sections.

    This is the ONLY place application code reads model IDs, thresholds,
    retrieval parameters, and reliability policy. Never read models.yaml
    directly in routes, services, or LangGraph nodes.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def _get(self, *keys: str, required: bool = True) -> Any:
        node: Any = self._data
        path = ".".join(keys)
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                if required:
                    raise KeyError(f"Required key '{path}' missing from models.yaml")
                return None
            node = node[key]
        return node

    # ── Config version ────────────────────────────────────────────────────────
    @property
    def config_version(self) -> str:
        return str(self._get("runtime", "config_version"))

    # ── LLM ──────────────────────────────────────────────────────────────────
    @property
    def llm_model(self) -> str:
        val = self._get("llm", "model")
        settings = get_settings()
        return settings.gemini_model or val

    @property
    def llm_temperature(self) -> float:
        return float(self._get("llm", "temperature"))

    @property
    def llm_top_p(self) -> float:
        return float(self._get("llm", "top_p"))

    @property
    def llm_max_output_tokens(self) -> int:
        return int(self._get("llm", "max_output_tokens"))

    @property
    def llm_timeout_seconds(self) -> int:
        return int(self._get("llm", "timeout_seconds"))

    @property
    def llm_max_retries(self) -> int:
        return int(self._get("llm", "max_retries"))

    # ── Embedding ─────────────────────────────────────────────────────────────
    @property
    def embedding_provider(self) -> str:
        return str(self._get("embedding", "provider", required=False) or "google_genai")

    @property
    def embedding_model(self) -> str:
        val = self._get("embedding", "model")
        settings = get_settings()
        return settings.gemini_embedding_model or val

    @property
    def embedding_dimensionality(self) -> int:
        val = int(self._get("embedding", "output_dimensionality"))
        settings = get_settings()
        return settings.embedding_dim if settings.embedding_dim is not None else val

    @property
    def embedding_version(self) -> str:
        return str(self._get("embedding", "version"))

    @property
    def embedding_cache_dir(self) -> str:
        return str(self._get("embedding", "cache_dir", required=False) or ".model_cache")

    # ── Verification ──────────────────────────────────────────────────────────
    @property
    def verification_model(self) -> str:
        val = self._get("verification", "model")
        settings = get_settings()
        return settings.gemini_verification_model or val

    @property
    def verification_temperature(self) -> float:
        return float(self._get("verification", "temperature"))

    @property
    def verification_max_output_tokens(self) -> int:
        return int(self._get("verification", "max_output_tokens"))

    @property
    def verification_timeout_seconds(self) -> int:
        return int(self._get("verification", "timeout_seconds"))

    # ── Reranker ─────────────────────────────────────────────────────────────
    @property
    def reranker_enabled(self) -> bool:
        return bool(self._get("reranker", "enabled"))

    @property
    def reranker_model(self) -> str:
        return self._get("reranker", "model")

    @property
    def reranker_top_k(self) -> int:
        return int(self._get("reranker", "top_k"))

    # ── Retrieval ─────────────────────────────────────────────────────────────
    @property
    def dense_top_k(self) -> int:
        return int(self._get("retrieval", "dense_top_k"))

    @property
    def sparse_top_k(self) -> int:
        return int(self._get("retrieval", "sparse_top_k"))

    @property
    def fusion_method(self) -> str:
        return self._get("retrieval", "fusion_method")

    @property
    def rrf_k(self) -> int:
        return int(self._get("retrieval", "rrf_k"))

    @property
    def fusion_top_k(self) -> int:
        return int(self._get("retrieval", "fusion_top_k"))

    @property
    def max_context_chunks(self) -> int:
        return int(self._get("retrieval", "max_context_chunks"))

    # ── Ingestion ─────────────────────────────────────────────────────────────
    @property
    def chunk_size(self) -> int:
        return int(self._get("ingestion", "chunk_size"))

    @property
    def chunk_overlap(self) -> int:
        return int(self._get("ingestion", "chunk_overlap"))

    @property
    def supported_formats(self) -> list[str]:
        return list(self._get("ingestion", "supported_formats"))

    @property
    def max_file_size_mb(self) -> int:
        return int(self._get("ingestion", "max_file_size_mb"))

    # ── Reliability ──────────────────────────────────────────────────────────
    @property
    def minimum_evidence_coverage(self) -> float:
        return float(self._get("reliability", "minimum_evidence_coverage"))

    @property
    def maximum_contradiction_rate(self) -> float:
        return float(self._get("reliability", "maximum_contradiction_rate"))

    @property
    def abstain_below(self) -> float:
        return float(self._get("reliability", "abstain_below"))

    # ── Recovery ─────────────────────────────────────────────────────────────
    @property
    def max_recovery_attempts(self) -> int:
        return int(self._get("recovery", "max_recovery_attempts"))

    @property
    def max_query_rewrites(self) -> int:
        return int(self._get("recovery", "max_query_rewrites"))

    # ── Cost controls ─────────────────────────────────────────────────────────
    @property
    def max_input_tokens(self) -> int:
        return int(self._get("cost_controls", "max_input_tokens"))

    @property
    def max_verification_claims(self) -> int:
        return int(self._get("cost_controls", "max_verification_claims"))

    def as_snapshot(self) -> dict[str, Any]:
        """Return a flat dict for recording with each analysis run."""
        return {
            "config_version": self.config_version,
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "embedding_version": self.embedding_version,
            "embedding_dimensionality": self.embedding_dimensionality,
            "verification_model": self.verification_model,
            "reranker_enabled": self.reranker_enabled,
            "reranker_model": self.reranker_model if self.reranker_enabled else None,
            "fusion_method": self.fusion_method,
            "max_context_chunks": self.max_context_chunks,
            "abstain_below": self.abstain_below,
            "max_recovery_attempts": self.max_recovery_attempts,
        }


# ─── Singletons ───────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application Settings singleton."""
    return Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_model_config() -> ModelConfig:
    """Return the cached ModelConfig singleton loaded from models.yaml."""
    raw = _load_models_yaml()
    return ModelConfig(raw)


def reload_settings() -> Settings:
    """Clear cached settings singleton and re-read environment variables."""
    get_settings.cache_clear()
    return get_settings()
