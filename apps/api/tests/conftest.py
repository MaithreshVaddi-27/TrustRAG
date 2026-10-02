"""
Pytest configuration and test environment setup.
Sets default environment variables so that unit tests can import app modules
without requiring live production secrets or pre-existing local .env files.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Test secrets come from an env FILE, never hardcoded literals here:
# apps/api/.env.test is committed (synthetic values only) so CI and dev machines
# share identical config without editing code. override=True is deliberate:
# it makes the suite hermetic, so an exported shell key or a developer's real
# .env can never win over the dummies and make results machine-dependent.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env.test", override=True)
except Exception:
    pass

# Hermetic provider config: a developer's local .env (e.g. AI_PROVIDER=ollama)
# must not leak into the suite — tests assert models.yaml defaults
# (test_create_analysis expects llama_cpp). Pop, don't default: an ambient
# value would otherwise win over setdefault and make results machine-dependent.
for _leaky_var in (
    "AI_PROVIDER",
    "LLM_PROVIDER",
    "OLLAMA_MODEL",
    "LLAMACPP_MODEL",
    # Removed envs (single ONNX engine since 2026-09-27) kept out defensively.
    "EMBEDDING_PROVIDER",
    "EMBEDDING_BACKEND",
    "EMBEDDING_MODEL",
):
    os.environ.pop(_leaky_var, None)
del _leaky_var

# Last-resort defaults, only if .env.test is missing (e.g. a partial checkout).
# These are format-valid SYNTHETIC dummies, never real credentials.
os.environ.setdefault(
    "JWT_SECRET",
    "test-secret-minimum-32-characters-long-key-for-unit-testing",
)
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("APP_ENV", "development")


# Clear global caches between tests to avoid cross-test pollution
def _clear_all_caches() -> None:
    """Reset every process-global cache that can leak state between tests."""
    # Provider hermeticity: app/core/config.py runs load_dotenv() at import,
    # so a developer's local .env (e.g. AI_PROVIDER=ollama) lands in
    # os.environ AFTER this module's top-level pop. Strip file-loaded values
    # here too, before the config caches below are cleared and re-read.
    for _leaky_var in (
        "AI_PROVIDER",
        "LLM_PROVIDER",
        "OLLAMA_MODEL",
        "LLAMACPP_MODEL",
        "LLAMA_CPP_MODEL",
        "MLX_MODEL",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_BACKEND",
        "EMBEDDING_MODEL",
    ):
        os.environ.pop(_leaky_var, None)
    # No volatile caches exist (singletons, registries, query/reranker result
    # caches all removed): nothing to clear here.
    # OCR engine/error globals (a failed load would otherwise poison later tests)
    try:
        from app.rag.ingestion.ocr import reset_engine_for_tests

        reset_engine_for_tests()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clear_global_caches():
    """Clear global caches before and after each test."""
    _clear_all_caches()
    yield
    _clear_all_caches()
