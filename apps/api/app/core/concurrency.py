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
import weakref

from app.core.hardware import get_system_memory_info
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level semaphore and initialization lock
# Keyed by the loop *object* in a WeakKeyDictionary, not by id(loop): CPython
# reuses ids once an object is collected, so an id-keyed map can hand a semaphore
# bound to a dead loop to a brand-new one that lands on the same address. Weak
# keys also drop the entry when the loop closes.
_global_semaphores: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)
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
        logger.debug("Failed to get global semaphore, using safe fallback")
        return 3  # Safe fallback


def get_global_semaphore() -> asyncio.Semaphore:
    """
    Return the global concurrency semaphore, initializing it exactly once.

    Thread-safe initialization using a lock. The semaphore is bound to the
    current event loop at first access (asyncio.Semaphore is loop-local).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop (sync setup code). Return a detached semaphore; it
        # binds lazily on first contention, inside whichever loop awaits it.
        semaphore = asyncio.Semaphore(_compute_concurrency())
        logger.info("Initialized detached concurrency semaphore", concurrency=semaphore._value)
        return semaphore

    existing = _global_semaphores.get(loop)
    if existing is not None:
        return existing

    with _semaphore_lock:
        existing = _global_semaphores.get(loop)
        if existing is None:
            concurrency = _compute_concurrency()
            existing = asyncio.Semaphore(concurrency)
            _global_semaphores[loop] = existing
            logger.info("Initialized concurrency semaphore", concurrency=concurrency)

    return existing


async def reset_global_semaphore() -> None:
    """Reset the global semaphore (primarily for testing)."""
    with _semaphore_lock:
        _global_semaphores.clear()
