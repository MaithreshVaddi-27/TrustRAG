"""
TRUSTRAG — API rate limiting.

The limiter was configured but **never enforced**. slowapi applies
``default_limits`` only through ``SlowAPIMiddleware``, and the middleware was
never added to the app: 70 consecutive authenticated requests to
``GET /models/providers`` all returned 200, while the per-route auth limits
(``@_auth_limiter.limit``) did fire.

Adding slowapi's own middleware does not work here either: this FastAPI
version keeps the included router as a single ``_IncludedRouter`` entry, so
slowapi's ``_find_route_handler`` cannot resolve a route handler and treats
**every** API route as exempt. The global limit is therefore implemented here,
directly and without slowapi, while the per-route auth limits keep using
slowapi unchanged.

Two decisions worth stating:

- **Client key.** ``get_remote_address`` returns the direct peer, which behind
  a reverse proxy (Render, Cloudflare — both are deployment targets) is the
  proxy itself. Every user would share one bucket and the first busy user
  would throttle everybody. The forwarded client address is used when the
  proxy sets it.
- **Limit value.** The dead constant was ``60/minute``. The app's own polling
  — dashboard auto-refresh (24/min), settings (4/min), playground (7.5/min),
  backend health probe (3/min) and the analysis fallback poll (30/min while a
  run is in flight) — reaches ~69/min on its own, so a 60/min ceiling would
  throttle normal use rather than abuse. The default is 240/minute, which
  keeps ~3.5x headroom over the measured baseline while still bounding a
  runaway client. It is configurable via ``RATE_LIMIT_PER_MINUTE``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

__all__ = [
    "DEFAULT_RATE_LIMIT_PER_MINUTE",
    "EXCLUDED_PATHS",
    "FixedWindowLimiter",
    "GlobalRateLimitMiddleware",
    "client_key",
    "install_rate_limiting",
]

# Requests per minute per client. See the module docstring for how this was
# chosen and why the old (never enforced) 60/minute was too low.
DEFAULT_RATE_LIMIT_PER_MINUTE = 240

# Monitoring endpoints are called by load balancers and uptime checks on their
# own schedule; counting them would spend a share of the budget on traffic
# nobody chooses to make.
EXCLUDED_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/health/ready",
        "/api/v1/health/detailed",
        "/api/v1/metrics",
    }
)

# The error envelope every other API error uses.
_RATE_LIMIT_BODY = {"error": {"code": "RATE_LIMITED", "message": "Too many requests. Slow down."}}


def client_key(request: Request) -> str:
    """Identify the client for rate limiting.

    Prefers the forwarded client address (set by a reverse proxy) and falls
    back to the direct peer address.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # "client, proxy1, proxy2" — the left-most entry is the original client.
        candidate = forwarded.split(",")[0].strip()
        if candidate:
            return candidate
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class FixedWindowLimiter:
    """A small in-process fixed-window request counter.

    One bucket per (client, path). The window resets a fixed number of
    seconds after it opens, so a client that keeps hammering a path is
    rejected until the window rolls over.
    """

    def __init__(self, per_minute: int, window_seconds: int = 60) -> None:
        self.limit = max(0, int(per_minute))
        self.window_seconds = max(1, int(window_seconds))
        self._hits: dict[tuple[str, str], tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, path: str) -> tuple[bool, int, int]:
        """Count one request.

        Returns ``(allowed, remaining, retry_after_seconds)``.
        """
        if self.limit <= 0:
            return True, self.limit, 0

        now = time.monotonic()
        bucket = (key, path)
        with self._lock:
            window_start, count = self._hits.get(bucket, (now, 0))
            if now - window_start >= self.window_seconds:
                window_start, count = now, 0
            count += 1
            self._hits[bucket] = (window_start, count)
            if len(self._hits) > 10_000:
                # Drop expired buckets so the table cannot grow without bound.
                self._hits = {
                    k: v for k, v in self._hits.items() if now - v[0] < self.window_seconds
                }

        if count > self.limit:
            retry_after = max(1, int(self.window_seconds - (now - window_start)))
            return False, 0, retry_after
        return True, max(0, self.limit - count), 0

    def reset(self) -> None:
        """Forget every bucket (tests only)."""
        with self._lock:
            self._hits.clear()


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce the per-client request budget.

    Installed **inside** the CORS layer, so preflight requests are answered by
    CORS without being counted.

    The limiter is read from ``app.state.rate_limiter`` on every request (like
    slowapi does) so it can be swapped at runtime — by a test, or by an
    operator endpoint that changes the budget.
    """

    def __init__(self, app, excluded: Iterable[str]) -> None:
        super().__init__(app)
        self._excluded = frozenset(excluded)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self._excluded:
            return await call_next(request)

        limiter: FixedWindowLimiter = request.app.state.rate_limiter
        allowed, remaining, retry_after = limiter.check(client_key(request), path)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content=_RATE_LIMIT_BODY,
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limiter.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def install_rate_limiting(
    app: FastAPI,
    per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
    excluded_paths: Iterable[str] = EXCLUDED_PATHS,
) -> FixedWindowLimiter:
    """Install the global request budget on the app."""
    limiter = FixedWindowLimiter(per_minute)
    app.state.rate_limiter = limiter
    app.add_middleware(GlobalRateLimitMiddleware, excluded=excluded_paths)
    return limiter
