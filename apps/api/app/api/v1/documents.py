"""
TRUSTRAG API — Document metadata retrieval routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.api.v1.schemas.kb import DocResponse
from app.core.exceptions import NotFoundError
from app.db.mongodb import Collections, get_collection
from app.services.kb_service import delete_document, get_kb, serialize_doc

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{doc_id}", response_model=DocResponse, summary="Get document details")
async def get_document_endpoint(
    doc_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> DocResponse:
    """Fetch details of a specific document, validating user ownership of the parent KB."""
    try:
        oid = ObjectId(doc_id)
    except Exception as exc:
        # Static detail: bson's message echoes the malformed input back.
        raise NotFoundError("Document not found", detail="malformed id") from exc

    doc = await get_collection(Collections.DOCUMENTS).find_one({"_id": oid})
    if not doc:
        raise NotFoundError("Document not found")

    # Verify ownership of the parent knowledge base
    await get_kb(str(doc["knowledge_base_id"]), str(current_user["_id"]))

    return serialize_doc(doc)


@router.delete("/{doc_id}", status_code=204, summary="Delete a document")
async def delete_document_endpoint(
    doc_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> None:
    """Delete a document, its chunks, and associated vectors, validating user ownership."""
    await delete_document(doc_id, str(current_user["_id"]))


@router.get(
    "/{doc_id}/pages/{page}/image",
    summary="Serve an OCR page render (Answer → chunk → page → image chain)",
    response_class=FileResponse,
)
async def get_document_page_image_endpoint(
    doc_id: str, page: int, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> FileResponse:
    """Serve the exact page render the OCR engine read for one document page.

    Ownership is verified through the parent knowledge base (same rule as the
    document detail route). 404 when the document, the page chunk, the stored
    ref, or the file itself is missing — never leak which of those it was
    beyond the status code.
    """
    from app.rag.ingestion import page_images as page_images_mod

    try:
        oid = ObjectId(doc_id)
    except Exception as exc:
        raise NotFoundError("Document not found", detail="malformed id") from exc
    if page < 1:
        raise NotFoundError("Page image not found")

    doc = await get_collection(Collections.DOCUMENTS).find_one({"_id": oid})
    if not doc:
        raise NotFoundError("Document not found")

    # Verify ownership of the parent knowledge base (raises 403/404).
    await get_kb(str(doc["knowledge_base_id"]), str(current_user["_id"]))

    chunk = await get_collection(Collections.DOCUMENT_CHUNKS).find_one(
        {"document_id": oid, "page": page}
    )
    ref = (chunk or {}).get("page_image_ref")
    path = page_images_mod.resolve_page_image_path(ref) if ref else None
    if path is None:
        raise NotFoundError("Page image not found")
    return FileResponse(str(path), media_type="image/png")
