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
    """Must return a device torch can actually use, and must agree with the
    torch-free accelerator detection. Asserting only `in ("cuda","mps","cpu")`
    would pass against a function hardcoded to always return "cpu" — the exact
    failure mode this replaces."""
    dev = get_optimal_torch_device()
    assert dev in ("cuda", "mps", "cpu")

    # Cross-check: the torch probe and the torch-free path must not disagree
    # about the host. cuda/mps may legitimately differ (torch may fail to load
    # where the accelerator is merely absent), but on a host where torch sees
    # nothing accelerated, neither should the profile claim acceleration.
    profile = detect_hardware_profile()
    if dev == "cpu":
        # Nothing accelerated for torch; the profile should not be claiming
        # a torch-backed accelerator either.
        assert profile["accelerator"] in ("cpu",) or profile.get("vram_gb", 0) == 0, (
            f"torch reports cpu but profile claims {profile['accelerator']!r}"
        )


def test_detect_hardware_profile_is_internally_consistent():
    """The old assertions checked only that keys existed, so a profile of
    {"max_concurrency": 1} for every host passed. Now the values must be
    coherent with each other and with the batch-size table."""
    profile = detect_hardware_profile()

    mem = profile["memory"]
    assert mem["total_gb"] > 0, "total memory must be a positive measurement"
    # used + free must reconcile against total, not be three unrelated numbers.
    assert mem["used_gb"] + mem["free_gb"] == pytest.approx(mem["total_gb"], abs=0.51), (
        f"memory does not reconcile: {mem}"
    )
    assert 0 <= mem["usage_pct"] <= 100, f"usage_pct out of range: {mem['usage_pct']}"
    # usage_pct must be DERIVED from used/total, not merely in range. A hardcoded
    # 50.0 satisfies a range check while being wrong on every real host — and
    # health status keys off this value (hardware.py:349,355), so a bogus
    # percentage would mislabel an OOM-risk machine as optimal.
    expected_pct = (mem["used_gb"] / mem["total_gb"]) * 100
    assert mem["usage_pct"] == pytest.approx(expected_pct, abs=0.2), (
        f"usage_pct {mem['usage_pct']} does not match used/total "
        f"({mem['used_gb']}/{mem['total_gb']} = {expected_pct:.1f})"
    )
    # RSS must be a real measurement. A hardcoded 0.0 would pass `>= 0`.
    assert profile["process_rss_mb"] > 0, "RSS must be measured, not defaulted to 0"

    # The tier must be one the batch-size table actually knows about.
    assert profile["tier"].startswith(("lean", "standard", "high")), profile["tier"]

    # Every recommended model must be a real model id, not an empty string.
    rec = profile["recommendations"]
    for key in ("primary_llm", "primary_embedding"):
        assert rec.get(key), f"recommendation '{key}' is empty: {rec}"


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
    """The consumer that actually dragged torch in must stay clean too.

    The old assertion was `> 0`, which a hardcoded `return 1` would satisfy.
    It is now tied to the detected tier's configured size.
    """
    from app.core.hardware import _INGEST_EMBED_BATCH_BY_TIER, get_ingest_embed_batch_size

    _install_torch_trap(monkeypatch)
    size = get_ingest_embed_batch_size()

    assert size > 0
    # Must be one of the sizes the tier table defines, not an arbitrary number.
    assert size in {s for _, s in _INGEST_EMBED_BATCH_BY_TIER}, (
        f"batch size {size} is not a configured tier size"
    )


@pytest.mark.parametrize(
    "tier,expected",
    [("lean_accelerated", 32), ("lean_cpu", 32), ("standard_gpu", 64), ("high_gpu", 128)],
)
def test_ingest_batch_size_follows_the_tier(monkeypatch, tier, expected):
    """Pins the tier -> batch-size mapping. Previously nothing tied the two
    together, so a retune that made every tier return the same size passed."""
    from app.core import hardware

    monkeypatch.setattr(hardware, "get_cached_hardware_profile", lambda: {"tier": tier})
    assert hardware.get_ingest_embed_batch_size() == expected


def test_unknown_tier_falls_back_to_the_documented_default(monkeypatch):
    from app.core import hardware

    monkeypatch.setattr(hardware, "get_cached_hardware_profile", lambda: {"tier": "something_new"})
    assert hardware.get_ingest_embed_batch_size() == 64


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
