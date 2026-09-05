"""
Pydantic schemas for authentication and user management.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_complexity(password: str) -> str:
    """Validate password meets complexity requirements."""
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        raise ValueError("Password must contain at least one special character.")
    return password


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        description=(
            "Password must be at least 12 characters with upper, lower, digit, and special char."
        ),
    )
    full_name: str = Field(..., min_length=1, description="Full name cannot be empty.")

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="String representation of MongoDB ObjectId")
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user: UserResponse
