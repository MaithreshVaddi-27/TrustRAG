"""
TRUSTRAG — security and authentication helpers.

Handles:
  - Password hashing and verification via standard bcrypt library
  - JWT token generation and decoding (user and service tokens)
  - Service-to-service authentication
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

ALGORITHM = "HS256"

# Service-to-service authentication constants
SERVICE_TOKEN_TYPE = "service"
SERVICE_TOKEN_TTL_HOURS = 24  # Service tokens valid for 24 hours


def hash_password(password: str) -> str:
    """Hash password using standard bcrypt gensalt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Generate a signed JWT access token.

    Each token carries a unique ``jti`` claim so it can be individually
    revoked (SEC-H1). subject: Typically the user's ID as a string or
    unique email.
    """
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)
    return encoded_jwt


def jti_key(payload: dict[str, Any]) -> str:
    """
    Stable revocation key for a decoded token payload.

    Modern tokens use their unique ``jti``. Legacy tokens issued before
    SEC-H1 lack ``jti``, so fall back to ``sub:iat`` which is equally
    unique for the lifetime of the token.
    """
    jti = payload.get("jti")
    if jti:
        return str(jti)
    return f"{payload.get('sub')}:{payload.get('iat')}"


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises AuthenticationError if invalid or expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError as exc:
        raise AuthenticationError("Token signature has expired", detail=str(exc)) from exc
    except JWTError as exc:
        raise AuthenticationError("Invalid authentication token", detail=str(exc)) from exc


# ─── Service-to-Service Authentication ────────────────────────────────────────


def create_service_token(
    service_name: str,
    permissions: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Generate a signed JWT token for service-to-service authentication.

    Args:
        service_name: Unique identifier for the service (e.g., "ingestion-worker", "api-gateway")
        permissions: List of permission strings (e.g., ["ingest:write", "search:read"])
        expires_delta: Optional custom expiration. Defaults to SERVICE_TOKEN_TTL_HOURS.

    Returns:
        Encoded JWT token string.
    """
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=SERVICE_TOKEN_TTL_HOURS)

    to_encode = {
        "exp": expire,
        "sub": service_name,
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
        "type": SERVICE_TOKEN_TYPE,
        "permissions": permissions or [],
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)
    return encoded_jwt


def decode_service_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a service-to-service JWT token.
    Raises AuthenticationError if invalid, expired, or not a service token.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])

        # Verify this is a service token
        if payload.get("type") != SERVICE_TOKEN_TYPE:
            raise AuthenticationError("Token is not a service token")

        return payload
    except ExpiredSignatureError as exc:
        raise AuthenticationError("Service token signature has expired", detail=str(exc)) from exc
    except JWTError as exc:
        raise AuthenticationError("Invalid service token", detail=str(exc)) from exc


def verify_service_permission(token: str, required_permission: str) -> bool:
    """
    Verify a service token has the required permission.

    Args:
        token: Service JWT token
        required_permission: Permission string to check (e.g., "ingest:write")

    Returns:
        True if token has permission, False otherwise
    """
    try:
        payload = decode_service_token(token)
        permissions = payload.get("permissions", [])
        return required_permission in permissions
    except AuthenticationError:
        return False


def get_service_name_from_token(token: str) -> str | None:
    """Extract service name from a valid service token."""
    try:
        payload = decode_service_token(token)
        return payload.get("sub")
    except AuthenticationError:
        return None
