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


@router.get(
    "/{doc_id}/pages/{page}/image",
    summary="Get OCR source page image",
    response_class=FileResponse,
)
async def get_document_page_image_endpoint(
    doc_id: str, page: int, current_user: Mapping[str, Any] = Depends(get_current_user)
):
    """Serve the exact page render the OCR engine read (Phase 7 chain).

    Resolves authoritatively from the chunk record (document_id + page), so
    the image is provably the one behind the served evidence. 404 when the
    document, chunk, or image file does not exist.
    """
    from app.ingestion.page_images import resolve_page_image_path

    try:
        oid = ObjectId(doc_id)
    except Exception as exc:
        raise NotFoundError("Document not found", detail=str(exc)) from exc

    doc = await get_collection(Collections.DOCUMENTS).find_one({"_id": oid})
    if not doc:
        raise NotFoundError("Document not found")

    # Verify ownership of the parent knowledge base
    await get_kb(str(doc["knowledge_base_id"]), str(current_user["_id"]))

    chunk = await get_collection(Collections.DOCUMENT_CHUNKS).find_one(
        {"document_id": oid, "page": page}, {"page_image_ref": 1}
    )
    ref = chunk.get("page_image_ref") if chunk else None
    path = resolve_page_image_path(ref)
    if path is None:
        raise NotFoundError("No source image for this page")
    return FileResponse(path, media_type="image/png", filename=f"p{page}.png")
