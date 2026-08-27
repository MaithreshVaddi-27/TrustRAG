"""
TRUSTRAG — security and authentication helpers.

Handles:
  - Password hashing and verification via standard bcrypt library
  - JWT token generation and decoding
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash password using standard bcrypt gensalt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Generate a signed JWT access token.
    
    subject: Typically the user's ID as a string or unique email.
    """
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(UTC)
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises AuthenticationError if invalid or expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token signature has expired", detail=str(exc)) from exc
    except jwt.JWTError as exc:
        raise AuthenticationError("Invalid authentication token", detail=str(exc)) from exc
