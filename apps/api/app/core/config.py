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
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Paths ────────────────────────────────────────────────────────────────

# apps/api/ root (one level above app/)
_API_ROOT = Path(__file__).resolve().parents[2]
_MODELS_YAML_PATH = _API_ROOT / "config" / "models.yaml"
# Repo root config/ports.yaml — canonical port registry (see scripts/apply_ports.py)
_PORTS_YAML_PATH = _API_ROOT.parent.parent / "config" / "ports.yaml"

# P0-CFG FIX (2026-09-06 audit): ModelConfig reads os.environ directly while
# Settings loads .env via pydantic-settings (which does NOT export to
# os.environ). Without this, .env values like EMBEDDING_PROVIDER/AI_PROVIDER
# were silently ignored and models.yaml defaults won (e.g. Settings said
# huggingface while ModelConfig reported google_genai). Loading .env into
# os.environ here keeps both paths consistent.
load_dotenv(_API_ROOT / ".env", override=False)
load_dotenv(_API_ROOT.parent.parent / ".env", override=False)


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


# ─── Settings ─────────────────────────────────────────────────────────────


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
    jwt_issuer: str = "trustrag-api"
    jwt_audience: str = "trustrag-client"
    cors_origins: str = "http://localhost:5173"
    trusted_proxy_ips: str = ""  # Comma-separated proxy IPs/CIDRs allowed to supply X-Forwarded-For
    login_max_attempts: int = 5
    login_lockout_seconds: int = 900  # 15 min

    # ── Hugging Face ──────────────────────────────────────────────────────────
    hf_token: str = ""  # Optional read-only token to prevent download rate-limits

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
        default="http://127.0.0.1:8090/v1",
        validation_alias=AliasChoices("MLX_BASE_URL"),
        description="MLX server OpenAI-compatible base URL (Apple Silicon only)",
    )
    mlx_model: str = Field(
        default="",
        validation_alias=AliasChoices("MLX_MODEL"),
        description="Override MLX model identifier from models.yaml via env",
    )

    # ── NVIDIA NIM & Tavily Search ─────────────────────────────────────────────
    nvidia_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("NVIDIA_API_KEY", "NIM_API_KEY"),
        description="NVIDIA NIM API key for Llama, Mistral, and Nemotron models",
    )
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias=AliasChoices("NVIDIA_BASE_URL"),
        description="NVIDIA NIM API base URL",
    )
    tavily_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TAVILY_API_KEY"),
        description="Tavily AI Search API key",
    )

    # ── Multi-Provider Engine Selectors ────────────────────────────────────────
    ai_provider: str = Field(
        default="ollama",
        validation_alias=AliasChoices("AI_PROVIDER", "LLM_PROVIDER"),
        description=(
            "Active AI generation & verification provider: 'ollama', "
            "'llama_cpp', 'mlx' (Apple Silicon), 'gemini', or 'nvidia'"
        ),
    )
    embedding_provider: str = Field(
        default="huggingface",
        validation_alias=AliasChoices("EMBEDDING_PROVIDER", "EMBEDDING_BACKEND"),
        description="Active embedding engine: 'huggingface' (local-only)",
    )
    search_provider: str = Field(
        default="auto",
        validation_alias=AliasChoices("SEARCH_PROVIDER"),
        description="Web search engine: 'auto', 'tavily', 'duckduckgo', or 'both'",
    )

    # ── MongoDB Atlas ──────────────────────────────────────────────────────────
    mongodb_uri: str
    mongodb_database: str = "trustrag_db"

    # ── Qdrant ─────────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""  # Empty string = no auth (local dev)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_analyses_per_minute: int = 10
    rate_limit_auth_per_minute: int = 20
    rate_limit_upload_per_minute: int = 10
    rate_limit_url_ingest_per_minute: int = 10

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
        validation_alias=AliasChoices("EMBEDDING_MODEL", "LOCAL_EMBEDDING_MODEL"),
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

    @property
    def trusted_proxy_list(self) -> list[str]:
        return [p.strip() for p in self.trusted_proxy_ips.split(",") if p.strip()]

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


# ─── Model config (from models.yaml) ──────────────────────────────────────


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

    # ── Config version ─────────────────────────────────────────────────────
    @property
    def config_version(self) -> str:
        return str(self._get("runtime", "config_version"))

    # ── LLM ─────────────────────────────────────────────────────────────────
    @property
    def llm_provider(self) -> str:
        val = self._get("llm", "provider", required=False)
        env_val = os.environ.get("AI_PROVIDER") or os.environ.get("LLM_PROVIDER")
        if env_val:
            return env_val.lower()
        return str(val or "ollama").lower()

    @property
    def llm_model(self) -> str:
        return self.llm_model_for(self.llm_provider)

    def llm_model_for(self, provider: str) -> str:
        """Resolve the model id for an explicit provider (not the configured one)."""
        self._get("llm")
        p = provider.lower()
        if p == "ollama":
            env_model = os.environ.get("OLLAMA_MODEL")
            return (
                env_model
                or str(self._get("llm", "model_ollama", required=False) or "")
                or str(self._get("llm", "model") or "granite4.2:3b-q4_K_M")
            )
        if p in ("llama_cpp", "llamacpp"):
            env_model = os.environ.get("LLAMACPP_MODEL") or os.environ.get("LLAMA_CPP_MODEL")
            return (
                env_model
                or str(self._get("llm", "model_llamacpp", required=False) or "")
                or str(self._get("llm", "model") or "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M")
            )
        if p == "mlx":
            env_model = os.environ.get("MLX_MODEL")
            return (
                env_model
                or str(self._get("llm", "model_mlx", required=False) or "")
                # Never fall back to llm.model here: it may be a GGUF id the
                # MLX server cannot serve (exact-match routing → 404).
                or "mlx-community/Llama-3.2-1B-Instruct-4bit"
            )
        env_model = os.environ.get("LLM_MODEL") or os.environ.get("GEMINI_MODEL")
        if env_model:
            return env_model
        if p in ("nvidia", "nim"):
            # Never fall back to llm.model here: it is a local GGUF id the
            # cloud endpoint cannot serve (same rule as the mlx branch).
            return str(self._get("llm", "model_nvidia", required=False) or "openai/gpt-oss-20b")
        if p in ("gemini", "google_genai"):
            # Never fall back to llm.model here: it is a local GGUF id, not a
            # Gemini model id. Override via LLM_MODEL env or model_gemini yaml.
            return str(self._get("llm", "model_gemini", required=False) or "gemini-3.5-flash-lite")
        return str(self._get("llm", "model") or "gemini-3.5-flash-lite")

    @property
    def ollama_base_url(self) -> str:
        env_url = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST")
        if env_url:
            return env_url
        port = get_ports().get("ollama")
        if port:
            return f"http://localhost:{port}"
        return str(self._get("llm", "ollama_base_url", required=False) or "http://localhost:11434")

    @property
    def llamacpp_base_url(self) -> str:
        env_url = os.environ.get("LLAMACPP_BASE_URL") or os.environ.get("LLAMA_CPP_BASE_URL")
        if env_url:
            return env_url
        port = get_ports().get("llamacpp")
        if port:
            return f"http://127.0.0.1:{port}/v1"
        return str(
            self._get("llm", "llamacpp_base_url", required=False) or "http://127.0.0.1:8080/v1"
        )

    @property
    def mlx_base_url(self) -> str:
        env_url = os.environ.get("MLX_BASE_URL")
        if env_url:
            return env_url
        # Separate port (:8090) so llama-server (:8080) and mlx_lm.server (:8090)
        # can run side-by-side. pydantic env > Field default > _DEFAULT_MLX_BASE_URL.
        return str(self._get("llm", "mlx_base_url", required=False) or _DEFAULT_MLX_BASE_URL)

    @property
    def llm_temperature(self) -> float:
        """Default temperature for generation."""
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

    # ── Embedding ─────────────────────────────────────────────────────────
    @property
    def embedding_provider(self) -> str:
        val = self._get("embedding", "provider", required=False)
        env_val = os.environ.get("EMBEDDING_PROVIDER") or os.environ.get("EMBEDDING_BACKEND")
        if env_val:
            return env_val.lower()
        return str(val or "huggingface").lower()

    @property
    def embedding_model(self) -> str:
        val = self._get("embedding", "model")
        env_model = os.environ.get("EMBEDDING_MODEL") or os.environ.get("LOCAL_EMBEDDING_MODEL")
        if env_model:
            return env_model
        return str(val or "BAAI/bge-small-en-v1.5")

    @property
    def embedding_dimensionality(self) -> int:
        val = int(self._get("embedding", "output_dimensionality"))
        env_dim = _blank_as_none("EMBEDDING_DIM") or _blank_as_none("EMBEDDING_DIMENSIONALITY")
        return int(env_dim) if env_dim is not None else val

    @property
    def embedding_version(self) -> str:
        return str(self._get("embedding", "version"))

    @property
    def embedding_cache_dir(self) -> str:
        # MODEL_CACHE_DIR wins so the backend reads the same directory that
        # scripts/bootstrap.py writes (see ensure_onnx_models._cache_dir).
        # NOTE: CACHE_DIR is intentionally NOT honored here — at runtime it
        # means the SQLite disk cache (disk_cache.py), not model weights.
        env_dir = os.environ.get("MODEL_CACHE_DIR")
        if env_dir and env_dir.strip():
            return env_dir
        return str(self._get("embedding", "cache_dir", required=False) or ".model_cache")

    @property
    def embedding_max_seq_length(self) -> int:
        val = self._get("embedding", "max_seq_length", required=False)
        if val is not None:
            return int(val)
        return 512  # Default for BGE-small

    # ── Embedding Quantization (Phase 4.2) ──────────────────────────────────────
    @property
    def embedding_quantization(self) -> bool:
        """Enable int8 quantization for embedding model (~500-1000MB RAM savings)."""
        value = self._get("embedding", "quantization", required=False)
        env_val = os.environ.get("EMBEDDING_QUANTIZATION")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, False)  # Default disabled, opt-in

    # ── Verification ──────────────────────────────────────────────────────
    @property
    def verification_provider(self) -> str:
        val = self._get("verification", "provider", required=False)
        env_val = os.environ.get("AI_PROVIDER") or os.environ.get("LLM_PROVIDER")
        if env_val:
            return env_val.lower()
        return str(val or "ollama").lower()

    @property
    def verification_model(self) -> str:
        return self.verification_model_for(self.verification_provider)

    def verification_model_for(self, provider: str) -> str:
        """Resolve the verifier model id for an explicit provider."""
        p = provider.lower()
        if p == "ollama":
            env_model = os.environ.get("OLLAMA_MODEL")
            return (
                env_model
                or str(self._get("verification", "model_ollama", required=False) or "")
                or str(self._get("verification", "model") or "granite4.2:3b-q4_K_M")
            )
        if p in ("llama_cpp", "llamacpp"):
            env_model = os.environ.get("LLAMACPP_MODEL") or os.environ.get("LLAMA_CPP_MODEL")
            return (
                env_model
                or str(self._get("verification", "model_llamacpp", required=False) or "")
                or str(
                    self._get("verification", "model") or "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M"
                )
            )
        if p == "mlx":
            env_model = os.environ.get("MLX_MODEL")
            return (
                env_model
                or str(self._get("verification", "model_mlx", required=False) or "")
                # Same no-GGUF-fallback rule as llm_model_for (exact-match routing).
                or "mlx-community/Llama-3.2-1B-Instruct-4bit"
            )
        val = self._get("verification", "model")
        env_model = os.environ.get("GEMINI_VERIFICATION_MODEL") or os.environ.get(
            "VERIFICATION_MODEL"
        )
        if env_model:
            return env_model
        if p in ("nvidia", "nim"):
            # Never fall back to verification.model / llm.model (local GGUF ids).
            return str(
                self._get("verification", "model_nvidia", required=False)
                or self._get("llm", "model_nvidia", required=False)
                or "openai/gpt-oss-20b"
            )
        if p in ("gemini", "google_genai"):
            # Never fall back to verification.model / llm.model (local GGUF ids).
            return str(
                self._get("verification", "model_gemini", required=False)
                or self._get("llm", "model_gemini", required=False)
                or "gemini-3.5-flash-lite"
            )
        return str(val or "gemini-3.5-flash-lite")

    @property
    def supported_gemini_models(self) -> list[str]:
        """Cloud allowlist: models API callers may select for gemini."""
        val = self._get("llm", "supported_models_gemini", required=False)
        if isinstance(val, list) and val:
            return [str(m) for m in val]
        # Fallback mirrors the last hardcoded set (pre-1.20 configs).
        return ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]

    @property
    def supported_nvidia_models(self) -> list[str]:
        """Cloud allowlist: models API callers may select for nvidia."""
        val = self._get("llm", "supported_models_nvidia", required=False)
        if isinstance(val, list) and val:
            return [str(m) for m in val]
        return ["openai/gpt-oss-20b", "google/gemma-4-31b-it", "meta/muse-glimmer-30b"]

    @property
    def verification_temperature(self) -> float:
        return float(self._get("verification", "temperature"))

    @property
    def verification_max_output_tokens(self) -> int:
        return int(self._get("verification", "max_output_tokens"))

    @property
    def verification_timeout_seconds(self) -> int:
        return int(self._get("verification", "timeout_seconds"))

    @property
    def fused_decompose_verify(self) -> bool:
        val = self._get("verification", "fused_decompose_verify", required=False)
        env_val = os.environ.get("FUSED_DECOMPOSE_VERIFY")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(val, True)

    @property
    def max_verification_time_seconds(self) -> int:
        return int(self._get("verification", "max_verification_time_seconds"))

    @property
    def verification_max_retries(self) -> int:
        """Retry budget for verification LLM calls (models.yaml: verification.max_retries)."""
        val = self._get("verification", "max_retries", required=False)
        env_val = os.environ.get("VERIFICATION_MAX_RETRIES")
        if env_val is not None:
            return int(env_val)
        if val is None:
            return int(self._get("llm", "max_retries"))
        return int(val)

    # ── Reranker ─────────────────────────────────────────────────────────
    @property
    def reranker_enabled(self) -> bool:
        return bool(self._get("reranker", "enabled"))

    @property
    def reranker_model(self) -> str:
        return self._get("reranker", "model")

    @property
    def reranker_top_k(self) -> int:
        return int(self._get("reranker", "top_k"))

    @property
    def reranker_batch_size(self) -> int:
        return int(self._get("reranker", "batch_size"))

    @property
    def reranker_early_termination_confidence(self) -> float:
        return float(self._get("reranker", "early_termination_confidence"))

    @property
    def reranker_score_gap_threshold(self) -> float:
        return float(self._get("reranker", "score_gap_threshold"))

    @property
    def reranker_use_onnx(self) -> bool:
        val = self._get("reranker", "use_onnx", required=False)
        env_val = os.environ.get("RERANKER_USE_ONNX")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(val, True)  # Default to ONNX for speed

    @property
    def reranker_onnx_model_path(self) -> str:
        val = self._get("reranker", "onnx_model_path", required=False)
        env_val = os.environ.get("RERANKER_ONNX_MODEL_PATH")
        if env_val is not None:
            return env_val
        return str(val or "")

    @property
    def reranker_cache_size(self) -> int:
        """Maximum number of query-document pairs to cache for reranker."""
        value = self._get("reranker", "cache_size", required=False)
        env_val = _blank_as_none("RERANKER_CACHE_SIZE")
        return int(env_val) if env_val is not None else int(value or 500)

    # ── Retrieval ─────────────────────────────────────────────────────────
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
    def sparse_k1(self) -> float:
        return float(self._get("retrieval", "sparse_k1", required=False) or 1.2)

    @property
    def sparse_b(self) -> float:
        return float(self._get("retrieval", "sparse_b", required=False) or 0.75)

    @property
    def sparse_avg_len_tokens(self) -> int:
        return int(self._get("retrieval", "sparse_avg_len_tokens", required=False) or 128)

    @property
    def max_context_chunks(self) -> int:
        return int(self._get("retrieval", "max_context_chunks"))

    @property
    def router_enabled(self) -> bool:
        return bool(self._get("retrieval", "query_router", "enabled", required=False) is not False)

    @property
    def max_fanout_sub_queries(self) -> int:
        value = self._get("retrieval", "query_router", "max_sub_queries", required=False)
        return int(value) if value is not None else 3

    # ── Ingestion ─────────────────────────────────────────────────────────
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

    @property
    def chunking_strategy(self) -> str:
        """Chunking strategy name (models.yaml: ingestion.chunking_strategy)."""
        return str(self._get("ingestion", "chunking_strategy", required=False) or "sliding_window")

    # ── OCR fallback ─────────────────────────────────────────────────────
    @property
    def ocr_enabled(self) -> bool:
        return bool(self._get("ingestion", "ocr", "enabled", required=False) is not False)

    @property
    def ocr_min_native_chars(self) -> int:
        return int(self._get("ingestion", "ocr", "min_native_chars", required=False) or 50)

    @property
    def ocr_dpi(self) -> int:
        return int(self._get("ingestion", "ocr", "dpi", required=False) or 300)

    @property
    def ocr_min_confidence(self) -> float:
        return float(self._get("ingestion", "ocr", "min_confidence", required=False) or 0.5)

    @property
    def ocr_store_page_images(self) -> bool:
        return bool(self._get("ingestion", "ocr", "store_page_images", required=False) is not False)

    # ── Reliability ──────────────────────────────────────────────────────
    @property
    def minimum_evidence_coverage(self) -> float:
        return float(self._get("reliability", "minimum_evidence_coverage"))

    @property
    def maximum_contradiction_rate(self) -> float:
        return float(self._get("reliability", "maximum_contradiction_rate"))

    @property
    def abstain_below(self) -> float:
        return float(self._get("reliability", "abstain_below"))

    # ── Recovery ─────────────────────────────────────────────────────────
    @property
    def max_recovery_attempts(self) -> int:
        return int(self._get("recovery", "max_recovery_attempts"))

    @property
    def recovery_strategy_priority(self) -> list[str]:
        """Return ordered recovery strategies, e.g. ['query_rewrite', 're_retrieve']."""
        val = self._get("recovery", "strategy_priority", required=False)
        if isinstance(val, list) and val:
            return [str(s) for s in val]
        return ["query_rewrite", "re_retrieve"]

    @property
    def max_recovery_tokens(self) -> int:
        return int(self._get("recovery", "max_recovery_tokens", required=False) or 2000)

    @property
    def max_recovery_latency_seconds(self) -> int:
        return int(self._get("recovery", "max_recovery_latency_seconds", required=False) or 180)

    # ── Observability (Phase 10) ─────────────────────────────────────────
    @property
    def pre_request_budget_enforcement(self) -> bool:
        return bool(
            self._get("observability", "pre_request_budget_enforcement", required=False)
            is not False
        )

    # ── Cost controls ─────────────────────────────────────────────────────
    @property
    def max_input_tokens(self) -> int:
        return int(self._get("cost_controls", "max_input_tokens"))

    @property
    def max_verification_claims(self) -> int:
        return int(self._get("cost_controls", "max_verification_claims"))

    @property
    def max_individual_nli_fallback(self) -> int:
        value = self._get("cost_controls", "max_individual_nli_fallback", required=False)
        return int(value) if value is not None else 5

    @property
    def max_claim_retrievals(self) -> int:
        value = self._get("cost_controls", "max_claim_retrievals", required=False)
        return int(value) if value is not None else 3

    @property
    def claim_retrieval_top_k(self) -> int:
        value = self._get("cost_controls", "claim_retrieval_top_k", required=False)
        return int(value) if value is not None else 5

    # ── Local LLM Inference Parameters ────────────────────────────────────────
    @property
    def local_llm_num_ctx(self) -> int:
        value = self._get("local_llm", "num_ctx", required=False)
        env_val = _blank_as_none("LOCAL_LLM_NUM_CTX")
        return int(env_val) if env_val is not None else int(value or 4096)

    @property
    def local_llm_num_batch(self) -> int:
        value = self._get("local_llm", "num_batch", required=False)
        env_val = _blank_as_none("LOCAL_LLM_NUM_BATCH")
        return int(env_val) if env_val is not None else int(value or 512)

    @property
    def local_llm_keep_alive(self) -> str:
        value = self._get("local_llm", "keep_alive", required=False)
        env_val = _blank_as_none("LOCAL_LLM_KEEP_ALIVE")
        return env_val if env_val is not None else str(value or "5m")

    # ── Speculative Decoding / Early Exit (Phase 2.5) ──────────────────────
    @property
    def local_llm_min_p(self) -> float:
        """Min-p sampling: only tokens with p >= min_p * p_max are considered.
        0.0 = disabled, 0.1 = aggressive filtering for speed."""
        value = self._get("local_llm", "min_p", required=False)
        env_val = _blank_as_none("LOCAL_LLM_MIN_P")
        return float(env_val) if env_val is not None else float(value or 0.0)

    @property
    def local_llm_top_k(self) -> int:
        """Top-k sampling: restrict to top K tokens. 0 = disabled (no limit)."""
        value = self._get("local_llm", "top_k", required=False)
        env_val = _blank_as_none("LOCAL_LLM_TOP_K")
        return int(env_val) if env_val is not None else int(value or 0)

    @property
    def local_llm_early_exit_eos(self) -> bool:
        """Early stop on EOS token (n_predict streaming with early termination)."""
        value = self._get("local_llm", "early_exit_eos", required=False)
        env_val = os.environ.get("LOCAL_LLM_EARLY_EXIT_EOS")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)  # Default enabled for speed

    # ── Model Offloading (Phase 4.1) ────────────────────────────────────────────
    @property
    def local_llm_model_unload_enabled(self) -> bool:
        """Enable auto-unloading of inactive models from memory."""
        value = self._get("local_llm", "model_unload_enabled", required=False)
        env_val = os.environ.get("LOCAL_LLM_MODEL_UNLOAD_ENABLED")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)  # Default enabled for low RAM

    @property
    def local_llm_model_unload_timeout(self) -> str:
        """Time before considering a model idle for unloading."""
        value = self._get("local_llm", "model_unload_timeout", required=False)
        env_val = _blank_as_none("LOCAL_LLM_MODEL_UNLOAD_TIMEOUT")
        return env_val if env_val is not None else str(value or "5m")

    # ── Inference Acceleration & KV Cache Optimization ────────────────────────
    @property
    def kv_cache_quantization(self) -> str:
        value = self._get("optimization", "kv_cache_quantization", required=False)
        env_val = os.environ.get("KV_CACHE_QUANTIZATION")
        return env_val if env_val is not None else str(value or "q4_0")

    @property
    def flash_attention(self) -> bool:
        value = self._get("optimization", "flash_attention", required=False)
        env_val = os.environ.get("FLASH_ATTENTION")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)

    @property
    def prompt_caching(self) -> bool:
        value = self._get("optimization", "prompt_caching", required=False)
        env_val = os.environ.get("PROMPT_CACHING")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)

    @property
    def adaptive_top_k(self) -> bool:
        value = self._get("optimization", "adaptive_top_k", required=False)
        env_val = os.environ.get("ADAPTIVE_TOP_K")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)

    # ── Context Compression (Phase 2.4) ─────────────────────────────────────────
    @property
    def context_compression_enabled(self) -> bool:
        value = self._get("optimization", "context_compression_enabled", required=False)
        env_val = os.environ.get("CONTEXT_COMPRESSION_ENABLED")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)  # Default enabled for RAM savings

    @property
    def context_compression_target_reduction(self) -> float:
        """Target compression ratio (e.g., 0.5 = 50% of original size)."""
        value = self._get("optimization", "context_compression_target_reduction", required=False)
        env_val = _blank_as_none("CONTEXT_COMPRESSION_TARGET_REDUCTION")
        if env_val is not None:
            return float(env_val)
        return float(value or 0.5)

    @property
    def context_compression_provider(self) -> str:
        """Which providers should use context compression: 'cloud' (gemini, nvidia),
        'local' (ollama, llama_cpp, mlx), or 'off' (disabled)."""
        value = self._get("optimization", "context_compression_provider", required=False)
        env_val = os.environ.get("CONTEXT_COMPRESSION_PROVIDER")
        return (env_val or value or "cloud").lower()

    def tier_caps(self, provider: str | None = None) -> dict[str, int]:
        """Return cost-control caps for the current provider tier.

        Args:
            provider: Explicit provider to get caps for. If None, uses llm_provider.

        Returns:
            Dict with max_verification_claims, max_context_chunks, max_claim_retrievals
        """
        prov = (provider or self.llm_provider).lower()
        is_cloud = prov in ("gemini", "google_genai", "nvidia", "nim")
        is_mlx = prov == "mlx"

        if is_cloud:
            tier = "cloud_tier"
        elif is_mlx or prov in ("ollama", "llama_cpp", "llamacpp"):
            # Detect lean vs balanced by available RAM (proxy via num_ctx)
            num_ctx = self.local_llm_num_ctx
            tier = "balanced_tier" if num_ctx >= 8192 else "lean_tier"
        else:
            tier = "cloud_tier"  # fallback

        tier_config = self._get("cost_controls", tier, required=False) or {}
        defaults = {
            "max_verification_claims": 8,
            "max_context_chunks": 8,
            "max_claim_retrievals": 3,
        }
        return {k: int(tier_config.get(k, v)) for k, v in defaults.items()}

    def as_snapshot(self) -> dict[str, Any]:
        """Return a flat dict for recording with each analysis run."""
        return {
            "config_version": self.config_version,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_version": self.embedding_version,
            "embedding_dimensionality": self.embedding_dimensionality,
            "verification_provider": self.verification_provider,
            "verification_model": self.verification_model,
            "reranker_enabled": self.reranker_enabled,
            "reranker_model": self.reranker_model if self.reranker_enabled else None,
            "fusion_method": self.fusion_method,
            "fusion_top_k": self.fusion_top_k,
            "max_fanout_sub_queries": self.max_fanout_sub_queries,
            "ocr_enabled": self.ocr_enabled,
            "ocr_store_page_images": self.ocr_store_page_images,
            "sparse_k1": self.sparse_k1,
            "sparse_b": self.sparse_b,
            "sparse_avg_len_tokens": self.sparse_avg_len_tokens,
            "max_context_chunks": self.max_context_chunks,
            "abstain_below": self.abstain_below,
            "max_recovery_attempts": self.max_recovery_attempts,
            "max_claim_retrievals": self.max_claim_retrievals,
        }


# ─── Singletons ───────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application Settings singleton."""
    return Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_model_config() -> ModelConfig:
    """Return the cached ModelConfig singleton loaded from models.yaml."""
    raw = _load_models_yaml()
    return ModelConfig(raw)


@lru_cache(maxsize=1)
def get_ports() -> dict[str, int]:
    """Return the canonical port registry from repo-root config/ports.yaml."""
    return _load_ports_yaml()


def reload_ports() -> dict[str, int]:
    """Clear cached ports and re-read config/ports.yaml."""
    get_ports.cache_clear()
    return get_ports()


def reload_settings() -> Settings:
    """Clear cached settings singleton and re-read environment variables."""
    get_settings.cache_clear()
    return get_settings()
