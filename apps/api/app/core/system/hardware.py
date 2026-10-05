"""
TRUSTRAG — Hardware Acceleration & System Health Intelligence Engine.

Automatically detects host architecture (Apple Silicon Metal/MPS, NVIDIA CUDA, CPU),
evaluates available memory tiers, auto-tunes PyTorch/inference devices, and provides
proactive memory guardrails to maintain system health and responsiveness.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Any

from app.core.config.model_config import get_model_config
from app.core.observability.logging import get_logger
from app.core.system.memory import get_memory_usage_mb

logger = get_logger(__name__)

# Module-level cache for hardware profile
_hardware_profile_cache: dict[str, Any] | None = None
_HARDWARE_PROFILE_TTL_SECONDS = 300  # 5 minutes


def get_llamacpp_launch_args() -> list[str]:
    """Hardware-derived llama-server launch flags.

    `llama-server` vendors its own Metal/CUDA backends (no torch dependency),
    so detection here uses platform probes, not torch. Goals: full GPU offload
    when one exists, and tighter KV-cache/thread budgets on unified-memory
    hosts so the model doesn't cook the machine.
    """
    mem = get_system_memory_info()
    total_gb = mem["total_gb"]
    is_arm_mac = sys.platform == "darwin" and platform.machine() == "arm64"

    args: list[str] = []

    # Quantized KV cache: honors optimization.kv_cache_quantization
    # (models.yaml, default q8_0 — halves KV-cache RAM with negligible quality
    # loss, community-measured). Travels with --flash-attn on — without FA the
    # server dequantizes per attention op and the saving turns into a
    # slowdown. CPU-only path keeps f16 (no FA there). Unknown values fall
    # back to q8_0 (e.g. "fp16" is not a valid llama-server k-quant).
    try:
        _kv_quant = str(get_model_config().kv_cache_quantization or "q8_0").strip().lower()
    except Exception:
        _kv_quant = "q8_0"
    if _kv_quant not in ("q8_0", "q4_0", "q4_1"):
        logger.warning(
            "Unsupported kv_cache_quantization; falling back to q8_0",
            configured=_kv_quant,
        )
        _kv_quant = "q8_0"
    kv_quant_flags = ["-ctk", _kv_quant, "-ctv", _kv_quant]

    if is_arm_mac:
        # Metal is native on Apple Silicon — no further probe needed.
        args += ["-ngl", "all", "--flash-attn", "on", *kv_quant_flags]
    elif _nvidia_smi_available():
        # CUDA only when a GPU both exists and responds.
        args += [
            "-ngl",
            "all",
            "--flash-attn",
            "on",
            *kv_quant_flags,
            "--split-mode",
            "layer",
        ]
    # else: CPU-only — no GPU flags.

    # Context + concurrency budget by available memory.
    # KV cache ~ n_embd(2048) x 2 (K/V) x n_ctx x 4B x slots; conservative.
    # llama-server divides -c evenly across -np slots, and the backend sends
    # num_ctx=4096 requests through a single serial consumer
    # (LOCAL_LLM_MAX_CONCURRENCY=1). So -np must keep n_ctx_slot >= 4096:
    # measured on 8 GB (LFM2.5-1.2B): -np 2 gives 2x2048 slots (backend
    # contexts overflow the slot) while -np 1 gives 1x4096 at the same RSS.
    if total_gb <= 8.5:
        args += ["-c", "4096", "-np", "1"]
    elif total_gb <= 16.5:
        args += ["-c", "8192", "-np", "2"]
    else:
        args += ["-c", "16384", "-np", "4"]

    return args


def get_optimal_torch_device() -> str:
    """
    Determine the highest-performance acceleration device available for PyTorch.

    Returns:
        'cuda': If an NVIDIA GPU with CUDA is available.
        'mps':  If Apple Silicon Metal Performance Shaders is available.
        'cpu':  Fallback to multi-threaded CPU.

    Torch-only by design. This helper is for the PyTorch code paths that
    genuinely need a device (currently the `sentence_transformers` CrossEncoder
    fallback in `model_registry.get_reranker`), and torch is already resident on
    those paths.

    Do NOT call this from `detect_hardware_profile()` or any other code reached
    by the ONNX ingest/serving path. Importing torch costs ~177 MB RSS, and the
    embedding stack is deliberately ONNX-based. Use `detect_accelerator()`
    there instead — it is torch-free and answers the same question.
    """
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
            and torch.backends.mps.is_built()
        ):
            return "mps"
    except Exception as exc:
        logger.debug("Torch device detection fallback to cpu", error=str(exc))

    return "cpu"


def _nvidia_smi_available() -> bool:
    """True when an NVIDIA GPU exists and `nvidia-smi` responds. Torch-free."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return False
    try:
        probe = subprocess.run(  # noqa: S603 — resolved binary path, fixed argv
            [smi],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception as exc:
        logger.debug("nvidia-smi probe failed", error=str(exc))
        return False
    if probe.returncode != 0:
        logger.debug("nvidia-smi returned non-zero; treating host as CPU-only")
        return False
    return True


def _nvidia_vram_gb() -> float | None:
    """Total GPU memory in GB, read from nvidia-smi. Torch-free."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    try:
        out = subprocess.run(  # noqa: S603 — resolved binary path, fixed argv
            [smi, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).stdout.decode()
        first = out.strip().splitlines()[0].strip()
        return round(int(first) / 1024, 2)
    except Exception as exc:
        logger.debug("nvidia-smi VRAM query failed", error=str(exc))
        return None


def detect_accelerator() -> str:
    """
    Identify the host accelerator WITHOUT importing torch.

    Returns 'cuda' | 'mps' | 'cpu'. This is the probe `detect_hardware_profile()`
    must use: the embedding path is ONNX-based, and `get_optimal_torch_device()`
    would pull ~177 MB of PyTorch into a process that has no other use for it.
    """
    # Metal is native on Apple Silicon — no probe needed, same reasoning as
    # get_llamacpp_launch_args().
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return "mps"
    if _nvidia_smi_available():
        return "cuda"
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
            vm = subprocess.check_output(
                ["/usr/sbin/vm_stat"], stderr=subprocess.DEVNULL, timeout=5
            ).decode()
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
            logger.debug("vm_stat failed, estimating free memory as 25% of total")
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
            logger.debug("/proc/meminfo read failed, estimating free memory as 25% of total")
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


# Audit MEDIUM backend-3: ingest embedding batch size follows the RAM tier so
# lean hosts never hold a 50-vector torch batch while high-RAM hosts get
# throughput (lean 32 / standard 64 / high 128).
_INGEST_EMBED_BATCH_BY_TIER = (("lean", 32), ("standard", 64), ("high", 128))


def get_ingest_embed_batch_size(default: int = 64) -> int:
    """Return the tier-appropriate ingest embedding batch size."""
    try:
        tier = str(get_cached_hardware_profile().get("tier", ""))
        for prefix, size in _INGEST_EMBED_BATCH_BY_TIER:
            if tier.startswith(prefix):
                return size
    except Exception as exc:
        logger.debug("Tier batch-size lookup failed; using default", error=str(exc))
    return default


def get_cached_hardware_profile() -> dict[str, Any]:
    """
    Get hardware profile with caching.
    Only runs the expensive subprocess probe once per TTL period.
    """
    global _hardware_profile_cache
    import time

    if _hardware_profile_cache is not None:
        # Check if cache is still valid
        cache_time = _hardware_profile_cache.get("_cache_time", 0)
        if time.time() - cache_time < _HARDWARE_PROFILE_TTL_SECONDS:
            return _hardware_profile_cache

    # Cache miss or expired - run fresh detection
    profile = detect_hardware_profile()
    profile["_cache_time"] = time.time()
    _hardware_profile_cache = profile
    return profile


def detect_hardware_profile() -> dict[str, Any]:
    """
    Introspect full system hardware topology, accelerator capabilities, and memory.
    Generates intelligent model and concurrency recommendations tailored to the host.

    Torch-free by design: the embedding/serving stack is ONNX-based, so this runs
    on the ingest hot path. See `detect_accelerator()`.
    """
    os_name = platform.system()
    machine = platform.machine()
    device = detect_accelerator()
    mem = get_system_memory_info()

    # Detailed device identity
    device_label = "Optimized Multi-Threaded CPU"
    vram_gb: float | None = None

    if device == "cuda":
        vram_gb = _nvidia_vram_gb()
        device_label = "NVIDIA CUDA GPU" if vram_gb is None else f"NVIDIA CUDA GPU ({vram_gb} GB)"
    elif device == "mps":
        device_label = "Apple Silicon GPU (Metal Performance Shaders)"
        # On Apple Silicon, unified memory is shared between CPU and GPU
        vram_gb = mem["total_gb"]

    # Classify memory tier (L-1: each tier gets weights that fit it — a 64GB
    # host must not be told to run the same model as an 8GB host). All IDs
    # come from the configured local lists in config/models.yaml.
    total_ram = mem["total_gb"]
    if total_ram <= 8.5:
        tier = "lean_accelerated" if device in ("mps", "cuda") else "lean_cpu"
        # 1B class (~1GB resident): the only safe weights for 8GB hosts.
        recommended_llm = "ibm-granite/granite-4.0-h-1b-GGUF:Q4_K_M"
        recommended_llm_alt = "gemma3:1b"  # ollama 1B fallback
        recommended_embedding = "BAAI/bge-small-en-v1.5"
        max_batch_size = 16
        max_concurrency = 2
    elif total_ram <= 16.5:
        tier = "standard_accelerated" if device in ("mps", "cuda") else "standard_cpu"
        # 3B class (~2.2GB resident): best quality that fits 16GB hosts.
        recommended_llm = "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M"
        recommended_llm_alt = "granite4.2:3b-q4_K_M"
        recommended_embedding = "BAAI/bge-small-en-v1.5"
        max_batch_size = 32
        max_concurrency = 4
    else:
        tier = "high_performance"
        # 3B class stays the local default (largest configured local weights);
        # heavy work should route to the configured cloud provider (gemini).
        recommended_llm = "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M"
        recommended_llm_alt = "ggml-org/SmolLM3-3B-GGUF:Q4_K_M"
        recommended_embedding = "BAAI/bge-small-en-v1.5"
        max_batch_size = 64
        max_concurrency = 8

    # System Health Evaluation
    process_rss_mb = get_memory_usage_mb()

    health_status = "optimal"
    health_notes: list[str] = []

    if mem["usage_pct"] > 92.0:
        health_status = "critical"
        health_notes.append(
            "System memory is under heavy pressure (>92% used). "
            "Freeing background caches recommended."
        )
    elif mem["usage_pct"] > 85.0:
        health_status = "warning"
        health_notes.append(
            "System memory usage is elevated (>85% used). Quantized Q4 models are advised."
        )
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
