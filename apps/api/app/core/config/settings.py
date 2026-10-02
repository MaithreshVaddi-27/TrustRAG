"""
TRUSTRAG API — core settings.

Reads from environment (via .env) and from config/models.yaml.
Business code must import from this module — never read env vars directly.

Separation of concerns:
  .env          → secrets, deployment-specific values (GEMINI_API_KEY, URIs, etc.)
  models.yaml   → model IDs, thresholds, tuning parameters, retrieval config
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog
import yaml
from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)
# ─── Paths ────────────────────────────────────────────────────────────────

# apps/api/ root (three levels above this file: config/ -> core/ -> app/)
_API_ROOT = Path(__file__).resolve().parents[3]
_MODELS_YAML_PATH = _API_ROOT / "config" / "models.yaml"
# Repo root config/ports.yaml — canonical port registry (see scripts/apply_ports.py)
_PORTS_YAML_PATH = _API_ROOT.parent.parent / "config" / "ports.yaml"

# P0-CFG FIX (2026-09-06 audit): ModelConfig reads os.environ directly while
# Settings loads .env via pydantic-settings (which does NOT export to
# os.environ). Without this, .env values like AI_PROVIDER
# were silently ignored and models.yaml defaults won. Loading .env into
# os.environ here keeps both paths consistent.
load_dotenv(_API_ROOT / ".env", override=False)
load_dotenv(_API_ROOT.parent.parent / ".env", override=False)


def _load_ports_yaml() -> dict[str, int]:
    """Load repo-root config/ports.yaml. Returns {} if absent (dev fallback)."""
    try:
        if not _PORTS_YAML_PATH.exists():
            return {}
        with _PORTS_YAML_PATH.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        ports = (data or {}).get("ports", {}) if isinstance(data, dict) else {}
        return {k: int(v) for k, v in ports.items() if isinstance(v, int)}
    except Exception:
        logger.debug("Failed to load ports.yaml, using empty config")
        return {}


def _blank_as_none(name: str) -> str | None:
    """Return env var value, treating missing/blank as None.

    Docker/`.env` files often carry empty entries (e.g. `LOCAL_LLM_NUM_CTX=`),
    which must fall back to the yaml default instead of crashing
    `int("")`/`float("")`.
    """
    val = os.environ.get(name)
    if val is None or not val.strip():
        return None
    return val


def _parse_bool(value: Any, default: bool = False) -> bool:
    """Coerce a yaml/env flag to bool (single place for truthy-string parsing).

    Accepts real bools, None (→ default), and the common truthy strings
    1/true/yes/on (case-insensitive, whitespace-tolerant).
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# Local LLM base URLs derived once from the canonical port registry so a fresh
# checkout works with zero provider config — explicit env vars still win
# (pydantic env > Field default), and models.yaml stays the ID source.
_PORTS_FALLBACK = _load_ports_yaml()
_DEFAULT_OLLAMA_BASE_URL = f"http://localhost:{_PORTS_FALLBACK.get('ollama', 11434)}"
_DEFAULT_LLAMACPP_BASE_URL = f"http://127.0.0.1:{_PORTS_FALLBACK.get('llamacpp', 8080)}/v1"
_DEFAULT_MLX_BASE_URL = f"http://127.0.0.1:{_PORTS_FALLBACK.get('mlx', 8090)}/v1"


class Settings(BaseSettings):
    """
    Application settings.

    Values come from environment variables (or .env file).
    Model/AI configuration is read from models.yaml via model_config property.
    """

    # pydantic-settings applies env files in order with LATER files winning,
    # so list least-precedence first. Anchored entries last guarantee Settings
    # reads the same files as the module-level load_dotenv() calls
    # (repo-root .env, then apps/api/.env wins) no matter which directory
    # uvicorn/pytest starts from. CWD-relative entries stay as fallback for
    # exotic layouts. Missing files are skipped.
    model_config = SettingsConfigDict(
        env_file=(
            "../../.env",
            "../.env",
            ".env",
            str(_API_ROOT.parent.parent / ".env"),
            str(_API_ROOT / ".env"),
        ),
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
    jwt_issuer: str = "trustrag-api"
    jwt_audience: str = "trustrag-client"
    cors_origins: str = "http://localhost:5173"
    login_max_attempts: int = 5
    login_lockout_seconds: int = 900  # 15 min

    # ── Hugging Face ──────────────────────────────────────────────────────────
    hf_token: str = ""  # Optional read-only token to prevent download rate-limits
    hf_tokenizer_revision: str = Field(
        default="5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        validation_alias=AliasChoices("HF_TOKENIZER_REVISION"),
        description=(
            "Pinned tokenizer revision for ONNX embeddings (Bandit B615 supply-chain "
            "pin). Only change alongside a fresh `scripts/export_bge_onnx.py` run."
        ),
    )

    # ── Google Gemini (Optional if using local LLMs) ───────────────────────────
    gemini_api_key: str = ""

    # ── Local LLM Providers (Ollama & llama.cpp) ──────────────────────────────
    # Defaults derive from config/ports.yaml (see _DEFAULT_*_BASE_URL above);
    # set OLLAMA_BASE_URL / LLAMACPP_BASE_URL env vars to override per deploy
    # (e.g. host.docker.internal inside containers).
    ollama_base_url: str = Field(
        default=_DEFAULT_OLLAMA_BASE_URL,
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "OLLAMA_HOST"),
        description="Ollama local API server endpoint",
    )
    ollama_model: str = Field(
        default="",
        validation_alias=AliasChoices("OLLAMA_MODEL"),
        description="Override Ollama model name from models.yaml via env",
    )
    llamacpp_base_url: str = Field(
        default=_DEFAULT_LLAMACPP_BASE_URL,
        validation_alias=AliasChoices("LLAMACPP_BASE_URL", "LLAMA_CPP_BASE_URL"),
        description="llama.cpp server OpenAI-compatible base URL",
    )
    llamacpp_model: str = Field(
        default="",
        validation_alias=AliasChoices("LLAMACPP_MODEL", "LLAMA_CPP_MODEL"),
        description="Override llama.cpp model identifier from models.yaml via env",
    )
    mlx_base_url: str = Field(
        default=_DEFAULT_MLX_BASE_URL,
        validation_alias=AliasChoices("MLX_BASE_URL"),
        description="MLX server OpenAI-compatible base URL (Apple Silicon only)",
    )
    mlx_model: str = Field(
        default="",
        validation_alias=AliasChoices("MLX_MODEL"),
        description="Override MLX model identifier from models.yaml via env",
    )

    # ── Tavily Search ───────────────────────────────
    tavily_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TAVILY_API_KEY"),
        description="Tavily AI Search API key",
    )

    search_provider: str = Field(
        default="auto",
        validation_alias=AliasChoices("SEARCH_PROVIDER"),
        description="Web search engine: 'tavily'",
    )

    # ── MongoDB Atlas ──────────────────────────────────────────────────────────
    mongodb_uri: str
    mongodb_database: str = "trustrag_db"

    # ── Qdrant ─────────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""  # Empty string = no auth (local dev)

    # ── Model Configuration Overrides (env takes precedence over models.yaml) ──
    gemini_model: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_MODEL", "LLM_MODEL"),
        description="Override primary LLM model ID in .env",
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
        if self.app_env == "production":
            if not self.qdrant_api_key:
                raise ValueError("QDRANT_API_KEY must be set in production")
            # The .env.example placeholder is 44 chars, so it clears the
            # length check above — without this it would silently become the
            # production signing key for anyone who copies the template.
            if self.jwt_secret.upper().startswith(("REPLACE_WITH", "CHANGE_ME", "CHANGEME")):
                raise ValueError(
                    "JWT_SECRET is still the .env.example placeholder. "
                    'Generate a real one: python -c "import secrets; print(secrets.token_hex(64))"'
                )
        return self

    def is_production(self) -> bool:
        return self.app_env == "production"

    def is_development(self) -> bool:
        return self.app_env == "development"


def get_settings() -> Settings:
    """Build application Settings from environment (fresh read, no cache).

    No singleton: every call re-reads the environment so operator changes
    (rotated keys, new overrides) take effect without restarts or explicit
    cache invalidation. Construction is microseconds — caching bought nothing
    but stale-state bugs.
    """
    return Settings()  # type: ignore[call-arg]


def get_ports() -> dict[str, int]:
    """Return the canonical port registry from repo-root config/ports.yaml."""
    return _load_ports_yaml()
