"""
TRUSTRAG — Claims API routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends

from app.api.v1.auth import get_current_user
from app.api.v1.schemas.analysis import ClaimResponse
from app.services import analysis_service

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("", response_model=list[ClaimResponse], summary="List all verified claims")
async def list_all_claims_endpoint(
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[ClaimResponse]:
    """Retrieve all verified claims across analyses for the authenticated user."""
    return await analysis_service.list_all_user_claims(str(current_user["_id"]))
