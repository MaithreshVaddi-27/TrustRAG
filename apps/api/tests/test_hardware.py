"""
Tests for hardware acceleration detection, memory profiling, and model recommendations.
"""

from app.core.hardware import (
    detect_hardware_profile,
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
