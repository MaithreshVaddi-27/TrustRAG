"""
Unit tests for the Health and Diagnostics API endpoints.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_public_success():
    """Public /health returns minimal status for load balancers."""
    with (
        patch("app.api.v1.health.mongo_health_check", AsyncMock(return_value=True)),
        patch("app.api.v1.health.qdrant_health_check", return_value=True),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["app"] == "TRUSTRAG"
        assert data["version"] == "0.1.0"
        # Public endpoint does NOT include environment, models, hardware, formats
        assert "environment" not in data
        assert "services" not in data
        assert "models" not in data
        assert "hardware" not in data


def test_health_endpoint_public_mongo_degraded():
    """Public /health shows degraded status when MongoDB is down."""
    with (
        patch("app.api.v1.health.mongo_health_check", AsyncMock(return_value=False)),
        patch("app.api.v1.health.qdrant_health_check", return_value=True),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "degraded"


def test_health_detailed_requires_auth():
    """Detailed /health/detailed requires authentication."""
    with (
        patch("app.api.v1.health.mongo_health_check", AsyncMock(return_value=True)),
        patch("app.api.v1.health.qdrant_health_check", return_value=True),
    ):
        # No auth header → 401/403
        response = client.get("/api/v1/health/detailed")
        assert response.status_code in (401, 403)


def test_health_detailed_reports_rss_and_metrics():
    """UL-8: authed detailed health carries current RSS + NLI metrics."""
    from app.api.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"_id": "u1"}
    try:
        with (
            patch("app.api.v1.health.mongo_health_check", AsyncMock(return_value=True)),
            patch("app.api.v1.health.qdrant_health_check", return_value=True),
        ):
            response = client.get("/api/v1/health/detailed")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data["rss_mb"], (int, float))
            assert data["rss_mb"] >= 0
            assert "batch_total_failures" in data["metrics"]["nli"]
    finally:
        app.dependency_overrides.clear()


def test_providers_endpoint_degrades_on_status_check_failure():
    """A crashing status check must degrade to a stub, never a 500.

    Otherwise the Playground renders an empty model list with no offline
    warning (the exact reported regression).
    """
    from app.api.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"_id": "u1"}
    try:
        with (
            patch(
                "app.api.v1.models.check_ollama_status",
                AsyncMock(
                    return_value={
                        "connected": False,
                        "provider": "ollama",
                        "models": [],
                        "default_model": "",
                    }
                ),
            ),
            patch(
                "app.api.v1.models.check_llamacpp_status",
                AsyncMock(side_effect=RuntimeError("discovery exploded")),
            ),
        ):
            response = client.get("/api/v1/models/providers")
            assert response.status_code == 200
            data = response.json()
            llama = data["providers"]["llama_cpp"]
            assert llama["connected"] is False
            assert llama["models"] == []
            assert llama["default_model"] == ""
            assert "error" in llama
    finally:
        app.dependency_overrides.clear()


def test_no_fastapi_deprecation_warning_on_requests():
    """Regression: custom default_response_class (ORJSONResponse) warned per request.

    The app must serialize via FastAPI's native path — any
    FastAPIDeprecationWarning raised as an error fails this test.
    """
    import warnings

    from fastapi.exceptions import FastAPIDeprecationWarning

    with (
        patch("app.api.v1.health.mongo_health_check", AsyncMock(return_value=True)),
        patch("app.api.v1.health.qdrant_health_check", return_value=True),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("error", FastAPIDeprecationWarning)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
