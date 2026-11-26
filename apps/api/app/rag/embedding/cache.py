"""
TRUSTRAG — ONNX BGE embedding cache wrapper.

An in-memory LRU cache around the ONNX BGE embedding engine. A cached
embedding is returned without touching ONNX Runtime, which turns a ~4.6 ms
cold embed into a ~0.0 ms lookup.

The cache is **process-local and RAM-bounded**: it does not survive a restart
and it is not shared between workers. (An earlier revision of this docstring
claimed a second, persistent SQLite tier — no such tier was ever
implemented, and this wrapper has never contained any SQLite code.)

Query and document embeddings of the same string are different vectors
(the BGE query instruction is prepended only for queries), so they are
namespaced by mode as well as text.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from langchain_core.embeddings import Embeddings

from app.config import get_model_config
from app.rag.embedding.engine import (
    EMBEDDING_MODE_DOCUMENT,
    EMBEDDING_MODE_QUERY,
    ONNXBGEEmbeddings,
)

__all__ = ["ONNXBGEEmbeddingsWrapper"]


class ONNXBGEEmbeddingsWrapper(Embeddings):
    """
    In-memory LRU cache wrapper for ONNX BGE embeddings.

    Capacity comes from ``retrieval.query_cache_capacity`` in models.yaml
    (env override: ``RETRIEVAL_QUERY_CACHE_CAPACITY``); the cache is
    process-local and does not survive a restart.
    """

    def __init__(
        self,
        onnx_embeddings: ONNXBGEEmbeddings,
        max_cache_size: int | None = None,
        model_name: str | None = None,
    ) -> None:
        self._base = onnx_embeddings
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._mem_lock = threading.RLock()
        if max_cache_size is None:
            try:
                max_cache_size = get_model_config().query_cache_capacity
            except Exception:
                max_cache_size = 512
        self._max_size = max(1, int(max_cache_size))
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
