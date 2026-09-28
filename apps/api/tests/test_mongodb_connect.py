"""
connect_db() failure-path tests (audit finding).

Two distinct defects shared one root cause — the retry handler assumed the code
inside its `try` had always run:

1. `candidate_client` was assigned inside the `try`, but the `except` referenced
   it unconditionally. A URI that makes `AsyncIOMotorClient(...)` itself raise
   left the name unbound, so the handler died with `UnboundLocalError` — a
   misleading error that hid the real problem, and skipped the documented
   retry/backoff and DatabaseError translation entirely.

2. The handler caught only `PyMongoError`. An out-of-range port raises a plain
   `ValueError`, which is NOT a PyMongoError, so it escaped the handler and the
   retry policy altogether.

Both are now handled by validating MONGODB_URI up front, which also stops a
permanently invalid address from burning 12 exponential-backoff retries.
"""

from __future__ import annotations

import asyncio

import pytest

import app.db.mongodb as mongodb_mod
from app.core.config import get_settings
from app.core.exceptions import DatabaseError

# Every one of these is permanently unusable, so no amount of retrying helps.
BAD_URIS = [
    "mongodb://",  # no host -> InvalidURI from the client constructor
    "mongodb://a:b@host:999999/db",  # out-of-range port -> plain ValueError
    "not-a-uri",  # no scheme -> InvalidURI
    "mongodb://user:pass@host:notaport/db",  # non-numeric port
]


@pytest.mark.parametrize("uri", BAD_URIS)
def test_malformed_uri_raises_database_error_immediately(uri, monkeypatch):
    """A config typo must fail fast and say so — not retry for minutes and then
    surface an UnboundLocalError."""
    settings = get_settings()
    monkeypatch.setattr(settings, "mongodb_uri", uri)

    async def _run():
        with pytest.raises(DatabaseError) as exc:
            await mongodb_mod.connect_db()
        return exc.value

    error = asyncio.run(_run())
    assert "MONGODB_URI" in str(error), f"error does not name the setting: {error}"


def test_malformed_uri_does_not_retry(monkeypatch):
    """Retrying a permanently invalid address just delays the same fatal error.
    The whole point of the pre-flight check is that this returns in milliseconds."""
    settings = get_settings()
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb://")

    slept: list[float] = []

    async def _fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(mongodb_mod.asyncio, "sleep", _fake_sleep)

    async def _run():
        with pytest.raises(DatabaseError):
            await mongodb_mod.connect_db()

    asyncio.run(_run())
    assert slept == [], f"a malformed URI triggered {len(slept)} backoff retries"


def test_valid_uri_passes_validation(monkeypatch):
    """The pre-flight check must not reject a legitimate URI."""
    settings = get_settings()
    for uri in (
        "mongodb://localhost:27017",
        "mongodb://localhost:27017/trustrag",
        "mongodb://user:pass@host.example.com:27017/db?replicaSet=rs0",
    ):
        monkeypatch.setattr(settings, "mongodb_uri", uri)
        mongodb_mod._validate_mongodb_uri(uri)  # must not raise


def test_unbound_client_is_never_referenced(monkeypatch):
    """Regression guard for the exact UnboundLocalError: if the constructor
    raises, the handler must still produce a DatabaseError, not a NameError."""
    from pymongo.errors import InvalidURI

    settings = get_settings()
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb://")

    def _boom(*_a, **_k):
        raise InvalidURI("nope")

    monkeypatch.setattr(mongodb_mod, "AsyncIOMotorClient", _boom)
    # Bypass the pre-flight so we exercise the retry handler itself.
    monkeypatch.setattr(mongodb_mod, "_validate_mongodb_uri", lambda _uri: None)
    monkeypatch.setattr(mongodb_mod, "_CONNECT_MAX_ATTEMPTS", 1)

    async def _run():
        with pytest.raises(DatabaseError):
            await mongodb_mod.connect_db()

    asyncio.run(_run())


def test_value_error_from_client_is_translated(monkeypatch):
    """A ValueError raised by the driver (bad port) must reach the DatabaseError
    translation, not escape as a bare ValueError."""

    def _boom(*_a, **_k):
        raise ValueError("Port must be an integer between 0 and 65535")

    settings = get_settings()
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb://localhost:27017")
    monkeypatch.setattr(mongodb_mod, "AsyncIOMotorClient", _boom)
    monkeypatch.setattr(mongodb_mod, "_validate_mongodb_uri", lambda _uri: None)
    monkeypatch.setattr(mongodb_mod, "_CONNECT_MAX_ATTEMPTS", 1)

    async def _run():
        with pytest.raises(DatabaseError):
            await mongodb_mod.connect_db()

    asyncio.run(_run())
