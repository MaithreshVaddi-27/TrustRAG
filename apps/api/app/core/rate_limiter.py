"""
TRUSTRAG — Shared SlowAPI rate limiter instance.

Defined in a separate module to break the circular import cycle:
  main.py → router.py → routes.py → main.py (circular)

Both main.py and route modules import from this module instead.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_client_ip(request) -> str:  # type: ignore[no-untyped-def]
    """
    Extract client IP respecting reverse proxy headers.

    Priority:
      1. X-Forwarded-For (first IP = original client, set by Nginx/Cloudflare/Render)
      2. X-Real-IP (alternative proxy header)
      3. Direct connection IP (fallback)
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For format: "client, proxy1, proxy2" — take the first (original client)
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return get_remote_address(request)


limiter = Limiter(key_func=_get_client_ip)
