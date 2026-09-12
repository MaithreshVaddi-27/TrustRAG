"""
TRUSTRAG API — health endpoints.

GET /api/v1/health
  Public health check: minimal status for load balancers, Docker healthchecks.
  Returns: status, timestamp, app, version.

GET /api/v1/health/detailed
  Authenticated detailed health: includes services, models, hardware, supported formats.
  Requires valid JWT. Used by frontend and admin tooling.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import get_model_config, get_settings
from app.core.hardware import get_cached_hardware_profile
from app.core.model_registry import registry_status
from app.db.mongodb import health_check as mongo_health_check
from app.db.qdrant import health_check as qdrant_health_check

router = APIRouter(tags=["health"])


@router.get("/health", summary="Public application health check")
async def health() -> dict:
    """
    Public health check — minimal response for load balancers and Docker healthchecks.

    Always returns 200 so monitoring tools can always receive a response.
    Inspect the `status` field to determine actual health.
    """
    mongo_ok = await mongo_health_check()
    qdrant_ok = await qdrant_health_check()

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
    }


@router.get("/health/detailed", summary="Authenticated detailed health check")
async def health_detailed(current_user=Depends(get_current_user)) -> dict:
    """
    Detailed health check — requires authentication.

    Returns full service status, active model configuration, hardware profile,
    and supported formats. For frontend status panel and admin tooling.
    """
    mongo_ok = await mongo_health_check()
    qdrant_ok = await qdrant_health_check()

    services = {
        "mongodb": "ok" if mongo_ok else "degraded",
        "qdrant": "ok" if qdrant_ok else "degraded",
    }

    overall_status = "ok" if all(v == "ok" for v in services.values()) else "degraded"

    cfg = get_model_config()
    settings = get_settings()

    return {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "app": "TRUSTRAG",
        "version": "0.1.0",
        "environment": settings.app_env,
        "services": services,
        "models": registry_status(),
        "hardware": get_cached_hardware_profile(),
        "supported_formats": cfg.supported_formats,
    }
