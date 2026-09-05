"""
TRUSTRAG API — Model discovery & local provider status endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import get_model_config, get_settings
from app.core.hardware import get_cached_hardware_profile
from app.core.local_llm import check_llamacpp_status, check_ollama_status

router = APIRouter(prefix="/models", tags=["models"])


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

    ollama_info = await check_ollama_status(settings.ollama_base_url)
    llamacpp_info = await check_llamacpp_status(settings.llamacpp_base_url)

    # Explicit user-configured LLM models
    target_ollama_models = ["granite4.2:3b-q4_K_M", "qwen3.5:4b", "gemma4:e2b-it-qat"]
    for m in reversed(target_ollama_models):
        if m not in ollama_info.get("models", []):
            ollama_info["models"] = [m, *ollama_info.get("models", [])]

    target_llamacpp_models = [
        "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M",
        "psychopenguin/Qwen3.5-4B-Q4_K_M-GGUF:Q4_K_M",
        "google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0",
    ]
    for m in reversed(target_llamacpp_models):
        if m not in llamacpp_info.get("models", []):
            llamacpp_info["models"] = [m, *llamacpp_info.get("models", [])]

    # Embedding models list
    ollama_emb_models = ollama_info.get("embedding_models", [])
    if "embeddinggemma:300m-qat-q8_0" not in ollama_emb_models:
        ollama_emb_models = ["embeddinggemma:300m-qat-q8_0", *ollama_emb_models]

    embedding_providers = {
        "huggingface": {
            "name": "Local Hugging Face (PyTorch / BGE)",
            "type": "local",
            "connected": True,
            "default_model": "BAAI/bge-small-en-v1.5",
            "models": [
                {
                    "id": "BAAI/bge-small-en-v1.5",
                    "name": "BAAI/bge-small-en-v1.5 (384d SOTA)",
                    "dim": 384,
                    "tag": "Recommended",
                },
                {
                    "id": "sentence-transformers/all-MiniLM-L6-v2",
                    "name": "all-MiniLM-L6-v2 (384d Fast)",
                    "dim": 384,
                    "tag": "Fast",
                },
            ],
        },
        "ollama": {
            "name": "Local Ollama Embeddings",
            "type": "local",
            "connected": ollama_info.get("connected", False),
            "default_model": "embeddinggemma:300m-qat-q8_0",
            "models": [
                {
                    "id": "embeddinggemma:300m-qat-q8_0",
                    "name": "embeddinggemma:300m-qat-q8_0 (768d)",
                    "dim": 768,
                    "tag": "Ollama SOTA",
                },
            ]
            + [
                {"id": m, "name": f"{m} (768d)", "dim": 768, "tag": "Local Ollama"}
                for m in ollama_emb_models
                if m != "embeddinggemma:300m-qat-q8_0"
            ],
        },
        "llamacpp": {
            "name": "Local llama.cpp Embeddings",
            "type": "local",
            "connected": llamacpp_info.get("connected", False),
            "default_model": "ggml-org/embeddinggemma-300M-GGUF:Q8_0",
            "models": [
                {
                    "id": "ggml-org/embeddinggemma-300M-GGUF:Q8_0",
                    "name": "embeddinggemma-300M (768d GGUF)",
                    "dim": 768,
                    "tag": "llama.cpp Cache",
                },
            ],
        },
        "google_genai": {
            "name": "Google Gemini (Cloud)",
            "type": "cloud",
            "connected": bool(settings.gemini_api_key),
            "default_model": "models/gemini-embedding-001",
            "models": [
                {
                    "id": "models/gemini-embedding-001",
                    "name": "gemini-embedding-001 (384d Matryoshka)",
                    "dim": 384,
                    "tag": "Google API",
                },
            ],
        },
        "nvidia": {
            "name": "NVIDIA NIM (Cloud)",
            "type": "cloud",
            "connected": bool(settings.nvidia_api_key),
            "default_model": "nvidia/nv-embedqa-e5-v5",
            "models": [
                {
                    "id": "nvidia/nv-embedqa-e5-v5",
                    "name": "nv-embedqa-e5-v5 (384d)",
                    "dim": 384,
                    "tag": "NVIDIA Cloud",
                },
            ],
        },
    }

    return {
        "active_provider": cfg.llm_provider,
        "active_model": cfg.llm_model,
        "active_embedding_provider": cfg.embedding_provider,
        "active_embedding_model": cfg.embedding_model,
        "providers": {
            "ollama": {
                "name": "Ollama (Local)",
                "type": "local",
                "connected": ollama_info.get("connected", False),
                "base_url": settings.ollama_base_url,
                "default_model": settings.ollama_model
                or ollama_info.get("default_model", "gemma4:e2b"),
                "models": ollama_info.get("models", ["gemma4:e2b"]),
                "error": ollama_info.get("error"),
            },
            "llama_cpp": {
                "name": "llama.cpp (Local)",
                "type": "local",
                "connected": llamacpp_info.get("connected", False),
                "base_url": settings.llamacpp_base_url,
                "default_model": settings.llamacpp_model or "gemma-4-E2B-it-qat-q4_0-gguf:Q4_0",
                "models": llamacpp_info.get("models", ["gemma-4-E2B-it-qat-q4_0-gguf:Q4_0"]),
                "cache_models": llamacpp_info.get("cache_models", []),
                "error": llamacpp_info.get("error"),
            },
            "gemini": {
                "name": "Google Gemini (Cloud)",
                "type": "cloud",
                "connected": bool(settings.gemini_api_key),
                "default_model": cfg.llm_model
                if cfg.llm_provider == "gemini"
                else "gemini-3.5-flash-lite",
                "models": [
                    "gemini-3.5-flash-lite",
                    "gemini-2.5-flash",
                    "gemini-2.5-pro",
                ],
            },
            "nvidia": {
                "name": "NVIDIA NIM (Cloud)",
                "type": "cloud",
                "connected": bool(settings.nvidia_api_key),
                "default_model": "meta/llama-3.3-70b-instruct",
                "models": [
                    "meta/llama-3.3-70b-instruct",
                    "mistralai/mistral-large-2-instruct",
                    "nvidia/llama-3.1-nemotron-70b-instruct",
                ],
            },
        },
        "embedding_providers": embedding_providers,
        "hardware": get_cached_hardware_profile(),
    }


@router.get("/hardware", summary="Hardware acceleration and resource health profile")
async def get_hardware_endpoint(
    _user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Return host hardware profile, GPU/MPS acceleration status, and system health recommendations.
    """
    return get_cached_hardware_profile()


@router.post("/memory/trim", summary="Trigger proactive heap compaction and GC")
async def trim_memory_endpoint(
    _user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Manually invoke garbage collection and glibc malloc_trim to free resident memory.
    """
    import asyncio

    from app.core.memory import get_memory_usage_mb, trim_memory

    before_mb = get_memory_usage_mb()
    await asyncio.to_thread(trim_memory)
    after_mb = get_memory_usage_mb()
    return {
        "status": "ok",
        "before_mb": before_mb,
        "after_mb": after_mb,
        "freed_mb": round(max(0.0, before_mb - after_mb), 2),
    }
