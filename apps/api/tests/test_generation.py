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
