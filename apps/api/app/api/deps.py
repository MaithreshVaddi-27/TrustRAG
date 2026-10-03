"""
TRUSTRAG API — dependency injection helpers.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from bson import ObjectId
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security.exceptions import AuthenticationError
from app.core.security.security import decode_access_token, decode_service_token, jti_key
from app.db.mongodb import Collections, get_collection

# Login endpoint URL (under the API prefix)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # We raise custom exception instead of plain 401
)


async def _raise_if_token_revoked(payload: dict, *, detail: str) -> None:
    """SEC-H1: reject a decoded token that is on the revocation denylist.

    Shared by the user-token and service-token paths. They were previously
    separate inlined copies of this lookup; they still are separate callers
    only because their failure messages differ.
    """
    revoked = await get_collection(Collections.REVOKED_TOKENS).find_one({"_id": jti_key(payload)})
    if revoked:
        raise AuthenticationError("Token has been revoked", detail=detail)


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> Mapping[str, Any]:
    """
    Validate incoming JWT token and return the current user's document.

    Raises AuthenticationError (which maps to 401) on failures.
    """
    if not token:
        raise AuthenticationError("Not authenticated", detail="Missing Authorization header")

    payload = decode_access_token(token)

    await _raise_if_token_revoked(payload, detail="Please sign in again")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Invalid token format", detail="Missing subject field")

    try:
        user_id = ObjectId(user_id_str)
    except Exception as exc:
        # Static detail: bson's message echoes the malformed input back.
        raise AuthenticationError("Invalid user identity format", detail="malformed id") from exc

    # Two independent lookups on different collections, awaited one after the
    # other — on EVERY authenticated request. The UI polls analyses every 5s and
    # claims/conflicts/KBs/health/providers on top of that, so this was ~10
    # serialized round-trips per minute of an idle dashboard before any real
    # work. Gather them; revocation is still evaluated FIRST so a revoked token
    # never gets to use the fetched user document.
    revoked_doc, user = await asyncio.gather(
        get_collection(Collections.REVOKED_TOKENS).find_one({"_id": jti_key(payload)}),
        get_collection(Collections.USERS).find_one({"_id": user_id}),
    )
    if revoked_doc:
        raise AuthenticationError("Token has been revoked", detail="Please sign in again")
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
        # SEC: service tokens are denylist-checked like user tokens (24h TTL
        # would otherwise be the compromise window).
        await _raise_if_token_revoked(payload, detail="Service token revoked")
        permissions = payload.get("permissions", [])
        if not isinstance(permissions, list) or not all(isinstance(p, str) for p in permissions):
            raise AuthenticationError(
                "Invalid token format", detail="permissions must be list[str]"
            )
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


def enforce_service_tenant(
    service_payload: Mapping[str, Any], kb_id: str, user_id: str | None = None
) -> None:
    """M-2 tenant guard (single implementation for all service routes).

    Unbound (service-level) tokens keep full access; bound tokens are confined
    to their bound KB and, when user_id is given, their bound user. Raises 403
    on mismatch so bound callers can't probe existence.
    """
    bound_kb = service_payload.get("bound_kb_id")
    if bound_kb and str(bound_kb) != str(kb_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service token not authorized for this knowledge base",
        )
    if user_id is not None:
        bound_user = service_payload.get("bound_user_id")
        if bound_user and str(bound_user) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service token not authorized for this user",
            )
