"""
TRUSTRAG — models.yaml registry (single source of truth for IDs/params).

Secrets stay in .env; this module reads model IDs, thresholds, and tuning
parameters. See app.core.config.settings for env-sourced Settings.
"""

from __future__ import annotations

import os
from typing import Any

import structlog
import yaml

from app.core.config.settings import (
    _DEFAULT_MLX_BASE_URL,
    _MODELS_YAML_PATH,
    _blank_as_none,
    _parse_bool,
    get_ports,
)

logger = structlog.get_logger(__name__)


def _load_models_yaml() -> dict[str, Any]:
    """Load and parse config/models.yaml. Fails loudly on missing/malformed file."""
    if not _MODELS_YAML_PATH.exists():
        raise FileNotFoundError(
            f"models.yaml not found at {_MODELS_YAML_PATH}. "
            "This file must exist — it is the centralized config registry."
        )
    with _MODELS_YAML_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"models.yaml must be a YAML mapping. Got: {type(data)}")
    return data


# Canonical provider spellings. Several aliases are accepted on input
# (`gemini`, `llamacpp`); normalizing in one place keeps the
# allowlist check, the resolved model, the persisted document, and downstream
# provider switches from disagreeing about the provider's name (audit B-15/B-18).
_PROVIDER_ALIASES = {
    "gemini": "gemini",
    "llamacpp": "llama_cpp",
    "llama-cpp": "llama_cpp",
}

SUPPORTED_LLM_PROVIDERS = frozenset({"ollama", "llama_cpp", "mlx", "gemini"})


def normalize_provider(provider: str | None) -> str:
    """Canonical lowercase provider name. Unknown names pass through lowercased
    so the caller can reject them with a useful message."""
    p = (provider or "").strip().lower()
    return _PROVIDER_ALIASES.get(p, p)


class ModelConfig:
    """
    Typed access to models.yaml sections.

    This is the ONLY place application code reads model IDs, thresholds,
    retrieval parameters, and reliability policy. Never read models.yaml
    directly in routes, services, or LangGraph nodes.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def _get(self, *keys: str, required: bool = True) -> Any:
        node: Any = self._data
        path = ".".join(keys)
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                if required:
                    raise KeyError(f"Required key '{path}' missing from models.yaml")
                return None
            node = node[key]
        return node

    # ── Config version ─────────────────────────────────────────────────────
    @property
    def config_version(self) -> str:
        return str(self._get("runtime", "config_version"))

    # ── LLM ─────────────────────────────────────────────────────────────────
    @property
    def llm_provider(self) -> str:
        val = self._get("llm", "provider", required=False)
        env_val = os.environ.get("AI_PROVIDER") or os.environ.get("LLM_PROVIDER")
        if env_val:
            return env_val.lower()
        return str(val or "ollama").lower()

    @property
    def llm_model(self) -> str:
        return self.llm_model_for(self.llm_provider)

    def llm_model_for(self, provider: str) -> str:
        """Resolve the model id for an explicit provider (not the configured one)."""
        self._get("llm")
        p = provider.lower()
        if p == "ollama":
            env_model = os.environ.get("OLLAMA_MODEL")
            return (
                env_model
                or str(self._get("llm", "model_ollama", required=False) or "")
                or str(self._get("llm", "model"))
            )
        if p in ("llama_cpp", "llamacpp"):
            env_model = os.environ.get("LLAMACPP_MODEL") or os.environ.get("LLAMA_CPP_MODEL")
            return (
                env_model
                or str(self._get("llm", "model_llamacpp", required=False) or "")
                or str(self._get("llm", "model"))
            )
        if p == "mlx":
            env_model = os.environ.get("MLX_MODEL")
            if env_model:
                return env_model
            # Never fall back to llm.model here: it may be a GGUF id the
            # MLX server cannot serve (exact-match routing → 404).
            # Required yaml key — fail fast if absent.
            return str(self._get("llm", "model_mlx"))
        env_model = os.environ.get("LLM_MODEL") or os.environ.get("GEMINI_MODEL")
        if env_model:
            return env_model
        if p in ("gemini"):
            # Never fall back to llm.model here: it is a local GGUF id, not a
            # Gemini model id. Override via LLM_MODEL env or model_gemini yaml.
            return str(self._get("llm", "model_gemini"))
        return str(self._get("llm", "model"))

    @property
    def ollama_base_url(self) -> str:
        env_url = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST")
        if env_url:
            return env_url
        port = get_ports().get("ollama")
        if port:
            return f"http://localhost:{port}"
        return str(self._get("llm", "ollama_base_url", required=False) or "http://localhost:11434")

    @property
    def llamacpp_base_url(self) -> str:
        env_url = os.environ.get("LLAMACPP_BASE_URL") or os.environ.get("LLAMA_CPP_BASE_URL")
        if env_url:
            return env_url
        port = get_ports().get("llamacpp")
        if port:
            return f"http://127.0.0.1:{port}/v1"
        return str(
            self._get("llm", "llamacpp_base_url", required=False) or "http://127.0.0.1:8080/v1"
        )

    @property
    def mlx_base_url(self) -> str:
        env_url = os.environ.get("MLX_BASE_URL")
        if env_url:
            return env_url
        # Separate port (:8090) so llama-server (:8080) and mlx_lm.server (:8090)
        # can run side-by-side. pydantic env > Field default > _DEFAULT_MLX_BASE_URL.
        return str(self._get("llm", "mlx_base_url", required=False) or _DEFAULT_MLX_BASE_URL)

    @property
    def llm_temperature(self) -> float:
        """Default temperature for generation."""
        return float(self._get("llm", "temperature"))

    @property
    def llm_top_p(self) -> float:
        return float(self._get("llm", "top_p"))

    @property
    def llm_max_output_tokens(self) -> int:
        return int(self._get("llm", "max_output_tokens"))

    @property
    def llm_timeout_seconds(self) -> int:
        return int(self._get("llm", "timeout_seconds"))

    @property
    def llm_max_retries(self) -> int:
        return int(self._get("llm", "max_retries"))

    # ── Embedding ─────────────────────────────────────────────────────────
    # Single embedding engine: ONNX BGE (torch-free). `embedding.model` in
    # models.yaml is the sole source of truth — there is no provider choice,
    # no EMBEDDING_PROVIDER env, and no per-request override. Update the model
    # ID in models.yaml and every stage (ingest, retrieval, verification)
    # follows automatically.
    @property
    def embedding_model(self) -> str:
        return str(self._get("embedding", "model"))

    @property
    def embedding_dimensionality(self) -> int:
        val = int(self._get("embedding", "output_dimensionality"))
        env_dim = _blank_as_none("EMBEDDING_DIM") or _blank_as_none("EMBEDDING_DIMENSIONALITY")
        return int(env_dim) if env_dim is not None else val

    @property
    def embedding_version(self) -> str:
        return str(self._get("embedding", "version"))

    @property
    def embedding_cache_dir(self) -> str:
        # MODEL_CACHE_DIR wins so the backend reads the same directory that
        # scripts/bootstrap.py writes (see ensure_onnx_models._cache_dir).
        env_dir = os.environ.get("MODEL_CACHE_DIR")
        if env_dir and env_dir.strip():
            return env_dir
        return str(self._get("embedding", "cache_dir", required=False) or ".model_cache")

    @property
    def embedding_max_seq_length(self) -> int:
        return int(self._get("embedding", "max_seq_length"))

    # ── Verification ──────────────────────────────────────────────────────
    @property
    def verification_provider(self) -> str:
        val = self._get("verification", "provider", required=False)
        env_val = os.environ.get("AI_PROVIDER") or os.environ.get("LLM_PROVIDER")
        if env_val:
            return env_val.lower()
        return str(val or "ollama").lower()

    @property
    def verification_model(self) -> str:
        return self.verification_model_for(self.verification_provider)

    def verification_model_for(self, provider: str) -> str:
        """Resolve the verifier model id for an explicit provider."""
        p = provider.lower()
        if p == "ollama":
            env_model = os.environ.get("OLLAMA_MODEL")
            return (
                env_model
                or str(self._get("verification", "model_ollama", required=False) or "")
                or str(self._get("verification", "model"))
            )
        if p in ("llama_cpp", "llamacpp"):
            env_model = os.environ.get("LLAMACPP_MODEL") or os.environ.get("LLAMA_CPP_MODEL")
            return (
                env_model
                or str(self._get("verification", "model_llamacpp", required=False) or "")
                or str(self._get("verification", "model"))
            )
        if p == "mlx":
            env_model = os.environ.get("MLX_MODEL")
            if env_model:
                return env_model
            # Same no-GGUF-fallback rule as llm_model_for (exact-match routing).
            # Required yaml key — fail fast if absent.
            return str(self._get("verification", "model_mlx"))
        val = self._get("verification", "model")
        env_model = os.environ.get("GEMINI_VERIFICATION_MODEL") or os.environ.get(
            "VERIFICATION_MODEL"
        )
        if env_model:
            return env_model
        if p in ("gemini"):
            # Never fall back to verification.model / llm.model (local GGUF ids).
            return str(
                self._get("verification", "model_gemini", required=False)
                or self._get("llm", "model_gemini")
            )
        return str(val)

    @property
    def supported_gemini_models(self) -> list[str]:
        """Cloud allowlist: models API callers may select for gemini.

        Required yaml key (`llm.supported_models_gemini`) — adding a newly
        released model is a config change here, never a code change.
        """
        val = self._get("llm", "supported_models_gemini")
        if isinstance(val, list) and val:
            return [str(m) for m in val]
        raise KeyError("Required key 'llm.supported_models_gemini' missing from models.yaml")

    @property
    def verification_max_output_tokens(self) -> int:
        return int(self._get("verification", "max_output_tokens"))

    @property
    def verification_timeout_seconds(self) -> int:
        return int(self._get("verification", "timeout_seconds"))

    @property
    def fused_decompose_verify(self) -> bool:
        val = self._get("verification", "fused_decompose_verify", required=False)
        env_val = os.environ.get("FUSED_DECOMPOSE_VERIFY")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(val, True)

    @property
    def max_verification_time_seconds(self) -> int:
        return int(self._get("verification", "max_verification_time_seconds"))

    @property
    def verification_max_retries(self) -> int:
        """Retry budget for verification LLM calls (models.yaml: verification.max_retries)."""
        val = self._get("verification", "max_retries", required=False)
        env_val = os.environ.get("VERIFICATION_MAX_RETRIES")
        if env_val is not None:
            return int(env_val)
        if val is None:
            return int(self._get("llm", "max_retries"))
        return int(val)

    # ── Reranker ─────────────────────────────────────────────────────────
    @property
    def reranker_enabled(self) -> bool:
        return bool(self._get("reranker", "enabled"))

    @property
    def reranker_model(self) -> str:
        return self._get("reranker", "model")

    @property
    def reranker_top_k(self) -> int:
        return int(self._get("reranker", "top_k"))

    @property
    def reranker_batch_size(self) -> int:
        return int(self._get("reranker", "batch_size"))

    @property
    def reranker_early_termination_confidence(self) -> float:
        return float(self._get("reranker", "early_termination_confidence"))

    @property
    def reranker_score_gap_threshold(self) -> float:
        return float(self._get("reranker", "score_gap_threshold"))

    @property
    def reranker_use_onnx(self) -> bool:
        val = self._get("reranker", "use_onnx", required=False)
        env_val = os.environ.get("RERANKER_USE_ONNX")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(val, True)  # Default to ONNX for speed

    @property
    def reranker_onnx_model_path(self) -> str:
        val = self._get("reranker", "onnx_model_path", required=False)
        env_val = os.environ.get("RERANKER_ONNX_MODEL_PATH")
        if env_val is not None:
            return env_val
        return str(val or "")

    @property
    def reranker_max_seq_length(self) -> int:
        """Max sequence length for the reranker tokenizer (models.yaml).

        Previously hardcoded to 512 at every construction site; centralizing
        here lets a yaml edit propagate to all ONNX reranker instances.
        """
        value = self._get("reranker", "max_seq_length", required=False)
        env_val = _blank_as_none("RERANKER_MAX_SEQ_LENGTH")
        if env_val is not None:
            return int(env_val)
        return int(value or 512)

    @property
    def reranker_batch_size_effective(self) -> int:
        """Batch size for reranker inference: explicit env wins, then yaml.

        `onnx_reranker.predict()` consults this single property so
        RERANKER_BATCH_SIZE and models.yaml stay consistent.
        """
        env_val = _blank_as_none("RERANKER_BATCH_SIZE")
        if env_val is not None:
            return int(env_val)
        return int(self.reranker_batch_size)

    # ── ONNX Runtime (shared embedding + reranker engine) ──────────────
    # Central knobs for every ORT session (see `onnx:` in models.yaml).
    # Env vars (ONNX_*) win over yaml so a deploy can tune without editing
    # config. 0 intra-op threads = auto → min(cpu_count, 4) at session build.
    @property
    def onnx_providers(self) -> list[str]:
        env_val = _blank_as_none("ONNX_PROVIDERS")
        if env_val is not None:
            return [p.strip() for p in env_val.split(",") if p.strip()]
        val = self._get("onnx", "providers", required=False)
        if isinstance(val, list) and val:
            return [str(p) for p in val]
        return ["CPUExecutionProvider"]

    @property
    def onnx_intra_op_threads(self) -> int:
        env_val = _blank_as_none("ONNX_INTRA_OP_THREADS")
        if env_val is not None:
            return int(env_val)
        val = self._get("onnx", "intra_op_threads", required=False)
        return int(val) if val is not None else 0

    @property
    def onnx_inter_op_threads(self) -> int:
        env_val = _blank_as_none("ONNX_INTER_OP_THREADS")
        if env_val is not None:
            return int(env_val)
        val = self._get("onnx", "inter_op_threads", required=False)
        return int(val) if val is not None else 1

    @property
    def onnx_graph_optimization(self) -> str:
        env_val = _blank_as_none("ONNX_GRAPH_OPTIMIZATION")
        if env_val is not None:
            return env_val.strip().lower()
        return str(self._get("onnx", "graph_optimization", required=False) or "all").lower()

    @property
    def onnx_cpu_mem_arena(self) -> bool:
        env_val = _blank_as_none("ONNX_CPU_MEM_ARENA")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(self._get("onnx", "cpu_mem_arena", required=False), True)

    @property
    def onnx_mem_pattern(self) -> bool:
        env_val = _blank_as_none("ONNX_MEM_PATTERN")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(self._get("onnx", "mem_pattern", required=False), True)

    @property
    def onnx_embed_micro_batch(self) -> int:
        env_val = _blank_as_none("ONNX_EMBED_MICRO_BATCH")
        if env_val is not None:
            return int(env_val)
        val = self._get("onnx", "embed_micro_batch", required=False)
        # NOTE: 0 is a meaningful value (auto → tier-aware), so test
        # `is None` explicitly — `or 32` would swallow the 0 default.
        return int(val) if val is not None else 32

    # ── Retrieval ─────────────────────────────────────────────────────────
    @property
    def dense_top_k(self) -> int:
        return int(self._get("retrieval", "dense_top_k"))

    @property
    def sparse_top_k(self) -> int:
        return int(self._get("retrieval", "sparse_top_k"))

    @property
    def fusion_method(self) -> str:
        return self._get("retrieval", "fusion_method")

    @property
    def rrf_k(self) -> int:
        return int(self._get("retrieval", "rrf_k"))

    @property
    def fusion_top_k(self) -> int:
        return int(self._get("retrieval", "fusion_top_k"))

    @property
    def branch_timeout_seconds(self) -> float:
        """Per-branch retrieval budget; 0 = unset (module fallback 45s)."""
        value = self._get("retrieval", "branch_timeout_seconds", required=False)
        return float(value) if value is not None else 0.0

    @property
    def hybrid_timeout_seconds(self) -> float:
        """Hybrid retrieval budget; 0 = unset (module fallback 60s)."""
        value = self._get("retrieval", "hybrid_timeout_seconds", required=False)
        return float(value) if value is not None else 0.0

    @property
    def sparse_k1(self) -> float:
        return float(self._get("retrieval", "sparse_k1", required=False) or 1.2)

    @property
    def sparse_b(self) -> float:
        return float(self._get("retrieval", "sparse_b", required=False) or 0.75)

    @property
    def sparse_avg_len_tokens(self) -> int:
        return int(self._get("retrieval", "sparse_avg_len_tokens", required=False) or 128)

    @property
    def max_context_chunks(self) -> int:
        return int(self._get("retrieval", "max_context_chunks"))

    @property
    def router_enabled(self) -> bool:
        return bool(self._get("retrieval", "query_router", "enabled", required=False) is not False)

    @property
    def max_fanout_sub_queries(self) -> int:
        value = self._get("retrieval", "query_router", "max_sub_queries", required=False)
        return int(value) if value is not None else 3

    # ── Ingestion ─────────────────────────────────────────────────────────
    @property
    def chunk_size(self) -> int:
        return int(self._get("ingestion", "chunk_size"))

    @property
    def chunk_overlap(self) -> int:
        return int(self._get("ingestion", "chunk_overlap"))

    @property
    def supported_formats(self) -> list[str]:
        return list(self._get("ingestion", "supported_formats"))

    @property
    def max_file_size_mb(self) -> int:
        return int(self._get("ingestion", "max_file_size_mb"))

    @property
    def qdrant_upsert_batch(self) -> int:
        """Points per Qdrant upsert call (models.yaml ingestion.qdrant_upsert_batch)."""
        value = self._get("ingestion", "qdrant_upsert_batch", required=False)
        env_val = _blank_as_none("QDRANT_UPSERT_BATCH")
        if env_val is not None:
            return int(env_val)
        return int(value) if value is not None else 100

    @property
    def chunking_strategy(self) -> str:
        """Chunking strategy name (models.yaml: ingestion.chunking_strategy)."""
        return str(self._get("ingestion", "chunking_strategy", required=False) or "sliding_window")

    # ── OCR fallback ─────────────────────────────────────────────────────
    @property
    def ocr_enabled(self) -> bool:
        return bool(self._get("ingestion", "ocr", "enabled", required=False) is not False)

    @property
    def ocr_min_native_chars(self) -> int:
        return int(self._get("ingestion", "ocr", "min_native_chars", required=False) or 50)

    @property
    def ocr_dpi(self) -> int:
        return int(self._get("ingestion", "ocr", "dpi", required=False) or 300)

    @property
    def ocr_min_confidence(self) -> float:
        return float(self._get("ingestion", "ocr", "min_confidence", required=False) or 0.5)

    @property
    def ocr_store_page_images(self) -> bool:
        return bool(self._get("ingestion", "ocr", "store_page_images", required=False) is not False)

    # ── Reliability ──────────────────────────────────────────────────────
    @property
    def minimum_evidence_coverage(self) -> float:
        return float(self._get("reliability", "minimum_evidence_coverage"))

    @property
    def maximum_contradiction_rate(self) -> float:
        return float(self._get("reliability", "maximum_contradiction_rate"))

    @property
    def abstain_below(self) -> float:
        return float(self._get("reliability", "abstain_below"))

    # ── Recovery ─────────────────────────────────────────────────────────
    @property
    def max_recovery_attempts(self) -> int:
        return int(self._get("recovery", "max_recovery_attempts"))

    @property
    def recovery_strategy_priority(self) -> list[str]:
        """Return ordered recovery strategies, e.g. ['query_rewrite', 're_retrieve']."""
        val = self._get("recovery", "strategy_priority", required=False)
        if isinstance(val, list) and val:
            return [str(s) for s in val]
        return ["query_rewrite", "re_retrieve"]

    @property
    def max_recovery_tokens(self) -> int:
        return int(self._get("recovery", "max_recovery_tokens", required=False) or 2000)

    @property
    def max_recovery_latency_seconds(self) -> int:
        return int(self._get("recovery", "max_recovery_latency_seconds", required=False) or 180)

    @property
    def max_analysis_seconds(self) -> int:
        """Wall-clock ceiling for one whole analysis (audit L-1).

        `max_recovery_latency_seconds` only counts time spent inside the
        recovery node, so it cannot bound a full multi-round run (retrieval +
        generation + verification x3). This bounds the entire graph, so the
        user gets a verified-or-abstained answer inside a predictable window.
        Set to 0 to disable the bound.
        """
        override = os.getenv("MAX_ANALYSIS_SECONDS", "").strip()
        if override:
            try:
                return int(override)
            except ValueError:
                pass
        val = self._get("cost_controls", "max_analysis_seconds", required=False)
        return int(val or 0)

    # ── Observability ─────────────────────────────────────────
    @property
    def pre_request_budget_enforcement(self) -> bool:
        return bool(
            self._get("observability", "pre_request_budget_enforcement", required=False)
            is not False
        )

    # ── Cost controls ─────────────────────────────────────────────────────
    @property
    def max_input_tokens(self) -> int:
        return int(self._get("cost_controls", "max_input_tokens"))

    @property
    def max_query_tokens(self) -> int:
        """Query-scoped pre-request bound (audit B-4).

        The pre-request check used to compare the query against
        `max_input_tokens` (100000), which pydantic's 2000-char query cap made
        unreachable — so `pre_request_budget_enforcement` never fired. This is
        the separate, meaningful query budget.
        """
        return int(self._get("cost_controls", "max_query_tokens"))

    @property
    def max_llm_calls_per_analysis(self) -> int:
        """Per-analysis LLM call ceiling for cloud tiers (audit B-4).

        The real spend guard. `max_input_tokens` is an input-token ceiling; this
        bounds the number of billable round-trips, which is what actually costs
        money when a recovery loop multiplies calls.
        """
        return int(self._get("cost_controls", "max_llm_calls_per_analysis"))

    @property
    def max_verification_claims(self) -> int:
        return int(self._get("cost_controls", "max_verification_claims"))

    @property
    def max_individual_nli_fallback(self) -> int:
        value = self._get("cost_controls", "max_individual_nli_fallback", required=False)
        return int(value) if value is not None else 5

    @property
    def max_claim_retrievals(self) -> int:
        value = self._get("cost_controls", "max_claim_retrievals", required=False)
        return int(value) if value is not None else 3

    @property
    def claim_retrieval_top_k(self) -> int:
        value = self._get("cost_controls", "claim_retrieval_top_k", required=False)
        return int(value) if value is not None else 5

    # ── Local LLM Inference Parameters ────────────────────────────────────────
    @property
    def local_llm_num_ctx(self) -> int:
        value = self._get("local_llm", "num_ctx", required=False)
        env_val = _blank_as_none("LOCAL_LLM_NUM_CTX")
        return int(env_val) if env_val is not None else int(value or 4096)

    @property
    def local_llm_num_batch(self) -> int:
        value = self._get("local_llm", "num_batch", required=False)
        env_val = _blank_as_none("LOCAL_LLM_NUM_BATCH")
        return int(env_val) if env_val is not None else int(value or 512)

    @property
    def local_llm_keep_alive(self) -> str:
        value = self._get("local_llm", "keep_alive", required=False)
        env_val = _blank_as_none("LOCAL_LLM_KEEP_ALIVE")
        return env_val if env_val is not None else str(value or "5m")

    # ── Speculative Decoding / Early Exit ──────────────────────
    @property
    def local_llm_min_p(self) -> float:
        """Min-p sampling: only tokens with p >= min_p * p_max are considered.
        0.0 = disabled, 0.1 = aggressive filtering for speed."""
        value = self._get("local_llm", "min_p", required=False)
        env_val = _blank_as_none("LOCAL_LLM_MIN_P")
        return float(env_val) if env_val is not None else float(value or 0.0)

    @property
    def local_llm_top_k(self) -> int:
        """Top-k sampling: restrict to top K tokens. 0 = disabled (no limit)."""
        value = self._get("local_llm", "top_k", required=False)
        env_val = _blank_as_none("LOCAL_LLM_TOP_K")
        return int(env_val) if env_val is not None else int(value or 0)

    @property
    def local_llm_early_exit_eos(self) -> bool:
        """Early stop on EOS token (n_predict streaming with early termination)."""
        value = self._get("local_llm", "early_exit_eos", required=False)
        env_val = os.environ.get("LOCAL_LLM_EARLY_EXIT_EOS")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)  # Default enabled for speed

    # ── Inference Acceleration & KV Cache Optimization ────────────────────────
    @property
    def kv_cache_quantization(self) -> str:
        value = self._get("optimization", "kv_cache_quantization", required=False)
        env_val = os.environ.get("KV_CACHE_QUANTIZATION")
        return env_val if env_val is not None else str(value or "q4_0")

    @property
    def prompt_caching(self) -> bool:
        value = self._get("optimization", "prompt_caching", required=False)
        env_val = os.environ.get("PROMPT_CACHING")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)

    # ── Context Compression ─────────────────────────────────────────
    @property
    def context_compression_enabled(self) -> bool:
        value = self._get("optimization", "context_compression_enabled", required=False)
        env_val = os.environ.get("CONTEXT_COMPRESSION_ENABLED")
        if env_val is not None:
            return _parse_bool(env_val)
        return _parse_bool(value, True)  # Default enabled for RAM savings

    @property
    def context_compression_provider(self) -> str:
        """Which providers should use context compression: 'cloud' (gemini),
        'local' (ollama, llama_cpp, mlx), or 'off' (disabled)."""
        value = self._get("optimization", "context_compression_provider", required=False)
        env_val = os.environ.get("CONTEXT_COMPRESSION_PROVIDER")
        return (env_val or value or "off").lower()

    @property
    def context_compression_min_tokens(self) -> int:
        """Skip compression when the context is smaller than this (audit B-7).

        Compression costs a second full LLM call against the same model. For
        cloud tiers with 128K-1M windows that is almost never worth it at
        realistic context sizes, so the threshold is explicit and configurable
        instead of firing in a narrow band where it costs the most and helps
        least. 0 disables the check.
        """
        value = self._get("optimization", "context_compression_min_tokens", required=False)
        env_val = _blank_as_none("CONTEXT_COMPRESSION_MIN_TOKENS")
        if env_val is not None:
            return int(env_val)
        return int(value or 0)

    def tier_caps(self, provider: str | None = None) -> dict[str, int]:
        """Return cost-control caps for the current provider tier.

        Args:
            provider: Explicit provider to get caps for. If None, uses llm_provider.

        Returns:
            Dict with max_verification_claims, max_context_chunks, max_claim_retrievals
        """
        prov = (provider or self.llm_provider).lower()
        is_cloud = prov in "gemini"
        is_mlx = prov == "mlx"

        if is_cloud:
            tier = "cloud_tier"
        elif is_mlx or prov in ("ollama", "llama_cpp", "llamacpp"):
            # Detect lean vs balanced by available RAM (proxy via num_ctx)
            num_ctx = self.local_llm_num_ctx
            tier = "balanced_tier" if num_ctx >= 8192 else "lean_tier"
        else:
            tier = "cloud_tier"  # fallback

        tier_config = self._get("cost_controls", tier, required=False) or {}
        defaults = {
            "max_verification_claims": 8,
            "max_context_chunks": 8,
            "max_claim_retrievals": 3,
        }
        return {k: int(tier_config.get(k, v)) for k, v in defaults.items()}

    def as_snapshot(self) -> dict[str, Any]:
        """Return a flat dict for recording with each analysis run."""
        return {
            "config_version": self.config_version,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "embedding_version": self.embedding_version,
            "embedding_dimensionality": self.embedding_dimensionality,
            "verification_provider": self.verification_provider,
            "verification_model": self.verification_model,
            "reranker_enabled": self.reranker_enabled,
            "reranker_model": self.reranker_model if self.reranker_enabled else None,
            "fusion_method": self.fusion_method,
            "fusion_top_k": self.fusion_top_k,
            "max_fanout_sub_queries": self.max_fanout_sub_queries,
            "ocr_enabled": self.ocr_enabled,
            "ocr_store_page_images": self.ocr_store_page_images,
            "sparse_k1": self.sparse_k1,
            "sparse_b": self.sparse_b,
            "sparse_avg_len_tokens": self.sparse_avg_len_tokens,
            "max_context_chunks": self.max_context_chunks,
            "abstain_below": self.abstain_below,
            "max_recovery_attempts": self.max_recovery_attempts,
            "max_claim_retrievals": self.max_claim_retrievals,
        }


# ─── Factory (no cache: fresh read per call) ────────────────────────────────


def get_model_config() -> ModelConfig:
    """Load ModelConfig from models.yaml (fresh read, no cache).

    No singleton: a yaml edit takes effect without restarts or explicit
    invalidation. The file is small (~350 lines); re-parsing per call costs
    single-digit milliseconds and removes a whole class of stale-state bugs.
    """
    raw = _load_models_yaml()
    cfg = ModelConfig(raw)
    _validate_chunk_windows(cfg)
    return cfg


def _validate_chunk_windows(cfg: ModelConfig) -> None:
    """Fail fast on chunk settings that would silently degrade chunking (M3).

    `chunk_overlap >= chunk_size` used to collapse the progressive step to 1
    character (507x chunk blowup → 99k embedding calls). The strategies now
    guard at chunk time; this rejects the misconfiguration at startup so it
    is fixed instead of merely survived.
    """
    try:
        size = int(cfg.chunk_size)
        overlap = int(cfg.chunk_overlap)
    except (KeyError, TypeError, ValueError):
        return  # Missing keys are reported by the properties themselves.
    if size <= 0:
        raise ValueError(f"Invalid ingestion.chunk_size={size}: must be positive")
    if overlap < 0:
        raise ValueError(f"Invalid ingestion.chunk_overlap={overlap}: must be non-negative")
    if overlap >= size:
        raise ValueError(
            f"Invalid ingestion chunk windows: chunk_overlap ({overlap}) >= "
            f"chunk_size ({size}). Overlap must be smaller than the window."
        )
