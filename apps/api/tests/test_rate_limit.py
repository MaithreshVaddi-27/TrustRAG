"""
Rate limiter threshold tests (TEST-M2).

Asserts the auth endpoints return HTTP 429 once the configured per-minute
ceiling is exceeded. Uses a unique X-Forwarded-For address per test so the
count is isolated from other tests that share the module-level TestClient and
the global SlowAPI in-memory storage.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_auth_login_rate_limit_returns_429():
    """Two login attempts allowed per low ceiling; the third gets a 429."""
    settings = get_settings()
    original_limit = settings.rate_limit_auth_per_minute
    settings.rate_limit_auth_per_minute = 2
    try:
        mock_collection = MagicMock()
        # find_one returns None → authenticate_user rejects with 401 (no user).
        mock_collection.find_one = AsyncMock(return_value=None)

        with patch("app.services.auth_service.get_collection", return_value=mock_collection):
            headers = {"X-Forwarded-For": "203.0.113.50"}
            payload = {"email": "ratelimit@example.com", "password": "WrongPass123!"}

            first = client.post("/api/v1/auth/login", json=payload, headers=headers)
            second = client.post("/api/v1/auth/login", json=payload, headers=headers)
            third = client.post("/api/v1/auth/login", json=payload, headers=headers)

            assert first.status_code == 401
            assert second.status_code == 401
            assert third.status_code == 429
    finally:
        settings.rate_limit_auth_per_minute = original_limit


def test_rate_limit_not_hit_below_ceiling():
    """Requests within the allowance succeed without a 429."""
    settings = get_settings()
    original_limit = settings.rate_limit_auth_per_minute
    settings.rate_limit_auth_per_minute = 10
    try:
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=None)

        with patch("app.services.auth_service.get_collection", return_value=mock_collection):
            headers = {"X-Forwarded-For": "203.0.113.60"}
            payload = {"email": "ratelimit2@example.com", "password": "WrongPass123!"}

            responses = [
                client.post("/api/v1/auth/login", json=payload, headers=headers) for _ in range(5)
            ]

            assert all(r.status_code == 401 for r in responses)
            assert all(r.status_code != 429 for r in responses)
    finally:
        settings.rate_limit_auth_per_minute = original_limit
