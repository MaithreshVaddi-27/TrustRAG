"""Re-ingest tests for documents left in a failed state."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pymongo
import pytest
from bson import ObjectId

from app.persistence.mongodb import Collections
from app.security.exceptions import ConflictError
from app.services.kb_service import add_document


def _collections(documents: MagicMock, chunks: MagicMock):
    return lambda name: documents if name == Collections.DOCUMENTS else chunks


def _failed_doc(kb_id: ObjectId) -> dict:
    return {
        "_id": ObjectId(),
        "knowledge_base_id": kb_id,
        "filename": "notes.txt",
        "file_size": 12,
        "content_hash": "abc123",
        "ingestion_status": "failed",
        "error_message": "Ingestion error (ConfigurationError)",
        "effective_from": None,
        "effective_until": None,
        "created_at": datetime.now(UTC),
        "version": "1.0",
    }


@pytest.mark.asyncio
async def test_failed_document_is_reset_for_reingest():
    """A failed document must not block re-upload of the same bytes."""
    kb_id, user_id = ObjectId(), ObjectId()
    existing = _failed_doc(kb_id)
    documents = MagicMock()
    documents.insert_one = AsyncMock(
        side_effect=pymongo.errors.DuplicateKeyError(
            "E11000 duplicate key error index: doc_kb_content_hash_unique"
        )
    )
    documents.find_one = AsyncMock(return_value=existing)
    documents.update_one = AsyncMock()
    # The indexing pipeline clears stale chunks for this document ID, so the
    # service only needs to reset the metadata record.
    chunks = MagicMock()

    with (
        patch("app.services.kb_service.get_kb", AsyncMock()),
        patch(
            "app.services.kb_service.get_collection",
            side_effect=_collections(documents, chunks),
        ),
    ):
        result = await add_document(
            kb_id_str=str(kb_id),
            filename="notes.txt",
            file_size=12,
            content_hash="abc123",
            user_id_str=str(user_id),
        )

    assert result.id == str(existing["_id"])
    assert result.ingestion_status == "pending"
    assert result.error_message is None
    documents.update_one.assert_awaited_once()
    reset = documents.update_one.await_args.args[1]["$set"]
    assert reset["ingestion_status"] == "pending"
    assert reset["error_message"] is None


@pytest.mark.asyncio
async def test_successfully_ingested_document_still_conflicts():
    """Only failed documents may be re-uploaded; duplicates stay 409."""
    kb_id, user_id = ObjectId(), ObjectId()
    existing = _failed_doc(kb_id)
    existing["ingestion_status"] = "completed"
    documents = MagicMock()
    documents.insert_one = AsyncMock(
        side_effect=pymongo.errors.DuplicateKeyError("doc_kb_content_hash_unique")
    )
    documents.find_one = AsyncMock(return_value=existing)
    documents.update_one = AsyncMock()
    chunks = MagicMock()

    with (
        patch("app.services.kb_service.get_kb", AsyncMock()),
        patch(
            "app.services.kb_service.get_collection",
            side_effect=_collections(documents, chunks),
        ),
        pytest.raises(ConflictError),
    ):
        await add_document(
            kb_id_str=str(kb_id),
            filename="notes.txt",
            file_size=12,
            content_hash="abc123",
            user_id_str=str(user_id),
        )

    documents.update_one.assert_not_awaited()
