"""
TRUSTRAG API — Analysis routes.
"""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
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
from app.core.rate_limiter import limiter
from app.services import analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])

# Rate limit string evaluated once at module load (SlowAPI expects a string, not a callable)
_ANALYSIS_RATE_LIMIT = f"{get_settings().rate_limit_analyses_per_minute}/minute"

# In-memory short-lived SSE ticket store: {ticket: (user_id, analysis_id, expires_at)}
# Tickets are single-use and expire after 60 seconds to avoid JWT-in-URL exposure.
_SSE_TICKETS: dict[str, tuple[str, str, float]] = {}


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate analysis run",
)
@limiter.limit(_ANALYSIS_RATE_LIMIT)
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


@router.post(
    "/{analysis_id}/stream-ticket",
    summary="Issue short-lived SSE stream ticket",
    status_code=status.HTTP_201_CREATED,
)
async def create_stream_ticket_endpoint(
    analysis_id: str,
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """
    Issue a 60-second single-use ticket for the SSE stream endpoint.

    Use this instead of passing the full JWT in the query string,
    which would expose it in server logs and browser history.
    The ticket is a cryptographically random token stored in memory.
    """
    # Purge expired tickets lazily
    now = time.time()
    expired = [k for k, v in _SSE_TICKETS.items() if v[2] < now]
    for k in expired:
        _SSE_TICKETS.pop(k, None)

    ticket = secrets.token_urlsafe(32)
    _SSE_TICKETS[ticket] = (str(current_user["_id"]), analysis_id, now + 60)
    return {"ticket": ticket}


@router.get("/{analysis_id}/stream", summary="Stream live execution trace")
async def stream_trace_endpoint(
    analysis_id: str,
    ticket: str = Query(
        ..., description="Short-lived single-use stream ticket (from POST /stream-ticket)"
    ),
) -> StreamingResponse:
    """
    Establish Server-Sent Events (SSE) stream for live trace updates.

    Requires a short-lived (60s), single-use `ticket` issued by POST /stream-ticket.
    Raw JWTs are NOT accepted in the query string — they would leak into access logs,
    proxy logs, and browser history.
    """
    # Validate and consume the ticket
    now = time.time()
    entry = _SSE_TICKETS.pop(ticket, None)
    if not entry or entry[2] < now or entry[1] != analysis_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired stream ticket",
        )
    user_id_str = entry[0]

    async def event_publisher():
        async for event_data in analysis_service.sse_event_generator(analysis_id, user_id_str):
            # Format according to SSE spec: data: <json_string>\n\n
            yield f"data: {json.dumps(event_data)}\n\n"

    return StreamingResponse(
        event_publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
