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
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.embeddings import Embeddings

from app.core.config import ModelConfig, get_model_config, get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)

# ─── LLM Response Cache ────────────────────────────────────────────────────────
# Enable LangChain's in-memory LLM cache to avoid redundant calls for identical prompts.
# This reduces load on both local and cloud LLMs for repeated/similar queries.
_llm_cache_enabled = False


def _enable_llm_cache() -> None:
    """Set up LangChain in-memory cache for LLM responses (idempotent)."""
    global _llm_cache_enabled
    if _llm_cache_enabled:
        return
    try:
        import langchain
        from langchain_core.caches import InMemoryCache

        langchain.llm_cache = InMemoryCache()
        _llm_cache_enabled = True
        logger.info("LLM response cache enabled (InMemoryCache)")
    except Exception as exc:
        logger.debug("Could not enable LLM cache", error=str(exc))


# ─── LLM ─────────────────────────────────────────────────────────────────────


# ─── LLM ─────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=16)
def get_llm(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """
    Return the primary LLM for answer generation.

    Supports:
      - ollama: ChatOllamaClient (local, zero cloud keys)
      - llama_cpp / llamacpp: ChatLlamaCppClient (local, OpenAI-compatible server)
      - gemini: ChatGoogleGenerativeAI via langchain-google-genai
      - nvidia: ChatNVIDIA via langchain-nvidia-ai-endpoints
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
    else:
        active_model = model or cfg.llm_model

    logger.info(
        "Initializing LLM",
        provider=active_provider,
        model=active_model,
        temperature=cfg.llm_temperature,
        max_output_tokens=cfg.llm_max_output_tokens,
    )

    try:
        if active_provider == "ollama":
            from app.core.local_llm import ChatOllamaClient

            llm = ChatOllamaClient(
                base_url=settings.ollama_base_url,
                model=active_model or "granite4.2:3b-q4_K_M",
                temperature=cfg.llm_temperature,
                top_p=cfg.llm_top_p,
                timeout=float(cfg.llm_timeout_seconds),
            )
            _enable_llm_cache()
            return llm

        if active_provider in ("llama_cpp", "llamacpp"):
            from app.core.local_llm import ChatLlamaCppClient

            llm = ChatLlamaCppClient(
                base_url=settings.llamacpp_base_url,
                model=active_model or "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M",
                temperature=cfg.llm_temperature,
                top_p=cfg.llm_top_p,
                max_tokens=cfg.llm_max_output_tokens,
                timeout=float(cfg.llm_timeout_seconds),
            )
            _enable_llm_cache()
            return llm

        if active_provider in ("nvidia", "nim"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            if not settings.nvidia_api_key:
                raise ConfigurationError("NVIDIA_API_KEY must be set when AI_PROVIDER is 'nvidia'")

            llm = ChatNVIDIA(
                model=active_model,
                api_key=settings.nvidia_api_key,
                temperature=cfg.llm_temperature,
                max_tokens=cfg.llm_max_output_tokens,
                timeout=cfg.llm_timeout_seconds,
            )
            _enable_llm_cache()
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
            temperature=cfg.llm_temperature,
            top_p=cfg.llm_top_p,
            max_output_tokens=cfg.llm_max_output_tokens,
            timeout=cfg.llm_timeout_seconds,
            max_retries=cfg.llm_max_retries,
        )
        _enable_llm_cache()
        return llm
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize LLM '{active_model}' (provider: {active_provider})",
            detail=str(exc),
        ) from exc


# ─── Verification LLM ─────────────────────────────────────────────────────────


@lru_cache(maxsize=16)
def get_verification_model(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """
    Return the verification LLM for claim-level structured verification.

    Separate from the primary LLM to allow independent cost/quality tuning.
    Temperature is forced to 0.0 for deterministic verification.
    """
    settings = get_settings()
    cfg: ModelConfig = get_model_config()

    active_provider = (provider or cfg.verification_provider).lower()
    # Same empty-override fallback as get_llm, per requested provider.
    if active_provider == "ollama":
        active_model = model or settings.ollama_model or cfg.verification_model_for("ollama")
    elif active_provider in ("llama_cpp", "llamacpp"):
        active_model = model or settings.llamacpp_model or cfg.verification_model_for("llama_cpp")
    else:
        active_model = model or cfg.verification_model

    logger.info(
        "Initializing verification model",
        provider=active_provider,
        model=active_model,
        temperature=0.0,
    )

    try:
        if active_provider == "ollama":
            from app.core.local_llm import ChatOllamaClient

            return ChatOllamaClient(
                base_url=settings.ollama_base_url,
                model=active_model or "granite4.2:3b-q4_K_M",
                temperature=0.0,
                timeout=float(cfg.verification_timeout_seconds),
            )

        if active_provider in ("llama_cpp", "llamacpp"):
            from app.core.local_llm import ChatLlamaCppClient

            return ChatLlamaCppClient(
                base_url=settings.llamacpp_base_url,
                model=active_model or "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M",
                temperature=0.0,
                max_tokens=cfg.verification_max_output_tokens,
                timeout=float(cfg.verification_timeout_seconds),
            )

        if active_provider in ("nvidia", "nim"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            if not settings.nvidia_api_key:
                raise ConfigurationError("NVIDIA_API_KEY must be set when AI_PROVIDER is 'nvidia'")

            return ChatNVIDIA(
                model=active_model,
                api_key=settings.nvidia_api_key,
                temperature=0.0,
                max_tokens=cfg.verification_max_output_tokens,
                timeout=cfg.verification_timeout_seconds,
            )

        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY must be set when using Google Gemini provider. "
                "Switch to 'ollama' or 'llama_cpp' to run completely locally without an API key."
            )

        return ChatGoogleGenerativeAI(
            model=active_model,
            google_api_key=settings.gemini_api_key,
            temperature=cfg.verification_temperature,
            max_output_tokens=cfg.verification_max_output_tokens,
            timeout=cfg.verification_timeout_seconds,
            max_retries=cfg.llm_max_retries,
        )
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
            return self._base.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            import torch

            with torch.inference_mode():
                return self._base.embed_documents(texts)
        except Exception:
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

        from app.core.disk_cache import get_cached_embeddings_batch, set_cached_embedding

        cached_map, missing_indices = get_cached_embeddings_batch(texts, self._model_name)
        if not missing_indices:
            return [cached_map[i] for i in range(len(texts))]

        missing_texts = [texts[i] for i in missing_indices]
        computed_vectors = self._base.embed_documents(missing_texts)

        for i, idx in enumerate(missing_indices):
            vec = computed_vectors[i]
            cached_map[idx] = vec
            self._store_mem(texts[idx], vec)
            set_cached_embedding(texts[idx], self._model_name, vec)

        return [cached_map[i] for i in range(len(texts))]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        from app.core.disk_cache import get_cached_embeddings_batch, set_cached_embedding

        cached_map, missing_indices = await asyncio.to_thread(
            get_cached_embeddings_batch, texts, self._model_name
        )
        if not missing_indices:
            return [cached_map[i] for i in range(len(texts))]

        missing_texts = [texts[i] for i in missing_indices]
        computed_vectors = await self._base.aembed_documents(missing_texts)

        for i, idx in enumerate(missing_indices):
            vec = computed_vectors[i]
            cached_map[idx] = vec
            self._store_mem(texts[idx], vec)
            await asyncio.to_thread(set_cached_embedding, texts[idx], self._model_name, vec)

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
      - google_genai / gemini: Cloud-hosted Google Gemini embeddings (ultra-low RAM <60MB)
      - nvidia / nim: Cloud-hosted NVIDIA NIM embeddings

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

    # ── Retired: local LLM-server embeddings (LLM-only now) ────────────────────
    _emb_model_lower = active_model.lower() if isinstance(active_model, str) else ""
    if active_provider in ("ollama", "llamacpp", "llama_cpp") or (
        any(k in _emb_model_lower for k in ("embeddinggemma", "nomic-embed"))
        and active_provider
        not in ("huggingface", "local", "google_genai", "gemini", "nvidia", "nim")
    ):
        raise ConfigurationError(
            "Ollama/llama.cpp embeddings were removed — those servers are LLM-only now. "
            "Set EMBEDDING_PROVIDER=huggingface (local BGE, 384d) and re-upload "
            "documents to re-index existing knowledge bases.",
            detail=f"requested provider={active_provider} model={active_model}",
        )

    # ── Option 2: NVIDIA NIM Embeddings ─────────────────────────────────────────
    if active_provider in ("nvidia", "nim"):
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        if not settings.nvidia_api_key:
            raise ConfigurationError(
                "NVIDIA_API_KEY must be set when EMBEDDING_PROVIDER is 'nvidia'"
            )

        logger.info(
            "Initializing NVIDIA NIM embedding model",
            model=active_model,
        )
        try:
            return _wrap_with_cache(
                NVIDIAEmbeddings(
                    model=active_model,
                    api_key=settings.nvidia_api_key,
                    truncate="END",
                )
            )
        except Exception as exc:
            raise ConfigurationError(
                f"Failed to initialize NVIDIA embedding model '{active_model}'",
                detail=str(exc),
            ) from exc

    # ── Option 3: Google Gemini Embeddings (Cloud) ──────────────────────────────
    if active_provider in ("google_genai", "gemini"):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        logger.info(
            "Initializing Google Generative AI embedding model",
            model=active_model,
            dimensionality=cfg.embedding_dimensionality,
        )
        try:
            return _wrap_with_cache(
                GoogleGenerativeAIEmbeddings(
                    model=active_model,
                    google_api_key=settings.gemini_api_key,
                    output_dimensionality=cfg.embedding_dimensionality,
                )
            )
        except Exception as exc:
            raise ConfigurationError(
                f"Failed to initialize Google embedding model '{active_model}'",
                detail=str(exc),
            ) from exc

    # ── Option 4: Local Hugging Face Embeddings (Sentence-Transformers / BGE) ────
    from langchain_huggingface import HuggingFaceEmbeddings

    cache_dir = Path(cfg.embedding_cache_dir).resolve()

    logger.info(
        "Initializing local HuggingFace embedding model",
        model=active_model,
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

        from app.core.hardware import get_optimal_torch_device

        opt_device = get_optimal_torch_device()
        model_kwargs: dict[str, Any] = {"device": opt_device}
        if settings.hf_token:
            model_kwargs["token"] = settings.hf_token

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
        logger.warning("sentence-transformers not installed. Reranker disabled. Using Hybrid RRF.")
        return None

    logger.info("Initializing reranker", model=cfg.reranker_model)

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
    get_llm.cache_clear()
    get_verification_model.cache_clear()
    get_embedding_model.cache_clear()
    get_reranker.cache_clear()
    logger.info("Cleared all model registry caches")
