"""
TRUSTRAG API — health endpoint.

GET /api/v1/health
  Returns application health status including:
  - API status
  - MongoDB connectivity
  - Active model configuration (model IDs only — no secrets)
  - Application version

Used by Docker healthchecks, load balancers, and CI smoke tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.model_registry import registry_status
from app.db.mongodb import health_check as mongo_health_check
from app.db.qdrant import health_check as qdrant_health_check

router = APIRouter(tags=["health"])


@router.get("/health", summary="Application health check")
async def health() -> dict:
    """
    Return application health and active configuration.

    Always returns 200 so monitoring tools can always receive a response.
    Inspect the `status` field to determine actual health.
    Individual service statuses are in `services`.
    """
    mongo_ok = await mongo_health_check()
    qdrant_ok = qdrant_health_check()

    services = {
        "mongodb": "ok" if mongo_ok else "degraded",
        "qdrant": "ok" if qdrant_ok else "degraded",
    }

    overall_status = "ok" if all(v == "ok" for v in services.values()) else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "app": "TRUSTRAG",
        "version": "0.1.0",
        "services": services,
        "models": registry_status(),
    }
