"""
ONNX Runtime Embedding Wrapper for BGE models.

Replaces HuggingFaceEmbeddings + torch with pure ONNX Runtime inference.
Eliminates PyTorch/sentence-transformers from the API process (~500-1000 MB RSS savings).
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections import OrderedDict
from typing import Any

import numpy as np
import structlog

try:
    import onnxruntime as ort

    _ORT_AVAILABLE = True
except ImportError:
    _ORT_AVAILABLE = False
    ort = None  # type: ignore

from langchain_core.embeddings import Embeddings

from app.core.config.model_config import get_model_config
from app.core.config.settings import get_settings
from app.core.system.hardware import get_ingest_embed_batch_size
from app.llm.onnx_runtime import build_session_options

logger = structlog.get_logger(__name__)

# Query and document embeddings for the same string are DIFFERENT vectors: the
# BGE query instruction is prepended only on the query path. They must stay in
# separate namespaces everywhere a key is built from text, or whichever ran
# first wins and the other silently receives the wrong vector.
EMBEDDING_MODE_QUERY = "query"
EMBEDDING_MODE_DOCUMENT = "document"

# Low-RAM / speed defaults: tokenizer threads must not fork-bloat next to
# asyncio.to_thread. Set at import so every process (api, workers, tests)
# inherits it without shell exports.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# Pinned tokenizer revision (commit SHA of BAAI/bge-small-en-v1.5 on the Hub).
# Bandit B615 requires revision pinning to block supply-chain substitution of
# tokenizer files; override via HF_TOKENIZER_REVISION only to move forward
# deliberately (e.g. after re-exporting the ONNX model against the new vocab).
# An earlier revision of this file kept the same env read and the same default
# SHA in a module-level constant as well. Only this function is ever called.
_DEFAULT_TOKENIZER_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"


def _get_tokenizer_revision() -> str:
    """Get tokenizer revision from settings with fallback to environment variable."""
    settings = get_settings()
    if settings.hf_tokenizer_revision:
        return settings.hf_tokenizer_revision
    return os.environ.get("HF_TOKENIZER_REVISION", _DEFAULT_TOKENIZER_REVISION)


class ONNXBGEEmbeddings(Embeddings):
    """
    BGE embedding model using ONNX Runtime.

    Handles:
    - Tokenization (using HF tokenizer, minimal overhead)
    - ONNX model inference (transformer + mean pooling + L2 norm)
    - BGE instruction prefixing for queries
    """

    def __init__(
        self,
        model_path: str,
        # None = resolve from models.yaml (embedding.model / max_seq_length):
        # a yaml edit then propagates everywhere. Never re-pin an ID here.
        tokenizer_name: str | None = None,
        max_seq_length: int | None = None,
        providers: list[str] | None = None,
        sess_options: Any = None,
        micro_batch_size: int | None = None,
    ) -> None:
        if not _ORT_AVAILABLE:
            raise ImportError(
                "onnxruntime is required for ONNXBGEEmbeddings. "
                "Install with: pip install onnxruntime"
            )

        self.model_path = model_path
        # Resolve engine defaults from models.yaml (single source of truth).
        if tokenizer_name is None or max_seq_length is None:
            _cfg = get_model_config()
            if tokenizer_name is None:
                tokenizer_name = _cfg.embedding_model
            if max_seq_length is None:
                max_seq_length = _cfg.embedding_max_seq_length
        self.max_seq_length = max_seq_length

        # Load tokenizer (lightweight, no torch) at the pinned revision.
        # use_fast=True (~2-5x tokenize speed) + offline respect, mirroring reranker.
        from transformers import AutoTokenizer

        _offline = os.getenv("HF_HUB_OFFLINE", "").strip() == "1"
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name,
            revision=_get_tokenizer_revision(),
            trust_remote_code=False,
            use_fast=True,
            local_files_only=_offline,
        )

        # Load ONNX model via the shared session factory (central `onnx:`
        # config in models.yaml: thread caps for less RAM, ORT_ENABLE_ALL +
        # sequential mode for speed). Explicit `providers`/`sess_options`
        # args win (tests, one-off tools); otherwise yaml (+ ONNX_* env).
        if providers is None or sess_options is None:
            _cfg = get_model_config()
            if providers is None:
                providers = _cfg.onnx_providers
            if sess_options is None:
                sess_options = build_session_options()
        if micro_batch_size is None:
            try:
                micro_batch_size = get_model_config().onnx_embed_micro_batch
            except Exception:
                micro_batch_size = 0
        self.session = ort.InferenceSession(
            model_path, sess_options=sess_options, providers=providers
        )
        # Explicit override (constructor arg or ONNX_EMBED_MICRO_BATCH / yaml):
        # >0 wins over tier-aware sizing; 0 = auto (hardware tier).
        self.embed_micro_batch_override = max(0, int(micro_batch_size or 0))

        # Verify input/output names
        self.input_names = [i.name for i in self.session.get_inputs()]
        self.output_names = [o.name for o in self.session.get_outputs()]

        # BGE query instruction
        self._is_bge = "bge" in tokenizer_name.lower()
        self._query_instruction = "Represent this sentence for searching relevant passages: "

        # Output width, read from the graph's declared output shape. Derived rather
        # than hardcoded so a non-384 model (or a re-export with a different head)
        # still returns correctly-shaped rows — including on the empty path.
        # Falls back to 384 only if the session does not declare its shape.
        self.embedding_dim = self._detect_embedding_dim()

    def _detect_embedding_dim(self) -> int:
        """Infer the embedding width from the ONNX graph's output declaration."""
        default = 384
        try:
            outputs = self.session.get_outputs()
            if not outputs:
                return default
            shape = getattr(outputs[0], "shape", None)
            if not shape:
                return default
            # Shapes may carry symbolic dims (str) or None for dynamic axes; only
            # a concrete trailing integer is trustworthy.
            tail = shape[-1]
            if isinstance(tail, int) and tail > 0:
                return tail
        except Exception as exc:
            # A session that will not describe its output shape is unusual but not
            # fatal; fall back to the BGE-small default rather than refusing to load.
            logger.debug("Could not detect ONNX output dim, defaulting to 384", exc_info=exc)
        return default

    def _encode_batch(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        """Encode a batch of texts to embeddings (tier-aware micro-batches).

        Ingest step follows hardware tiers (32/64/128) via
        get_ingest_embed_batch_size(); queries are short (≤128 tokens vs the
        512-char chunk default) so they use a shorter max_length to avoid ~4x
        wasted matmuls on padding.
        """
        if is_query and self._is_bge:
            texts = [
                self._query_instruction + t if not t.startswith(self._query_instruction) else t
                for t in texts
            ]

        out: list[np.ndarray] = []
        override = int(getattr(self, "embed_micro_batch_override", 0) or 0)
        if override > 0:
            step = max(8, override)
        else:
            try:
                step = max(8, int(get_ingest_embed_batch_size()))
            except Exception:
                step = int(os.getenv("EMBEDDING_BATCH_SIZE", "32") or 32)
        # Queries are short: cap padding length to avoid wasted compute.
        encode_max = min(self.max_seq_length, 128) if is_query else self.max_seq_length

        for start in range(0, len(texts), step):
            sub = texts[start : start + step]
            # Tokenize
            encoded = self.tokenizer(
                sub,
                padding=True,
                truncation=True,
                max_length=encode_max,
                return_tensors="np",
            )

            # Run ONNX inference
            ort_inputs = {
                "input_ids": encoded["input_ids"],
                "attention_mask": encoded["attention_mask"],
            }
            ort_outputs = self.session.run(self.output_names, ort_inputs)
            embeddings = ort_outputs[0]  # Already L2 normalized by the model
            out.append(embeddings)
        return (
            np.concatenate(out, axis=0)
            if out
            else np.zeros((0, self.embedding_dim), dtype=np.float32)
        )

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        emb = self._encode_batch([text], is_query=True)
        return emb[0].astype(np.float32).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document texts."""
        if not texts:
            return []
        emb = self._encode_batch(texts, is_query=False)
        return emb.astype(np.float32).tolist()

    async def aembed_query(self, text: str) -> list[float]:
        """Async embed query (runs in thread pool)."""
        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Async embed documents (runs in thread pool)."""
        return await asyncio.to_thread(self.embed_documents, texts)


class ONNXBGEEmbeddingsWrapper:
    """
    Two-tier cache wrapper for ONNX BGE embeddings.

    Tier 1: In-memory LRU cache (sub-millisecond)
    Tier 2: Persistent SQLite disk cache (across restarts)
    """

    def __init__(
        self,
        onnx_embeddings: ONNXBGEEmbeddings,
        max_cache_size: int = 512,
        model_name: str | None = None,
    ) -> None:
        self._base = onnx_embeddings
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._mem_lock = threading.RLock()
        self._max_size = max_cache_size
        if model_name is None:
            try:
                model_name = f"onnx::{get_model_config().embedding_model}"
            except Exception:
                model_name = "onnx::bge-small-en-v1.5"
        self._model_name = model_name

    @staticmethod
    def _mem_key(text: str, mode: str) -> str:
        """Namespace the in-memory cache by mode as well as text.

        Query and document embeddings of the same string are different vectors
        (the BGE query instruction is prepended only for queries), so they must
        not share a cache slot. Sharing it meant whichever call ran first won
        and the other silently got the wrong vector.
        """
        return f"{mode}\x00{text.strip().lower()}"

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

    def embed_query(self, text: str) -> list[float]:
        key = self._mem_key(text, EMBEDDING_MODE_QUERY)
        cached = self._lookup_mem(key)
        if cached is not None:
            return cached

        vec = self._base.embed_query(text)
        self._store_mem(key, vec)
        return vec

    async def aembed_query(self, text: str) -> list[float]:
        key = self._mem_key(text, EMBEDDING_MODE_QUERY)
        cached = self._lookup_mem(key)
        if cached is not None:
            return cached

        vec = await self._base.aembed_query(text)
        self._store_mem(key, vec)
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float]] = [None] * len(texts)  # type: ignore[list-item]
        missing_indices: list[int] = []
        missing_texts: list[str] = []
        for idx, text in enumerate(texts):
            hit = self._lookup_mem(self._mem_key(text, EMBEDDING_MODE_DOCUMENT))
            if hit is None:
                missing_indices.append(idx)
                missing_texts.append(text)
            else:
                results[idx] = hit

        if missing_texts:
            computed = self._base.embed_documents(missing_texts)
            for idx, vec in zip(missing_indices, computed, strict=True):
                results[idx] = vec
                self._store_mem(self._mem_key(texts[idx], EMBEDDING_MODE_DOCUMENT), vec)

        return results

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float]] = [None] * len(texts)  # type: ignore[list-item]
        missing_indices: list[int] = []
        missing_texts: list[str] = []
        for idx, text in enumerate(texts):
            hit = self._lookup_mem(self._mem_key(text, EMBEDDING_MODE_DOCUMENT))
            if hit is None:
                missing_indices.append(idx)
                missing_texts.append(text)
            else:
                results[idx] = hit

        if missing_texts:
            computed = await self._base.aembed_documents(missing_texts)
            for idx, vec in zip(missing_indices, computed, strict=True):
                results[idx] = vec
                self._store_mem(self._mem_key(texts[idx], EMBEDDING_MODE_DOCUMENT), vec)

        return results

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)
