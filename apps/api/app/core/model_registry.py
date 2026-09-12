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

# ─── Bounded LLM Registry (replaces lru_cache on get_llm/get_verification_model) ────
# Limits concurrent model instances to prevent RAM/GPU leak from user-controlled keys.
_MAX_LLM_INSTANCES = 4
_LLM_REGISTRY: OrderedDict[str, "BaseChatModel"] = OrderedDict()
_LLM_REGISTRY_LOCK = threading.RLock()
_LLM_REGISTRY_CLOSED = False


def _llm_registry_key(provider: str, model: str | None) -> str:
    return f"{provider}:{model or 'default'}"


def _close_llm_instance(llm: "BaseChatModel") -> None:
    """Best-effort close for LLM instances that support it."""
    try:
        # ChatOllamaClient and ChatLlamaCppClient may have close methods
        if hasattr(llm, "close"):
            llm.close()
        elif hasattr(llm, "aclose"):
            # Can't await in sync context; log and skip
            logger.debug("LLM instance has async close; skipping sync close")
    except Exception as exc:
        logger.debug("Error closing LLM instance", error=str(exc))


def get_llm_instance(provider: str, model: str | None) -> "BaseChatModel | None":
    """Get existing LLM instance from registry (no creation)."""
    key = _llm_registry_key(provider, model)
    with _LLM_REGISTRY_LOCK:
        if key in _LLM_REGISTRY:
            # LRU: move to end
            _LLM_REGISTRY.move_to_end(key)
            return _LLM_REGISTRY[key]
    return None


def put_llm_instance(provider: str, model: str | None, llm: "BaseChatModel") -> None:
    """Put LLM instance into bounded registry with LRU eviction."""
    global _LLM_REGISTRY_CLOSED
    if _LLM_REGISTRY_CLOSED:
        # If registry is closed, close the new instance immediately
        _close_llm_instance(llm)
        return

    key = _llm_registry_key(provider, model)
    with _LLM_REGISTRY_LOCK:
        # Evict LRU if at capacity
        if len(_LLM_REGISTRY) >= _MAX_LLM_INSTANCES and key not in _LLM_REGISTRY:
            evicted_key, evicted_llm = _LLM_REGISTRY.popitem(last=False)
            _close_llm_instance(evicted_llm)
            logger.debug("Evicted LLM from registry", evicted=evicted_key)

        _LLM_REGISTRY[key] = llm
        _LLM_REGISTRY.move_to_end(key)


def close_all_llm_instances() -> None:
    """Close all LLM instances and prevent new registrations."""
    global _LLM_REGISTRY_CLOSED
    with _LLM_REGISTRY_LOCK:
        _LLM_REGISTRY_CLOSED = True
        for llm in _LLM_REGISTRY.values():
            _close_llm_instance(llm)
        _LLM_REGISTRY.clear()
        logger.info("Closed all LLM instances and sealed registry")


# ─── Generation-scoped LLM Response Cache (TTL + bounded) ───────────────────────────
# Replaces global unbounded InMemoryCache. Scoped to generation calls only,
# keyed on (query_hash, chunk_hash) with TTL to prevent NLI-prompt bloat.
_GEN_CACHE: OrderedDict[str, tuple[float, Any]] = OrderedDict()  # key -> (expires_at, value)
_GEN_CACHE_LOCK = threading.RLock()
_GEN_CACHE_MAX_SIZE = 256
_GEN_CACHE_TTL_SECONDS = 300  # 5 minutes


def _gen_cache_key(query: str, chunk_hash: str) -> str:
    import hashlib
    return hashlib.sha256(f"{query}:{chunk_hash}".encode()).hexdigest()[:32]


def gen_cache_get(query: str, chunk_hash: str) -> Any | None:
    """Get cached generation result if not expired."""
    key = _gen_cache_key(query, chunk_hash)
    now = time.time()
    with _GEN_CACHE_LOCK:
        entry = _GEN_CACHE.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if now > expires_at:
            _GEN_CACHE.pop(key, None)
            return None
        _GEN_CACHE.move_to_end(key)
        return value


def gen_cache_set(query: str, chunk_hash: str, value: Any) -> None:
    """Set generation result in cache with TTL."""
    key = _gen_cache_key(query, chunk_hash)
    now = time.time()
    with _GEN_CACHE_LOCK:
        # Evict LRU if at capacity
        if len(_GEN_CACHE) >= _GEN_CACHE_MAX_SIZE and key not in _GEN_CACHE:
            _GEN_CACHE.popitem(last=False)
        _GEN_CACHE[key] = (now + _GEN_CACHE_TTL_SECONDS, value)
        _GEN_CACHE.move_to_end(key)


def gen_cache_clear() -> None:
    """Clear generation cache."""
    with _GEN_CACHE_LOCK:
        _GEN_CACHE.clear()


# ─── LLM Response Cache (legacy global — kept for backward compat, but gen-only now) ───
_llm_cache_enabled = False


def _enable_llm_cache() -> None:
    """Set up LangChain in-memory cache for LLM responses (idempotent).
    NOTE: This global cache is now deprecated in favor of gen_cache_get/set
    which scopes to generation calls only. Kept for any legacy callers.
    """
    global _llm_cache_enabled
    if _llm_cache_enabled:
        return
    try:
        import langchain
        from langchain_core.caches import InMemoryCache

        # Use a bounded wrapper instead of raw InMemoryCache
        class BoundedCache(InMemoryCache):
            def __init__(self):
                super().__init__()
                self._cache = OrderedDict()
                self._max_size = 512

            def update(self, prompt: str, llm_string: str, return_val: list) -> None:
                key = f"{prompt}:{llm_string}"
                with _GEN_CACHE_LOCK:  # Reuse the same lock
                    if len(self._cache) >= self._max_size:
                        self._cache.popitem(last=False)
                    self._cache[key] = return_val
                    self._cache.move_to_end(key)

            def lookup(self, prompt: str, llm_string: str) -> list | None:
                key = f"{prompt}:{llm_string}"
                return self._cache.get(key)

        langchain.llm_cache = BoundedCache()
        _llm_cache_enabled = True
        logger.info("LLM response cache enabled (BoundedCache, generation-scoped)")
    except Exception as exc:
        logger.debug("Could not enable LLM cache", error=str(exc))


# ─── LLM ─────────────────────────────────────────────────────────────────────


def get_llm(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """
    Return the primary LLM for answer generation.

    Supports:
      - ollama: ChatOllamaClient (local, zero cloud keys)
      - llama_cpp / llamacpp: ChatLlamaCppClient (local, OpenAI-compatible server)
      - gemini: ChatGoogleGenerativeAI via langchain-google-genai
      - nvidia: ChatNVIDIA via langchain-nvidia-ai-endpoints

    Uses bounded registry (max 4 instances) with LRU eviction to prevent
    RAM/GPU leak from user-controlled model strings.
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
            put_llm_instance(active_provider, active_model, llm)
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
            put_llm_instance(active_provider, active_model, llm)
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
            put_llm_instance(active_provider, active_model, llm)
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
        put_llm_instance(active_provider, active_model, llm)
        return llm
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to initialize LLM '{active_model}' (provider: {active_provider})",
            detail=str(exc),
        ) from exc


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
    else:
        active_model = model or cfg.verification_model

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

        if active_provider in ("nvidia", "nim"):
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            if not settings.nvidia_api_key:
                raise ConfigurationError("NVIDIA_API_KEY must be set when AI_PROVIDER is 'nvidia'")

            llm = ChatNVIDIA(
                model=active_model,
                api_key=settings.nvidia_api_key,
                temperature=0.0,
                max_tokens=cfg.verification_max_output_tokens,
                timeout=cfg.verification_timeout_seconds,
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
            max_retries=cfg.llm_max_retries,
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
        api_base = Path(__file__).parent.parent.parent
        cache_dir = (api_base / cfg.embedding_cache_dir).resolve()
        onnx_model_path = cache_dir / "bge-small-en-v1.5.onnx"
        if not onnx_model_path.exists():
            raise ConfigurationError(
                f"ONNX model not found at {onnx_model_path}. "
                "Run 'python scripts/export_bge_onnx.py' to export the model.",
            )

        logger.info(
            "Initializing ONNX Runtime BGE embedding model",
            model=active_model,
            onnx_path=str(onnx_model_path),
        )

        base_emb = ONNXBGEEmbeddings(
            model_path=str(onnx_model_path),
            tokenizer_name=active_model,
            max_seq_length=cfg.embedding_max_seq_length if hasattr(cfg, 'embedding_max_seq_length') else 512,
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
    get_embedding_model.cache_clear()
    get_reranker.cache_clear()
    # Clear new bounded registry and generation cache
    close_all_llm_instances()
    gen_cache_clear()
    logger.info("Cleared all model registry caches")
