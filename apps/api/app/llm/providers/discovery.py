"""
TRUSTRAG — Local LLM provider: model discovery.

Runtime discovery of locally-installed generative models via CLI tools
(ollama list, llama-server --cache-list, MLX HF scan). Includes persistence
to/from a JSON snapshot file so later-started processes seed identically.
"""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress
from pathlib import Path

from app.observability.logging import get_logger
from app.llm.providers.capabilities import _is_embedding_model_name

logger = get_logger(__name__)

__all__ = [
    "_DISCOVERED_LLMS",
    "_DISCOVERED_LLMS_LOCK",
    "_DISCOVERY_SNAPSHOT_PATH",
    "_is_embedding_model_name",
    "discover_llamacpp_cache_models",
    "discover_mlx_cache_models",
    "discover_hf_hub_gguf_models",
    "discover_ollama_cli_models",
    "load_discovery_snapshot",
    "merge_discovered_llms",
    "save_discovery_snapshot",
    "seed_local_model_discovery",
]


# Lazy imports to avoid circular import with app.llm.local_llm
def _get_state():
    import app.llm.local_llm as m
    return m._DISCOVERED_LLMS, m._DISCOVERED_LLMS_LOCK, m._DISCOVERY_SNAPSHOT_PATH


# Backward-compat properties for __init__.py to import
@property
def _DISCOVERED_LLMS():
    return _get_state()[0]


@property
def _DISCOVERED_LLMS_LOCK():
    return _get_state()[1]


@property
def _DISCOVERY_SNAPSHOT_PATH():
    return _get_state()[2]


def merge_discovered_llms(provider: str, models: list[str], replace: bool = False) -> None:
    """Cache live-discovered GENERATIVE model ids for a local provider.

    With ``replace=True`` the bucket is replaced by the fresh authoritative
    list (used when live CLI/API discovery succeeded) so uninstalled models
    stop being offered. An empty fresh list never wipes the cache — a
    transient discovery failure must not break in-flight request validation.
    """
    _DISCOVERED_LLMS, _DISCOVERED_LLMS_LOCK, _ = _get_state()
    clean = [m for m in models if m and not _is_embedding_model_name(m)]
    if not clean:
        return
    with _DISCOVERED_LLMS_LOCK:
        if replace:
            _DISCOVERED_LLMS[provider] = set(clean)
        else:
            bucket = _DISCOVERED_LLMS.setdefault(provider, set())
            bucket.update(clean)


def get_discovered_llms(provider: str) -> frozenset[str]:
    """Return cached live-discovered model ids for a provider (empty if unknown)."""
    _DISCOVERED_LLMS, _DISCOVERED_LLMS_LOCK, _ = _get_state()
    with _DISCOVERED_LLMS_LOCK:
        return frozenset(_DISCOVERED_LLMS.get(provider, set()))


def save_discovery_snapshot() -> None:
    """Persist the current discovered-model cache for later processes."""
    _DISCOVERED_LLMS, _DISCOVERED_LLMS_LOCK, _DISCOVERY_SNAPSHOT_PATH = _get_state()
    with _DISCOVERED_LLMS_LOCK:
        payload = {
            "providers": {
                provider: sorted(models) for provider, models in _DISCOVERED_LLMS.items()
            },
        }
    try:
        _DISCOVERY_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = _DISCOVERY_SNAPSHOT_PATH.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(_DISCOVERY_SNAPSHOT_PATH)
        logger.debug("Persisted model discovery snapshot", path=str(_DISCOVERY_SNAPSHOT_PATH))
    except Exception as exc:
        logger.debug("Failed to persist model discovery snapshot", error=str(exc))


def load_discovery_snapshot() -> None:
    """Seed the in-process discovery cache from a previously-persisted snapshot."""
    _, _, _DISCOVERY_SNAPSHOT_PATH = _get_state()
    try:
        data = json.loads(_DISCOVERY_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except Exception:
        logger.debug("Failed to load model discovery snapshot", exc_info=True)
        return
    providers = data.get("providers", {}) if isinstance(data, dict) else {}
    for provider, models in providers.items():
        if isinstance(models, list):
            merge_discovered_llms(str(provider), [str(m) for m in models])


async def discover_ollama_cli_models() -> list[str]:
    """Run 'ollama list' CLI and return installed GENERATIVE model names only."""
    llm_models: list[str] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama",
            "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
        except TimeoutError:
            with suppress(Exception):
                proc.kill()
                await proc.wait()
            raise
        if proc.returncode == 0:
            lines = stdout.decode().strip().split("\n")
            for line in lines[1:]:
                parts = line.split()
                if parts and not _is_embedding_model_name(parts[0]):
                    llm_models.append(parts[0])
    except Exception:
        logger.debug("Failed to run 'ollama list' CLI", exc_info=True)
    return llm_models


async def discover_llamacpp_cache_models() -> list[str]:
    """Run 'llama-server --cache-list' CLI and return cached GENERATIVE model IDs only."""
    cache_models: list[str] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "llama-server",
            "--cache-list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
        except TimeoutError:
            with suppress(Exception):
                proc.kill()
                await proc.wait()
            raise
        if proc.returncode == 0:
            lines = stdout.decode().strip().split("\n")
            for line in lines:
                match = re.search(r"^\s*\d+\.\s*(.+)$", line)
                if match:
                    name = match.group(1).strip()
                    if not _is_embedding_model_name(name):
                        cache_models.append(name)
    except Exception:
        logger.debug("Failed to run 'llama-server --cache-list' CLI", exc_info=True)
    return cache_models


def discover_mlx_cache_models() -> list[str]:
    """Scan the local HuggingFace cache for downloaded MLX weights.

    MLX models ship as `.safetensors` (not GGUF), so the GGUF scan misses
    them. Matches `mlx-community` builds and any repo id containing `mlx`
    (case-insensitive); embedding models are filtered out by callers.
    Apple Silicon only — elsewhere the cache simply won't contain any.
    """
    mlx_models: list[str] = []
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        for model_dir in hf_cache.glob("models--*"):
            dir_name = model_dir.name.replace("models--", "").replace("--", "/")
            if "mlx" in dir_name.lower() and "gguf" not in dir_name.lower():
                mlx_models.append(dir_name)
    return sorted(set(mlx_models))


def discover_hf_hub_gguf_models() -> list[str]:
    """Scan local HuggingFace cache for any downloaded GGUF blobs or models."""
    gguf_models: list[str] = []
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        for model_dir in hf_cache.glob("models--*"):
            dir_name = model_dir.name.replace("models--", "").replace("--", "/")
            if "gguf" in dir_name.lower():
                gguf_models.append(dir_name)
    return gguf_models


async def seed_local_model_discovery() -> dict[str, list[str]]:
    """Discover locally-installed GENERATIVE models and warm the shared cache."""
    load_discovery_snapshot()

    # Import lazily so test monkeypatches on app.llm.local_llm take effect
    import app.llm.local_llm as _llm_mod

    ollama_models = [
        m for m in await _llm_mod.discover_ollama_cli_models() if not _is_embedding_model_name(m)
    ]
    llamacpp_models = [
        m for m in await _llm_mod.discover_llamacpp_cache_models() if not _is_embedding_model_name(m)
    ]
    mlx_models = [m for m in _llm_mod.discover_mlx_cache_models() if not _is_embedding_model_name(m)]

    merge_discovered_llms("ollama", ollama_models)
    merge_discovered_llms("llama_cpp", llamacpp_models)
    merge_discovered_llms("mlx", mlx_models)
    save_discovery_snapshot()

    return {"ollama": ollama_models, "llama_cpp": llamacpp_models, "mlx": mlx_models}
