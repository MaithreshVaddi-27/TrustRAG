"""
TRUSTRAG — Shared benchmark authentication.

The register endpoint is limited to **3 registrations per hour per client**,
and every benchmark run needs an account. Both the API benchmark and the
accuracy evaluation therefore share one account, cached on disk, and log in
again when the JWT expires.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["BENCH_PASSWORD", "credentials_path", "register_or_login"]

# Throwaway local benchmark credential — never a real secret.
BENCH_PASSWORD = "BenchPass-1234!"  # noqa: S105

_CRED_FILE = Path(
    os.environ.get(
        "BENCH_CRED_FILE",
        str(Path(tempfile.gettempdir()) / "trustrag_bench_creds.json"),
    )
)


def credentials_path() -> Path:
    """Where the shared benchmark credentials are cached."""
    return _CRED_FILE


async def register_or_login(client: Any, base_url: str) -> tuple[str, str]:
    """Return an access token for the shared benchmark account.

    Logs in when the cached account exists; registers a new one otherwise.
    """
    email = ""
    if _CRED_FILE.exists():
        try:
            email = json.loads(_CRED_FILE.read_text(encoding="utf-8")).get("email", "")
        except Exception:
            email = ""

    if email:
        token = await _login(client, base_url, email)
        if token:
            return token, email

    email = f"bench-{int(_now())}@bench.example.com"
    r = await client.post(
        f"{base_url}/api/v1/auth/register",
        json={"email": email, "password": BENCH_PASSWORD, "full_name": "Bench User"},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"register failed: {r.status_code} {r.text[:200]}")
    token = await _login(client, base_url, email)
    if not token:
        raise RuntimeError("login failed after registration")
    try:
        _CRED_FILE.write_text(json.dumps({"email": email}), encoding="utf-8")
    except OSError:
        pass
    return token, email


async def _login(client: Any, base_url: str, email: str) -> str | None:
    r = await client.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": email, "password": BENCH_PASSWORD},
    )
    if r.status_code not in (200, 201):
        return None
    return r.json()["access_token"]


def _now() -> float:
    import time

    return time.time()
