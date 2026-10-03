"""Regression tests for the two critical security fixes.

Rate limiting: `default_limits` was configured but SlowAPIMiddleware was never
registered, so the global limit was inert and the expensive endpoints were
unbounded. Login lockout: only the (email, ip) pair was counted, so spraying one
victim email from N addresses never locked the account.
"""

from __future__ import annotations

import pytest
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def _undecorated_app(limit: str) -> Starlette:
    """An app wired exactly the way main.py is: Limiter on state + middleware."""
    app = Starlette(routes=[Route("/expensive", endpoint=lambda r: JSONResponse({"ok": True}))])
    app.state.limiter = Limiter(key_func=get_remote_address, default_limits=[limit])
    app.add_middleware(SlowAPIMiddleware)
    return app


def _fake_failed_login_store(monkeypatch, auth_service) -> dict:
    """In-memory stand-in for the FAILED_LOGINS collection.

    Mirrors only the three operators the lockout path uses: find_one,
    update_one ($inc / $push / $set, upsert) and delete_one.
    """
    store: dict[str, dict] = {}

    class _Coll:
        async def find_one(self, q):
            return store.get(q["_id"])

        async def update_one(self, q, update, upsert=False):
            cur = store.setdefault(q["_id"], {"count": 0, "attempts": [], "window_expires": None})
            cur["count"] += update["$inc"]["count"]
            cur["attempts"].append(update["$push"]["attempts"])
            cur["window_expires"] = update["$set"]["window_expires"]

        async def delete_one(self, q):
            store.pop(q["_id"], None)

    monkeypatch.setattr(auth_service, "_get_failed_logins_coll", lambda: _Coll())
    # get_settings() deliberately re-reads the environment on every call (no
    # singleton), so an instance-level patch would never be observed. Patch the
    # accessor the lockout path actually calls.
    real = auth_service.get_settings()

    class _Settings:
        login_max_attempts = 3
        login_lockout_seconds = real.login_lockout_seconds

    monkeypatch.setattr(auth_service, "get_settings", lambda: _Settings())
    return store


class TestGlobalRateLimit:
    def test_default_limit_actually_429s_an_undecorated_route(self):
        client = TestClient(_undecorated_app("5/minute"))
        codes = [client.get("/expensive").status_code for _ in range(8)]
        assert codes.count(200) == 5, "limit should allow exactly 5"
        assert codes.count(429) == 3, "remaining requests must be rate limited"

    def test_production_app_registers_the_middleware(self):
        from app.main import app

        middleware_names = {m.cls for m in app.user_middleware}
        assert SlowAPIMiddleware in middleware_names, (
            "SlowAPIMiddleware must be registered or default_limits is inert"
        )

    def test_production_app_exposes_a_limiter_on_state(self):
        from app.main import app

        assert getattr(app.state, "limiter", None) is not None
        assert app.state.limiter.enabled


class TestLoginLockoutKeys:
    """Both the per-IP pair and the email aggregate must be counted/checked."""

    @pytest.mark.asyncio
    async def test_failed_logins_are_recorded_under_both_keys(self, monkeypatch):
        from app.services import auth_service

        _fake_failed_login_store(monkeypatch, auth_service)

        # Attacker sprays one victim email from three different addresses.
        for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
            await auth_service._record_failed_login("victim@example.com", ip)

        # Every address is under the per-IP threshold...
        for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
            assert await auth_service._is_locked_out("victim@example.com", ip) is True, (
                "the email aggregate must lock the account even though no single "
                "IP reached the threshold"
            )
        # ...and a fresh address is refused too.
        assert await auth_service._is_locked_out("victim@example.com", "4.4.4.4") is True

    @pytest.mark.asyncio
    async def test_other_accounts_are_not_locked(self, monkeypatch):
        from app.services import auth_service

        _fake_failed_login_store(monkeypatch, auth_service)
        for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
            await auth_service._record_failed_login("victim@example.com", ip)

        assert await auth_service._is_locked_out("bystander@example.com", "1.1.1.1") is False
