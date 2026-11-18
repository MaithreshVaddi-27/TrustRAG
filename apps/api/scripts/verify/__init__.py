"""
TRUSTRAG — the verification package.

Harnesses that check the *contract* between the parts of the system:

- ``validate_integration`` — every API call the frontend makes exists on the
  backend, and the whole user flow answers correctly, directly and through
  the frontend's own proxy.
- ``validate_resilience`` — concurrency, the rate limit, a provider outage and
  a database outage all behave as designed.

Both need the live stack (``scripts/start_local_services.sh``).
"""

from __future__ import annotations

__all__ = ["validate_integration", "validate_resilience"]
