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
