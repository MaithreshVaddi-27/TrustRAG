"""
TRUSTRAG — ONNX Runtime CrossEncoder for fast CPU inference.

Provides ONNX-accelerated cross-encoder reranking with int8 quantization
for 3-4x speedup over PyTorch on CPU, fully torch-free.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
import onnxruntime as ort

from app.core.config import get_model_config, get_settings
from app.core.onnx_runtime import build_session_options

logger = logging.getLogger(__name__)


class ONNXCrossEncoder:
    """
    ONNX Runtime CrossEncoder wrapper matching sentence-transformers CrossEncoder API.

    Supports int8 quantized models for ultra-fast CPU inference.
    """

    def __init__(
        self,
        model_path: str,
        tokenizer_name: str | None = None,
        max_seq_length: int | None = None,
    ):
        """
        Initialize ONNX CrossEncoder.

        Args:
            model_path: Path to ONNX model file
            tokenizer_name: HuggingFace tokenizer name (for tokenization)
            max_seq_length: Maximum sequence length for tokenization
        """
        # Single source of truth: models.yaml reranker.model / max_seq_length.
        # Explicit args still win (tests, exports); otherwise config propagates.
        if tokenizer_name is None or max_seq_length is None:
            try:
                _cfg = get_model_config()
                if tokenizer_name is None:
                    tokenizer_name = _cfg.reranker_model
                if max_seq_length is None:
                    try:
                        max_seq_length = _cfg.reranker_max_seq_length
                    except Exception as exc:
                        logger.debug("Reranker seq-len fell back to 512", error=str(exc))
                        max_seq_length = 512
            except Exception as exc:
                logger.debug("Reranker defaults fell back to built-ins", error=str(exc))
        self.model_path = model_path
        self.tokenizer_name = tokenizer_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.max_seq_length = int(max_seq_length or 512)
        self._session = None
        self._tokenizer = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize ONNX session and tokenizer."""
        # Shared session factory (central `onnx:` config in models.yaml —
        # capped at 4 threads so the reranker never oversubscribes against
        # embeddings + llama-server + uvicorn workers). Same effective
        # defaults as the previous inline block.
        sess_options = build_session_options()

        # Providers from central config (default CPU-only for flat RAM).
        try:
            providers = get_model_config().onnx_providers
        except Exception:
            providers = ["CPUExecutionProvider"]

        logger.info("Loading ONNX reranker model", path=self.model_path, providers=providers)
        self._session = ort.InferenceSession(
            self.model_path,
            sess_options=sess_options,
            providers=providers,
        )

        # Load tokenizer — prefer local cache when offline (HF_HUB_OFFLINE=1
        # set in app/main.py); otherwise allow download on first cold start.
        # Revision pinned for supply-chain security (Bandit B615).
        # NOTE: AutoTokenizer stays a lazy import — tests patch
        # transformers.AutoTokenizer.from_pretrained at its source.
        try:
            from transformers import AutoTokenizer

            settings = get_settings()
            _offline = os.environ.get("HF_HUB_OFFLINE", "").strip() == "1"
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.tokenizer_name,
                revision=settings.hf_tokenizer_revision,
                use_fast=True,
                local_files_only=_offline,
            )
            logger.debug("Loaded tokenizer", name=self.tokenizer_name)
        except Exception as exc:
            logger.warning("Failed to load tokenizer, using fallback", error=str(exc))
            raise

    def predict(
        self, pairs: list[tuple[str, str]], batch_size: int | None = None, **kwargs
    ) -> np.ndarray:
        """
        Predict relevance scores for query-document pairs.

        Args:
            pairs: List of (query, document) tuples
            batch_size: Batch size for inference (handled internally)

        Returns:
            Array of relevance scores (one per pair)
        """
        if not pairs:
            return np.array([], dtype=np.float32)

        # Batch loop: tokenizing + inferring all pairs at once spikes RAM and
        # latency (20 candidates x fan-out 3). Resolution: explicit arg >
        # RERANKER_BATCH_SIZE env > models.yaml reranker.batch_size > 16
        # (single property: cfg.reranker_batch_size_effective).
        # Lean tier (≤8 GB) is capped to 8 to bound peak RSS.
        _cfg_batch = 16
        try:
            _cfg_batch = int(get_model_config().reranker_batch_size_effective or 16)
        except Exception as exc:
            logger.debug("Reranker batch fell back to 16", error=str(exc))
        try:
            _lean = (os.getenv("TRUSTRAG_TIER", "").strip().lower() == "lean") or int(
                os.getenv("OMP_NUM_THREADS", "4")
            ) <= 2
        except ValueError:
            _lean = False
        if _lean:
            _cfg_batch = min(_cfg_batch, 8)
        _env_batch = os.environ.get("RERANKER_BATCH_SIZE", str(_cfg_batch)) or _cfg_batch
        effective_batch = int(batch_size or int(_env_batch or 16) or 16)
        session_inputs = {i.name for i in self._session.get_inputs()}
        all_scores: list[np.ndarray] = []
        for start in range(0, len(pairs), effective_batch):
            batch = pairs[start : start + effective_batch]
            queries = [p[0] for p in batch]
            docs = [p[1] for p in batch]

            # Tokenize with CrossEncoder format: [CLS] query [SEP] doc [SEP]
            encoded = self._tokenizer(
                queries,
                docs,
                padding=True,
                truncation="longest_first",
                max_length=self.max_seq_length,
                return_tensors="np",
            )

            # Run ONNX inference — feed only the inputs the exported graph expects
            # (token_type_ids exists only when the export included it).
            inputs: dict[str, np.ndarray] = {}
            if "input_ids" in session_inputs:
                inputs["input_ids"] = encoded["input_ids"].astype(np.int64)
            if "attention_mask" in session_inputs:
                inputs["attention_mask"] = encoded["attention_mask"].astype(np.int64)
            if "token_type_ids" in session_inputs and "token_type_ids" in encoded:
                inputs["token_type_ids"] = encoded["token_type_ids"].astype(np.int64)

            outputs = self._session.run(None, inputs)

            # Extract logits/scores (typically first output)
            logits = outputs[0]

            # CrossEncoder typically outputs single logit per pair
            if logits.ndim == 2 and logits.shape[1] == 1:
                scores = logits[:, 0]
            elif logits.ndim == 1:
                scores = logits
            else:
                # For classification heads, take the positive class (usually index 1)
                scores = logits[:, 1] if logits.shape[1] > 1 else logits[:, 0]
            all_scores.append(scores.astype(np.float32))

        return (
            np.concatenate(all_scores).astype(np.float32)
            if all_scores
            else np.array([], dtype=np.float32)
        )

    def __call__(self, *args: Any, **kwargs: Any) -> np.ndarray:
        """Allow calling like a function."""
        return self.predict(*args, **kwargs)


def export_crossencoder_to_onnx(
    model: Any,
    output_path: str,
    tokenizer_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    max_seq_length: int = 512,
    opset_version: int = 17,
    quantize_int8: bool = True,
) -> None:
    """
    Export a sentence-transformers CrossEncoder to ONNX format with optional int8 quantization.

    Args:
        model: sentence-transformers CrossEncoder instance
        output_path: Path to save ONNX model
        tokenizer_name: Tokenizer name for export
        max_seq_length: Maximum sequence length
        opset_version: ONNX opset version
        quantize_int8: Whether to apply int8 quantization
    """
    import torch
    from transformers import AutoTokenizer

    logger.info("Exporting CrossEncoder to ONNX", output_path=output_path, quantize=quantize_int8)

    # Prepare model for export — trace the inner HF module, not the
    # sentence-transformers wrapper (which has no (input_ids, attention_mask)
    # forward). CrossEncoder stores it as `.model`.
    inner = getattr(model, "model", model)
    inner.eval()
    inner.to("cpu")

    # Get tokenizer for dummy input (revision pinned for supply-chain security, Bandit B615)
    settings = get_settings()
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_name, use_fast=True, revision=settings.hf_tokenizer_revision
    )

    # Create dummy inputs
    dummy_queries = ["What is the capital of France?"]
    dummy_docs = ["Paris is the capital of France."]

    encoded = tokenizer(
        dummy_queries,
        dummy_docs,
        padding="max_length",
        truncation=True,
        max_length=max_seq_length,
        return_tensors="pt",
    )

    # Export to ONNX — include token_type_ids so graphs for BERT-style
    # encoders match what predict() feeds at inference time.
    dummy_inputs = (encoded["input_ids"], encoded["attention_mask"], encoded["token_type_ids"])
    torch.onnx.export(
        inner,
        dummy_inputs,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input_ids", "attention_mask", "token_type_ids"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "sequence_length"},
            "attention_mask": {0: "batch_size", 1: "sequence_length"},
            "token_type_ids": {0: "batch_size", 1: "sequence_length"},
            "logits": {0: "batch_size"},
        },
    )

    logger.info("Base ONNX export complete", path=output_path)

    if quantize_int8:
        try:
            from onnxruntime.quantization import QuantType, quantize_dynamic

            quantized_path = output_path.replace(".onnx", "_int8.onnx")
            quantize_dynamic(
                output_path,
                quantized_path,
                weight_type=QuantType.QInt8,
                optimize_model=True,
                per_channel=False,
                reduce_range=False,
            )

            # Replace original with quantized version
            import shutil

            shutil.move(quantized_path, output_path)
            logger.info("Int8 quantization complete", path=output_path)
        except Exception as exc:
            logger.warning("Int8 quantization failed, keeping FP32 model", error=str(exc))

    logger.info("ONNX export complete", path=output_path)
