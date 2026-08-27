"""
Unit tests for Analysis runs and execution trace routes.
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
        "created_at": "2026-08-27T10:00:00Z"
    }


@pytest.fixture
def mock_kb_doc():
    return {
        "_id": ObjectId("64ee39d09c6292376e191982"),
        "name": "Refund Policies",
        "description": "Standard refund schedules",
        "user_id": ObjectId("64ee39d09c6292376e191981"),
        "created_at": "2026-08-27T10:00:00Z"
    }


@pytest.fixture
def mock_analysis_doc():
    return {
        "_id": ObjectId("64ee39d09c6292376e191983"),
        "user_id": ObjectId("64ee39d09c6292376e191981"),
        "knowledge_base_id": ObjectId("64ee39d09c6292376e191982"),
        "query": "Is there a 45 days policy?",
        "status": "pending",
        "answer": None,
        "reliability": {"score": None, "status": "PENDING"},
        "diagnosis": {"type": None, "failures": []},
        "created_at": "2026-08-27T10:00:00Z"
    }


@pytest.fixture(autouse=True)
def setup_dependency_override(mock_user_doc):
    # Override current user dependency to bypass JWT extraction and DB fetch
    app.dependency_overrides[get_current_user] = lambda: mock_user_doc
    yield
    app.dependency_overrides.clear()


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_create_analysis(mock_create_indexes, mock_connect, mock_kb_doc):
    # Mock kb ownership check inside analysis_service
    with patch("app.services.analysis_service.get_kb", return_value=mock_kb_doc):
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId("64ee39d09c6292376e191983")))

        with patch("app.services.analysis_service.get_collection", return_value=mock_collection):
            # Mock trace event insert
            with patch("app.services.analysis_service.add_trace_event", AsyncMock()) as mock_add_trace:
                payload = {
                    "knowledge_base_id": "64ee39d09c6292376e191982",
                    "query": "Is there a 45 days policy?"
                }
                response = client.post("/api/v1/analyses", json=payload)

                assert response.status_code == 201
                data = response.json()
                assert data["query"] == "Is there a 45 days policy?"
                assert data["status"] == "pending"
                assert data["reliability"]["status"] == "PENDING"
                mock_add_trace.assert_called_once_with(
                    analysis_id_str="64ee39d09c6292376e191983",
                    event="analysis.started",
                    data={"message": "Analysis run initiated"}
                )
