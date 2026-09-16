#!/usr/bin/env python3
"""
Evaluate embedding parity between the torch (huggingface) and ONNX providers.

Compares, over a set of representative query/document texts:
  1. Mean cosine similarity between torch and ONNX vectors (≈1.0 expected).
  2. Max absolute element difference (export fidelity check).
  3. Retrieval-rank overlap: for each query, rank the documents by cosine
     similarity under each provider and report top-1 agreement + mean
     reciprocal-rank displacement.

Usage:
    cd apps/api && .venv/bin/python ../../scripts/eval_embedding_parity.py

Requires torch stack (sentence-transformers) AND apps/api/.model_cache/
bge-small-en-v1.5.onnx to both be present.

Exit 0 with PARITY OK when mean cosine >= 0.999 and top-1 agreement is
perfect; exit 1 otherwise.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import numpy as np

API_DIR = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(API_DIR))

SAMPLES = [
    "Annual contract customers can get a full refund within 30 days.",
    "Monthly subscriptions can be canceled anytime with immediate effect.",
    "Data backups are retained for 90 days after deactivation.",
    "What is the refund policy for annual contracts?",
    "Describe the knowledge base and its contents.",
    "Pattern recognition identifies structures or anomalies in data.",
    "Effective from 2026-01-01 until 2026-12-31.",
    "Classification assigns items to predefined categories.",
]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


async def main() -> int:
    from app.core.model_registry import get_embedding_model

    # Purge stale ONNX rows first: the disk cache is keyed by text+model, so a
    # re-exported .onnx file would otherwise compare torch against CACHED
    # (previous-export) vectors and report a bogus mismatch.
    import sqlite3

    from app.core.disk_cache import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM embedding_cache WHERE model LIKE 'onnx::%'")
    conn.commit()
    conn.close()

    torch_emb = get_embedding_model(provider="huggingface")
    print(f"torch provider: {type(torch_emb).__name__}")
    onnx_emb = get_embedding_model(provider="onnx")
    print(f"onnx provider:  {type(onnx_emb).__name__}")

    torch_vecs = np.array(await torch_emb.aembed_documents(SAMPLES), dtype=np.float64)
    onnx_vecs = np.array(await onnx_emb.aembed_documents(SAMPLES), dtype=np.float64)
    assert torch_vecs.shape == onnx_vecs.shape, (torch_vecs.shape, onnx_vecs.shape)
    print(f"shapes: {torch_vecs.shape}")

    cosines = [cosine(t, o) for t, o in zip(torch_vecs, onnx_vecs)]
    max_abs_diff = float(np.max(np.abs(torch_vecs - onnx_vecs)))
    mean_cos = float(np.mean(cosines))
    print(f"mean cosine similarity: {mean_cos:.6f}")
    print(f"max abs element diff:   {max_abs_diff:.6f}")

    # Retrieval-rank overlap: each sample as query vs all samples as docs.
    top1_agree = 0
    rank_disp: list[int] = []
    for i in range(len(SAMPLES)):
        torch_scores = sorted(
            ((cosine(torch_vecs[i], torch_vecs[j]), j) for j in range(len(SAMPLES)) if j != i),
            reverse=True,
        )
        onnx_scores = sorted(
            ((cosine(onnx_vecs[i], onnx_vecs[j]), j) for j in range(len(SAMPLES)) if j != i),
            reverse=True,
        )
        torch_rank = [j for _, j in torch_scores]
        onnx_rank = [j for _, j in onnx_scores]
        if torch_rank[0] == onnx_rank[0]:
            top1_agree += 1
        # Displacement of torch top-1 inside the onnx ranking.
        rank_disp.append(onnx_rank.index(torch_rank[0]) + 1)
    print(f"top-1 agreement: {top1_agree}/{len(SAMPLES)}")
    print(f"mean rank displacement of torch top-1 in onnx ranking: {np.mean(rank_disp):.3f}")

    ok = mean_cos >= 0.999 and top1_agree == len(SAMPLES)
    print("PARITY OK" if ok else "PARITY MISMATCH — do not flip the default")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
