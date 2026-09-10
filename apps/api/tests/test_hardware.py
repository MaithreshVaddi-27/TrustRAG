"""
Tests for hardware acceleration detection, memory profiling, and model recommendations.
"""

import platform
import shutil
import sys

from app.core.hardware import (
    detect_hardware_profile,
    get_llamacpp_launch_args,
    get_optimal_torch_device,
    get_system_memory_info,
)
from app.core.memory import (
    check_and_enforce_memory_guard,
    get_memory_usage_mb,
    trim_memory,
)


def test_get_optimal_torch_device():
    dev = get_optimal_torch_device()
    assert dev in ("cuda", "mps", "cpu")


def test_get_system_memory_info():
    mem = get_system_memory_info()
    assert "total_gb" in mem
    assert "free_gb" in mem
    assert "used_gb" in mem
    assert "usage_pct" in mem
    assert mem["total_gb"] > 0


def test_llamacpp_launch_args_fit_host():
    args = get_llamacpp_launch_args()
    # Always ends with context + slots budgets, both within this host's memory.
    assert args[-4] == "-c"
    assert int(args[-3]) in (4096, 8192, 16384)
    assert args[-2] == "-np"
    assert int(args[-1]) in (2, 4)
    # Full-GPU offload must be expressed as concrete tokens llama.cpp parses.
    if sys.platform == "darwin" and platform.machine() == "arm64":
        assert "-ngl" in args and "all" in args
        fa_i = args.index("--flash-attn")
        assert args[fa_i + 1] == "on"
        # Lean-RAM: quantized KV cache halves KV memory; travels with flash-attn.
        assert args[args.index("-ctk") + 1] == "q8_0"
        assert args[args.index("-ctv") + 1] == "q8_0"


def test_llamacpp_cpu_path_has_no_kv_quant_flags(monkeypatch):
    """CPU-only hosts get no GPU flags (quantized KV needs flash-attn)."""
    import app.core.hardware as hw

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(shutil, "which", lambda *a, **k: None)
    monkeypatch.setattr(
        hw,
        "get_system_memory_info",
        lambda: {"total_gb": 8.0, "free_gb": 4.0, "used_gb": 4.0, "usage_pct": 50.0},
    )
    args = hw.get_llamacpp_launch_args()
    assert "-ctk" not in args and "-ctv" not in args
    assert args[-4:] == ["-c", "4096", "-np", "2"]


def test_detect_hardware_profile():
    profile = detect_hardware_profile()
    assert "os" in profile
    assert "accelerator" in profile
    assert "accelerator_name" in profile
    assert "memory" in profile
    assert "recommendations" in profile
    assert "primary_llm" in profile["recommendations"]
    assert "primary_embedding" in profile["recommendations"]
    assert profile["recommendations"]["max_concurrency"] >= 1
    assert "health" in profile


def test_memory_utilities():
    rss = get_memory_usage_mb()
    assert isinstance(rss, float)
    assert rss >= 0.0

    # Ensure trim_memory executes without raising exceptions
    trim_memory()

    # Test guard check
    guard = check_and_enforce_memory_guard(max_rss_mb=100000.0)
    assert "rss_mb" in guard
    assert guard["status"] == "healthy"
