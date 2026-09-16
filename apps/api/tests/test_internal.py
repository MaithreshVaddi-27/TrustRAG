"""
Unit tests for internal service endpoint input contracts.

Covers the M-2 hardening: strict Pydantic bodies reject malformed
service-triggered ingestion with 422 instead of 500s on missing keys.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.internal import InternalDocumentIngest, InternalUrlIngest


def test_internal_document_ingest_accepts_valid_body():
    body = InternalDocumentIngest(
        filename="policy.txt",
        file_size=128,
        content_hash="abc123",
        user_id="64ee39d09c6292376e191981",
    )
    assert body.filename == "policy.txt"
    assert body.effective_from is None


def test_internal_document_ingest_rejects_bad_user_id():
    with pytest.raises(ValidationError):
        InternalDocumentIngest(
            filename="policy.txt",
            file_size=128,
            content_hash="abc123",
            user_id="not-an-object-id",
        )


def test_internal_document_ingest_rejects_missing_keys():
    with pytest.raises(ValidationError):
        InternalDocumentIngest(filename="policy.txt", file_size=128)


def test_internal_document_ingest_rejects_negative_size():
    with pytest.raises(ValidationError):
        InternalDocumentIngest(
            filename="policy.txt",
            file_size=-5,
            content_hash="abc123",
            user_id="64ee39d09c6292376e191981",
        )


def test_internal_url_ingest_accepts_and_rejects():
    ok_body = InternalUrlIngest(url="https://example.com/doc.pdf")
    assert ok_body.url.startswith("https://")
    assert ok_body.user_id is None
    with pytest.raises(ValidationError):
        InternalUrlIngest(url="https://example.com/doc.pdf", user_id="bad-id")
