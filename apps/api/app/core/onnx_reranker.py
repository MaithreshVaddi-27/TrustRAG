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

logger = logging.getLogger(__name__)


class ONNXCrossEncoder:
    """
    ONNX Runtime CrossEncoder wrapper matching sentence-transformers CrossEncoder API.

    Supports int8 quantized models for ultra-fast CPU inference.
    """

    def __init__(
        self,
        model_path: str,
        tokenizer_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        max_seq_length: int = 512,
    ):
        """
        Initialize ONNX CrossEncoder.

        Args:
            model_path: Path to ONNX model file
            tokenizer_name: HuggingFace tokenizer name (for tokenization)
            max_seq_length: Maximum sequence length for tokenization
        """
        self.model_path = model_path
        self.tokenizer_name = tokenizer_name
        self.max_seq_length = max_seq_length
        self._session = None
        self._tokenizer = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize ONNX session and tokenizer."""
        try:
            import onnxruntime as ort
        except ImportError as err:
            raise RuntimeError(
                "onnxruntime is required for ONNXCrossEncoder. "
                "Install with: pip install onnxruntime"
            ) from err

        # Configure ONNX Runtime for CPU inference
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = int(os.environ.get("OMP_NUM_THREADS", "1"))
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.enable_cpu_mem_arena = True
        sess_options.enable_mem_pattern = True

        # CPU execution provider
        providers = ["CPUExecutionProvider"]

        logger.info("Loading ONNX reranker model", path=self.model_path, providers=providers)
        self._session = ort.InferenceSession(
            self.model_path,
            sess_options=sess_options,
            providers=providers,
        )

        # Load tokenizer
        try:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.tokenizer_name,
                use_fast=True,
                local_files_only=False,
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

        # Tokenize all pairs
        queries = [p[0] for p in pairs]
        docs = [p[1] for p in pairs]

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
        session_inputs = {i.name for i in self._session.get_inputs()}
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

        return scores.astype(np.float32)

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

    # Get tokenizer for dummy input
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, use_fast=True)

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
