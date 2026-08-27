"""
TRUSTRAG API — dependency injection helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bson import ObjectId
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.mongodb import Collections, get_collection

# Login endpoint URL (under the API prefix)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # We raise custom exception instead of plain 401
)


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> Mapping[str, Any]:
    """
    Validate incoming JWT token and return the current user's document.

    Raises AuthenticationError (which maps to 401) on failures.
    """
    if not token:
        raise AuthenticationError("Not authenticated", detail="Missing Authorization header")

    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Invalid token format", detail="Missing subject field")

    try:
        user_id = ObjectId(user_id_str)
    except Exception as exc:
        raise AuthenticationError("Invalid user identity format", detail=str(exc)) from exc

    user = await get_collection(Collections.USERS).find_one({"_id": user_id})
    if not user:
        raise AuthenticationError("User session not found", detail="Subject user does not exist")

    if not user.get("is_active", True):
        raise AuthenticationError("Inactive account", detail="Your account has been deactivated")

    return user
