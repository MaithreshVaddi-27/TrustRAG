"""
Unit tests for Knowledge Bases and document attachment routes.
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
        "email": "test@example.com",
        "hashed_password": "hashed-stuff",
        "full_name": "Test User",
        "is_active": True,
        "created_at": "2026-08-27T10:00:00Z",
    }


@pytest.fixture
def mock_kb_doc():
    return {
        "_id": ObjectId("64ee39d09c6292376e191982"),
        "name": "Refund Policies",
        "description": "Standard refund schedules",
        "user_id": ObjectId("64ee39d09c6292376e191981"),
        "created_at": "2026-08-27T10:00:00Z",
    }


@pytest.fixture(autouse=True)
def setup_dependency_override(mock_user_doc):
    # Override current user dependency to bypass JWT extraction and DB fetch
    app.dependency_overrides[get_current_user] = lambda: mock_user_doc
    yield
    app.dependency_overrides.clear()


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_create_kb(mock_create_indexes, mock_connect):
    # Mock database call
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId("64ee39d09c6292376e191982"))
    )

    with patch("app.services.kb_service.get_collection", return_value=mock_collection):
        payload = {"name": "Refund Policies", "description": "Standard refund schedules"}
        response = client.post("/api/v1/knowledge-bases", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Refund Policies"
        assert data["description"] == "Standard refund schedules"
        assert "id" in data


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_list_kbs(mock_create_indexes, mock_connect, mock_kb_doc):
    # Mock async iterator for cursor.find()
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)

    async def mock_async_gen():
        yield mock_kb_doc

    mock_cursor.__aiter__ = MagicMock(side_effect=mock_async_gen)

    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    mock_collection.count_documents = AsyncMock(return_value=2)  # document_count

    with patch("app.services.kb_service.get_collection", return_value=mock_collection):
        response = client.get("/api/v1/knowledge-bases")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Refund Policies"
        assert data[0]["document_count"] == 2
