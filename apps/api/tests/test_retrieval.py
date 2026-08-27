"""
Unit tests for the hybrid dense + sparse retriever.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.retrieval.retriever import apply_temporal_filtering, reciprocal_rank_fusion


def test_reciprocal_rank_fusion_logic():
    # Mock ScoredPoint structures from Qdrant
    dense_point = MagicMock()
    dense_point.id = "point-1"
    dense_point.score = 0.9
    dense_point.payload = {"text": "dense text content", "document_id": "doc-1"}

    sparse_point_1 = MagicMock()
    sparse_point_1.id = "point-1"
    sparse_point_1.score = 0.5
    sparse_point_1.payload = {"text": "dense text content", "document_id": "doc-1"}

    sparse_point_2 = MagicMock()
    sparse_point_2.id = "point-2"
    sparse_point_2.score = 0.8
    sparse_point_2.payload = {"text": "sparse text content", "document_id": "doc-2"}

    dense_results = [dense_point]
    sparse_results = [sparse_point_1, sparse_point_2]

    # Fused with k=60
    fused = reciprocal_rank_fusion(dense_results, sparse_results, k=60)

    assert len(fused) == 2
    # point-1 was ranked 1st in dense and 1st in sparse, so it must be first
    assert fused[0]["id"] == "point-1"
    # RRF score calculation: 1/(1+60) + 1/(1+60) = 2/61 = ~0.0327
    assert abs(fused[0]["rrf_score"] - (2.0 / 61.0)) < 1e-5

    # point-2 was ranked 2nd in sparse and not found in dense
    assert fused[1]["id"] == "point-2"
    # RRF score calculation: 1/(2+60) = 1/62 = ~0.0161
    assert abs(fused[1]["rrf_score"] - (1.0 / 62.0)) < 1e-5


@pytest.mark.asyncio
async def test_temporal_validity_filtering():
    results = [
        {"document_id": "64ee39d09c6292376e191981", "text": "active chunk"},
        {"document_id": "64ee39d09c6292376e191982", "text": "expired chunk"},
        {"document_id": "64ee39d09c6292376e191983", "text": "future chunk"},
    ]

    ref_time = datetime(2026, 8, 1, tzinfo=UTC)

    # Document mock outputs from MongoDB
    mock_docs = [
        {
            "_id": "64ee39d09c6292376e191981",
            "filename": "active.txt",
            "effective_from": datetime(2026, 7, 1, tzinfo=UTC),
            "effective_until": datetime(2026, 9, 1, tzinfo=UTC),
        },
        {
            "_id": "64ee39d09c6292376e191982",
            "filename": "expired.txt",
            "effective_from": datetime(2026, 6, 1, tzinfo=UTC),
            "effective_until": datetime(2026, 7, 15, tzinfo=UTC),
        },
        {
            "_id": "64ee39d09c6292376e191983",
            "filename": "future.txt",
            "effective_from": datetime(2026, 8, 15, tzinfo=UTC),
            "effective_until": datetime(2026, 9, 15, tzinfo=UTC),
        },
    ]

    # Mock cursor
    mock_cursor = MagicMock()

    async def mock_async_gen():
        for d in mock_docs:
            yield d

    mock_cursor.__aiter__ = MagicMock(side_effect=mock_async_gen)

    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)

    with patch("app.retrieval.retriever.get_collection", return_value=mock_collection):
        filtered = await apply_temporal_filtering(results, ref_time)

        # Only doc-active fits (2026-08-01 lies between 2026-07-01 and 2026-09-01)
        assert len(filtered) == 1
        assert filtered[0]["document_id"] == "64ee39d09c6292376e191981"
        assert filtered[0]["filename"] == "active.txt"
