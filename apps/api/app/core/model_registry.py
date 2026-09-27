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

import asyncio
import threading
import time
import warnings
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.embeddings import Embeddings

from app.core.config import ModelConfig, get_model_config, get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger

try:
    import psutil
except ImportError:
    psutil = None

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)


@contextmanager
def _suppress_nvidia_unknown_type_warning(model: str):
    """Silence the vendor 'type is unknown' UserWarning on ChatNVIDIA init.

    langchain-nvidia-ai-endpoints warns (with a venv path) on every
    construction for models it can't classify — observed for
    nvidia/nemotron-3.5-lightning-30b-a3b. Nothing app-side avoids it short
    of switching models; liveness is covered by probe_cloud_llm, so the raw
    warning is noise. A debug line keeps the signal.
    """
    logger.debug("Constructing ChatNVIDIA client (type-check warning suppressed)", model=model)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*but type is unknown and inference may fail.*",
            category=UserWarning,
        )
        yield


def _resolve_embedding_onnx_path(cache_dir: Path, active_model: str) -> Path | None:
    """Resolve the ONNX embedding weights for a model id (canonical + legacy).

    Canonical: ``<base>.onnx`` (e.g. ``bge-small-en-v1.5.onnx``); legacy
    accepts the underscored variant (``bge-small-en-v1_5.onnx``). Returns None
    when neither exists so callers fail with one actionable message.
    """
    base = active_model.split("/")[-1]
    for candidate in (cache_dir / f"{base}.onnx", cache_dir / f"{base.replace('.', '_')}.onnx"):
        if candidate.exists():
            return candidate
    return None


def _resolve_reranker_onnx_path(cache_dir: Path, reranker_model: str) -> Path:
    """Canonical reranker ONNX path (mirrors get_reranker auto-generation)."""
    base = reranker_model.split("/")[-1].replace(".", "_")
    return cache_dir / f"reranker-{base}_int8.onnx"


def onnx_model_status() -> dict[str, Any]:
    """Report presence of the ONNX weight files required by the configuration.

    Startup calls this so a missing bake fails loudly in logs (with the exact
    bootstrap command) instead of surfacing as per-query ConfigurationError
    or silent RRF-only reranking.
    """
    cfg: ModelConfig = get_model_config()
    api_base = Path(__file__).parent.parent.parent
    cache_dir = (api_base / cfg.embedding_cache_dir).resolve()
    emb = _resolve_embedding_onnx_path(cache_dir, cfg.embedding_model)
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


# ─── Bounded LLM Registry (replaces lru_cache on get_llm/get_verification_model) ────
# Limits concurrent model instances to prevent RAM/GPU leak from user-controlled keys.
# Phase 2.2: Aggressive eviction - configurable max instances based on RAM
_MAX_LLM_INSTANCES = 2  # Reduced from 4 for ultra-low RAM usage (8GB systems)
_LLM_REGISTRY: OrderedDict[str, BaseChatModel] = OrderedDict()
_LLM_REGISTRY_LOCK = threading.RLock()
_LLM_REGISTRY_CLOSED = False
# TTL cache for get_max_llm_instances() (see below).
_MAX_INSTANCES_CACHE: dict[str, float] = {}


def get_max_llm_instances() -> int:
    """Get the maximum number of LLM instances based on available RAM.

    Cached for 60 s: the value changes ~never, and every uncached call costs
    a psutil syscall on the LLM-construction path.
    """
    now = time.monotonic()
    with _LLM_REGISTRY_LOCK:
        cached = _MAX_INSTANCES_CACHE.get("value")
        cached_at = _MAX_INSTANCES_CACHE.get("at", 0.0)
        if cached is not None and (now - cached_at) < 60.0:
            return int(cached)
    try:
        import psutil as _psutil

        total_ram_gb = _psutil.virtual_memory().total / (1024**3)
        if total_ram_gb <= 8:
            resolved = 1  # Ultra-aggressive for 8GB systems
        elif total_ram_gb <= 16:
            resolved = 2  # Conservative for 16GB systems
        else:
            resolved = 4  # Standard for 32GB+ systems
    except ImportError:
        resolved = _MAX_LLM_INSTANCES  # Default fallback
    with _LLM_REGISTRY_LOCK:
        _MAX_INSTANCES_CACHE["value"] = resolved
        _MAX_INSTANCES_CACHE["at"] = now
    return resolved


def _llm_registry_key(provider: str, model: str | None) -> str:
    return f"{provider}:{model or 'default'}"


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
    registry_prefix: str = "",
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
        from app.core.local_llm import ChatOllamaClient

        llm = ChatOllamaClient(
            base_url=settings.ollama_base_url,
            model=model,
            temperature=temperature,
            top_p=top_p if top_p is not None else cfg.llm_top_p,
            timeout=timeout,
        )
        return llm

    if provider in ("llama_cpp", "llamacpp"):
        from app.core.local_llm import ChatLlamaCppClient

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
        from app.core.local_llm import ChatLlamaCppClient

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

    if provider in ("nvidia", "nim"):
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        if not settings.nvidia_api_key:
            raise ConfigurationError("NVIDIA_API_KEY must be set when AI_PROVIDER is 'nvidia'")

        with _suppress_nvidia_unknown_type_warning(model):
            llm = ChatNVIDIA(
                model=model,
                api_key=settings.nvidia_api_key,
                temperature=temperature,
                max_completion_tokens=(
                    max_completion_tokens or max_tokens or cfg.llm_max_output_tokens
                ),
                timeout=timeout,
            )
        return llm

    from langchain_google_genai import ChatGoogleGenerativeAI

    if not settings.gemini_api_key:
        raise ConfigurationError(
            "GEMINI_API_KEY must be set when using Google Gemini provider. "
            "Switch to 'ollama' or 'llama_cpp' to run completely locally without an API key."
        )

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        top_p=top_p if top_p is not None else cfg.llm_top_p,
        max_output_tokens=max_tokens if max_tokens is not None else cfg.llm_max_output_tokens,
        timeout=timeout,
        max_retries=max_retries if max_retries is not None else cfg.llm_max_retries,
    )
    return llm


async def _close_llm_instance(llm: BaseChatModel) -> None:
    """Best-effort close for LLM instances that support it."""
    try:
        # Prefer async close if available
        if hasattr(llm, "aclose"):
            await llm.aclose()
        elif hasattr(llm, "close"):
            llm.close()
    except Exception as exc:
        logger.debug("Error closing LLM instance", error=str(exc))


def get_llm_instance(provider: str, model: str | None) -> BaseChatModel | None:
    """Get existing LLM instance from registry (no creation)."""
    key = _llm_registry_key(provider, model)
    with _LLM_REGISTRY_LOCK:
        if key in _LLM_REGISTRY:
            # LRU: move to end
            _LLM_REGISTRY.move_to_end(key)
            return _LLM_REGISTRY[key]
    return None


# Instances evicted while no event loop is running (sync call sites, worker
# threads) wait here until close_all_llm_instances() drains them at shutdown.
_PENDING_CLOSE: list[BaseChatModel] = []


def _schedule_close(llm: BaseChatModel) -> None:
    """Best-effort async close: direct task when a loop runs, else deferred."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and not loop.is_closed():
        loop.create_task(_close_llm_instance(llm))
    else:
        with _LLM_REGISTRY_LOCK:
            _PENDING_CLOSE.append(llm)


def put_llm_instance(provider: str, model: str | None, llm: BaseChatModel) -> None:
    """Put LLM instance into bounded registry with LRU eviction (sync).

    Sync by design: get_llm/get_verification_model are sync factories called
    from both async and sync code. Evicted instances close via the running
    loop when there is one, otherwise wait in _PENDING_CLOSE for shutdown.
    """
    global _LLM_REGISTRY_CLOSED
    if _LLM_REGISTRY_CLOSED:
        # If registry is closed, close the new instance immediately
        _schedule_close(llm)
        return

    key = _llm_registry_key(provider, model)
    max_instances = get_max_llm_instances()
    evicted: tuple[str, BaseChatModel] | None = None
    with _LLM_REGISTRY_LOCK:
        # Evict LRU if at capacity
        if len(_LLM_REGISTRY) >= max_instances and key not in _LLM_REGISTRY:
            evicted = _LLM_REGISTRY.popitem(last=False)

        _LLM_REGISTRY[key] = llm
        _LLM_REGISTRY.move_to_end(key)

    if evicted is not None:
        evicted_key, evicted_llm = evicted
        logger.debug("Evicted LLM from registry", evicted=evicted_key, max_instances=max_instances)
        _schedule_close(evicted_llm)


async def close_all_llm_instances(seal: bool = False) -> None:
    """Close all LLM instances; seal the registry only on app shutdown.

    Args:
        seal: When True, prevent new registrations (shutdown path).
            `clear_model_caches()` passes False so the registry reopens.
    """
    global _LLM_REGISTRY_CLOSED
    with _LLM_REGISTRY_LOCK:
        _LLM_REGISTRY_CLOSED = seal
        pending = list(_LLM_REGISTRY.values()) + list(_PENDING_CLOSE)
        _LLM_REGISTRY.clear()
        _PENDING_CLOSE.clear()
    for llm in pending:
        await _close_llm_instance(llm)
    if seal:
        logger.info("Closed all LLM instances and sealed registry")
    else:
        logger.info("Closed all LLM instances (registry reopened)")


def _clear_llm_registry_sync() -> None:
    """Sync registry drain for sync call sites (clear_model_caches, tests).

    Instances move to _PENDING_CLOSE and close via the running loop when
    there is one; anything left is drained by close_all_llm_instances().
    """
    with _LLM_REGISTRY_LOCK:
        pending = list(_LLM_REGISTRY.values())
        _LLM_REGISTRY.clear()
        _PENDING_CLOSE.extend(pending)
    for llm in pending:
        # Sync close when the client offers one; async-only clients wait for
        # the loop task / shutdown drain.
        close_fn = getattr(llm, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception as exc:
                logger.debug("Error closing LLM instance", error=str(exc))
        else:
            _schedule_close(llm)


# ─── LLM ─────────────────────────────────────────────────────────────────────


def get_llm(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """
    Return the primary LLM for answer generation.

    Supports:
      - ollama: ChatOllamaClient (local, zero cloud keys)
      - llama_cpp / llamacpp: ChatLlamaCppClient (local, OpenAI-compatible server)
      - mlx: ChatLlamaCppClient pointed at mlx_lm.server (Apple Silicon, OpenAI-compatible)
      - gemini: ChatGoogleGenerativeAI via langchain-google-genai
      - nvidia: ChatNVIDIA via langchain-nvidia-ai-endpoints

    Uses bounded registry (max instances scale with RAM: 1/2/4) with LRU
    eviction to prevent RAM/GPU leak from user-controlled model strings.
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

    # Check registry first
    cached = get_llm_instance(active_provider, active_model)
    if cached is not None:
        logger.debug("LLM cache hit", provider=active_provider, model=active_model)
        return cached

    logger.info(
        "Initializing LLM",
        provider=active_provider,
        model=active_model,
        temperature=cfg.llm_temperature,
        max_output_tokens=cfg.llm_max_output_tokens,
    )

    llm = _create_llm(
        provider=active_provider,
        model=active_model,
        temperature=cfg.llm_temperature,
        max_tokens=cfg.llm_max_output_tokens,
        timeout=float(cfg.llm_timeout_seconds),
        top_p=cfg.llm_top_p,
        max_completion_tokens=cfg.llm_max_output_tokens,
        max_retries=cfg.llm_max_retries,
        registry_prefix="",
    )
    put_llm_instance(active_provider, active_model, llm)
    return llm


# ─── Verification LLM ─────────────────────────────────────────────────────────


def get_verification_model(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """
    Return the verification LLM for claim-level structured verification.

    Separate from the primary LLM to allow independent cost/quality tuning.
    Temperature is forced to 0.0 for deterministic verification.

    Uses bounded registry (max 4 instances) with LRU eviction.
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

    # Check registry first (use distinct key prefix for verification models)
    cached = get_llm_instance(f"verify:{active_provider}", active_model)
    if cached is not None:
        logger.debug("Verification LLM cache hit", provider=active_provider, model=active_model)
        return cached

    logger.info(
        "Initializing verification model",
        provider=active_provider,
        model=active_model,
        temperature=0.0,
    )

    llm = _create_llm(
        provider=active_provider,
        model=active_model,
        temperature=0.0,
        max_tokens=cfg.verification_max_output_tokens,
        timeout=float(cfg.verification_timeout_seconds),
        top_p=cfg.llm_top_p,
        max_completion_tokens=cfg.verification_max_output_tokens,
        max_retries=cfg.verification_max_retries,
        registry_prefix="verify:",
    )
    put_llm_instance(f"verify:{active_provider}", active_model, llm)
    return llm
    """
    Return the verification LLM for claim-level structured verification.

    Separate from the primary LLM to allow independent cost/quality tuning.
    Temperature is forced to 0.0 for deterministic verification.

    Uses bounded registry (max 4 instances) with LRU eviction.
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

    # Check registry first (use distinct key prefix for verification models)
    cached = get_llm_instance(f"verify:{active_provider}", active_model)
    if cached is not None:
        logger.debug("Verification LLM cache hit", provider=active_provider, model=active_model)
        return cached

    logger.info(
        "Initializing verification model",
        provider=active_provider,
        model=active_model,
        temperature=0.0,
    )

    try:
        if active_provider == "ollama":
            from app.core.local_llm import ChatOllamaClient

            llm = ChatOllamaClient(
                base_url=settings.ollama_base_url,
                model=active_model or "granite4.2:3b-q4_K_M",
                temperature=0.0,
                timeout=float(cfg.verification_timeout_seconds),
            )
            put_llm_instance(f"verify:{active_provider}", active_model, llm)
            return llm

        if active_provider in ("llama_cpp", "llamacpp"):
            from app.core.local_llm import ChatLlamaCppClient

            llm = ChatLlamaCppClient(
                base_url=settings.llamacpp_base_url,
                model=active_model or "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M",
                temperature=0.0,
                max_tokens=cfg.verification_max_output_tokens,
                timeout=float(cfg.verification_timeout_seconds),
            )
            put_llm_instance(f"verify:{active_provider}", active_model, llm)
            return llm

        if active_provider == "mlx":
            from app.core.local_llm import ChatLlamaCppClient

            llm = ChatLlamaCppClient(
                base_url=settings.mlx_base_url,
                model=active_model or "mlx-community/Llama-3.2-1B-Instruct-4bit",
                temperature=0.0,
                max_tokens=cfg.verification_max_output_tokens,
                timeout=float(cfg.verification_timeout_seconds),
            )
            put_llm_instance(f"verify:{active_provider}", active_model, llm)
            return llm

        if active_provider in ("nvidia", "nim"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            if not settings.nvidia_api_key:
                raise ConfigurationError("NVIDIA_API_KEY must be set when AI_PROVIDER is 'nvidia'")

            # Same ChatNVIDIA field rule as get_llm: max_completion_tokens +
            # client timeout (max_tokens/timeout are silently ignored).
            with _suppress_nvidia_unknown_type_warning(active_model):
                llm = ChatNVIDIA(
                    model=active_model,
                    api_key=settings.nvidia_api_key,
                    temperature=0.0,
                    max_completion_tokens=cfg.verification_max_output_tokens,
                    timeout=float(cfg.verification_timeout_seconds),
                )
            put_llm_instance(f"verify:{active_provider}", active_model, llm)
            return llm

        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY must be set when using Google Gemini provider. "
                "Switch to 'ollama' or 'llama_cpp' to run completely locally without an API key."
            )

        llm = ChatGoogleGenerativeAI(
            model=active_model,
            google_api_key=settings.gemini_api_key,
            temperature=cfg.verification_temperature,
            max_output_tokens=cfg.verification_max_output_tokens,
            timeout=cfg.verification_timeout_seconds,
            max_retries=cfg.verification_max_retries,
        )
        put_llm_instance(f"verify:{active_provider}", active_model, llm)
        return llm
    except Exception as exc:
        msg = (
            f"Failed to initialize verification model '{active_model}' "
            f"(provider: {active_provider})"
        )
        raise ConfigurationError(msg, detail=str(exc)) from exc


# ─── Embedding Model (single engine: ONNX BGE) ──────────────────────────────
#
# There is exactly one embedding engine: ONNX Runtime BGE (torch-free).
# `embedding.model` in models.yaml is the sole source of truth — no provider
# choice, no EMBEDDING_PROVIDER env, no per-request override. Update the model
# ID in models.yaml and every stage follows automatically.


@lru_cache(maxsize=8)
def get_embedding_model(model: str | None = None) -> Embeddings:
    """
    Return the ONNX embedding model wrapped with persistent disk cache.

    Args:
        model: Optional model ID override (defaults to models.yaml
            `embedding.model`). The engine is always ONNX Runtime BGE.

    Cloud embeddings (google_genai, nvidia) were removed: embeddings are a
    local-only concern now, so ingestion and retrieval work fully offline.
    NOTE (2026-09-06): Ollama / llama.cpp are LLM-only providers — their embedding
    usage was removed. Requesting them raises ConfigurationError with a fix.
    """
    cfg: ModelConfig = get_model_config()

    active_model = model or cfg.embedding_model

    try:
        from app.core.onnx_embeddings import ONNXBGEEmbeddings, ONNXBGEEmbeddingsWrapper
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
    onnx_model_path = _resolve_embedding_onnx_path(cache_dir, active_model)
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
    return ONNXBGEEmbeddingsWrapper(base_emb, model_name=f"onnx::{active_model}")


# ─── Reranker ─────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
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
            from app.core.onnx_reranker import ONNXCrossEncoder

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

            # If ONNX model doesn't exist, we'll fall back to PyTorch
            if not Path(onnx_path).exists():
                logger.info("ONNX model not found, will export from PyTorch", path=str(onnx_path))
                try:
                    import importlib.util

                    if importlib.util.find_spec("torch") is not None:
                        # Import torch locally for export
                        import torch  # noqa: F401 - used by CrossEncoder internally
                        from sentence_transformers import CrossEncoder

                        model = CrossEncoder(cfg.reranker_model)
                        # Export to ONNX
                        from app.core.onnx_reranker import export_crossencoder_to_onnx

                        export_crossencoder_to_onnx(
                            model, str(onnx_path), tokenizer_name=cfg.reranker_model
                        )
                        logger.info("Successfully exported reranker to ONNX", path=str(onnx_path))
                    else:
                        raise ImportError("torch not available")
                except Exception as export_exc:
                    logger.warning(
                        "Failed to export reranker to ONNX, falling back to PyTorch",
                        error=str(export_exc),
                    )

            if Path(onnx_path).exists():
                return ONNXCrossEncoder(str(onnx_path), tokenizer_name=cfg.reranker_model)
            else:
                logger.warning("ONNX export failed, falling back to PyTorch CrossEncoder")
        except ImportError:
            logger.warning("ONNX runtime not available for reranker, falling back to PyTorch")
        except Exception as exc:
            logger.warning(
                "ONNX reranker initialization failed, falling back to PyTorch", error=str(exc)
            )

    # Fallback to PyTorch CrossEncoder
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        logger.warning("sentence-transformers not installed. Reranker disabled. Using Hybrid RRF.")
        return None

    logger.info("Initializing PyTorch reranker", model=cfg.reranker_model)

    from app.core.hardware import get_optimal_torch_device

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
        "nvidia_configured": bool(settings.nvidia_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
        "reranker_enabled": cfg.reranker_enabled,
        "reranker_model": cfg.reranker_model if cfg.reranker_enabled else None,
    }


def clear_model_caches() -> None:
    """Clear cached model singletons so updated API keys or model configs take effect."""
    get_embedding_model.cache_clear()
    get_reranker.cache_clear()
    # Clear the bounded LLM registry (reopened unless sealed at shutdown)
    _clear_llm_registry_sync()
    logger.info("Cleared all model registry caches")
