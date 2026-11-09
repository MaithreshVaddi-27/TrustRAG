"""
TRUSTRAG — Local LLM providers sub-package.

Public API re-exported from focused modules:

- ``app.llm.providers.base`` — shared HTTP client pooling & message conversion
- ``app.llm.providers.capabilities`` — output caps, small/reasoning model detection
- ``app.llm.providers.ollama`` — ``ChatOllamaClient``
- ``app.llm.providers.llama_cpp`` — ``ChatLlamaCppClient``
- ``app.llm.providers.mlx`` — ``ChatMLXClient`` (alias for llama.cpp client)
- ``app.llm.providers.discovery`` — model discovery via CLI + snapshot persistence
- ``app.llm.providers.health`` — provider status/probe functions
"""

from __future__ import annotations

from app.llm.providers.base import (
    _HTTP_CLIENTS,
    _HTTP_CLIENTS_LOCK,
    _convert_messages_to_dict,
    _shared_http_client,
    close_local_llm_clients,
)
from app.llm.providers.capabilities import (  # noqa: F401
    LOCAL_LLM_PROVIDERS,
    _is_embedding_model_name,
    is_reasoning_model,
    is_small_model,
    local_cap_kwargs,
    verification_cap_kwargs,
)
from app.llm.providers.discovery import (
    _DISCOVERED_LLMS,
    _DISCOVERED_LLMS_LOCK,
    _DISCOVERY_SNAPSHOT_PATH,
    discover_llamacpp_cache_models,
    discover_mlx_cache_models,
    discover_ollama_cli_models,
    get_discovered_llms,
    load_discovery_snapshot,
    merge_discovered_llms,
    save_discovery_snapshot,
    seed_local_model_discovery,
)
from app.llm.providers.health import (  # noqa: F401
    _classify_cloud_probe_error,
    _record_probe_success,
    _status_code_of,
    check_llamacpp_status,
    check_mlx_status,
    check_ollama_status,
    probe_cloud_llm,
)
from app.llm.providers.llama_cpp import (
    ChatLlamaCppClient,
)
from app.llm.providers.mlx import (
    ChatMLXClient,
)
from app.llm.providers.ollama import (
    ChatOllamaClient,
)

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
    "_convert_messages_to_dict",
    "_shared_http_client",
    "_status_code_of",
    "close_local_llm_clients",
    "discover_llamacpp_cache_models",
    "discover_mlx_cache_models",
    "discover_ollama_cli_models",
    "get_discovered_llms",
    "is_reasoning_model",
    "is_small_model",
    "load_discovery_snapshot",
    "local_cap_kwargs",
    "merge_discovered_llms",
    "probe_cloud_llm",
    "save_discovery_snapshot",
    "seed_local_model_discovery",
    "verification_cap_kwargs",
]
