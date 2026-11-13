"""
Regression tests for API rate limiting (audit change B3.3).

The limiter was configured but **never enforced**: slowapi applies
``default_limits`` only through ``SlowAPIMiddleware``, and the middleware was
never added to the app. Every endpoint except the auth routes had no limit at
all — 70 consecutive authenticated requests to ``GET /models/providers`` all
returned 200.

Adding slowapi's own middleware does not work here either: this FastAPI
version keeps the included router as a single ``_IncludedRouter`` entry, so
slowapi cannot resolve a route handler and exempts every API route.

These tests pin that the limit is now enforced, that the rejection uses the
API's standard error envelope, and that the monitoring endpoints stay
exempt (a load balancer polling /health must not spend the budget).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.rate_limiting import (
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    EXCLUDED_PATHS,
    FixedWindowLimiter,
    client_key,
)

# An endpoint that needs no database and no credentials: the service-token
# guard rejects it with 401 without touching MongoDB.
_PROTECTED_PATH = "/api/v1/internal/search"


@pytest.fixture
def limited_client():
    """A client whose limiter allows three requests per minute."""
    from app.main import app

    limiter = FixedWindowLimiter(per_minute=3)
    original = getattr(app.state, "rate_limiter", None)
    app.state.rate_limiter = limiter
    try:
        yield TestClient(app), limiter
    finally:
        if original is not None:
            app.state.rate_limiter = original


def test_the_global_limit_is_actually_enforced(limited_client):
    """The core regression: a limit that is configured but never applied."""
    client, _limiter = limited_client

    codes = [client.post(_PROTECTED_PATH, json={}).status_code for _ in range(4)]

    assert codes[:3] != [429] * 3, "the limit fired too early"
    assert codes[3] == 429, f"the limit was not enforced: {codes}"


def test_the_rejection_uses_the_api_error_envelope(limited_client):
    """A 429 must look like every other API error."""
    client, _limiter = limited_client

    for _ in range(3):
        client.post(_PROTECTED_PATH, json={})
    response = client.post(_PROTECTED_PATH, json={})

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "message" in body["error"]
    assert response.headers.get("Retry-After")


def test_each_path_has_its_own_budget():
    """The budget is per (client, path): one noisy path must not lock out another."""
    limiter = FixedWindowLimiter(per_minute=2)

    for _ in range(2):
        assert limiter.check("1.2.3.4", "/a")[0] is True
    assert limiter.check("1.2.3.4", "/a")[0] is False
    # A different path, and a different client, still have their own budget.
    assert limiter.check("1.2.3.4", "/b")[0] is True
    assert limiter.check("5.6.7.8", "/a")[0] is True


def test_monitoring_endpoints_are_excluded():
    """A load balancer polling /health must not spend the request budget."""
    assert "/api/v1/health" in EXCLUDED_PATHS
    assert "/api/v1/health/ready" in EXCLUDED_PATHS
    assert "/api/v1/metrics" in EXCLUDED_PATHS


def test_excluded_paths_are_never_limited():
    """The middleware skips the excluded paths entirely."""
    from app.main import app

    limiter = FixedWindowLimiter(per_minute=1)
    client = TestClient(app)
    original = getattr(app.state, "rate_limiter", None)
    app.state.rate_limiter = limiter
    try:
        codes = [client.get("/api/v1/health").status_code for _ in range(5)]
    finally:
        if original is not None:
            app.state.rate_limiter = original

    assert 429 not in codes, f"a monitoring endpoint was rate limited: {codes}"


def test_the_client_key_prefers_the_forwarded_address():
    """Behind a reverse proxy every user shares one peer address."""

    class _Request:
        def __init__(self, headers, host):
            self.headers = headers
            self.client = type("C", (), {"host": host})()

    forwarded = _Request({"x-forwarded-for": "203.0.113.7, 10.0.0.1"}, "10.0.0.1")
    assert client_key(forwarded) == "203.0.113.7"

    direct = _Request({}, "198.51.100.9")
    assert client_key(direct) == "198.51.100.9"

    empty = _Request({"x-forwarded-for": "  "}, "198.51.100.9")
    assert client_key(empty) == "198.51.100.9"


def test_the_default_limit_leaves_headroom_over_the_apps_own_polling():
    """The old (never enforced) 60/minute was below the app's own request rate.

    Dashboard auto-refresh 24/min + settings 4/min + playground 7.5/min +
    health probe 3/min + analysis fallback poll 30/min ≈ 69/min.
    """
    assert DEFAULT_RATE_LIMIT_PER_MINUTE >= 120, (
        "the default limit must not throttle the app's own polling"
    )


def test_a_zero_limit_disables_the_budget():
    """`RATE_LIMIT_PER_MINUTE=0` turns the limiter off."""
    limiter = FixedWindowLimiter(per_minute=0)
    for _ in range(100):
        assert limiter.check("1.2.3.4", "/a")[0] is True
