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

@pytest.fixture(autouse=True)
def clear_global_caches():
    """Clear global caches before each test."""
    # Clear reranker cache
    from app.retrieval.reranker import _reranker_cache
    if _reranker_cache is not None:
        _reranker_cache.clear()
    yield
    # Clear again after test
    if _reranker_cache is not None:
        _reranker_cache.clear()
