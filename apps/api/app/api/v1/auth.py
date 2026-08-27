"""
TRUSTRAG API — Authentication routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.api.v1.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
async def register(schema: UserRegister) -> UserResponse:
    """Register user details and return profile info."""
    return await auth_service.register_user(schema)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login session generation"
)
async def login(schema: UserLogin) -> TokenResponse:
    """Verify credentials and return access JWT token."""
    token, user = await auth_service.authenticate_user(schema.email, schema.password)
    return TokenResponse(access_token=token, user=user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Fetch current user profile"
)
async def me(current_user: Mapping[str, Any] = Depends(get_current_user)) -> UserResponse:
    """Fetch detail profile of the currently logged-in user."""
    return auth_service.serialize_user(current_user)
