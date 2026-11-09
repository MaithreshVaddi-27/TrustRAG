"""
TRUSTRAG — Model Registry: LLM and verification model factories.

Single place that instantiates LangChain model objects. All other modules
receive models through dependency injection or by calling these factory
functions. No instance caching: every call constructs a fresh client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.config import ModelConfig, get_model_config
from app.config.settings import get_settings
from app.observability.logging import get_logger
from app.security.exceptions import ConfigurationError

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)

__all__ = ["_create_llm", "get_llm", "get_verification_model"]


def _create_llm(
    *,
    provider: str,
    model: str,
    temperature: float,
    max_tokens: int | None,
    timeout: float,
    top_p: float | None = None,
    max_completion_tokens: int | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """Unified LLM factory used by get_llm and get_verification_model."""
    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    logger.info(
        "Initializing LLM",
        provider=provider,
        model=model,
        temperature=temperature,
        max_output_tokens=max_tokens,
        max_completion_tokens=max_completion_tokens,
        timeout=timeout,
    )

    if provider == "ollama":
        from app.llm.local_llm import ChatOllamaClient

        return ChatOllamaClient(
            base_url=settings.ollama_base_url,
            model=model,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            timeout=timeout,
        )

    if provider in ("llama_cpp", "llamacpp"):
        from app.llm.local_llm import ChatLlamaCppClient

        return ChatLlamaCppClient(
            base_url=settings.llamacpp_base_url,
            model=model,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            max_tokens=max_tokens if max_tokens is not None else cfg.llm_max_output_tokens,
            max_completion_tokens=max_completion_tokens,
            timeout=timeout,
        )

    if provider == "mlx":
        from app.llm.local_llm import ChatLlamaCppClient

        return ChatLlamaCppClient(
            base_url=settings.mlx_base_url,
            model=model,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            max_tokens=max_tokens if max_tokens is not None else cfg.llm_max_output_tokens,
            max_completion_tokens=max_completion_tokens,
            timeout=timeout,
        )

    if provider != "gemini":
        # Without this, ANY unknown provider fell through to the Gemini branch
        # below and silently served Gemini — the frontend still offered a
        # "NVIDIA" button long after the NIM integration was removed, so
        # choosing it returned Gemini responses labelled as NVIDIA.
        # normalize_provider documents that unknown names pass through
        # "so the caller can reject them with a useful message"; this is that
        # rejection. Fail loud instead of answering as a different provider.
        from app.config import SUPPORTED_LLM_PROVIDERS

        raise ConfigurationError(
            f"Unknown LLM provider '{provider}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_LLM_PROVIDERS))}."
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    if not settings.gemini_api_key:
        raise ConfigurationError(
            "GEMINI_API_KEY must be set when using Google Gemini provider. "
            "Switch to 'ollama' or 'llama_cpp' to run completely locally without an API key."
        )

    try:
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            max_output_tokens=max_tokens if max_tokens is not None else cfg.llm_max_output_tokens,
            timeout=timeout,
            max_retries=max_retries if max_retries is not None else cfg.llm_max_retries,
        )
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize Google Gemini client for model '{model}'. "
            "The API key may be invalid, revoked, or not permitted for this model."
        ) from exc
    return cast(BaseChatModel, llm)


def get_llm(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """
    Return the primary LLM for answer generation.

    Supports:
      - ollama: ChatOllamaClient (local, zero cloud keys)
      - llama_cpp / llamacpp: ChatLlamaCppClient (local, OpenAI-compatible server)
      - mlx: ChatLlamaCppClient pointed at mlx_lm.server (Apple Silicon, OpenAI-compatible)
      - gemini: ChatGoogleGenerativeAI via langchain-google-genai

    No instance caching: every call constructs a fresh client. HTTP-backed
    LLM clients are cheap to build; sharing them across analyses caused
    stale-state bugs (evicted mid-request clients, sealed registries).
    """
    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    active_provider = (provider or cfg.llm_provider).lower()
    # Local paths prefer the explicit Settings override but fall back to the
    # models.yaml default FOR THE REQUESTED PROVIDER (never a hardcoded id the
    # server may not serve, and never another provider's configured model).
    if active_provider == "ollama":
        active_model = model or settings.ollama_model or cfg.llm_model_for("ollama")
    elif active_provider in ("llama_cpp", "llamacpp"):
        active_model = model or settings.llamacpp_model or cfg.llm_model_for("llama_cpp")
    elif active_provider == "mlx":
        active_model = model or settings.mlx_model or cfg.llm_model_for("mlx")
    else:
        active_model = model or cfg.llm_model_for(active_provider)

    logger.info(
        "Initializing LLM",
        provider=active_provider,
        model=active_model,
        temperature=cfg.llm_temperature,
        max_output_tokens=cfg.llm_max_output_tokens,
    )

    return _create_llm(
        provider=active_provider,
        model=active_model,
        temperature=cfg.llm_temperature,
        max_tokens=cfg.llm_max_output_tokens,
        timeout=float(cfg.llm_timeout_seconds),
        top_p=cfg.llm_top_p,
        max_completion_tokens=cfg.llm_max_output_tokens,
        max_retries=cfg.llm_max_retries,
    )


def get_verification_model(
    provider: str | None = None, model: str | None = None
) -> BaseChatModel:
    """
    Return the verification LLM for claim-level structured verification.

    Separate from the primary LLM to allow independent cost/quality tuning.
    Temperature is forced to 0.0 for deterministic verification.

    No instance caching (see get_llm).
    """
    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    active_provider = (provider or cfg.verification_provider).lower()
    # Same empty-override fallback as get_llm, per requested provider.
    if active_provider == "ollama":
        active_model = model or settings.ollama_model or cfg.verification_model_for("ollama")
    elif active_provider in ("llama_cpp", "llamacpp"):
        active_model = model or settings.llamacpp_model or cfg.verification_model_for("llama_cpp")
    elif active_provider == "mlx":
        active_model = model or settings.mlx_model or cfg.verification_model_for("mlx")
    else:
        active_model = model or cfg.verification_model_for(active_provider)

    logger.info(
        "Initializing verification model",
        provider=active_provider,
        model=active_model,
        temperature=0.0,
    )

    return _create_llm(
        provider=active_provider,
        model=active_model,
        temperature=0.0,
        max_tokens=cfg.verification_max_output_tokens,
        timeout=float(cfg.verification_timeout_seconds),
        top_p=cfg.llm_top_p,
        max_completion_tokens=cfg.verification_max_output_tokens,
        max_retries=cfg.verification_max_retries,
    )
