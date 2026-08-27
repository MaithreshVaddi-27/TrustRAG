"""
TRUSTRAG API — Analysis routes.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.api.v1.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    ClaimResponse,
    EvidenceResponse,
    TraceEventResponse,
)
from app.core.exceptions import AuthenticationError
from app.services import analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate analysis run",
)
async def create_analysis_endpoint(
    schema: AnalysisCreate, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> AnalysisResponse:
    """Create a new analysis run, verify KB access, and queue execution."""
    return await analysis_service.create_analysis(schema, str(current_user["_id"]))


@router.get("", response_model=list[AnalysisResponse], summary="List analysis history")
async def list_analyses_endpoint(
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[AnalysisResponse]:
    """List all analysis runs submitted by the logged-in user."""
    return await analysis_service.list_analyses(str(current_user["_id"]))


@router.get("/{analysis_id}", response_model=AnalysisResponse, summary="Get analysis run details")
async def get_analysis_endpoint(
    analysis_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> AnalysisResponse:
    """Fetch status and generated answer for a specific analysis run."""
    return await analysis_service.get_analysis(analysis_id, str(current_user["_id"]))


@router.get(
    "/{analysis_id}/claims",
    response_model=list[ClaimResponse],
    summary="Get claims extracted during analysis",
)
async def get_claims_endpoint(
    analysis_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> list[ClaimResponse]:
    """Retrieve the list of decomposed claims and their verification states."""
    return await analysis_service.get_analysis_claims(analysis_id, str(current_user["_id"]))


@router.get(
    "/{analysis_id}/evidence",
    response_model=list[EvidenceResponse],
    summary="Get evidence retrieved during analysis",
)
async def get_evidence_endpoint(
    analysis_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> list[EvidenceResponse]:
    """Retrieve details of documents and chunks used as evidence for verifying claims."""
    return await analysis_service.get_analysis_evidence(analysis_id, str(current_user["_id"]))


@router.get(
    "/{analysis_id}/trace",
    response_model=list[TraceEventResponse],
    summary="Get execution trace history",
)
async def get_trace_endpoint(
    analysis_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> list[TraceEventResponse]:
    """Retrieve full timeline of trace events from MongoDB (fallback for SSE)."""
    return await analysis_service.get_analysis_trace(analysis_id, str(current_user["_id"]))


@router.get("/{analysis_id}/stream", summary="Stream live execution trace")
async def stream_trace_endpoint(
    analysis_id: str,
    token: str | None = Query(
        None, description="Auth token (required since EventSource doesn't support headers)"
    ),
) -> StreamingResponse:
    """
    Establish Server-Sent Events (SSE) stream for live trace updates.

    Validates token from query parameters.
    """
    if not token:
        raise AuthenticationError(
            "Not authenticated", detail="Token must be passed as query parameter"
        )

    # Reuse get_current_user logic manually
    user = await get_current_user(token)
    user_id_str = str(user["_id"])

    async def event_publisher():
        async for event_data in analysis_service.sse_event_generator(analysis_id, user_id_str):
            # Format according to SSE spec: data: <json_string>\n\n
            yield f"data: {json.dumps(event_data)}\n\n"

    return StreamingResponse(event_publisher(), media_type="text/event-stream")
