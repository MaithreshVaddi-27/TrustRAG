"""
TRUSTRAG — Shared Concurrency Control.

Provides a single, hardware-aware semaphore for local LLM inference and analysis pipelines.
Both the local LLM client layer (local_llm.py) and the analysis pipeline (analysis_service.py)
use this shared semaphore to prevent overloading the single inference server.

The semaphore capacity is derived from system memory:
- <=8GB  total: 2 concurrent
- <=16GB total: 4 concurrent
- >16GB  total: 8 concurrent

Can be overridden via LOCAL_LLM_MAX_CONCURRENCY environment variable.
"""

from __future__ import annotations

import asyncio
import os
import threading

from app.core.hardware import get_system_memory_info
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level semaphore and initialization lock
_global_semaphore: asyncio.Semaphore | None = None
_semaphore_lock = threading.Lock()


def _compute_concurrency() -> int:
    """Compute the hardware-aware concurrency limit."""
    # Allow env var override (same as before)
    env_override = os.getenv("LOCAL_LLM_MAX_CONCURRENCY")
    if env_override:
        try:
            return int(env_override)
        except ValueError:
            logger.warning(
                "Invalid LOCAL_LLM_MAX_CONCURRENCY value, using hardware default",
                value=env_override,
            )

    # Hardware-aware default
    try:
        total_gb = get_system_memory_info().get("total_gb", 8)
        if total_gb <= 8.5:
            return 2
        elif total_gb <= 16.5:
            return 4
        return 8
    except Exception:
        return 3  # Safe fallback


def get_global_semaphore() -> asyncio.Semaphore:
    """
    Return the global concurrency semaphore, initializing it exactly once.

    Thread-safe initialization using a lock. The semaphore is bound to the
    current event loop at first access (asyncio.Semaphore is loop-local).
    """
    global _global_semaphore

    # Fast path: already initialized
    if _global_semaphore is not None:
        return _global_semaphore

    # Slow path: initialize under lock
    with _semaphore_lock:
        if _global_semaphore is None:
            concurrency = _compute_concurrency()
            _global_semaphore = asyncio.Semaphore(concurrency)
            logger.info("Initialized global concurrency semaphore", concurrency=concurrency)

    return _global_semaphore


async def reset_global_semaphore() -> None:
    """Reset the global semaphore (primarily for testing)."""
    global _global_semaphore
    with _semaphore_lock:
        _global_semaphore = None
