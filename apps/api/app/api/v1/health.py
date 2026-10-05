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

from fastapi import APIRouter, Depends, Response
from fastapi.responses import PlainTextResponse

from app.api.deps import get_current_user
from app.core.config.model_config import get_model_config
from app.core.config.settings import get_settings
from app.core.observability.metrics import render_prometheus
from app.core.system.hardware import get_cached_hardware_profile
from app.core.system.memory import get_memory_usage_mb
from app.db.mongodb import health_check as mongo_health_check
from app.db.qdrant import health_check as qdrant_health_check
from app.llm.model_registry import registry_status
from app.rag.verification.verifier import get_nli_metrics

router = APIRouter(tags=["health"])


@router.get(
    "/metrics",
    summary="Prometheus metrics exposition",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def prometheus_metrics() -> PlainTextResponse:
    """Prometheus exposition, dependency-free (public, counters only — no secrets)."""
    return PlainTextResponse(render_prometheus(), media_type="text/plain; version=0.0.4")


@router.get("/health", summary="Public application health check")
async def health() -> dict:
    """
    Public health check — minimal response for load balancers and Docker healthchecks.

    Always returns 200 so monitoring tools can always receive a response.
    Inspect the `status` field to determine actual health.
    """
    mongo_ok = await mongo_health_check()
    qdrant_ok = await qdrant_health_check()
    settings = get_settings()

    services = {
        "mongodb": "ok" if mongo_ok else "degraded",
        "qdrant": "ok" if qdrant_ok else "degraded",
    }

    overall_status = "ok" if all(v == "ok" for v in services.values()) else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "app": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/health/ready", summary="Readiness probe (503 when degraded)")
async def health_ready(response: Response) -> dict:
    """Readiness for Docker/K8s: 200 when all deps ok, 503 otherwise."""
    mongo_ok = await mongo_health_check()
    qdrant_ok = await qdrant_health_check()
    if not (mongo_ok and qdrant_ok):
        response.status_code = 503
        return {
            "status": "degraded",
            "timestamp": datetime.now(UTC).isoformat(),
            "services": {
                "mongodb": "ok" if mongo_ok else "degraded",
                "qdrant": "ok" if qdrant_ok else "degraded",
            },
        }
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": {"mongodb": "ok", "qdrant": "ok"},
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
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "services": services,
        "models": registry_status(),
        "hardware": get_cached_hardware_profile(),
        "supported_formats": cfg.supported_formats,
        "rss_mb": get_memory_usage_mb(),
        "metrics": {"nli": get_nli_metrics()},
    }
