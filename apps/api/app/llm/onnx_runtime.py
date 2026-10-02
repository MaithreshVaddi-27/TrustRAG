"""
TRUSTRAG — Shared ONNX Runtime session factory (less RAM + faster inference).

Single place where every ORT ``SessionOptions`` in the backend is built.
Both the embedding engine (``onnx_embeddings.py``) and the reranker
(``onnx_reranker.py``) create their sessions through here, so one config
change in ``models.yaml`` (``onnx:`` block, env ``ONNX_*`` wins) updates
everywhere.

Defaults are RAM-first:
- intra-op threads auto → ``min(cpu_count, 4)`` (no oversubscription next to
  uvicorn workers + tokenizer pool),
- inter-op threads ``1`` (no parallel-branch memory),
- graph optimization ``ORT_ENABLE_ALL`` (op fusion = faster warm inference),
- CPU arena + mem pattern on (disable both on ≤2 GB containers via
  ``ONNX_CPU_MEM_ARENA=false`` / ``ONNX_MEM_PATTERN=false``).
"""

from __future__ import annotations

import os
from typing import Any

from app.core.config.model_config import get_model_config


def _graph_optimization_level(name: str) -> Any:
    """Map a config string to ``ort.GraphOptimizationLevel`` (lazy import)."""
    import onnxruntime as ort

    mapping = {
        "none": ort.GraphOptimizationLevel.ORT_DISABLE_ALL,
        "basic": ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
        "extended": ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
        "all": ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
    }
    return mapping.get((name or "all").strip().lower(), ort.GraphOptimizationLevel.ORT_ENABLE_ALL)


def resolve_intra_op_threads(configured: int) -> int:
    """Resolve ``0``/negative (auto) to a RAM-safe concrete thread count.

    Honors ``OMP_NUM_THREADS`` when set (legacy alias already used by the
    reranker path), capped at 4 so the pool never oversubscribes next to
    uvicorn workers, the tokenizer pool, and llama-server. Falls back to
    ``min(cpu_count, 4)``.
    """
    if configured and configured > 0:
        return configured
    try:
        omp = int(os.getenv("OMP_NUM_THREADS", "") or 0)
    except ValueError:
        omp = 0
    base = omp if omp > 0 else (os.cpu_count() or 4)
    return max(1, min(4, base))


def build_session_options(
    intra_op_threads: int | None = None,
    inter_op_threads: int | None = None,
    graph_optimization: str | None = None,
    cpu_mem_arena: bool | None = None,
    mem_pattern: bool | None = None,
) -> Any:
    """Build a tuned ``ort.SessionOptions`` from central config.

    Explicit arguments win (used by tests); ``None`` falls back to
    ``models.yaml`` ``onnx:`` via ``get_model_config()`` with ``ONNX_*`` env
    overrides. Importing ``onnxruntime`` here keeps the factory torch-free.
    """
    import onnxruntime as ort

    if (
        intra_op_threads is None
        or inter_op_threads is None
        or graph_optimization is None
        or cpu_mem_arena is None
        or mem_pattern is None
    ):
        cfg = get_model_config()
        if intra_op_threads is None:
            intra_op_threads = cfg.onnx_intra_op_threads
        if inter_op_threads is None:
            inter_op_threads = cfg.onnx_inter_op_threads
        if graph_optimization is None:
            graph_optimization = cfg.onnx_graph_optimization
        if cpu_mem_arena is None:
            cpu_mem_arena = cfg.onnx_cpu_mem_arena
        if mem_pattern is None:
            mem_pattern = cfg.onnx_mem_pattern

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = resolve_intra_op_threads(int(intra_op_threads or 0))
    opts.inter_op_num_threads = max(1, int(inter_op_threads or 1))
    # Sequential execution: one node at a time = lowest peak RAM.
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opts.graph_optimization_level = _graph_optimization_level(str(graph_optimization or "all"))
    opts.enable_cpu_mem_arena = bool(cpu_mem_arena)
    opts.enable_mem_pattern = bool(mem_pattern)
    return opts
