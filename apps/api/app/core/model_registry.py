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


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Return the primary LLM for answer generation.

    Uses ChatGoogleGenerativeAI via langchain-google-genai.
    Model ID and all parameters come from models.yaml.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    logger.info(
        "Initializing LLM",
        model=cfg.llm_model,
        temperature=cfg.llm_temperature,
        max_output_tokens=cfg.llm_max_output_tokens,
    )

    try:
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
            f"Failed to initialize LLM '{cfg.llm_model}'",
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
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    logger.info(
        "Initializing verification model",
        model=cfg.verification_model,
        temperature=cfg.verification_temperature,
    )

    try:
        return ChatGoogleGenerativeAI(
            model=cfg.verification_model,
            google_api_key=settings.gemini_api_key,
            temperature=cfg.verification_temperature,
            max_output_tokens=cfg.verification_max_output_tokens,
            timeout=cfg.verification_timeout_seconds,
            max_retries=cfg.llm_max_retries,
        )
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize verification model '{cfg.verification_model}'",
            detail=str(exc),
        ) from exc


# ─── Embedding Model ──────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_embedding_model() -> Embeddings:
    """
    Return the embedding model.

    Uses HuggingFaceEmbeddings (sentence-transformers) — fully local,
    no API key required, free to run.

    Model is downloaded once and cached in the configured cache directory.
    Embedding dimensionality from models.yaml MUST match the Qdrant collection.
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    cfg: ModelConfig = get_model_config()
    cache_dir = Path(cfg.embedding_cache_dir).resolve()

    logger.info(
        "Initializing embedding model",
        model=cfg.embedding_model,
        dimensionality=cfg.embedding_dimensionality,
        cache_dir=str(cache_dir),
    )

    settings = get_settings()
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

        # Fast-path: if model is already pre-cached in Docker, load purely offline (0 network delay)
        if cache_dir.exists() and any(cache_dir.iterdir()):
            try:
                offline_kwargs = {**model_kwargs, "local_files_only": True}
                return HuggingFaceEmbeddings(
                    model_name=cfg.embedding_model,
                    cache_folder=str(cache_dir),
                    encode_kwargs={"normalize_embeddings": True},
                    model_kwargs=offline_kwargs,
                )
            except Exception as offline_err:
                logger.debug(
                    "Offline cache fast-path skipped, downloading model", error=str(offline_err)
                )

        return HuggingFaceEmbeddings(
            model_name=cfg.embedding_model,
            cache_folder=str(cache_dir),
            encode_kwargs={"normalize_embeddings": True},
            model_kwargs=model_kwargs,
        )
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

    from sentence_transformers import CrossEncoder

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


def registry_status() -> dict[str, str | bool | None]:
    """
    Return a safe summary of the active model configuration.
    Used by the health endpoint. Never includes secrets.
    """
    cfg = get_model_config()
    return {
        "config_version": cfg.config_version,
        "llm_model": cfg.llm_model,
        "embedding_model": cfg.embedding_model,
        "embedding_version": cfg.embedding_version,
        "verification_model": cfg.verification_model,
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
