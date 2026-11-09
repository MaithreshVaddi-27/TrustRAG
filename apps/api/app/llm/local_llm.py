"""
TRUSTRAG — Local LLM Client implementations for Ollama, llama.cpp, and MLX.

This module is a backward-compatible re-export shim. All implementation has
been split into the ``app.llm.providers`` sub-package:

- ``providers/base`` — shared HTTP client pooling & message conversion
- ``providers/capabilities`` — output caps, small/reasoning model detection
- ``providers/ollama`` — ``ChatOllamaClient``
- ``providers/llama_cpp`` — ``ChatLlamaCppClient``
- ``providers/mlx`` — ``ChatMLXClient``
- ``providers/discovery`` — model discovery + snapshot persistence
- ``providers/health`` — provider status/probe functions

Existing imports (``from app.llm.local_llm import ...``) continue to work.
"""

from __future__ import annotations

import asyncio
import httpx
import threading
from pathlib import Path

from app.llm.providers import (
    LOCAL_LLM_PROVIDERS,
    ChatLlamaCppClient,
    ChatMLXClient,
    ChatOllamaClient,
    close_local_llm_clients,
    discover_llamacpp_cache_models,
    discover_mlx_cache_models,
    discover_ollama_cli_models,
    get_discovered_llms,
    is_reasoning_model,
    is_small_model,
    load_discovery_snapshot,
    local_cap_kwargs,
    merge_discovered_llms,
    save_discovery_snapshot,
    seed_local_model_discovery,
    verification_cap_kwargs,
)
from app.llm.providers.base import (
    _HTTP_CLIENTS,
    _HTTP_CLIENTS_LOCK,
    _convert_messages_to_dict,
    _shared_http_client,
)
from app.llm.providers.capabilities import (
    _is_embedding_model_name,
)
from app.llm.providers.health import (
    _classify_cloud_probe_error,
    _record_probe_success,
    _status_code_of,
    check_llamacpp_status,
    check_mlx_status,
    check_ollama_status,
    probe_cloud_llm,
)
from app.llm.providers.local_llm_legacy import probe_local_llm_server
from app.core.system.concurrency import get_global_semaphore

# Names that tests patch directly on app.llm.local_llm (the flat module
# surface from the legacy graph.py) must resolve here at call time.
from app.llm.providers.local_llm_legacy import discover_hf_hub_gguf_models

# Module-level state for discovery (backward-compat: tests patch these)
_DISCOVERED_LLMS: dict[str, set[str]] = {}
_DISCOVERED_LLMS_LOCK = asyncio.Lock() if hasattr(asyncio, "Lock") else None
try:
    _DISCOVERED_LLMS_LOCK = threading.Lock()
except Exception:
    pass
_DISCOVERY_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "discovered_models.json"


__all__ = [
    "LOCAL_LLM_PROVIDERS",
    "_DISCOVERED_LLMS",
    "_DISCOVERED_LLMS_LOCK",
    "_DISCOVERY_SNAPSHOT_PATH",
    "_HTTP_CLIENTS",
    "_HTTP_CLIENTS_LOCK",
    "ChatLlamaCppClient",
    "ChatMLXClient",
    "ChatOllamaClient",
    "_classify_cloud_probe_error",
    "_convert_messages_to_dict",
    "_is_embedding_model_name",
    "_record_probe_success",
    "_shared_http_client",
    "_status_code_of",
    "check_llamacpp_status",
    "check_mlx_status",
    "check_ollama_status",
    "close_local_llm_clients",
    "discover_llamacpp_cache_models",
    "discover_mlx_cache_models",
    "discover_ollama_cli_models",
    "discover_hf_hub_gguf_models",
    "get_discovered_llms",
    "get_global_semaphore",
    "httpx",
    "is_reasoning_model",
    "is_small_model",
    "load_discovery_snapshot",
    "local_cap_kwargs",
    "merge_discovered_llms",
    "probe_cloud_llm",
    "probe_local_llm_server",
    "save_discovery_snapshot",
    "seed_local_model_discovery",
    "verification_cap_kwargs",
]
