"""
Unit tests for authentication logic and routes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_user_doc():
    return {
        "_id": "64ee39d09c6292376e191981",  # valid 24-char hex string
        "email": "test@example.com",
        "hashed_password": "$2b$12$DUMMYHASHFORTIMINGATTACKSPREVENTIONSIG",
        "full_name": "Test User",
        "is_active": True,
        "created_at": "2026-08-27T10:00:00Z",
    }


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_register_user_success(mock_create_indexes, mock_connect, mock_user_doc):
    # Mock database insert
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id="64ee39d09c6292376e191981")
    )

    with patch("app.services.auth_service.get_collection", return_value=mock_collection):
        payload = {
            "email": "test@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User",
        }
        # Bypass startup database ping in tests by patching startup hook or connection checks
        with patch("app.db.mongodb.health_check", return_value=True):
            response = client.post("/api/v1/auth/register", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["full_name"] == "Test User"
            assert "id" in data


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_login_user_success(mock_create_indexes, mock_connect, mock_user_doc):
    # Mock find_one for login
    mock_collection = MagicMock()

    # Hash password correctly so check passes
    from app.core.security import hash_password

    mock_user_doc_hashed = dict(mock_user_doc)
    mock_user_doc_hashed["hashed_password"] = hash_password("StrongPass123!")

    mock_collection.find_one = AsyncMock(return_value=mock_user_doc_hashed)

    with patch("app.services.auth_service.get_collection", return_value=mock_collection):
        payload = {"email": "test@example.com", "password": "StrongPass123!"}
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_get_me_protected_route(mock_create_indexes, mock_connect, mock_user_doc):
    from bson import ObjectId

    # Mock deps.get_current_user to return mock_user_doc
    mock_user_with_oid = dict(mock_user_doc)
    mock_user_with_oid["_id"] = ObjectId("64ee39d09c6292376e191981")

    mock_collection = MagicMock()
    # First find_one is the revocation denylist check (returns None = not revoked),
    # second is the user lookup.
    mock_collection.find_one = AsyncMock(side_effect=[None, mock_user_with_oid])

    with patch("app.api.deps.get_collection", return_value=mock_collection):
        # Create a valid token
        from app.core.security import create_access_token

        token = create_access_token("64ee39d09c6292376e191981")

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"


def test_access_token_carries_jti_claim():
    """SEC-H1: every issued token must be individually revocable via its jti."""
    from app.core.security import create_access_token, decode_access_token

    token = create_access_token("64ee39d09c6292376e191981")
    payload = decode_access_token(token)
    assert payload.get("jti")


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_logout_revokes_token(mock_create_indexes, mock_connect, mock_user_doc):
    """SEC-H1: after /auth/logout the same token is rejected by /auth/me."""
    from bson import ObjectId

    from app.core.security import create_access_token

    mock_user_with_oid = dict(mock_user_doc)
    mock_user_with_oid["_id"] = ObjectId("64ee39d09c6292376e191981")

    users_coll = MagicMock()
    revoked_coll = MagicMock()
    revoked_coll.insert_one = AsyncMock()
    revoked_coll.find_one = AsyncMock(return_value=None)

    def fake_get_collection(name):
        # deps asks for REVOKED_TOKENS first (revoked check) then USERS.
        return revoked_coll if name.endswith("revoked_tokens") else users_coll

    token = create_access_token("64ee39d09c6292376e191981")
    headers = {"Authorization": f"Bearer {token}"}

    # Logout: revoke inserts into denylist.
    with patch("app.api.deps.get_collection", side_effect=fake_get_collection):
        with patch("app.services.auth_service.get_collection", side_effect=fake_get_collection):
            response = client.post("/api/v1/auth/logout", headers=headers)
            assert response.status_code == 204
            revoked_coll.insert_one.assert_awaited_once()

    # Subsequent /me with the same (revoked) token → 401.
    revoked_coll.find_one = AsyncMock(return_value={"_id": "some-jti"})
    users_coll.find_one = AsyncMock(return_value=mock_user_with_oid)
    with patch("app.api.deps.get_collection", side_effect=fake_get_collection):
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401


@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
def test_expired_token_rejected(mock_create_indexes, mock_connect, mock_user_doc):
    from datetime import timedelta

    from app.core.security import create_access_token

    users_coll = MagicMock()

    def fake_get_collection(name):
        return users_coll

    token = create_access_token("64ee39d09c6292376e191981", expires_delta=timedelta(seconds=-1))
    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.api.deps.get_collection", side_effect=fake_get_collection):
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
