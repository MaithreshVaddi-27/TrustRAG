"""
TRUSTRAG — Hardware Acceleration & System Health Intelligence Engine.

Automatically detects host architecture (Apple Silicon Metal/MPS, NVIDIA CUDA, CPU),
evaluates available memory tiers, auto-tunes PyTorch/inference devices, and provides
proactive memory guardrails to maintain system health and responsiveness.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def get_optimal_torch_device() -> str:
    """
    Determine the highest-performance acceleration device available for PyTorch/Embeddings.
    Returns:
        'cuda': If an NVIDIA GPU with CUDA is available.
        'mps':  If Apple Silicon Metal Performance Shaders is available.
        'cpu':  Fallback to multi-threaded CPU.
    """
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and torch.backends.mps.is_built():
            return "mps"
    except Exception as exc:
        logger.debug("Torch device detection fallback to cpu", error=str(exc))

    return "cpu"


def get_system_memory_info() -> dict[str, Any]:
    """
    Inspect total and available system memory across macOS, Linux, and Windows.
    Uses native OS system calls without external C-extension dependencies.
    """
    total_bytes = 0
    free_bytes = 0

    try:
        # Standard POSIX memory sizing
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        total_bytes = page_size * phys_pages
    except Exception:
        total_bytes = 8 * (1024**3)  # Safe default 8GB

    # macOS free memory calculation via vm_stat
    if sys.platform == "darwin":
        try:
            vm = subprocess.check_output(["vm_stat"], stderr=subprocess.DEVNULL).decode()
            v_page_size = 4096
            free_pages = 0
            speculative_pages = 0
            for line in vm.splitlines():
                if "page size of" in line:
                    v_page_size = int(line.split()[7])
                elif "Pages free:" in line:
                    free_pages = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages speculative:" in line:
                    speculative_pages = int(line.split(":")[1].strip().rstrip("."))
            free_bytes = (free_pages + speculative_pages) * v_page_size
        except Exception:
            free_bytes = int(total_bytes * 0.25)
    # Linux free memory via /proc/meminfo
    elif sys.platform.startswith("linux") and os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        free_bytes = int(line.split()[1]) * 1024
                        break
        except Exception:
            free_bytes = int(total_bytes * 0.25)
    else:
        free_bytes = int(total_bytes * 0.3)

    total_gb = round(total_bytes / (1024**3), 2)
    free_gb = round(free_bytes / (1024**3), 2)
    used_gb = round(max(0.0, total_gb - free_gb), 2)
    usage_pct = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 50.0

    return {
        "total_gb": total_gb,
        "free_gb": free_gb,
        "used_gb": used_gb,
        "usage_pct": usage_pct,
    }


def detect_hardware_profile() -> dict[str, Any]:
    """
    Introspect full system hardware topology, accelerator capabilities, and memory.
    Generates intelligent model and concurrency recommendations tailored to the host.
    """
    os_name = platform.system()
    machine = platform.machine()
    device = get_optimal_torch_device()
    mem = get_system_memory_info()

    # Detailed device identity
    device_label = "Optimized Multi-Threaded CPU"
    vram_gb: float | None = None

    if device == "cuda":
        try:
            import torch

            device_label = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            vram_gb = round(props.total_memory / (1024**3), 2)
        except Exception:
            device_label = "NVIDIA CUDA GPU"
    elif device == "mps":
        device_label = "Apple Silicon GPU (Metal Performance Shaders)"
        # On Apple Silicon, unified memory is shared between CPU and GPU
        vram_gb = mem["total_gb"]

    # Classify memory tier
    # 8GB Unified or low available memory requires lean quantized models
    total_ram = mem["total_gb"]
    if total_ram <= 8.5:
        tier = "lean_accelerated" if device in ("mps", "cuda") else "lean_cpu"
        recommended_llm = "granite4.2:3b-q4_K_M"
        recommended_llm_alt = "gemma4:e2b-it-qat"
        recommended_embedding = "embeddinggemma:300m-qat-q8_0"
        max_batch_size = 16
        max_concurrency = 2
    elif total_ram <= 16.5:
        tier = "standard_accelerated" if device in ("mps", "cuda") else "standard_cpu"
        recommended_llm = "qwen3.5:4b"
        recommended_llm_alt = "granite4.2:3b-q4_K_M"
        recommended_embedding = "embeddinggemma:300m-qat-q8_0"
        max_batch_size = 32
        max_concurrency = 4
    else:
        tier = "high_performance"
        recommended_llm = "qwen3.5:4b"
        recommended_llm_alt = "granite4.2:3b-q4_K_M"
        recommended_embedding = "embeddinggemma:300m-qat-q8_0"
        max_batch_size = 64
        max_concurrency = 8

    # System Health Evaluation
    from app.core.memory import get_memory_usage_mb

    process_rss_mb = get_memory_usage_mb()

    health_status = "optimal"
    health_notes: list[str] = []

    if mem["usage_pct"] > 92.0:
        health_status = "critical"
        health_notes.append("System memory is under heavy pressure (>92% used). Freeing background caches recommended.")
    elif mem["usage_pct"] > 85.0:
        health_status = "warning"
        health_notes.append("System memory usage is elevated (>85% used). Quantized Q4 models are advised.")
    else:
        health_notes.append("Hardware resources and memory operating within optimal parameters.")

    return {
        "os": os_name,
        "machine": machine,
        "accelerator": device,  # 'mps' | 'cuda' | 'cpu'
        "accelerator_name": device_label,
        "vram_gb": vram_gb,
        "memory": mem,
        "process_rss_mb": process_rss_mb,
        "tier": tier,
        "recommendations": {
            "primary_llm": recommended_llm,
            "secondary_llm": recommended_llm_alt,
            "primary_embedding": recommended_embedding,
            "max_batch_size": max_batch_size,
            "max_concurrency": max_concurrency,
        },
        "health": {
            "status": health_status,
            "notes": health_notes,
        },
    }
