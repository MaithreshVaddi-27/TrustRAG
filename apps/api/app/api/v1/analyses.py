"""
TRUSTRAG API — Analysis routes.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.api.v1.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    ClaimResponse,
    EvidenceResponse,
    TraceEventResponse,
)
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.rate_limiter import limiter
from app.services import analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate analysis run",
)
@limiter.limit(lambda: f"{get_settings().rate_limit_analyses_per_minute}/minute")
async def create_analysis_endpoint(
    request: Request,
    schema: AnalysisCreate,
    background_tasks: BackgroundTasks,
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> AnalysisResponse:
    """Create a new analysis run, verify KB access, and queue execution."""
    return await analysis_service.create_analysis(
        schema, str(current_user["_id"]), background_tasks
    )


@router.get("", response_model=list[AnalysisResponse], summary="List analysis history")
async def list_analyses_endpoint(
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    skip: int = Query(0, ge=0, description="Records to skip for pagination"),
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[AnalysisResponse]:
    """List all analysis runs submitted by the logged-in user with pagination."""
    return await analysis_service.list_analyses(str(current_user["_id"]), limit=limit, skip=skip)


@router.get("/{analysis_id}/export", summary="Export audit & compliance dossier")
async def export_analysis_endpoint(
    analysis_id: str,
    export_format: str = Query(
        "jsonld", alias="format", description="Export format: jsonld or json"
    ),
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Export complete verifiable dossier including answer, claim triples, and evidence hashes."""
    return await analysis_service.export_analysis_dossier(
        analysis_id, str(current_user["_id"]), export_format=export_format
    )


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
