"""
TRUSTRAG API — Model discovery & local provider status endpoints.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config.model_config import get_model_config
from app.core.config.settings import get_ports, get_settings
from app.core.observability.logging import get_logger
from app.core.system import memory as memory_mod
from app.core.system.hardware import get_cached_hardware_profile
from app.llm.local_llm import (
    check_llamacpp_status,
    check_mlx_status,
    check_ollama_status,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


async def _safe_provider_status(check_fn, base_url: str, provider: str) -> dict[str, Any]:
    """Run a provider status check without ever raising.

    The Playground renders its model dropdown AND the offline warning from
    this endpoint: a 500 here means an empty list with no warning, which reads
    as a broken UI. Degrade to an explicit disconnected stub instead.
    """
    try:
        return await check_fn(base_url)
    except Exception:
        logger.warning("Provider status check failed; degrading to stub", provider=provider)
        return {
            "connected": False,
            "provider": provider,
            "base_url": base_url,
            "models": [],
            "default_model": "",
            "error": "PROVIDER_UNREACHABLE",
        }


async def _safe_hardware_profile() -> dict[str, Any]:
    try:
        return await asyncio.to_thread(get_cached_hardware_profile)
    except Exception as exc:
        logger.warning("Hardware profile failed; degrading to empty", error=str(exc))
        return {}


@router.get("/providers", summary="Get status of AI providers and available models")
async def get_providers_endpoint(
    _user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Return connection status, detected models, and configuration for all supported LLM providers.
    Allows frontend to dynamically display online status and populate model dropdowns.

    Requires authentication — the response includes internal base URLs
    (ollama_base_url, llamacpp_base_url) which must not be publicly exposed.
    """
    settings = get_settings()
    cfg = get_model_config()

    # Concurrent: each check retries once internally, so sequential awaits
    # would triple the worst-case latency of this 8 s-polled endpoint.
    ollama_info, llamacpp_info, mlx_info = await asyncio.gather(
        _safe_provider_status(check_ollama_status, settings.ollama_base_url, "ollama"),
        _safe_provider_status(check_llamacpp_status, settings.llamacpp_base_url, "llama_cpp"),
        _safe_provider_status(check_mlx_status, settings.mlx_base_url, "mlx"),
    )

    # Embeddings are single-engine (ONNX BGE from models.yaml) — no provider
    # choice. The UI renders this as a fixed badge, not a selector.
    # NOTE: `embedding_providers` (plural choice map) was removed — single
    # default only. `embedding` below is informational (what is active).
    embedding_info = {
        "provider": "onnx",
        "name": "ONNX BGE (local, torch-free)",
        "type": "local",
        "connected": True,
        "default_model": cfg.embedding_model,
        "model": cfg.embedding_model,
        "dim": cfg.embedding_dimensionality,
    }

    return {
        "active_provider": cfg.llm_provider,
        "active_model": cfg.llm_model,
        "active_embedding_provider": "onnx",
        "active_embedding_model": cfg.embedding_model,
        # Canonical port registry (repo-root config/ports.yaml)
        "ports": get_ports(),
        "providers": {
            "ollama": {
                "name": "Ollama (Local)",
                "type": "local",
                "connected": ollama_info.get("connected", False),
                "base_url": settings.ollama_base_url,
                "default_model": ollama_info.get("default_model", ""),
                "models": ollama_info.get("models", []),
                "error": ollama_info.get("error"),
            },
            "llama_cpp": {
                "name": "llama.cpp (Local)",
                "type": "local",
                "connected": llamacpp_info.get("connected", False),
                "base_url": settings.llamacpp_base_url,
                "default_model": llamacpp_info.get("default_model", ""),
                "models": llamacpp_info.get("models", []),
                "cache_models": llamacpp_info.get("cache_models", []),
                "error": llamacpp_info.get("error"),
            },
            "mlx": {
                "name": "MLX (Local, Apple Silicon)",
                "type": "local",
                "connected": mlx_info.get("connected", False),
                "base_url": settings.mlx_base_url,
                "default_model": mlx_info.get("default_model", ""),
                "models": mlx_info.get("models", []),
                "cache_models": mlx_info.get("cache_models", []),
                "error": mlx_info.get("error"),
            },
            "gemini": {
                "name": "Google Gemini (Cloud)",
                "type": "cloud",
                "connected": bool(settings.gemini_api_key),
                # Single source of truth: models.yaml llm.supported_models_gemini
                # + llm.model_gemini. A yaml edit propagates here with no code change.
                "default_model": cfg.llm_model
                if cfg.llm_provider == "gemini"
                else cfg.llm_model_for("gemini"),
                "models": cfg.supported_gemini_models,
            },
        },
        "embedding": embedding_info,
        "hardware": await _safe_hardware_profile(),
    }


@router.get("/hardware", summary="Hardware acceleration and resource health profile")
async def get_hardware_endpoint(
    _user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Return host hardware profile, GPU/MPS acceleration status, and system health recommendations.
    """
    # Offloaded: on a cache miss this shells out to `nvidia-smi` / `vm_stat`
    # synchronously (hardware.py), which blocks the whole event loop for up to
    # ~10s — stalling every in-flight request and SSE heartbeat, not just this
    # one. main.py's startup warmup already wraps the same call in to_thread.
    return await asyncio.to_thread(get_cached_hardware_profile)


@router.post("/memory/trim", summary="Trigger proactive heap compaction and GC")
async def trim_memory_endpoint(
    _user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Manually invoke garbage collection and glibc malloc_trim to free resident memory.
    """
    before_mb = memory_mod.get_memory_usage_mb()
    await asyncio.to_thread(memory_mod.trim_memory)
    after_mb = memory_mod.get_memory_usage_mb()
    return {
        "status": "ok",
        "before_mb": before_mb,
        "after_mb": after_mb,
        "freed_mb": round(max(0.0, before_mb - after_mb), 2),
    }
