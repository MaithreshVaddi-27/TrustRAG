"""
TRUSTRAG — Conflicts API routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends

from app.api.v1.auth import get_current_user
from app.services import analysis_service

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("", summary="List all source & claim conflicts")
async def list_all_conflicts_endpoint(
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve all detected contradictions and integrity conflicts for the authenticated user."""
    return await analysis_service.list_all_user_conflicts(str(current_user["_id"]))
