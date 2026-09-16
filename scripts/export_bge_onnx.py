#!/usr/bin/env python3
"""
Export BGE-small-en-v1.5 to ONNX format for ONNX Runtime inference.

This removes the need for PyTorch/sentence-transformers in the API process,
cutting ~500-1000 MB RSS (torch + tokenizer + model weights).

Usage:
    python scripts/export_bge_onnx.py
    # Outputs to apps/api/data/models/bge-small-en-v1.5.onnx
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import torch
from sentence_transformers import SentenceTransformer

# ─── Config ─────────────────────────────────────────────────────────────────────
MODEL_NAME = "BAAI/bge-small-en-v1.5"
OUTPUT_DIR = Path(__file__).parent.parent / "apps" / "api" / "data" / "models"
OUTPUT_PATH = OUTPUT_DIR / "bge-small-en-v1.5.onnx"
MAX_SEQ_LENGTH = 512
BATCH_SIZE = 1  # Dynamic batch axis


def export_bge_to_onnx() -> None:
    """Export BGE model to ONNX with dynamic batch size."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    model.max_seq_length = MAX_SEQ_LENGTH
    # Force CPU for ONNX export (MPS not supported by torch.export)
    model.to("cpu")
    model.eval()

    # Create dummy input for tracing
    dummy_input = ["This is a test sentence for ONNX export."] * BATCH_SIZE

    # Get the tokenizer and model components
    tokenizer = model.tokenizer
    # The first module is typically the transformer (BERT/RoBERTa)
    transformer = model[0].auto_model

    # Tokenize dummy input
    encoded = tokenizer(
        dummy_input,
        padding=True,
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        return_tensors="pt",
    )

    input_ids = encoded["input_ids"]
    attention_mask = encoded["attention_mask"]

    print(f"Input shapes: input_ids={input_ids.shape}, attention_mask={attention_mask.shape}")

    # Export to ONNX
    print(f"Exporting to {OUTPUT_PATH}...")

    # We need to export the full pipeline: tokenize -> transformer -> pooling -> normalize
    # For simplicity, export the transformer + pooling, handle tokenization in Python.
    # CRITICAL: BAAI/bge-small-en-v1.5 uses CLS pooling (Pooling pooling_mode="cls"),
    # NOT mean pooling. Exporting with mean pooling yields vectors at ~0.95 cosine
    # to the true space — rankings mostly survive but absolute similarities shift,
    # which corrupts thresholds and cross-provider cache keys. Match CLS exactly.

    class BGEOnnxWrapper(torch.nn.Module):
        """Wrapper that includes transformer + CLS pooling + normalization."""

        def __init__(self, transformer):
            super().__init__()
            self.transformer = transformer

        def forward(self, input_ids, attention_mask):
            outputs = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
            token_embeddings = outputs.last_hidden_state  # (batch, seq_len, hidden)

            # CLS pooling: first-token embedding (matches sentence-transformers
            # Pooling with pooling_mode="cls" for BGE models)
            embeddings = token_embeddings[:, 0]

            # L2 normalize (matches Normalize module)
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            return embeddings

    wrapper = BGEOnnxWrapper(transformer)
    wrapper.eval()

    # Dynamic axes for batch size AND sequence length
    dynamic_axes = {
        "input_ids": {0: "batch", 1: "sequence"},
        "attention_mask": {0: "batch", 1: "sequence"},
        "embeddings": {0: "batch"},
    }

    torch.onnx.export(
        wrapper,
        (input_ids, attention_mask),
        str(OUTPUT_PATH),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["input_ids", "attention_mask"],
        output_names=["embeddings"],
        dynamic_axes=dynamic_axes,
        verbose=False,
        # Keep all weights in the main ONNX file (no external .data file)
        external_data=False,
    )

    print(f"✅ Exported to {OUTPUT_PATH}")
    print(f"   File size: {OUTPUT_PATH.stat().st_size / (1024*1024):.1f} MB")

    # Verify the ONNX model
    print("Verifying ONNX model...")
    import onnx
    onnx_model = onnx.load(str(OUTPUT_PATH))
    onnx.checker.check_model(onnx_model)
    print("   ONNX model check passed!")

    # Test with ONNX Runtime
    print("Testing with ONNX Runtime...")
    import onnxruntime as ort

    session = ort.InferenceSession(str(OUTPUT_PATH), providers=["CPUExecutionProvider"])

    # Test encode
    test_inputs = ["Test query for ONNX Runtime", "Another test sentence"]
    encoded = tokenizer(
        test_inputs,
        padding=True,
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        return_tensors="np",
    )

    ort_inputs = {
        "input_ids": encoded["input_ids"],
        "attention_mask": encoded["attention_mask"],
    }

    ort_outputs = session.run(None, ort_inputs)
    embeddings = ort_outputs[0]

    print(f"   ONNX output shape: {embeddings.shape}")
    print(f"   Sample embedding (first 5 dims): {embeddings[0][:5]}")

    # Compare with original PyTorch model
    print("Comparing with PyTorch model...")
    with torch.no_grad():
        pt_outputs = wrapper(
            torch.from_numpy(encoded["input_ids"]),
            torch.from_numpy(encoded["attention_mask"]),
        )
        pt_embeddings = pt_outputs.numpy()

    diff = abs(embeddings - pt_embeddings).max()
    print(f"   Max difference vs PyTorch: {diff:.6f}")
    if diff < 1e-4:
        print("   ✅ Numerical parity verified!")
    else:
        print("   ⚠️  Difference exceeds threshold - check export")


if __name__ == "__main__":
    export_bge_to_onnx()