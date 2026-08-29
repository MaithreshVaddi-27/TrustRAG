"""
TRUSTRAG — Authentication business logic service.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.api.v1.schemas.auth import UserRegister, UserResponse
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.mongodb import Collections, get_collection


def serialize_user(user_doc: Mapping[str, Any]) -> UserResponse:
    """Helper to convert MongoDB user document to Pydantic UserResponse."""
    return UserResponse(
        id=str(user_doc["_id"]),
        email=user_doc["email"],
        full_name=user_doc["full_name"],
        is_active=user_doc.get("is_active", True),
        created_at=user_doc["created_at"],
    )


async def register_user(schema: UserRegister) -> UserResponse:
    """
    Register a new user account.

    Raises ConflictError if the email already exists.
    """
    users_coll = get_collection(Collections.USERS)
    email_clean = schema.email.strip().lower()

    # Document to insert
    user_doc = {
        "email": email_clean,
        "hashed_password": hash_password(schema.password),
        "full_name": schema.full_name.strip(),
        "is_active": True,
        "created_at": datetime.now(UTC),
    }

    try:
        result = await users_coll.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        return serialize_user(user_doc)
    except DuplicateKeyError as exc:
        raise ConflictError(
            "User registration failed", detail="An account with this email already exists"
        ) from exc


async def authenticate_user(email: str, password: str) -> tuple[str, UserResponse]:
    """
    Verify login credentials and generate access token.

    Raises AuthenticationError on bad credentials.
    """
    users_coll = get_collection(Collections.USERS)
    email_clean = email.strip().lower()

    user = await users_coll.find_one({"email": email_clean})
    if not user:
        # Run a real bcrypt comparison against a valid dummy hash (same cost factor as
        # real hashes) so this branch takes as long as the "wrong password" branch below.
        # A malformed dummy hash would make bcrypt fail fast instead of doing the full
        # cost-12 computation, reopening the exact timing side-channel this guards against.
        verify_password(password, "$2b$12$Fhvxd2NUDtaI9Np/Ct9Tn.jCLcGFUPgwN5oMcPCk8PlX36lOm2iFO")
        raise AuthenticationError("Authentication failed", detail="Invalid email or password")

    if not verify_password(password, user["hashed_password"]):
        raise AuthenticationError("Authentication failed", detail="Invalid email or password")

    if not user.get("is_active", True):
        raise AuthenticationError("Authentication failed", detail="Account is deactivated")

    # Generate token
    token = create_access_token(str(user["_id"]))
    return token, serialize_user(user)
