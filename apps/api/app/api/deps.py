"""
TRUSTRAG API — dependency injection helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bson import ObjectId
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token, decode_service_token, jti_key
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

    # SEC-H1: reject tokens that have been revoked (logout / denylist).
    revoked = await get_collection(Collections.REVOKED_TOKENS).find_one({"_id": jti_key(payload)})
    if revoked:
        raise AuthenticationError("Token has been revoked", detail="Please sign in again")

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


# ─── Service-to-Service Authentication ────────────────────────────────────────


async def get_current_service(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """
    Validate incoming service-to-service JWT token and return the service payload.

    Expected header format: "Authorization: Bearer <service_token>"

    Raises HTTPException 401 on authentication failure.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        payload = decode_service_token(token)
        return payload
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_service_permission(permission: str):
    """
    Create a dependency that requires a specific service permission.

    Usage:
        @router.post("/internal/ingest")
        async def internal_ingest(
            payload: dict = Depends(require_service_permission("ingest:write"))
        ):
            ...
    """

    async def permission_checker(
        service_payload: dict = Depends(get_current_service),
    ) -> dict[str, Any]:
        permissions = service_payload.get("permissions", [])
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Service lacks required permission: {permission}",
            )
        return service_payload

    return permission_checker


async def get_service_name(service_payload: dict = Depends(get_current_service)) -> str:
    """Extract service name from validated service token."""
    return service_payload.get("sub", "unknown")
