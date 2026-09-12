"""
TRUSTRAG API — Internal service-to-service endpoints.

These endpoints are protected by service token authentication and are
intended for communication between TrustRAG microservices (workers, gateways, etc.).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, field_validator

from app.api.deps import require_service_permission
from app.core.security import create_service_token
from app.services.kb_service import add_document

router = APIRouter(prefix="/internal", tags=["internal"])


class InternalDocumentIngest(BaseModel):
    """Strict body for service-triggered ingestion (422, never 500, on bad input)."""

    filename: str
    file_size: int
    content_hash: str
    user_id: str
    effective_from: datetime | None = None
    effective_until: datetime | None = None

    @field_validator("user_id")
    @classmethod
    def _valid_user_id(cls, value: str) -> str:
        if not ObjectId.is_valid(value):
            raise ValueError("user_id must be a valid ObjectId")
        return value

    @field_validator("file_size")
    @classmethod
    def _non_negative_size(cls, value: int) -> int:
        if value < 0:
            raise ValueError("file_size must be non-negative")
        return value


class InternalUrlIngest(BaseModel):
    """Strict body for service-triggered URL ingestion."""

    url: str
    user_id: str | None = None

    @field_validator("user_id")
    @classmethod
    def _valid_user_id(cls, value: str | None) -> str | None:
        if value is not None and not ObjectId.is_valid(value):
            raise ValueError("user_id must be a valid ObjectId")
        return value


# ─── Service Token Management ─────────────────────────────────────────────────


@router.post(
    "/tokens",
    status_code=status.HTTP_201_CREATED,
    summary="Generate service token (admin only)",
)
async def generate_service_token_endpoint(
    service_name: str,
    permissions: list[str],
    current_service: Mapping[str, Any] = Depends(require_service_permission("admin:token:create")),
) -> dict[str, Any]:
    """
    Generate a new service token for a microservice.

    Requires admin:token:create permission.
    """
    token = create_service_token(service_name=service_name, permissions=permissions)
    return {
        "service_name": service_name,
        "token": token,
        "permissions": permissions,
    }


# ─── Internal Ingestion Endpoints ────────────────────────────────────────────


@router.post(
    "/ingest/document",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Internal document ingestion trigger",
)
async def internal_ingest_document(
    kb_id: str,
    document_data: InternalDocumentIngest,
    current_service: Mapping[str, Any] = Depends(require_service_permission("ingest:write")),
) -> dict[str, Any]:
    """
    Trigger document ingestion from an internal service (e.g., worker, scheduler).

    Requires ingest:write permission. Malformed bodies are rejected with 422
    (the strict schema above); tenant binding of service tokens remains a
    tracked hardening item (M-2) — the KB-ownership check inside add_document
    is the current cross-tenant backstop.
    """
    service_name = current_service.get("sub")

    # Add document metadata
    doc = await add_document(
        kb_id_str=kb_id,
        filename=document_data.filename,
        file_size=document_data.file_size,
        content_hash=document_data.content_hash,
        user_id_str=document_data.user_id,
        effective_from=document_data.effective_from,
        effective_until=document_data.effective_until,
    )

    return {
        "document_id": doc.id,
        "status": "queued",
        "triggered_by": service_name,
    }


@router.post(
    "/ingest/url",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Internal URL ingestion trigger",
)
async def internal_ingest_url(
    kb_id: str,
    url_data: InternalUrlIngest,
    current_service: Mapping[str, Any] = Depends(require_service_permission("ingest:write")),
) -> dict[str, Any]:
    """
    Trigger URL document ingestion from an internal service.

    Requires ingest:write permission.
    """
    service_name = current_service.get("sub")

    # This would call the URL ingestion logic
    return {
        "status": "queued",
        "url": url_data.url,
        "triggered_by": service_name,
    }


# ─── Internal Search/Retrieval ────────────────────────────────────────────────


@router.post(
    "/search",
    summary="Internal hybrid search",
)
async def internal_search(
    query: str,
    kb_id: str,
    top_k: int = 10,
    current_service: Mapping[str, Any] = Depends(require_service_permission("search:read")),
) -> dict[str, Any]:
    """
    Perform hybrid search from an internal service.

    Requires search:read permission.
    """
    from app.core.exceptions import RetrievalOutageError
    from app.retrieval.retriever import retrieve_hybrid_chunks

    try:
        results = await retrieve_hybrid_chunks(query=query, kb_id=kb_id, top_k_override=top_k)
    except RetrievalOutageError as exc:
        return {
            "results": [],
            "count": 0,
            "error": f"retrieval outage: {exc}",
        }

    return {
        "results": results,
        "count": len(results),
    }


# ─── Internal Verification ───────────────────────────────────────────────────


@router.post(
    "/verify/claims",
    summary="Internal claim verification",
)
async def internal_verify_claims(
    claims: list[str],
    evidence_texts: list[str],
    current_service: Mapping[str, Any] = Depends(require_service_permission("verify:execute")),
) -> dict[str, Any]:
    """
    Verify claims against evidence from an internal service.

    Requires verify:execute permission.
    """
    from app.verification.verifier import batch_verify_claims_nli

    fake_chunks = [
        {"chunk_id": f"ev_{idx}", "text": text} for idx, text in enumerate(evidence_texts)
    ]
    verdicts = await batch_verify_claims_nli(claims=claims, chunks=fake_chunks)

    return {
        "verdicts": verdicts,
    }


# ─── Health & Status ──────────────────────────────────────────────────────────


@router.get(
    "/health",
    summary="Internal service health check",
)
async def internal_health() -> dict[str, str]:
    """
    Health check endpoint for service mesh / load balancer.
    No authentication required for basic liveness.
    """
    return {"status": "healthy"}


@router.get(
    "/status",
    summary="Detailed internal service status",
)
async def internal_status(
    current_service: Mapping[str, Any] = Depends(require_service_permission("admin:status:read")),
) -> dict[str, Any]:
    """
    Detailed status for internal monitoring.

    Requires admin:status:read permission.
    """
    from app.core.model_registry import registry_status

    return {
        "service": "trustrag-api",
        "status": "operational",
        "models": registry_status(),
    }
