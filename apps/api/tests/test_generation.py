"""
Unit tests for the grounded answer generation module.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.generation.generator import format_context, generate_grounded_answer


def test_context_formatting():
    chunks = [
        {"filename": "doc1.txt", "page": 2, "text": "This is sample context segment 1"},
        {"filename": "doc2.txt", "page": 4, "text": "This is sample context segment 2"},
    ]
    formatted = format_context(chunks)

    assert "[Source: doc1.txt, Page 2]" in formatted
    assert "This is sample context segment 1" in formatted
    assert "[Source: doc2.txt, Page 4]" in formatted


def test_context_format_is_byte_stable_regardless_of_input_order():
    """OPT-H11: identical chunks in any provider order must produce an
    identical byte string so repeated queries hit Ollama's KV cache."""
    chunk_a = {"filename": "doc_a.txt", "page": 1, "text": "Alpha facts about the policy."}
    chunk_b = {"filename": "doc_b.txt", "page": 7, "text": "Beta facts about the policy."}

    first = format_context([chunk_a, chunk_b])
    # Same documents, retrieved in the opposite order by the hybrid provider.
    second = format_context([chunk_b, chunk_a])

    assert first == second
    assert "Alpha facts" in first and "Beta facts" in first


def test_context_format_orders_by_score_then_text():
    """Higher-scoring chunks are always emitted first so the most relevant
    evidence forms a stable prompt prefix."""
    low = {"filename": "doc.txt", "page": 1, "text": "low relevance chunk text", "rrf_score": 0.2}
    high = {"filename": "doc.txt", "page": 2, "text": "high relevance chunk text", "rrf_score": 0.9}

    formatted = format_context([low, high])
    assert formatted.index("high relevance") < formatted.index("low relevance")


@pytest.mark.asyncio
async def test_generation_abstention_on_empty_context():
    # Enforces immediate abstention without calling LLM when no segments are available
    answer = await generate_grounded_answer("test query", [])
    assert answer == "ABSTAIN"


@patch("app.generation.generator.get_llm")
@pytest.mark.asyncio
async def test_generation_successful_call(mock_get_llm):
    # Mock LangChain ChatGoogleGenerativeAI call
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Grounded answer text."
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_get_llm.return_value = mock_llm

    chunks = [{"filename": "doc.txt", "page": 1, "text": "Factual segment content."}]

    answer = await generate_grounded_answer("Is there matching info?", chunks)

    assert answer == "Grounded answer text."
    mock_llm.ainvoke.assert_called_once()
