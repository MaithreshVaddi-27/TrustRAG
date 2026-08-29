"""
Unit tests for the Evidence Integrity Audit module.
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from app.verification.integrity import audit_evidence_integrity


@pytest.mark.asyncio
async def test_audit_evidence_integrity_success():
    doc_id = ObjectId("64ee39d09c6292376e191981")
    text_1 = "Authentic document segment text."
    hash_1 = hashlib.sha256(text_1.encode("utf-8")).hexdigest()

    text_2 = "Tampered or modified document text."

    chunks = [
        {"document_id": str(doc_id), "chunk_index": 0, "text": text_1},
        {"document_id": str(doc_id), "chunk_index": 1, "text": text_2},
        {"document_id": str(doc_id), "chunk_index": 2, "text": "Missing from DB"},
    ]

    # Mock MongoDB response documents from document_chunks
    mock_db_records = [
        {
            "document_id": doc_id,
            "chunk_index": 0,
            "text_hash": hash_1,
        },
        {
            "document_id": doc_id,
            "chunk_index": 1,
            "text_hash": "original_hash_value_here",
        },
    ]

    mock_cursor = MagicMock()

    async def mock_async_gen():
        for d in mock_db_records:
            yield d

    mock_cursor.__aiter__ = MagicMock(side_effect=mock_async_gen)

    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)

    with patch("app.verification.integrity.get_collection", return_value=mock_collection):
        audited = await audit_evidence_integrity(chunks)

        assert len(audited) == 3
        # Chunk 0: matches hash exactly
        assert audited[0]["integrity_status"] == "VERIFIED"

        # Chunk 1: mismatch hash (tampered)
        assert audited[1]["integrity_status"] == "CORRUPTED"

        # Chunk 2: missing record in DB
        assert audited[2]["integrity_status"] == "CORRUPTED"
