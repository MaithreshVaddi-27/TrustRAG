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
        "embedding_provider": cfg.embedding_provider,
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
        logger.debug(
            "Evicted LLM from registry", evicted=evicted_key, max_instances=max_instances
        )
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


# ─── Embedding Model ──────────────────────────────────────────────────────────


class BGEAwareHuggingFaceEmbeddings:
    """
    Wrapper around HuggingFaceEmbeddings adding BGE query instruction prefixing
    and executing under torch.inference_mode() to minimize memory footprint.
    """

    def __init__(self, base_embeddings: Any, model_name: str) -> None:
        self._base = base_embeddings
        self._is_bge = "bge" in model_name.lower()

    def embed_query(self, text: str) -> list[float]:
        if self._is_bge and not text.startswith("Represent this sentence"):
            text = f"Represent this sentence for searching relevant passages: {text}"
        try:
            import torch

            with torch.inference_mode():
                return self._base.embed_query(text)
        except Exception:
            logger.debug("torch.inference_mode() failed for embed_query, falling back")
            return self._base.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            import torch

            with torch.inference_mode():
                return self._base.embed_documents(texts)
        except Exception:
            logger.debug("torch.inference_mode() failed for embed_documents, falling back")
            return self._base.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        if self._is_bge and not text.startswith("Represent this sentence"):
            text = f"Represent this sentence for searching relevant passages: {text}"
        return await self._base.aembed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._base.aembed_documents(texts)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


class CachedEmbeddingsWrapper(Embeddings):
    """
    Two-tier High-Speed Embedding Cache Wrapper:
      Tier 1: In-memory LRU cache (sub-millisecond memory hits)
      Tier 2: Persistent on-disk SQLite cache (eliminates repeat compute across reboots)
    Prevents redundant forward passes and network I/O for repeated queries and document chunks.
    """

    def __init__(
        self, base_embeddings: Any, max_cache_size: int = 512, model_name: str = "default"
    ) -> None:
        self._base = base_embeddings
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        # get_embedding_model is lru_cache'd per (provider, model), so every
        # caller for the same embedding serves from ONE wrapper instance. The
        # in-memory LRU is mutated via asyncio.to_thread (thread pool) and from
        # the event loop, so it must be guarded by a lock.
        self._mem_lock = threading.RLock()
        self._max_size = max_cache_size
        self._model_name = getattr(
            base_embeddings, "model", getattr(base_embeddings, "model_name", model_name)
        )

    def embed_query(self, text: str) -> list[float]:
        cached = self._lookup_mem(text)
        if cached is not None:
            return cached

        from app.core.disk_cache import get_cached_embedding, set_cached_embedding

        disk_hit = get_cached_embedding(text, self._model_name)
        if disk_hit:
            self._store_mem(text, disk_hit)
            return disk_hit

        vec = self._base.embed_query(text)
        self._store_mem(text, vec)
        set_cached_embedding(text, self._model_name, vec)
        return vec

    async def aembed_query(self, text: str) -> list[float]:
        cached = self._lookup_mem(text)
        if cached is not None:
            return cached

        from app.core.disk_cache import get_cached_embedding, set_cached_embedding

        disk_hit = await asyncio.to_thread(get_cached_embedding, text, self._model_name)
        if disk_hit:
            self._store_mem(text, disk_hit)
            return disk_hit

        vec = await self._base.aembed_query(text)
        self._store_mem(text, vec)
        await asyncio.to_thread(set_cached_embedding, text, self._model_name, vec)
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        from app.core.disk_cache import get_cached_embeddings_batch, set_cached_embeddings_batch

        cached_map, missing_indices = get_cached_embeddings_batch(texts, self._model_name)
        if not missing_indices:
            return [cached_map[i] for i in range(len(texts))]

        missing_texts = [texts[i] for i in missing_indices]
        computed_vectors = self._base.embed_documents(missing_texts)

        # Batch write computed vectors to disk cache
        set_cached_embeddings_batch(missing_texts, self._model_name, computed_vectors)

        for i, idx in enumerate(missing_indices):
            vec = computed_vectors[i]
            cached_map[idx] = vec
            self._store_mem(texts[idx], vec)

        return [cached_map[i] for i in range(len(texts))]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        from app.core.disk_cache import get_cached_embeddings_batch, set_cached_embeddings_batch

        cached_map, missing_indices = await asyncio.to_thread(
            get_cached_embeddings_batch, texts, self._model_name
        )
        if not missing_indices:
            return [cached_map[i] for i in range(len(texts))]

        missing_texts = [texts[i] for i in missing_indices]
        computed_vectors = await self._base.aembed_documents(missing_texts)

        # Batch write computed vectors to disk cache
        await asyncio.to_thread(
            set_cached_embeddings_batch, missing_texts, self._model_name, computed_vectors
        )

        for i, idx in enumerate(missing_indices):
            vec = computed_vectors[i]
            cached_map[idx] = vec
            self._store_mem(texts[idx], vec)

        return [cached_map[i] for i in range(len(texts))]

    def _lookup_mem(self, key: str) -> list[float] | None:
        with self._mem_lock:
            value = self._cache.get(key)
            if value is not None:
                self._cache.move_to_end(key)
            return value

    def _store_mem(self, key: str, val: list[float]) -> None:
        with self._mem_lock:
            self._cache[key] = val
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


@lru_cache(maxsize=8)
def get_embedding_model(provider: str | None = None, model: str | None = None) -> Embeddings:
    """
    Return the embedding model wrapped with persistent disk cache.

    Supported:
      - huggingface / local: Local BGE (BAAI/bge-small-en-v1.5, 0 API cost)
      - onnx: ONNX Runtime BGE (no PyTorch in API process, ~500-1000 MB RSS savings)

    Cloud embeddings (google_genai, nvidia) were removed: embeddings are a
    local-only concern now, so ingestion and retrieval work fully offline.
    NOTE (2026-09-06): Ollama / llama.cpp are LLM-only providers — their embedding
    usage was removed. Requesting them raises ConfigurationError with a fix.
    """
    cfg: ModelConfig = get_model_config()
    settings = get_settings()

    active_provider = (provider or cfg.embedding_provider).lower()
    active_model = model or cfg.embedding_model

    # Normalize provider to include splade option
    if active_provider == "splade":
        active_provider = "huggingface"  # SPLADE uses sentence-transformers under the hood

    def _wrap_with_cache(base_emb):
        """Wrap embedding model with persistent disk cache.

        The disk cache (embedding_cache.db) is shared across providers, so the
        cache key must carry the provider — otherwise two providers serving the
        same model string but different vectors would cross-contaminate.
        """
        from app.core.model_registry import CachedEmbeddingsWrapper

        cache_label = f"{active_provider}::{active_model}"
        return CachedEmbeddingsWrapper(base_emb, model_name=cache_label)

    # ── Retired providers ─────────────────────────────────────────────────────
    # Ollama / llama.cpp are LLM-only, and cloud embeddings (google_genai,
    # nvidia) were removed — embeddings are local-only (huggingface BGE).
    # Anything else is rejected with a fix instead of failing deep in the
    # pipeline. Knowledge bases indexed with a retired provider must be
    # re-uploaded to re-index with local BGE.
    _emb_model_lower = active_model.lower() if isinstance(active_model, str) else ""
    if active_provider not in ("huggingface", "local", "splade", "onnx") or any(
        k in _emb_model_lower for k in ("embeddinggemma", "nomic-embed")
    ):
        raise ConfigurationError(
            "Only local HuggingFace or ONNX embeddings are supported "
            "(EMBEDDING_PROVIDER=huggingface|onnx, e.g. BAAI/bge-small-en-v1.5, 384d). "
            "Re-upload documents to re-index knowledge bases built with a "
            "retired provider.",
            detail=f"requested provider={active_provider} model={active_model}",
        )

    # ── ONNX Runtime Embeddings (torch-free, ultra-low RAM) ────────────────────
    if active_provider == "onnx":
        from app.core.onnx_embeddings import ONNXBGEEmbeddings, ONNXBGEEmbeddingsWrapper

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

        base_emb = ONNXBGEEmbeddings(
            model_path=str(onnx_model_path),
            tokenizer_name=active_model,
            max_seq_length=cfg.embedding_max_seq_length,
        )
        return ONNXBGEEmbeddingsWrapper(base_emb, model_name=f"onnx::{active_model}")

    # ── Local Hugging Face Embeddings (Sentence-Transformers / BGE) ────
    from langchain_huggingface import HuggingFaceEmbeddings

    cache_dir = Path(cfg.embedding_cache_dir).resolve()

    logger.info(
        "Initializing local HuggingFace embedding model",
        model=active_model,
        dimensionality=cfg.embedding_dimensionality,
        cache_dir=str(cache_dir),
        quantization=cfg.embedding_quantization,
    )

    if settings.hf_token:
        import os

        os.environ["HF_TOKEN"] = settings.hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token

    try:
        from app.core.hardware import get_optimal_torch_device

        opt_device = get_optimal_torch_device()
        model_kwargs: dict[str, Any] = {"device": opt_device}
        if settings.hf_token:
            model_kwargs["token"] = settings.hf_token

        # Phase 4.2: Embedding Quantization (int8) for RAM savings
        if cfg.embedding_quantization:
            try:
                import importlib.util

                if importlib.util.find_spec("optimum.intel") is not None:
                    # Use OpenVINO for int8 quantization if available
                    model_kwargs["quantization_config"] = "int8"
                    logger.info("Int8 quantization enabled for embedding model")
                else:
                    raise ImportError("optimum-intel not available")
            except ImportError:
                logger.warning(
                    "Optimum-Intel not available, skipping int8 quantization. "
                    "Install 'optimum-intel' for CPU int8."
                )
                # Fallback: try torch int8 quantization
                try:
                    import importlib.util

                    if importlib.util.find_spec("torch") is not None and opt_device == "cpu":
                        import torch

                        if hasattr(torch, "quantization"):
                            logger.info("Using PyTorch dynamic int8 quantization for embeddings")
                except Exception:
                    logger.debug("PyTorch dynamic quantization not available")

        # Fast-path 1: Check local Hugging Face Hub snapshots directory
        hf_hub_name = "models--" + active_model.replace("/", "--")
        snapshots_dir = Path.home() / ".cache" / "huggingface" / "hub" / hf_hub_name / "snapshots"
        local_snapshot = next(snapshots_dir.glob("*"), None) if snapshots_dir.exists() else None

        if local_snapshot and local_snapshot.is_dir():
            try:
                base_emb = HuggingFaceEmbeddings(
                    model_name=str(local_snapshot),
                    encode_kwargs={"normalize_embeddings": True},
                    model_kwargs=model_kwargs,
                )
                logger.info(
                    "Loaded local embedding model directly from snapshot cache",
                    path=str(local_snapshot),
                )
                return _wrap_with_cache(BGEAwareHuggingFaceEmbeddings(base_emb, active_model))
            except Exception as snap_err:
                logger.debug(
                    "Local snapshot load failed, falling back to standard loader",
                    error=str(snap_err),
                )

        # Fast-path 2: Check custom cache_dir
        if cache_dir.exists() and any(cache_dir.iterdir()):
            try:
                offline_kwargs = {**model_kwargs, "local_files_only": True}
                base_emb = HuggingFaceEmbeddings(
                    model_name=active_model,
                    cache_folder=str(cache_dir),
                    encode_kwargs={"normalize_embeddings": True},
                    model_kwargs=offline_kwargs,
                )
                return _wrap_with_cache(BGEAwareHuggingFaceEmbeddings(base_emb, active_model))
            except Exception as offline_err:
                logger.debug(
                    "Offline cache fast-path fallback, attempting standard load",
                    error=str(offline_err),
                )

        base_emb = HuggingFaceEmbeddings(
            model_name=active_model,
            cache_folder=str(cache_dir) if cache_dir.exists() else None,
            encode_kwargs={"normalize_embeddings": True},
            model_kwargs=model_kwargs,
        )
        return _wrap_with_cache(BGEAwareHuggingFaceEmbeddings(base_emb, active_model))
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize embedding model '{active_model}'",
            detail=str(exc),
        ) from exc


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
    get_embedding_model.cache_clear()
    get_reranker.cache_clear()
    # Clear the bounded LLM registry (reopened unless sealed at shutdown)
    _clear_llm_registry_sync()
    logger.info("Cleared all model registry caches")
