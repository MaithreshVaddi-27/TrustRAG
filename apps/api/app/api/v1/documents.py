"""
TRUSTRAG API — Document metadata retrieval routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.schemas.kb import DocResponse
from app.core.exceptions import NotFoundError
from app.db.mongodb import Collections, get_collection
from app.services.kb_service import get_kb

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{doc_id}", response_model=DocResponse, summary="Get document details")
async def get_document_endpoint(
    doc_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> DocResponse:
    """Fetch details of a specific document, validating user ownership of the parent KB."""
    try:
        oid = ObjectId(doc_id)
    except Exception as exc:
        raise NotFoundError("Document not found", detail=str(exc)) from exc

    doc = await get_collection(Collections.DOCUMENTS).find_one({"_id": oid})
    if not doc:
        raise NotFoundError("Document not found")

    # Verify ownership of the parent knowledge base
    await get_kb(str(doc["knowledge_base_id"]), str(current_user["_id"]))

    from app.services.kb_service import serialize_doc

    return serialize_doc(doc)


@router.delete("/{doc_id}", status_code=204, summary="Delete a document")
async def delete_document_endpoint(
    doc_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> None:
    """Delete a document, its chunks, and associated vectors, validating user ownership."""
    from app.services.kb_service import delete_document

    await delete_document(doc_id, str(current_user["_id"]))
