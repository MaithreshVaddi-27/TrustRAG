"""
Unit tests for the Knowledge Ingestion pipeline components.
"""

from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.ingestion.chunker import chunk_text
from app.ingestion.parser import (
    extract_dates,
    parse_csv,
    parse_document,
    parse_docx,
    parse_html,
    parse_json,
)
from app.ingestion.sparse_vector import generate_sparse_vector, tokenize


def test_chunking_strategy():
    pages = [
        {"page": 1, "text": "This is page one text. " * 30},  # ~660 chars
        {"page": 2, "text": "Short page."},
    ]
    chunks = chunk_text(pages, chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    # Check shape
    assert chunks[0]["page"] == 1
    assert chunks[0]["chunk_index"] == 0
    assert "text" in chunks[0]

    # Last chunk page matching
    assert chunks[-1]["page"] == 2


def test_date_extraction():
    text_with_dates = """
    TRUSTRAG Policy Document
    Effective from: 2026-08-01
    Effective until: 2027-08-01

    This document outlines the standard return window of 30 days.
    """
    eff_from, eff_until = extract_dates(text_with_dates)

    assert eff_from is not None
    assert eff_until is not None
    assert eff_from.year == 2026
    assert eff_from.month == 8
    assert eff_from.day == 1
    assert eff_until.year == 2027


def test_date_extraction_missing():
    text_clean = "This document does not contain any effective dates."
    eff_from, eff_until = extract_dates(text_clean)
    assert eff_from is None
    assert eff_until is None


def test_sparse_vectorizer_tokenize():
    text = "This is a simple query, test query!"
    tokens = tokenize(text)

    # Stemmed tokens: "simple" -> "simpl", "query" -> "queri", "test" -> "test" (stopwords removed)
    assert "queri" in tokens
    assert "simpl" in tokens
    assert "test" in tokens
    assert "this" not in tokens


def test_sparse_vectorizer_generation():
    text = "refund processing refund window"
    sparse_vec = generate_sparse_vector(text)

    assert "indices" in sparse_vec
    assert "values" in sparse_vec
    assert len(sparse_vec["indices"]) == len(sparse_vec["values"])

    # "refund" appears twice out of 4 tokens (refund, processing, refund, window)
    # TF weight should be 2/4 = 0.5
    assert 0.5 in sparse_vec["values"]


@patch("app.ingestion.pipeline.init_kb_collection", AsyncMock())
@patch("app.ingestion.pipeline.get_qdrant_client")
@patch("app.ingestion.pipeline.get_embedding_model")
@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
@pytest.mark.asyncio
async def test_indexing_pipeline_execution(
    mock_create_indexes, mock_connect, mock_embed, mock_qdrant
):
    # Mock Qdrant client
    mock_client = MagicMock()
    mock_client.collection_exists = MagicMock(return_value=True)
    mock_qdrant.return_value = mock_client

    # Mock embedding model
    mock_embeddings = MagicMock()
    mock_embeddings.embed_documents = MagicMock(return_value=[[0.1] * 384, [0.2] * 384])
    mock_embed.return_value = mock_embeddings

    # Mock MongoDB updates
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(
        return_value={
            "_id": ObjectId("64ee39d09c6292376e191983"),
            "user_id": ObjectId("64ee39d09c6292376e191981"),
        }
    )
    mock_collection.update_one = AsyncMock()
    mock_collection.insert_many = AsyncMock()

    with patch("app.ingestion.pipeline.get_collection", return_value=mock_collection):
        from app.ingestion.pipeline import index_parsed_chunks

        chunks = [
            {"text": "chunk 1", "page": 1, "chunk_index": 0, "character_offset": 0},
            {"text": "chunk 2", "page": 1, "chunk_index": 1, "character_offset": 100},
        ]

        await index_parsed_chunks(
            doc_id_str="64ee39d09c6292376e191983",
            kb_id_str="64ee39d09c6292376e191982",
            chunks=chunks,
        )

        # Asserts status updates
        assert mock_collection.update_one.call_count == 2
        # Verify Qdrant client was called for upsert
        mock_client.upsert.assert_called_once()


def test_parse_csv():
    csv_data = b"Plan,Price,Window\nAnnual,1200,30 days\nMonthly,120,None"
    stream = io.BytesIO(csv_data)
    pages = parse_csv(stream)

    assert len(pages) == 1
    assert "Plan: Annual" in pages[0]["text"]
    assert "Price: 1200" in pages[0]["text"]


def test_parse_json():
    json_data = b'{"platform": "TRUSTRAG", "specs": {"max_size": 20}}'
    stream = io.BytesIO(json_data)
    pages = parse_json(stream)

    assert len(pages) == 1
    assert '"platform": "TRUSTRAG"' in pages[0]["text"]


def test_parse_html():
    html_data = (
        b"<html><body><h2>Service Terms</h2>"
        b"<p>All contracts include 30-day trial.</p></body></html>"
    )
    stream = io.BytesIO(html_data)
    pages = parse_html(stream)

    assert len(pages) == 1
    assert "Service Terms" in pages[0]["text"]
    assert "All contracts include 30-day trial." in pages[0]["text"]


def test_parse_docx():
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:t>Corporate Policy Document in DOCX</w:t></w:p></w:body>'
            '</w:document>'
        )
        zf.writestr("word/document.xml", xml)
    bio.seek(0)

    pages = parse_docx(bio)
    assert len(pages) == 1
    assert pages[0]["text"] == "Corporate Policy Document in DOCX"


def test_parse_document_routing():
    stream = io.BytesIO(b'{"key": "value"}')
    pages, _, _ = parse_document("config.json", stream)
    assert len(pages) == 1
    assert '"key": "value"' in pages[0]["text"]

