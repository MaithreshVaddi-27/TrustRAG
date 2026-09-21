"""
TRUSTRAG — Shared SlowAPI rate limiter instance.

Defined in a separate module to break the circular import cycle:
  main.py → router.py → routes.py → main.py (circular)

Both main.py and route modules import from this module instead.

Supports in-memory (dev) or Redis (prod) storage via SLOWAPI_STORAGE_URI env.
"""

from __future__ import annotations

import ipaddress
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _is_trusted_proxy(remote_host: str) -> bool:
    """Return True only when the direct peer may supply forwarding headers."""
    if not remote_host:
        return False

    for entry in get_settings().trusted_proxy_list:
        if remote_host == entry:
            return True
        try:
            remote_ip = ipaddress.ip_address(remote_host)
            proxy_network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if remote_ip in proxy_network:
            return True
    return False


def _get_client_ip(request) -> str:  # type: ignore[no-untyped-def]
    """
    Extract the rate-limit identity without trusting client-spoofed headers.

    X-Forwarded-For/X-Real-IP are honored only when the immediate peer is in
    TRUSTED_PROXY_IPS. Direct internet requests therefore use their actual
    connection address instead of an attacker-controlled header.
    """
    remote_host = request.client.host if request.client else get_remote_address(request)
    if _is_trusted_proxy(remote_host):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            candidate = forwarded_for.split(",")[0].strip()
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                return remote_host

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            candidate = real_ip.strip()
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                return remote_host

    return remote_host


# Storage URI: in-memory for dev, Redis for prod (via SLOWAPI_STORAGE_URI env or
# get_settings().rate_limit_storage_uri). Examples:
#   "" or not set → in-memory (default)
#   "redis://localhost:6379" → Redis
#   "redis://:password@host:6379/0" → Redis with auth/DB
_storage_uri = (
    os.environ.get("SLOWAPI_STORAGE_URI", "").strip()
    or getattr(get_settings(), "rate_limit_storage_uri", "").strip()
)

limiter = Limiter(key_func=_get_client_ip, storage_uri=_storage_uri if _storage_uri else None)
