"""
Tests for hardware acceleration detection, memory profiling, and model recommendations.
"""

import platform
import shutil
import sys

import pytest

from app.core.hardware import (
    detect_accelerator,
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


def test_detect_accelerator_is_torch_free():
    """detect_accelerator() must answer the device question without importing
    torch. The embedding stack is ONNX-based, so torch has no business being
    resident on that path (see test_detect_hardware_profile_does_not_import_torch)."""
    dev = detect_accelerator()
    assert dev in ("cuda", "mps", "cpu")


class _TorchImportTrap(BaseException):
    """Derives from BaseException on purpose.

    get_optimal_torch_device() wraps `import torch` in `except Exception`, so a
    trap raising AssertionError would be swallowed and the call would silently
    fall back to "cpu" — making the test pass against the very regression it
    guards. BaseException escapes that handler.
    """


def _install_torch_trap(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _trapped(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise _TorchImportTrap(
                "torch was imported on the ONNX hardware-detection path "
                "(~177 MB RSS regression, audit B-1)"
            )
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _trapped)
    # Drop any cached profile so detection actually re-runs under the trap.
    monkeypatch.setattr("app.core.hardware._hardware_profile_cache", None, raising=False)


def test_detect_hardware_profile_does_not_import_torch(monkeypatch):
    """Regression (audit B-1): the ingest path reached `import torch` via
    get_ingest_embed_batch_size -> get_cached_hardware_profile ->
    detect_hardware_profile -> get_optimal_torch_device, costing ~177 MB RSS on
    an ONNX-only host."""
    _install_torch_trap(monkeypatch)
    profile = detect_hardware_profile()
    assert profile["accelerator"] in ("cuda", "mps", "cpu")
    assert profile["tier"]
    assert profile["recommendations"]["primary_embedding"]


def test_ingest_batch_size_path_is_torch_free(monkeypatch):
    """The consumer that actually dragged torch in must stay clean too."""
    from app.core.hardware import get_ingest_embed_batch_size

    _install_torch_trap(monkeypatch)
    assert get_ingest_embed_batch_size() > 0


def test_torch_trap_actually_has_teeth(monkeypatch):
    """Meta-test: the guard above must FAIL if the torch path is reintroduced.

    Without this, a broad `except Exception` anywhere on the path would silently
    neutralise the trap and the two tests above would pass vacuously.
    """
    from app.core import hardware

    _install_torch_trap(monkeypatch)
    with pytest.raises(_TorchImportTrap):
        hardware.get_optimal_torch_device()


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
    assert int(args[-1]) in (1, 2, 4)
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
    # 8 GB tier is single-slot: -np 2 would halve each slot to 2048 ctx while
    # the backend sends num_ctx=4096 through one serial consumer (measured).
    assert args[-4:] == ["-c", "4096", "-np", "1"]


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


def test_ingest_embed_batch_size_follows_tier():
    """Audit MEDIUM backend-3: lean 32 / standard 64 / high 128, safe default."""
    from unittest.mock import patch

    from app.core.hardware import get_ingest_embed_batch_size

    for tier, expected in [
        ("lean_cpu", 32),
        ("lean_accelerated", 32),
        ("standard_cpu", 64),
        ("standard_accelerated", 64),
        ("high_performance", 128),
        ("unknown-tier", 64),
    ]:
        with patch(
            "app.core.hardware.get_cached_hardware_profile",
            return_value={"tier": tier},
        ):
            assert get_ingest_embed_batch_size() == expected

    with patch(
        "app.core.hardware.get_cached_hardware_profile",
        side_effect=RuntimeError("probe failed"),
    ):
        assert get_ingest_embed_batch_size() == 64
