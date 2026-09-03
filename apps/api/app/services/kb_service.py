"""
TRUSTRAG — Knowledge Base and Document management business logic.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from qdrant_client.http import models

from app.api.v1.schemas.kb import DocResponse, KBCreate, KBResponse
from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.db.mongodb import Collections, get_collection
from app.db.qdrant import delete_kb_collection, get_collection_name, get_qdrant_client

logger = get_logger(__name__)


def serialize_kb(kb_doc: Mapping[str, Any], doc_count: int = 0) -> KBResponse:
    """Helper to convert MongoDB KB document to Pydantic KBResponse."""
    return KBResponse(
        id=str(kb_doc["_id"]),
        name=kb_doc["name"],
        description=kb_doc.get("description", ""),
        user_id=str(kb_doc["user_id"]),
        document_count=doc_count,
        created_at=kb_doc["created_at"],
    )


def serialize_doc(doc_doc: Mapping[str, Any]) -> DocResponse:
    """Helper to convert MongoDB Document document to Pydantic DocResponse."""
    return DocResponse(
        id=str(doc_doc["_id"]),
        knowledge_base_id=str(doc_doc["knowledge_base_id"]),
        filename=doc_doc["filename"],
        file_size=doc_doc["file_size"],
        content_hash=doc_doc["content_hash"],
        ingestion_status=doc_doc.get("ingestion_status", "pending"),
        error_message=doc_doc.get("error_message"),
        effective_from=doc_doc.get("effective_from"),
        effective_until=doc_doc.get("effective_until"),
        created_at=doc_doc["created_at"],
    )


async def create_kb(schema: KBCreate, user_id: str) -> KBResponse:
    """Create a new knowledge base linked to user."""
    kb_coll = get_collection(Collections.KNOWLEDGE_BASES)
    kb_doc = {
        "name": schema.name.strip(),
        "description": schema.description.strip(),
        "user_id": ObjectId(user_id),
        "created_at": datetime.now(UTC),
    }
    result = await kb_coll.insert_one(kb_doc)
    kb_doc["_id"] = result.inserted_id
    return serialize_kb(kb_doc, 0)


async def get_kb(kb_id_str: str, user_id_str: str) -> KBResponse:
    """
    Retrieve knowledge base by ID and verify ownership.

    Raises NotFoundError or AuthorizationError on security check failure.
    """
    try:
        kb_id = ObjectId(kb_id_str)
    except Exception as exc:
        raise NotFoundError("Knowledge Base not found", detail=str(exc)) from exc

    kb = await get_collection(Collections.KNOWLEDGE_BASES).find_one({"_id": kb_id})
    if not kb:
        raise NotFoundError("Knowledge Base not found")

    if str(kb["user_id"]) != user_id_str:
        raise AuthorizationError("Access denied", detail="You do not own this knowledge base")

    # Count documents
    doc_count = await get_collection(Collections.DOCUMENTS).count_documents(
        {"knowledge_base_id": kb_id}
    )

    return serialize_kb(kb, doc_count)


async def list_kbs(user_id_str: str) -> list[KBResponse]:
    """List all knowledge bases owned by user with document counts in a single aggregation."""
    kb_coll = get_collection(Collections.KNOWLEDGE_BASES)
    doc_coll = get_collection(Collections.DOCUMENTS)

    # Fetch all KBs owned by user in one query
    user_obj_id = ObjectId(user_id_str)
    kbs_raw = await kb_coll.find({"user_id": user_obj_id}).sort("created_at", -1).to_list(500)

    if not kbs_raw:
        return []

    # Batch-fetch document counts using a single aggregation (avoids N+1 per-KB count queries)
    kb_ids = [kb["_id"] for kb in kbs_raw]
    count_pipeline = [
        {"$match": {"knowledge_base_id": {"$in": kb_ids}}},
        {"$group": {"_id": "$knowledge_base_id", "count": {"$sum": 1}}},
    ]
    count_map: dict = {}
    async for row in doc_coll.aggregate(count_pipeline):
        count_map[row["_id"]] = row["count"]

    return [serialize_kb(kb, count_map.get(kb["_id"], 0)) for kb in kbs_raw]


async def delete_kb(kb_id_str: str, user_id_str: str) -> None:
    """
    Delete a knowledge base and all associated documents.

    Verifies ownership before deleting.
    """
    # Ensure KB exists and belongs to the user
    await get_kb(kb_id_str, user_id_str)

    kb_id = ObjectId(kb_id_str)
    # 1. Delete associated documents in MongoDB
    await get_collection(Collections.DOCUMENTS).delete_many({"knowledge_base_id": kb_id})

    # 2. Delete associated document chunks in MongoDB
    await get_collection(Collections.DOCUMENT_CHUNKS).delete_many({"knowledge_base_id": kb_id})

    # 3. Drop the associated Qdrant vector collection to avoid orphaned storage
    await delete_kb_collection(kb_id_str)

    # 4. Delete the KB record itself
    await get_collection(Collections.KNOWLEDGE_BASES).delete_one({"_id": kb_id})


async def add_document(
    kb_id_str: str,
    filename: str,
    file_size: int,
    content_hash: str,
    user_id_str: str,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
) -> DocResponse:
    """
    Add a document metadata record. Verifies KB ownership first.
    """
    # Verify owner
    await get_kb(kb_id_str, user_id_str)

    doc_coll = get_collection(Collections.DOCUMENTS)
    doc_doc = {
        "user_id": ObjectId(user_id_str),
        "knowledge_base_id": ObjectId(kb_id_str),
        "filename": filename,
        "file_size": file_size,
        "content_hash": content_hash,
        "ingestion_status": "pending",
        "error_message": None,
        "effective_from": effective_from,
        "effective_until": effective_until,
        "created_at": datetime.now(UTC),
    }

    result = await doc_coll.insert_one(doc_doc)
    doc_doc["_id"] = result.inserted_id
    return serialize_doc(doc_doc)


async def list_kb_documents(kb_id_str: str, user_id_str: str) -> list[DocResponse]:
    """List all documents registered in a knowledge base."""
    # Verify owner
    await get_kb(kb_id_str, user_id_str)

    doc_coll = get_collection(Collections.DOCUMENTS)
    docs = []
    async for d in doc_coll.find({"knowledge_base_id": ObjectId(kb_id_str)}).sort("created_at", -1):
        docs.append(serialize_doc(d))
    return docs


async def delete_document(doc_id_str: str, user_id_str: str) -> None:
    """
    Delete a document, all its chunks, and associated Qdrant vector points.

    Verifies ownership of the parent KB before deleting.
    """
    from app.core.exceptions import NotFoundError

    try:
        doc_id = ObjectId(doc_id_str)
    except Exception as exc:
        raise NotFoundError("Document not found", detail=str(exc)) from exc

    doc_coll = get_collection(Collections.DOCUMENTS)
    doc = await doc_coll.find_one({"_id": doc_id})
    if not doc:
        raise NotFoundError("Document not found")

    # Verify ownership
    kb_id_str = str(doc["knowledge_base_id"])
    await get_kb(kb_id_str, user_id_str)

    # 1. Delete chunks in MongoDB
    await get_collection(Collections.DOCUMENT_CHUNKS).delete_many({"document_id": doc_id})

    # 2. Delete points from Qdrant collection
    client = get_qdrant_client()
    collection_name = get_collection_name(kb_id_str)
    try:
        if client.collection_exists(collection_name):
            client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=doc_id_str),
                            )
                        ]
                    )
                ),
            )
    except Exception as exc:
        logger.warning(
            "Failed to delete Qdrant points for document",
            doc_id=doc_id_str,
            error=str(exc),
        )

    # 3. Delete document record itself
    await doc_coll.delete_one({"_id": doc_id})
    logger.info("Document deleted successfully", doc_id=doc_id_str, kb_id=kb_id_str)
