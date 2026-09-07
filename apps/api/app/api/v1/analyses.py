"""
TRUSTRAG API — Analysis routes.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
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
from app.db.mongodb import Collections, get_collection
from app.services import analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])

# Rate limit string evaluated once at module load (SlowAPI expects a string, not a callable)
_ANALYSIS_RATE_LIMIT = f"{get_settings().rate_limit_analyses_per_minute}/minute"

# SSE stream tickets live in MongoDB (stream_tickets, TTL janitor), NOT in
# process memory — ticket issuance and stream consumption can land on different
# uvicorn workers. Single-use (atomic find-and-delete) with 60s validity.
_STREAM_TICKET_TTL_SECONDS = 60


async def _issue_stream_ticket(user_id: str, analysis_id: str) -> str:
    ticket = secrets.token_urlsafe(32)
    await get_collection(Collections.STREAM_TICKETS).insert_one(
        {
            "_id": ticket,
            "user_id": user_id,
            "analysis_id": analysis_id,
            "expires_at": datetime.now(UTC) + timedelta(seconds=_STREAM_TICKET_TTL_SECONDS),
        }
    )
    return ticket


async def _consume_stream_ticket(ticket: str, analysis_id: str) -> str | None:
    """Atomically consume a ticket. Returns user_id, or None if invalid/expired."""
    doc = await get_collection(Collections.STREAM_TICKETS).find_one_and_delete({"_id": ticket})
    if not doc or doc.get("analysis_id") != analysis_id:
        return None
    expires_at = doc.get("expires_at")
    if expires_at is not None:
        if getattr(expires_at, "tzinfo", None) is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None
    return doc.get("user_id")


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


@router.get(
    "/{analysis_id}/detail",
    summary="Get analysis with claims, evidence, and trace in one call",
)
async def get_analysis_detail_endpoint(
    analysis_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Single-round-trip finalize payload (1 ownership check, 3 parallel queries)."""
    return await analysis_service.get_analysis_detail(analysis_id, str(current_user["_id"]))


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
    The ticket is cryptographically random, single-use, and Mongo-backed so
    any uvicorn worker can consume it.
    """
    ticket = await _issue_stream_ticket(str(current_user["_id"]), analysis_id)
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
    # Validate and consume the ticket (atomic single-use)
    user_id_str = await _consume_stream_ticket(ticket, analysis_id)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired stream ticket",
        )

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
