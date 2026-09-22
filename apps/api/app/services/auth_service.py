"""
TRUSTRAG — Authentication business logic service.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.api.v1.schemas.auth import UserRegister, UserResponse
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    jti_key,
    verify_password,
)
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
            "User registration failed",
            detail="Registration could not be completed with the provided details.",
        ) from exc


# ─── Login lockout (Mongo TTL collection; works across replicas) ───────────────
# Collection: failed_logins
# Document: { _id: "<email>", count: int, attempts: [epoch_ts], window_expires: datetime }
# TTL index on window_expires auto-cleans expired docs.


def _get_failed_logins_coll():
    """Return the failed_logins collection.

    Goes through get_collection (like every other collection) so callers
    stay mockable, and relies on the TTL index created once at startup
    (see create_indexes) instead of re-creating it per request.
    """
    return get_collection(Collections.FAILED_LOGINS)


async def _is_locked_out(email: str) -> bool:
    settings = get_settings()
    now_dt = datetime.now(UTC)
    coll = _get_failed_logins_coll()
    doc = await coll.find_one({"_id": email})
    if not doc:
        return False
    # If window expired, TTL will clean it; but double-check
    if doc.get("window_expires") and doc["window_expires"] < now_dt:
        await coll.delete_one({"_id": email})
        return False
    return doc.get("count", 0) >= settings.login_max_attempts


async def _record_failed_login(email: str) -> None:
    settings = get_settings()
    now_dt = datetime.now(UTC)
    window = settings.login_lockout_seconds
    window_expires = datetime.fromtimestamp(now_dt.timestamp() + window, tz=UTC)
    coll = _get_failed_logins_coll()
    await coll.update_one(
        {"_id": email},
        {
            "$inc": {"count": 1},
            "$push": {"attempts": now_dt},
            "$set": {"window_expires": window_expires},
        },
        upsert=True,
    )


async def _clear_failed_logins(email: str) -> None:
    coll = _get_failed_logins_coll()
    await coll.delete_one({"_id": email})


async def authenticate_user(email: str, password: str) -> tuple[str, UserResponse]:
    """
    Verify login credentials and generate access token.

    Raises AuthenticationError on bad credentials or lockout.
    """
    email_clean = email.strip().lower()

    if await _is_locked_out(email_clean):
        raise AuthenticationError(
            "Too many failed attempts",
            detail="Account temporarily locked. Try again later.",
        )

    users_coll = get_collection(Collections.USERS)

    user = await users_coll.find_one({"email": email_clean})
    if not user:
        # Run a real bcrypt comparison against a valid dummy hash (same cost factor as
        # real hashes) so this branch takes as long as the "wrong password" branch below.
        # A malformed dummy hash would make bcrypt fail fast instead of doing the full
        # cost-12 computation, reopening the exact timing side-channel this guards against.
        verify_password(password, "$2b$12$Fhvxd2NUDtaI9Np/Ct9Tn.jCLcGFUPgwN5oMcPCk8PlX36lOm2iFO")
        await _record_failed_login(email_clean)
        raise AuthenticationError("Authentication failed", detail="Invalid email or password")

    if not verify_password(password, user["hashed_password"]):
        await _record_failed_login(email_clean)
        raise AuthenticationError("Authentication failed", detail="Invalid email or password")

    if not user.get("is_active", True):
        raise AuthenticationError("Authentication failed", detail="Account is deactivated")

    await _clear_failed_logins(email_clean)
    # Generate token
    token = create_access_token(str(user["_id"]))
    return token, serialize_user(user)


async def revoke_token(token: str) -> None:
    """
    Revoke an access token (SEC-H1).

    Records the token's ``jti`` in ``revoked_tokens`` until its ``exp``
    claim passes (documents self-clean via a TTL index at that moment).
    Idempotent — revoking the same token twice is a no-op.
    """
    payload = decode_access_token(token)
    key = jti_key(payload)

    exp_ts = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp_ts, tz=UTC) if exp_ts else datetime.now(UTC)

    revoked_coll = get_collection(Collections.REVOKED_TOKENS)
    try:
        await revoked_coll.insert_one(
            {
                "_id": key,
                "user_id": payload.get("sub"),
                "revoked_at": datetime.now(UTC),
                "expires_at": expires_at,
            }
        )
    except DuplicateKeyError:
        # Already revoked; nothing more to do.
        pass


async def is_token_revoked(token: str) -> bool:
    """Return True if the token is present in the revocation denylist."""
    payload = decode_access_token(token)
    key = jti_key(payload)
    revoked_coll = get_collection(Collections.REVOKED_TOKENS)
    doc = await revoked_coll.find_one({"_id": key})
    return doc is not None
