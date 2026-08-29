"""
TRUSTRAG — Evidence API routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends

from app.api.v1.auth import get_current_user
from app.api.v1.schemas.analysis import EvidenceResponse
from app.services import analysis_service

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("", response_model=list[EvidenceResponse], summary="List all retrieved evidence records")
async def list_all_evidence_endpoint(
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[EvidenceResponse]:
    """Retrieve all evidence chunks retrieved across analyses for the authenticated user."""
    return await analysis_service.list_all_user_evidence(str(current_user["_id"]))
