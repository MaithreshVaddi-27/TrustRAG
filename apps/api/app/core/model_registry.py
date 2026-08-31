"""
TRUSTRAG — Model Registry.

This is the ONLY place in the application that instantiates LangChain
model objects. All other modules receive models through dependency injection
or by calling these factory functions.

Architecture:
  TRUSTRAG → LangChain → langchain-google-genai → Gemini API
  TRUSTRAG → LangChain → langchain-huggingface → sentence-transformers (local)

Changing a model requires updating models.yaml only — no code changes.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import ModelConfig, get_model_config, get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)


# ─── LLM ─────────────────────────────────────────────────────────────────────


# ─── LLM ─────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Return the primary LLM for answer generation.

    Supports:
      - gemini: ChatGoogleGenerativeAI via langchain-google-genai
      - nvidia: ChatNVIDIA via langchain-nvidia-ai-endpoints
    """
    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    logger.info(
        "Initializing LLM",
        provider=cfg.llm_provider,
        model=cfg.llm_model,
        temperature=cfg.llm_temperature,
        max_output_tokens=cfg.llm_max_output_tokens,
    )

    try:
        if cfg.llm_provider in ("nvidia", "nim"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            if not settings.nvidia_api_key:
                raise ConfigurationError("NVIDIA_API_KEY must be set when AI_PROVIDER is 'nvidia'")

            return ChatNVIDIA(
                model=cfg.llm_model,
                api_key=settings.nvidia_api_key,
                temperature=cfg.llm_temperature,
                max_tokens=cfg.llm_max_output_tokens,
                timeout=cfg.llm_timeout_seconds,
            )

        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=cfg.llm_model,
            google_api_key=settings.gemini_api_key,
            temperature=cfg.llm_temperature,
            top_p=cfg.llm_top_p,
            max_output_tokens=cfg.llm_max_output_tokens,
            timeout=cfg.llm_timeout_seconds,
            max_retries=cfg.llm_max_retries,
        )
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize LLM '{cfg.llm_model}' (provider: {cfg.llm_provider})",
            detail=str(exc),
        ) from exc


# ─── Verification LLM ─────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_verification_model() -> BaseChatModel:
    """
    Return the verification LLM for claim-level structured verification.

    Separate from the primary LLM to allow independent cost/quality tuning.
    Temperature is forced to 0.0 for deterministic verification.
    """
    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    logger.info(
        "Initializing verification model",
        provider=cfg.verification_provider,
        model=cfg.verification_model,
        temperature=cfg.verification_temperature,
    )

    try:
        if cfg.verification_provider in ("nvidia", "nim"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            if not settings.nvidia_api_key:
                raise ConfigurationError("NVIDIA_API_KEY must be set when AI_PROVIDER is 'nvidia'")

            return ChatNVIDIA(
                model=cfg.verification_model,
                api_key=settings.nvidia_api_key,
                temperature=0.0,
                max_tokens=cfg.verification_max_output_tokens,
                timeout=cfg.verification_timeout_seconds,
            )

        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=cfg.verification_model,
            google_api_key=settings.gemini_api_key,
            temperature=cfg.verification_temperature,
            max_output_tokens=cfg.verification_max_output_tokens,
            timeout=cfg.verification_timeout_seconds,
            max_retries=cfg.llm_max_retries,
        )
    except Exception as exc:
        msg = (
            f"Failed to initialize verification model '{cfg.verification_model}' "
            f"(provider: {cfg.verification_provider})"
        )
        raise ConfigurationError(msg, detail=str(exc)) from exc


# ─── Embedding Model ──────────────────────────────────────────────────────────


class BGEAwareHuggingFaceEmbeddings:
    """
    Wrapper around HuggingFaceEmbeddings adding BGE query instruction prefixing.
    Implements standard LangChain Embeddings interface.
    """

    def __init__(self, base_embeddings: Any, model_name: str) -> None:
        self._base = base_embeddings
        self._is_bge = "bge" in model_name.lower()

    def embed_query(self, text: str) -> list[float]:
        if self._is_bge and not text.startswith("Represent this sentence"):
            text = f"Represent this sentence for searching relevant passages: {text}"
        return self._base.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._base.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        if self._is_bge and not text.startswith("Represent this sentence"):
            text = f"Represent this sentence for searching relevant passages: {text}"
        return await self._base.aembed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._base.aembed_documents(texts)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


@lru_cache(maxsize=1)
def get_embedding_model() -> Embeddings:
    """
    Return the embedding model.

    Supports:
      - huggingface / local: Local BGE (BAAI/bge-small-en-v1.5, 0 API cost, ~32ms query latency)
      - google_genai / gemini: Cloud-hosted Google Gemini embeddings (ultra-low RAM <60MB)
      - nvidia / nim: Cloud-hosted NVIDIA NIM embeddings
    """
    cfg: ModelConfig = get_model_config()
    settings = get_settings()

    # ── Option 1: NVIDIA NIM Embeddings ─────────────────────────────────────────
    if cfg.embedding_provider in ("nvidia", "nim"):
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        if not settings.nvidia_api_key:
            raise ConfigurationError(
                "NVIDIA_API_KEY must be set when EMBEDDING_PROVIDER is 'nvidia'"
            )

        logger.info(
            "Initializing NVIDIA NIM embedding model",
            model=cfg.embedding_model,
        )
        try:
            return NVIDIAEmbeddings(
                model=cfg.embedding_model,
                api_key=settings.nvidia_api_key,
                truncate="END",
            )
        except Exception as exc:
            raise ConfigurationError(
                f"Failed to initialize NVIDIA embedding model '{cfg.embedding_model}'",
                detail=str(exc),
            ) from exc

    # ── Option 2: Google Gemini Embeddings (Cloud) ──────────────────────────────
    if cfg.embedding_provider in ("google_genai", "gemini"):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        logger.info(
            "Initializing Google Generative AI embedding model",
            model=cfg.embedding_model,
            dimensionality=cfg.embedding_dimensionality,
        )
        try:
            return GoogleGenerativeAIEmbeddings(
                model=cfg.embedding_model,
                google_api_key=settings.gemini_api_key,
                output_dimensionality=cfg.embedding_dimensionality,
            )
        except Exception as exc:
            raise ConfigurationError(
                f"Failed to initialize Google embedding model '{cfg.embedding_model}'",
                detail=str(exc),
            ) from exc

    # ── Option 3: Local Hugging Face Embeddings (Sentence-Transformers / BGE) ────
    from langchain_huggingface import HuggingFaceEmbeddings

    cache_dir = Path(cfg.embedding_cache_dir).resolve()

    logger.info(
        "Initializing local HuggingFace embedding model",
        model=cfg.embedding_model,
        dimensionality=cfg.embedding_dimensionality,
        cache_dir=str(cache_dir),
    )

    if settings.hf_token:
        import os

        os.environ["HF_TOKEN"] = settings.hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token

    try:
        try:
            import torch

            torch.set_num_threads(1)
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("Could not limit torch thread count", error=str(exc))

        model_kwargs: dict[str, Any] = {"device": "cpu"}
        if settings.hf_token:
            model_kwargs["token"] = settings.hf_token

        # Fast-path: if model is already pre-cached, load purely offline (0 network delay)
        if cache_dir.exists() and any(cache_dir.iterdir()):
            try:
                offline_kwargs = {**model_kwargs, "local_files_only": True}
                base_emb = HuggingFaceEmbeddings(
                    model_name=cfg.embedding_model,
                    cache_folder=str(cache_dir),
                    encode_kwargs={"normalize_embeddings": True},
                    model_kwargs=offline_kwargs,
                )
                return BGEAwareHuggingFaceEmbeddings(base_emb, cfg.embedding_model)  # type: ignore[return-value]
            except Exception as offline_err:
                logger.debug(
                    "Offline cache fast-path skipped, downloading model", error=str(offline_err)
                )

        base_emb = HuggingFaceEmbeddings(
            model_name=cfg.embedding_model,
            cache_folder=str(cache_dir),
            encode_kwargs={"normalize_embeddings": True},
            model_kwargs=model_kwargs,
        )
        return BGEAwareHuggingFaceEmbeddings(base_emb, cfg.embedding_model)  # type: ignore[return-value]
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize embedding model '{cfg.embedding_model}'",
            detail=str(exc),
        ) from exc


# ─── Reranker ─────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_reranker():  # type: ignore[return]
    """
    Return the reranker model (cross-encoder via sentence-transformers).

    Returns None if reranking is disabled in models.yaml.
    Callers MUST check for None before use.
    """
    cfg: ModelConfig = get_model_config()

    if not cfg.reranker_enabled:
        logger.info("Reranker disabled in models.yaml")
        return None

    settings = get_settings()
    if settings.hf_token:
        import os

        os.environ["HF_TOKEN"] = settings.hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token

    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        logger.warning(
            "sentence-transformers not installed. Reranker disabled. Using Hybrid RRF."
        )
        return None

    logger.info("Initializing reranker", model=cfg.reranker_model)

    try:
        if settings.hf_token:
            return CrossEncoder(cfg.reranker_model, token=settings.hf_token)
        return CrossEncoder(cfg.reranker_model)
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize reranker '{cfg.reranker_model}'",
            detail=str(exc),
        ) from exc


# ─── Registry info ────────────────────────────────────────────────────────────


def registry_status() -> dict[str, Any]:
    """
    Return a safe summary of the active model configuration.
    Used by the health endpoint. Never includes secrets.
    """
    cfg = get_model_config()
    settings = get_settings()
    return {
        "config_version": cfg.config_version,
        "llm_provider": cfg.llm_provider,
        "llm_model": cfg.llm_model,
        "embedding_provider": cfg.embedding_provider,
        "embedding_model": cfg.embedding_model,
        "embedding_dimensionality": cfg.embedding_dimensionality,
        "embedding_version": cfg.embedding_version,
        "verification_provider": cfg.verification_provider,
        "verification_model": cfg.verification_model,
        "search_provider": settings.search_provider,
        "tavily_configured": bool(settings.tavily_api_key),
        "nvidia_configured": bool(settings.nvidia_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
        "reranker_enabled": cfg.reranker_enabled,
        "reranker_model": cfg.reranker_model if cfg.reranker_enabled else None,
    }


def clear_model_caches() -> None:
    """Clear cached model singletons so updated API keys or model configs take effect."""
    get_llm.cache_clear()
    get_verification_model.cache_clear()
    get_embedding_model.cache_clear()
    get_reranker.cache_clear()
    logger.info("Cleared all model registry caches")
