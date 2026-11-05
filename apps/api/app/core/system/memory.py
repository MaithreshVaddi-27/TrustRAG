"""
TRUSTRAG — High-Efficiency Memory Management Utility.

Provides:
  - Explicit garbage collection and heap compaction
  - glibc malloc_trim for Linux containers (Render, Docker)
  - Memory usage telemetry and leak prevention (current RSS via psutil)
"""

from __future__ import annotations

import gc
import sys
from typing import Any

from app.core.observability.logging import get_logger

logger = get_logger(__name__)

# Optional psutil for accurate current RSS; falls back to resource.ru_maxrss (peak).
# `resource` is Unix-only: on Windows without psutil the import itself would
# crash module load, so guard it (get_memory_usage_mb() then returns 0.0).
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

try:
    import resource  # type: ignore[import]
except ImportError:  # Windows without psutil
    resource = None  # type: ignore[assignment]


def trim_memory() -> None:
    """
    Force Python garbage collection and release freed memory back to the OS.

    - Linux: glibc malloc_trim(0) forces releasing heap pages.
    - Windows: psapi.EmptyWorkingSet trims unreferenced working set pages.
    """
    gc.collect()
    if sys.platform.startswith("linux"):
        try:
            import ctypes

            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except Exception as exc:
            logger.debug("malloc_trim skipped", error=str(exc))
    elif sys.platform == "win32":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.EmptyWorkingSet(handle)
        except Exception as exc:
            logger.debug("EmptyWorkingSet skipped", error=str(exc))


def get_memory_usage_mb() -> float:
    """Return the CURRENT resident set size (RSS) memory in megabytes.

    Uses psutil when available (accurate current RSS). Falls back to native OS
    telemetry (psapi.GetProcessMemoryInfo on Windows, resource.ru_maxrss on POSIX).
    """
    if _PSUTIL_AVAILABLE:
        try:
            process = psutil.Process()
            rss_bytes = process.memory_info().rss
            return float(round(rss_bytes / (1024 * 1024), 2))
        except Exception as exc:
            logger.debug("psutil RSS read failed; falling back to native telemetry", error=str(exc))

    # Windows native fallback via psapi.GetProcessMemoryInfo
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):  # noqa: N801
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            ):
                return round(counters.WorkingSetSize / (1024 * 1024), 2)
        except Exception:
            return 0.0

    # Fallback: resource.ru_maxrss (PEAK RSS, not current)
    if resource is not None:
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On macOS ru_maxrss is in bytes, on Linux it is in kilobytes
            if sys.platform == "darwin":
                return round(usage / (1024 * 1024), 2)
            return round(usage / 1024, 2)
        except Exception:
            logger.debug("resource.getrusage read failed")
            return 0.0

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
