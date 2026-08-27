"""
TRUSTRAG API — Knowledge Base routes.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import get_current_user
from app.api.v1.schemas.kb import KBCreate, KBResponse, DocResponse
from app.core.exceptions import FileTooLargeError, UnsupportedFormatError
from app.services import kb_service

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB as per specification
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


@router.post(
    "",
    response_model=KBResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new knowledge base"
)
async def create_kb_endpoint(
    schema: KBCreate,
    current_user: Mapping[str, Any] = Depends(get_current_user)
) -> KBResponse:
    """Create a new collection of documents under user ownership."""
    return await kb_service.create_kb(schema, str(current_user["_id"]))


@router.get(
    "",
    response_model=list[KBResponse],
    summary="List all user knowledge bases"
)
async def list_kbs_endpoint(
    current_user: Mapping[str, Any] = Depends(get_current_user)
) -> list[KBResponse]:
    """List all knowledge bases owned by the authenticated user."""
    return await kb_service.list_kbs(str(current_user["_id"]))


@router.get(
    "/{kb_id}",
    response_model=KBResponse,
    summary="Retrieve knowledge base metadata"
)
async def get_kb_endpoint(
    kb_id: str,
    current_user: Mapping[str, Any] = Depends(get_current_user)
) -> KBResponse:
    """Retrieve detailed knowledge base configuration and verify ownership."""
    return await kb_service.get_kb(kb_id, str(current_user["_id"]))


@router.delete(
    "/{kb_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge base"
)
async def delete_kb_endpoint(
    kb_id: str,
    current_user: Mapping[str, Any] = Depends(get_current_user)
) -> None:
    """Delete knowledge base and all registered documents from DB and vector storage."""
    await kb_service.delete_kb(kb_id, str(current_user["_id"]))


@router.get(
    "/{kb_id}/documents",
    response_model=list[DocResponse],
    summary="List documents in knowledge base"
)
async def list_documents_endpoint(
    kb_id: str,
    current_user: Mapping[str, Any] = Depends(get_current_user)
) -> list[DocResponse]:
    """List all documents registered in this knowledge base."""
    return await kb_service.list_kb_documents(kb_id, str(current_user["_id"]))


@router.post(
    "/{kb_id}/documents",
    response_model=DocResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and register document"
)
async def upload_document_endpoint(
    kb_id: str,
    file: UploadFile = File(...),
    current_user: Mapping[str, Any] = Depends(get_current_user)
) -> DocResponse:
    """
    Upload and parse a document.
    
    Accepts PDF, TXT, or MD files up to 20MB.
    Enforces format validation and registers document for parsing.
    """
    # Verify file extension
    filename = file.filename or "unknown"
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported file format '{ext}'",
            detail=f"Only the following formats are accepted: {list(ALLOWED_EXTENSIONS)}"
        )

    # Read content to check size and compute hash
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise FileTooLargeError(
            "Document upload failed",
            detail=f"File exceeds maximum limit of 20MB (got {file_size / (1024*1024):.2f}MB)"
        )

    # Compute content hash
    content_hash = hashlib.sha256(content).hexdigest()

    # Save to MongoDB
    doc = await kb_service.add_document(
        kb_id_str=kb_id,
        filename=filename,
        file_size=file_size,
        content_hash=content_hash,
        user_id_str=str(current_user["_id"])
    )

    # In Phase 5: Trigger asynchronous parsing task
    return doc
