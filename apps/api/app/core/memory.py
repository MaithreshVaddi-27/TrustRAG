"""
TRUSTRAG — High-Efficiency Memory Management Utility.

Provides:
  - Explicit garbage collection and heap compaction
  - glibc malloc_trim for Linux containers (Render, Docker)
  - Memory usage telemetry and leak prevention
"""

from __future__ import annotations

import gc
import sys
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def trim_memory() -> None:
    """
    Force Python garbage collection and release freed memory back to the OS.

    On Linux containers (such as Render 512MB free tier), glibc's memory allocator
    often retains freed pages in the process arena instead of returning them to the kernel.
    Invoking malloc_trim(0) forces glibc to release unused heap memory back to the OS,
    preventing artificial memory creep and OOM kills.
    """
    gc.collect()
    if sys.platform.startswith("linux"):
        try:
            import ctypes

            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except Exception as exc:
            logger.debug("malloc_trim skipped", error=str(exc))


def get_memory_usage_mb() -> float:
    """Return the current resident set size (RSS) memory in megabytes."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On macOS ru_maxrss is in bytes, on Linux it is in kilobytes
        if sys.platform == "darwin":
            return round(usage / (1024 * 1024), 2)
        return round(usage / 1024, 2)
    except Exception:
        return 0.0


def check_and_enforce_memory_guard(max_rss_mb: float = 3000.0) -> dict[str, Any]:
    """
    Check current process memory RSS and system pressure.
    If usage is elevated or exceeds threshold, trigger proactive heap compaction.
    """
    rss = get_memory_usage_mb()
    trimmed = False
    if rss > max_rss_mb:
        trim_memory()
        trimmed = True
        logger.info(
            "Memory guard triggered proactive heap compaction", rss_mb=rss, max_threshold=max_rss_mb
        )

    return {
        "rss_mb": rss,
        "trimmed": trimmed,
        "status": "warning" if rss > max_rss_mb else "healthy",
    }
