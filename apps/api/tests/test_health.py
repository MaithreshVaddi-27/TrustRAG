"""
Unit tests for the Health and Diagnostics API endpoint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_success():
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
        assert "environment" in data
        assert data["services"]["mongodb"] == "ok"
        assert data["services"]["qdrant"] == "ok"
        assert "models" in data
        assert "supported_formats" in data
        assert "docx" in data["supported_formats"]
        assert "csv" in data["supported_formats"]


def test_health_endpoint_mongo_degraded():
    with (
        patch("app.api.v1.health.mongo_health_check", AsyncMock(return_value=False)),
        patch("app.api.v1.health.qdrant_health_check", return_value=True),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "degraded"
        assert data["services"]["mongodb"] == "degraded"
        assert data["services"]["qdrant"] == "ok"
