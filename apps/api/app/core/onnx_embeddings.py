"""
ONNX Runtime Embedding Wrapper for BGE models.

Replaces HuggingFaceEmbeddings + torch with pure ONNX Runtime inference.
Eliminates PyTorch/sentence-transformers from the API process (~500-1000 MB RSS savings).
"""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

try:
    import onnxruntime as ort

    _ORT_AVAILABLE = True
except ImportError:
    _ORT_AVAILABLE = False
    ort = None  # type: ignore

from langchain_core.embeddings import Embeddings


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
        tokenizer_name: str = "BAAI/bge-small-en-v1.5",
        max_seq_length: int = 512,
        providers: list[str] | None = None,
    ) -> None:
        if not _ORT_AVAILABLE:
            raise ImportError(
                "onnxruntime is required for ONNXBGEEmbeddings. "
                "Install with: pip install onnxruntime"
            )

        self.model_path = model_path
        self.max_seq_length = max_seq_length

        # Load tokenizer (lightweight, no torch)
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

        # Load ONNX model
        if providers is None:
            providers = ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(model_path, providers=providers)

        # Verify input/output names
        self.input_names = [i.name for i in self.session.get_inputs()]
        self.output_names = [o.name for o in self.session.get_outputs()]

        # BGE query instruction
        self._is_bge = "bge" in tokenizer_name.lower()
        self._query_instruction = "Represent this sentence for searching relevant passages: "

    def _encode_batch(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        """Encode a batch of texts to embeddings."""
        if is_query and self._is_bge:
            texts = [
                self._query_instruction + t if not t.startswith(self._query_instruction) else t
                for t in texts
            ]

        # Tokenize
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_seq_length,
            return_tensors="np",
        )

        # Run ONNX inference
        ort_inputs = {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
        }
        ort_outputs = self.session.run(self.output_names, ort_inputs)
        embeddings = ort_outputs[0]  # Already L2 normalized by the model

        return embeddings

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
        import asyncio

        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Async embed documents (runs in thread pool)."""
        import asyncio

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
        model_name: str = "onnx::bge-small-en-v1.5",
    ) -> None:
        self._base = onnx_embeddings
        import threading
        from collections import OrderedDict

        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._mem_lock = threading.RLock()
        self._max_size = max_cache_size
        self._model_name = model_name

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

        # Batch write to disk cache
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

        # Batch write to disk cache
        await asyncio.to_thread(
            set_cached_embeddings_batch, missing_texts, self._model_name, computed_vectors
        )

        for i, idx in enumerate(missing_indices):
            vec = computed_vectors[i]
            cached_map[idx] = vec
            self._store_mem(texts[idx], vec)

        return [cached_map[i] for i in range(len(texts))]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)
