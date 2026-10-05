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

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.embeddings import Embeddings

from app.core.config.model_config import ModelConfig, get_model_config
from app.core.config.settings import get_settings
from app.core.observability.logging import get_logger
from app.core.security.exceptions import ConfigurationError

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)


def _resolve_embedding_onnx_path(cache_dir: Path) -> Path | None:
    """Resolve the ONNX embedding weights for the configured model.

    Single-model install: the id comes from ``embedding.model`` in
    models.yaml (default ``BAAI/bge-small-en-v1.5``). Canonical file is
    ``<base>.onnx`` (e.g. ``bge-small-en-v1.5.onnx``); the legacy
    underscored variant (``bge-small-en-v1_5.onnx``) is accepted.
    Returns None when neither exists so callers fail with one message.
    """
    active_model = get_model_config().embedding_model
    base = active_model.split("/")[-1]
    for candidate in (cache_dir / f"{base}.onnx", cache_dir / f"{base.replace('.', '_')}.onnx"):
        if candidate.exists():
            return candidate
    return None


def _resolve_reranker_onnx_path(cache_dir: Path, reranker_model: str) -> Path:
    """Canonical reranker ONNX path (mirrors get_reranker auto-generation)."""
    base = reranker_model.split("/")[-1].replace(".", "_")
    return cache_dir / f"reranker-{base}_int8.onnx"


# ─── ONNX singleton caches (P1-3) ────────────────────────────────────────────
# ORT InferenceSession + tokenizer construction (~130MB mmap + graph opt)
# must not run per query. Lock-guarded singletons keyed on resolved paths.
_embedding_lock = threading.Lock()
_embedding_cache: dict[tuple, Any] = {}
_reranker_lock = threading.Lock()
_reranker_cache: dict[tuple, Any] = {}


def clear_onnx_caches() -> None:
    """Clear cached ONNX singletons (tests only)."""
    with _embedding_lock:
        _embedding_cache.clear()
    with _reranker_lock:
        _reranker_cache.clear()


def onnx_model_status() -> dict[str, Any]:
    """Report presence of the ONNX weight files required by the configuration.

    Startup calls this so a missing bake fails loudly in logs (with the exact
    bootstrap command) instead of surfacing as per-query ConfigurationError
    or silent RRF-only reranking.
    """
    cfg: ModelConfig = get_model_config()
    api_base = Path(__file__).parent.parent.parent
    cache_dir = (api_base / cfg.embedding_cache_dir).resolve()
    emb = _resolve_embedding_onnx_path(cache_dir)
    rnk_path = (
        Path(cfg.reranker_onnx_model_path)
        if cfg.reranker_onnx_model_path
        else _resolve_reranker_onnx_path(cache_dir, cfg.reranker_model)
    )
    return {
        "embedding_provider": "onnx",
        "embedding_model": cfg.embedding_model,
        "embedding_onnx_present": emb is not None,
        "embedding_onnx_path": str(emb) if emb else str(cache_dir),
        "reranker_enabled": cfg.reranker_enabled,
        "reranker_use_onnx": cfg.reranker_use_onnx,
        "reranker_onnx_present": rnk_path.exists(),
        "reranker_onnx_path": str(rnk_path),
    }


# ─── LLM factories (no caching: fresh client per call) ────────────────────────


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

        llm = ChatOllamaClient(
            base_url=settings.ollama_base_url,
            model=model,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            timeout=timeout,
        )
        return llm

    if provider in ("llama_cpp", "llamacpp"):
        from app.llm.local_llm import ChatLlamaCppClient

        llm = ChatLlamaCppClient(
            base_url=settings.llamacpp_base_url,
            model=model,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            max_tokens=max_tokens if max_tokens is not None else cfg.llm_max_output_tokens,
            max_completion_tokens=max_completion_tokens,
            timeout=timeout,
        )
        return llm

    if provider == "mlx":
        from app.llm.local_llm import ChatLlamaCppClient

        llm = ChatLlamaCppClient(
            base_url=settings.mlx_base_url,
            model=model,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            max_tokens=max_tokens if max_tokens is not None else cfg.llm_max_output_tokens,
            max_completion_tokens=max_completion_tokens,
            timeout=timeout,
        )
        return llm

    if provider != "gemini":
        # Without this, ANY unknown provider fell through to the Gemini branch
        # below and silently served Gemini — the frontend still offered a
        # "NVIDIA" button long after the NIM integration was removed, so
        # choosing it returned Gemini responses labelled as NVIDIA.
        # normalize_provider documents that unknown names pass through
        # "so the caller can reject them with a useful message"; this is that
        # rejection. Fail loud instead of answering as a different provider.
        from app.core.config.model_config import SUPPORTED_LLM_PROVIDERS

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
    return llm


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


# ─── Verification LLM ─────────────────────────────────────────────────────────


def get_verification_model(provider: str | None = None, model: str | None = None) -> BaseChatModel:
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


# ─── Embedding Model (single engine: ONNX BGE) ──────────────────────────────
#
# There is exactly one embedding engine: ONNX Runtime BGE (torch-free).
# `embedding.model` in models.yaml is the sole source of truth — no provider
# choice, no EMBEDDING_PROVIDER env, no per-request override. Update the model
# ID in models.yaml and every stage follows automatically.


def get_embedding_model() -> Embeddings:
    """
    Return the single ONNX embedding model wrapped with persistent disk cache.

    The model id comes from models.yaml ``embedding.model`` (default
    ``BAAI/bge-small-en-v1.5``). There is no provider choice and no
    per-request override — the engine is always ONNX Runtime BGE.

    Cloud embeddings (google_genai) were removed: embeddings are a
    local-only concern now, so ingestion and retrieval work fully offline.
    NOTE (2026-09-06): Ollama / llama.cpp are LLM-only providers — their embedding
    usage was removed.
    """
    cfg: ModelConfig = get_model_config()

    active_model = cfg.embedding_model

    try:
        from app.llm.onnx_embeddings import ONNXBGEEmbeddings, ONNXBGEEmbeddingsWrapper
    except ImportError as exc:
        raise ConfigurationError(
            "ONNX embedding stack missing (needs 'onnxruntime' + 'transformers'). "
            "Run 'python scripts/bootstrap.py' from a venv with the base "
            "requirements installed: 'cd apps/api && pip install -e .'.",
            detail=str(exc)[:200],
        ) from exc

    # Use the API directory as base for relative cache_dir to ensure consistency
    # (Path.resolve() alone is CWD-dependent: repo-root vs apps/api runs
    # would split the cache in two. Always anchor to api_base.)
    api_base = Path(__file__).parent.parent.parent
    cache_dir = (api_base / cfg.embedding_cache_dir).resolve()
    onnx_model_path = _resolve_embedding_onnx_path(cache_dir)
    if onnx_model_path is None:
        raise ConfigurationError(
            f"ONNX embedding model not found in {cache_dir} "
            f"(looked for '{active_model.split('/')[-1]}.onnx' and legacy "
            "underscored variant). "
            "Run 'python scripts/bootstrap.py' (or "
            "'python scripts/ensure_onnx_models.py') to download/export it.",
        )

    logger.info(
        "Initializing ONNX Runtime BGE embedding model",
        model=active_model,
        onnx_path=str(onnx_model_path),
    )

    cache_key = (active_model, str(onnx_model_path), int(cfg.embedding_max_seq_length))
    with _embedding_lock:
        cached = _embedding_cache.get(cache_key)
        if isinstance(cached, Embeddings):
            return cached

    try:
        base_emb = ONNXBGEEmbeddings(
            model_path=str(onnx_model_path),
            tokenizer_name=active_model,
            max_seq_length=cfg.embedding_max_seq_length,
        )
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to load ONNX embedding model from {onnx_model_path}. "
            "Re-run 'python scripts/bootstrap.py --force' to re-export it.",
            detail=str(exc)[:300],
        ) from exc
    wrapped = ONNXBGEEmbeddingsWrapper(base_emb, model_name=f"onnx::{active_model}")
    with _embedding_lock:
        _embedding_cache[cache_key] = wrapped
    return wrapped


# ─── Reranker ─────────────────────────────────────────────────────────────────


def get_reranker():  # type: ignore[return]
    """
    Return the reranker model (cross-encoder via sentence-transformers or ONNX).

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

    # Check if ONNX quantization is requested
    if cfg.reranker_use_onnx:
        try:
            from app.llm.onnx_reranker import ONNXCrossEncoder

            logger.info("Initializing ONNX reranker", model=cfg.reranker_model)

            # Determine ONNX model path (canonical: reranker-<base>_int8.onnx,
            # next to the embedding ONNX — see scripts/ensure_onnx_models.py).
            # Anchored to api_base (not CWD) so repo-root and apps/api runs
            # share one cache.
            onnx_path = cfg.reranker_onnx_model_path
            if not onnx_path:
                api_base = Path(__file__).parent.parent.parent
                cache_dir = (api_base / cfg.embedding_cache_dir).resolve()
                onnx_path = _resolve_reranker_onnx_path(cache_dir, cfg.reranker_model)

            # Request path is read-only: never download/export inside a request
            # (P1-26). Missing weights fail closed to RRF order below.
            if not Path(onnx_path).exists():
                logger.warning(
                    "ONNX reranker weights missing, reranker disabled, using Hybrid RRF. "
                    "Run 'python scripts/ensure_onnx_models.py' to export it.",
                )
                return None

            cache_key = (cfg.reranker_model, str(onnx_path))
            with _reranker_lock:
                cached = _reranker_cache.get(cache_key)
                if cached is not None:
                    return cached
            instance = ONNXCrossEncoder(str(onnx_path), tokenizer_name=cfg.reranker_model)
            with _reranker_lock:
                _reranker_cache[cache_key] = instance
            return instance
        except ImportError:
            logger.warning("ONNX runtime not available for reranker, falling back to PyTorch")
        except Exception as exc:
            logger.warning(
                "ONNX reranker initialization failed, falling back to PyTorch", error=str(exc)
            )

    # ONNX-only enforcement (ONNX-1): when use_onnx is true (the default),
    # a failed ONNX init must NOT silently load torch weights at runtime —
    # that would violate the torch-free runtime contract the Docker image
    # relies on. Fail closed to RRF order (same as the torch-free image)
    # with an actionable message. Explicit `use_onnx: false` still opts in
    # to the PyTorch path below.
    if cfg.reranker_use_onnx:
        logger.warning(
            "ONNX reranker unavailable and use_onnx=true: reranker disabled, using Hybrid RRF. "
            "Run 'python scripts/ensure_onnx_models.py' to export it, or set "
            "reranker.use_onnx=false to explicitly opt into the PyTorch CrossEncoder."
        )
        return None

    # Fallback to PyTorch CrossEncoder (explicit opt-in via use_onnx=false only)
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        logger.warning("sentence-transformers not installed. Reranker disabled. Using Hybrid RRF.")
        return None

    logger.info("Initializing PyTorch reranker", model=cfg.reranker_model)

    from app.core.system.hardware import get_optimal_torch_device

    device = get_optimal_torch_device()
    logger.debug("Reranker target device", device=device)

    try:
        if settings.hf_token:
            return CrossEncoder(cfg.reranker_model, token=settings.hf_token, device=device)
        return CrossEncoder(cfg.reranker_model, device=device)
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
        "embedding_provider": "onnx",
        "embedding_model": cfg.embedding_model,
        "embedding_dimensionality": cfg.embedding_dimensionality,
        "embedding_version": cfg.embedding_version,
        "verification_provider": cfg.verification_provider,
        "verification_model": cfg.verification_model,
        "search_provider": settings.search_provider,
        "tavily_configured": bool(settings.tavily_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
        "reranker_enabled": cfg.reranker_enabled,
        "reranker_model": cfg.reranker_model if cfg.reranker_enabled else None,
    }
