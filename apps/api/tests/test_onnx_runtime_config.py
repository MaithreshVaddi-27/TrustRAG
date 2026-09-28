"""
ONNX central-config regression tests (hermetic — no model files needed).

Guards the v1.23 `onnx:` block + shared session factory:
- every ORT knob lives in models.yaml with an ONNX_* env override,
- the factory caps threads for less RAM and enables full graph fusion,
- reranker batch precedence is explicit > env > yaml > 16,
- production API-key fields still default to empty (env-only, never hardcoded).
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture()
def _clean_onnx_env(monkeypatch):
    for var in (
        "ONNX_PROVIDERS",
        "ONNX_INTRA_OP_THREADS",
        "ONNX_INTER_OP_THREADS",
        "ONNX_GRAPH_OPTIMIZATION",
        "ONNX_CPU_MEM_ARENA",
        "ONNX_MEM_PATTERN",
        "ONNX_EMBED_MICRO_BATCH",
        "RERANKER_BATCH_SIZE",
        "OMP_NUM_THREADS",
    ):
        monkeypatch.delenv(var, raising=False)
    from app.core.config import get_model_config, get_settings

    get_settings.cache_clear()
    get_model_config.cache_clear()
    yield
    get_settings.cache_clear()
    get_model_config.cache_clear()


def test_onnx_yaml_defaults(_clean_onnx_env):
    from app.core.config import get_model_config

    cfg = get_model_config()
    assert cfg.onnx_providers == ["CPUExecutionProvider"]
    assert cfg.onnx_intra_op_threads == 0  # auto
    assert cfg.onnx_inter_op_threads == 1
    assert cfg.onnx_graph_optimization == "all"
    assert cfg.onnx_cpu_mem_arena is True
    assert cfg.onnx_mem_pattern is True
    assert cfg.onnx_embed_micro_batch == 0  # auto (tier-aware)


def test_onnx_env_overrides_win(_clean_onnx_env, monkeypatch):
    monkeypatch.setenv("ONNX_INTRA_OP_THREADS", "2")
    monkeypatch.setenv("ONNX_CPU_MEM_ARENA", "false")
    monkeypatch.setenv("ONNX_PROVIDERS", "CUDAExecutionProvider,CPUExecutionProvider")
    monkeypatch.setenv("ONNX_EMBED_MICRO_BATCH", "16")
    from app.core.config import get_model_config

    get_model_config.cache_clear()
    cfg = get_model_config()
    assert cfg.onnx_intra_op_threads == 2
    assert cfg.onnx_cpu_mem_arena is False
    assert cfg.onnx_providers == ["CUDAExecutionProvider", "CPUExecutionProvider"]
    assert cfg.onnx_embed_micro_batch == 16


def test_factory_caps_threads_and_fuses_graph(_clean_onnx_env):
    from app.core.onnx_runtime import build_session_options, resolve_intra_op_threads

    assert resolve_intra_op_threads(0) == max(1, min(4, os.cpu_count() or 4))
    assert resolve_intra_op_threads(8) == 8  # explicit wins
    opts = build_session_options()
    assert opts.intra_op_num_threads == resolve_intra_op_threads(0)
    assert opts.inter_op_num_threads == 1

    import onnxruntime as ort

    assert opts.graph_optimization_level == ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    assert opts.execution_mode == ort.ExecutionMode.ORT_SEQUENTIAL
    assert opts.enable_cpu_mem_arena is True
    assert opts.enable_mem_pattern is True


def test_factory_honors_omp_and_explicit_args(_clean_onnx_env, monkeypatch):
    from app.core.onnx_runtime import build_session_options

    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    assert build_session_options().intra_op_num_threads == 2
    # Explicit constructor arg beats everything (incl. OMP + yaml).
    assert build_session_options(intra_op_threads=1).intra_op_num_threads == 1
    assert build_session_options(cpu_mem_arena=False).enable_cpu_mem_arena is False


def test_reranker_batch_precedence(_clean_onnx_env, monkeypatch):
    from app.core.config import get_model_config

    assert (
        get_model_config().reranker_batch_size_effective == get_model_config().reranker_batch_size
    )
    monkeypatch.setenv("RERANKER_BATCH_SIZE", "8")
    get_model_config.cache_clear()
    assert get_model_config().reranker_batch_size_effective == 8


def test_production_keys_default_empty_env_only(_clean_onnx_env):
    """No hardcoded secrets: key *field defaults* are empty — only env fills them.

    Asserts on the model definition (not runtime values, which legitimately
    pick up this machine's real `.env`), proving no real key lives in code.
    """
    from app.core.config import Settings

    for field in ("gemini_api_key", "nvidia_api_key", "tavily_api_key", "hf_token"):
        assert Settings.model_fields[field].default == "", field
