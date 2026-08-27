"""
TRUSTRAG — Shared SlowAPI rate limiter instance.

Defined in a separate module to break the circular import cycle:
  main.py → router.py → routes.py → main.py (circular)

Both main.py and route modules import from this module instead.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
