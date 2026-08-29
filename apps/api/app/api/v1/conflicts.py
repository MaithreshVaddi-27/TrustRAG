"""
TRUSTRAG — Conflicts API routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.services import analysis_service

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("", summary="List all source & claim conflicts")
async def list_all_conflicts_endpoint(
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    skip: int = Query(0, ge=0, description="Records to skip for pagination"),
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve all detected contradictions and conflicts for the user with pagination."""
    return await analysis_service.list_all_user_conflicts(
        str(current_user["_id"]), limit=limit, skip=skip
    )
