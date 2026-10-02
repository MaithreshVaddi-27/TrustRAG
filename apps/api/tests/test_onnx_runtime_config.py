"""
ONNX central-config regression tests (hermetic — no model files needed).

Guards the `onnx:` block + shared session factory, plus the shared
centralized knobs (retrieval budgets, query cache, upsert
batch, reranker seq-len):
- every ORT/infra knob lives in models.yaml with an env override,
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
        "RERANKER_MAX_SEQ_LENGTH",
        "RETRIEVAL_BRANCH_TIMEOUT_SECONDS",
        "RETRIEVAL_HYBRID_TIMEOUT_SECONDS",
        "RETRIEVAL_QUERY_CACHE_CAPACITY",
        "QDRANT_UPSERT_BATCH",
        "MAX_ANALYSIS_SECONDS",
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
    from app.llm.onnx_runtime import build_session_options, resolve_intra_op_threads

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
    from app.llm.onnx_runtime import build_session_options

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


def test_retrieval_infra_yaml_defaults(_clean_onnx_env):
    """Runtime knobs: budgets unset (module fallback), cache set."""
    from app.core.config import get_model_config

    cfg = get_model_config()
    assert cfg.branch_timeout_seconds == 0.0
    assert cfg.hybrid_timeout_seconds == 0.0
    assert cfg.query_cache_capacity == 1024
    assert cfg.qdrant_upsert_batch == 100
    assert cfg.reranker_max_seq_length == 512


def test_retrieval_infra_env_overrides_win(_clean_onnx_env, monkeypatch):
    monkeypatch.setenv("RETRIEVAL_QUERY_CACHE_CAPACITY", "256")
    monkeypatch.setenv("QDRANT_UPSERT_BATCH", "50")
    monkeypatch.setenv("RERANKER_MAX_SEQ_LENGTH", "256")
    # NOTE: branch/hybrid_timeout_seconds properties intentionally ignore env —
    # env is resolved in retriever._retrieval_timeouts() so the module globals
    # stay monkeypatch-able (see next test). Properties return yaml (0 = unset).
    from app.core.config import get_model_config

    get_model_config.cache_clear()
    cfg = get_model_config()
    assert cfg.query_cache_capacity == 256
    assert cfg.qdrant_upsert_batch == 50
    assert cfg.reranker_max_seq_length == 256
    assert cfg.branch_timeout_seconds == 0.0
    assert cfg.hybrid_timeout_seconds == 0.0


def test_retrieval_timeout_resolution_prefers_env_over_yaml(_clean_onnx_env, monkeypatch):
    """Module globals stay the monkeypatch-able fallback (tests rely on it)."""
    import app.rag.retrieval.retriever as retriever_mod
    from app.core.config import get_model_config

    get_model_config.cache_clear()
    branch, hybrid = retriever_mod._retrieval_timeouts()
    assert (branch, hybrid) == (45.0, 60.0)
    monkeypatch.setenv("RETRIEVAL_BRANCH_TIMEOUT_SECONDS", "20")
    monkeypatch.setenv("RETRIEVAL_HYBRID_TIMEOUT_SECONDS", "50")
    get_model_config.cache_clear()
    branch, hybrid = retriever_mod._retrieval_timeouts()
    assert (branch, hybrid) == (20.0, 50.0)


def test_production_keys_default_empty_env_only(_clean_onnx_env):
    """Key field defaults are empty; only env fills them (no real key in code)."""
    from app.core.config import Settings

    for field in ("gemini_api_key", "tavily_api_key", "hf_token"):
        assert Settings.model_fields[field].default == "", field


def test_analysis_latency_budget_default_and_disable(_clean_onnx_env, monkeypatch):
    """Audit L-1: whole-analysis wall-clock bound (0 disables)."""
    from app.core.config import get_model_config

    assert get_model_config().max_analysis_seconds == 120
    monkeypatch.setenv("MAX_ANALYSIS_SECONDS", "0")
    get_model_config.cache_clear()
    assert get_model_config().max_analysis_seconds == 0
