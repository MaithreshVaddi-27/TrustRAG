"""
TRUSTRAG API — Authentication routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_current_user, oauth2_scheme
from app.api.v1.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.core.security.exceptions import AuthenticationError
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
_auth_limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@_auth_limiter.limit("3/hour")
async def register(request: Request, schema: UserRegister) -> UserResponse:
    """Register user details and return profile info."""
    return await auth_service.register_user(schema)


@router.post("/login", response_model=TokenResponse, summary="User login session generation")
@_auth_limiter.limit("5/minute")
async def login(request: Request, schema: UserLogin) -> TokenResponse:
    """Verify credentials and return access JWT token."""
    client_ip = request.client.host if request.client else None
    token, user = await auth_service.authenticate_user(schema.email, schema.password, client_ip)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserResponse, summary="Fetch current user profile")
async def me(current_user: Mapping[str, Any] = Depends(get_current_user)) -> UserResponse:
    """Fetch detail profile of the currently logged-in user."""
    return auth_service.serialize_user(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current access token",
)
async def logout(token: str | None = Depends(oauth2_scheme)) -> None:
    """
    Revoke the presented access token (SEC-H1).

    The token is added to the denylist until its ``exp`` claim passes, so a
    stolen token can no longer authenticate after a logout. Idempotent.
    """
    if not token:
        raise AuthenticationError("Not authenticated", detail="Missing Authorization header")
    await auth_service.revoke_token(token)
