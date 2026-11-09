"""
TRUSTRAG — ONNX Runtime BGE embedding engine (pure inference).

Pure ONNX Runtime inference wrapper for BGE embedding models. Handles:
- Tokenization (HF tokenizer, minimal overhead, fast tokenizer)
- ONNX model inference (transformer + mean pooling + L2 norm)
- BGE instruction prefixing for queries

Replaces the engine half of the old flat ``onnx_embeddings.py``.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, cast

import numpy as np
import structlog

try:
    import onnxruntime as ort

    _ORT_AVAILABLE = True
except ImportError:  # pragma: no cover - environment dependent
    _ORT_AVAILABLE = False
    ort = None  # type: ignore


def _is_ort_available() -> bool:
    import sys

    shim = sys.modules.get("app.llm.onnx_embeddings")
    if shim is not None and hasattr(shim, "_ORT_AVAILABLE"):
        return bool(shim._ORT_AVAILABLE)
    return _ORT_AVAILABLE


def _get_ort() -> Any:
    import sys

    shim = sys.modules.get("app.llm.onnx_embeddings")
    if shim is not None and hasattr(shim, "ort") and shim.ort is not None:
        return shim.ort
    return ort

from langchain_core.embeddings import Embeddings

from app.config import get_model_config
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
_DEFAULT_TOKENIZER_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"


def _get_tokenizer_revision() -> str:
    """Get tokenizer revision from settings with fallback to environment variable."""
    from app.config.settings import get_settings

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
        if not _is_ort_available():
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
        self.session = _get_ort().InferenceSession(
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
        except Exception as exc:  # pragma: no cover - defensive
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
                self._query_instruction + t
                if not t.startswith(self._query_instruction)
                else t
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
        return cast(list[float], emb[0].astype(np.float32).tolist())

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document texts."""
        if not texts:
            return []
        emb = self._encode_batch(texts, is_query=False)
        return cast(list[list[float]], emb.astype(np.float32).tolist())

    async def aembed_query(self, text: str) -> list[float]:
        """Async embed query (runs in thread pool)."""
        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Async embed documents (runs in thread pool)."""
        return await asyncio.to_thread(self.embed_documents, texts)
