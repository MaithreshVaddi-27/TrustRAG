"""
Pytest configuration and test environment setup.
Sets default environment variables so that unit tests can import app modules
without requiring live production secrets or pre-existing local .env files.
"""

from __future__ import annotations

import os

# Set dummy test environment variables before any app modules are imported
os.environ.setdefault(
    "JWT_SECRET",
    "test-secret-minimum-32-characters-long-key-for-unit-testing",
)
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")


# Clear global caches between tests to avoid cross-test pollution
import pytest


def _clear_all_caches() -> None:
    """Reset every process-global cache that can leak state between tests."""
    # Reranker result cache
    from app.retrieval import reranker as reranker_module

    if reranker_module._reranker_cache is not None:
        reranker_module._reranker_cache.clear()
    # Query-vector embedding cache (dim-mismatch guard reads this)
    try:
        from app.retrieval.retriever import _query_cache

        _query_cache.clear()
    except Exception:
        pass
    # Settings / model-config lru_cache (tests that mutate env leak by order)
    try:
        from app.core.config import get_model_config, get_settings

        get_settings.cache_clear()
        get_model_config.cache_clear()
    except Exception:
        pass
    # OCR engine/error globals (a failed load would otherwise poison later tests)
    try:
        from app.ingestion.ocr import reset_engine_for_tests

        reset_engine_for_tests()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clear_global_caches():
    """Clear global caches before and after each test."""
    _clear_all_caches()
    yield
    _clear_all_caches()
