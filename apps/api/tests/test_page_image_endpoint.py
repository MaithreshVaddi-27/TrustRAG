"""
Unit tests for GET /documents/{id}/pages/{page}/image (Phase 7 residual).

RED: the route does not exist yet.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.ingestion.page_images import save_page_image
from app.main import app

client = TestClient(app)

USER_ID = "64ee39d09c6292376e191981"
KB_ID = "64ee39d09c6292376e191982"
DOC_ID = "64ee39d09c6292376e191999"

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def mock_user_doc():
    return {
        "_id": ObjectId(USER_ID),
        "email": "test@example.com",
        "hashed_password": "hashed-stuff",
        "full_name": "Test User",
        "is_active": True,
        "created_at": "2026-08-27T10:00:00Z",
    }


@pytest.fixture(autouse=True)
def setup_dependency_override(mock_user_doc):
    app.dependency_overrides[get_current_user] = lambda: mock_user_doc
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def image_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGE_IMAGES_DIR", str(tmp_path / "page_images"))
    return tmp_path / "page_images"


def _doc_record():
    return {
        "_id": ObjectId(DOC_ID),
        "knowledge_base_id": ObjectId(KB_ID),
        "user_id": ObjectId(USER_ID),
        "filename": "scan.pdf",
    }


def _kb_record():
    return {
        "_id": ObjectId(KB_ID),
        "name": "KB",
        "user_id": ObjectId(USER_ID),
        "created_at": "2026-08-27T10:00:00Z",
        "version": "1.0",
        "parent_kb_id": None,
        "is_snapshot": False,
    }


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_serve_ocr_page_image(mock_create_indexes, mock_connect, image_dir):
    ref = save_page_image(KB_ID, DOC_ID, 2, PNG_BYTES)
    chunk = {"document_id": ObjectId(DOC_ID), "page": 2, "page_image_ref": ref}

    mock_docs = MagicMock()
    mock_docs.find_one = AsyncMock(side_effect=[_doc_record(), chunk])
    mock_kb = MagicMock()
    mock_kb.find_one = AsyncMock(return_value=_kb_record())
    mock_kb.count_documents = AsyncMock(return_value=1)
    with (
        patch("app.api.v1.documents.get_collection", return_value=mock_docs),
        patch("app.services.kb_service.get_collection", return_value=mock_kb),
    ):
        response = client.get(f"/api/v1/documents/{DOC_ID}/pages/2/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG_BYTES


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_serve_image_404_when_chunk_has_no_ref(mock_create_indexes, mock_connect):
    chunk = {"document_id": ObjectId(DOC_ID), "page": 1}
    mock_docs = MagicMock()
    mock_docs.find_one = AsyncMock(side_effect=[_doc_record(), chunk])
    mock_kb = MagicMock()
    mock_kb.find_one = AsyncMock(return_value=_kb_record())
    mock_kb.count_documents = AsyncMock(return_value=1)
    with (
        patch("app.api.v1.documents.get_collection", return_value=mock_docs),
        patch("app.services.kb_service.get_collection", return_value=mock_kb),
    ):
        response = client.get(f"/api/v1/documents/{DOC_ID}/pages/1/image")

    assert response.status_code == 404


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_serve_image_404_for_unknown_document(mock_create_indexes, mock_connect):
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=None)
    with patch("app.api.v1.documents.get_collection", return_value=mock_collection):
        response = client.get(f"/api/v1/documents/{DOC_ID}/pages/1/image")

    assert response.status_code == 404
