"""
Unit tests for the Experiment Evaluation tracking routes and services.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_user_doc():
    return {
        "_id": ObjectId("64ee39d09c6292376e191981"),
        "email": "test@trustrag.ai",
        "hashed_password": "scryptedhashedpassword",
    }


@pytest.fixture(autouse=True)
def setup_dependency_override(mock_user_doc):
    app.dependency_overrides[get_current_user] = lambda: mock_user_doc
    yield
    app.dependency_overrides.clear()


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_create_experiment_route(mock_create_indexes, mock_connect):
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId("64ee39d09c6292376e191986"))
    )

    with patch("app.services.experiment_service.get_collection", return_value=mock_collection):
        payload = {
            "config_name": "dense_384_gemini_3.5_flash",
            "description": "Evaluating default dense vector space retrieval.",
            "metrics": {"precision": 0.88, "latency_ms": 320.0},
        }
        response = client.post("/api/v1/experiments", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["config_name"] == "dense_384_gemini_3.5_flash"
        assert data["metrics"]["precision"] == 0.88
        assert data["metrics"]["latency_ms"] == 320.0
        mock_collection.insert_one.assert_called_once()


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_list_experiments_route(mock_create_indexes, mock_connect, mock_user_doc):
    mock_collection = MagicMock()

    mock_docs = [
        {
            "_id": ObjectId("64ee39d09c6292376e191986"),
            "user_id": mock_user_doc["_id"],
            "config_name": "config-a",
            "description": "Desc A",
            "metrics": {"recall": 0.90},
            "created_at": "2026-08-27T10:00:00Z",
        }
    ]

    mock_cursor = MagicMock()

    async def mock_async_gen():
        for d in mock_docs:
            yield d

    mock_cursor.__aiter__ = MagicMock(side_effect=mock_async_gen)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    with patch("app.services.experiment_service.get_collection", return_value=mock_collection):
        response = client.get("/api/v1/experiments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["config_name"] == "config-a"
        assert data[0]["metrics"]["recall"] == 0.90
