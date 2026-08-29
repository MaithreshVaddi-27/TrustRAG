"""
TRUSTRAG — Claims API routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.api.v1.schemas.analysis import ClaimResponse
from app.services import analysis_service

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("", response_model=list[ClaimResponse], summary="List all verified claims")
async def list_all_claims_endpoint(
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    skip: int = Query(0, ge=0, description="Records to skip for pagination"),
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[ClaimResponse]:
    """Retrieve all verified claims across analyses for the authenticated user with pagination."""
    return await analysis_service.list_all_user_claims(
        str(current_user["_id"]), limit=limit, skip=skip
    )
