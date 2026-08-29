"""
Unit tests for the Agentic Adaptive Recovery LangGraph workflow.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.agent.graph import (
    generation_node,
    recovery_node,
    retrieval_node,
    should_recover,
    verification_node,
)


def test_should_recover_router():
    # Pass status ends graph
    state_pass = {"verdict_status": "PASS", "attempts": 0}
    assert should_recover(state_pass) == "end"

    # Fail status under attempts ceiling triggers recover
    state_fail = {"verdict_status": "FAIL", "attempts": 1}
    assert should_recover(state_fail) == "recover"

    # Exceeding attempts ceiling ends graph
    state_max = {"verdict_status": "FAIL", "attempts": 2}
    assert should_recover(state_max) == "end"


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.audit_evidence_integrity")
@patch("app.agent.graph.rerank_candidate_chunks")
@patch("app.agent.graph.retrieve_hybrid_chunks")
@patch("app.agent.graph.get_collection")
@pytest.mark.asyncio
async def test_retrieval_node(mock_collection, mock_retrieve, mock_rerank, mock_audit):
    # Mock retriever segments output
    mock_chunks = [
        {"text": "segment text", "document_id": "64ee39d09c6292376e191981", "chunk_index": 0}
    ]
    mock_retrieve.return_value = mock_chunks
    mock_rerank.return_value = mock_chunks

    # Mock audit verification
    mock_chunks_audited = [
        {
            "text": "segment text",
            "document_id": "64ee39d09c6292376e191981",
            "chunk_index": 0,
            "integrity_status": "VERIFIED",
        }
    ]
    mock_audit.return_value = mock_chunks_audited

    mock_db = MagicMock()
    mock_db.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId("64ee39d09c6292376e191985"))
    )
    mock_collection.return_value = mock_db

    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "kb_id": "64ee39d09c6292376e191982",
        "query": "original query",
        "current_query": "original query",
        "answer": None,
        "chunks": [],
        "evidence_ids": [],
        "attempts": 0,
        "verdict_status": "FAIL",
        "recovery_strategy": None,
    }

    res = await retrieval_node(state)
    assert len(res["chunks"]) == 1
    assert res["chunks"][0]["integrity_status"] == "VERIFIED"
    assert len(res["evidence_ids"]) == 1
    mock_retrieve.assert_called_once_with(
        query="original query", kb_id="64ee39d09c6292376e191982", top_k_override=None
    )


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.generate_grounded_answer")
@pytest.mark.asyncio
async def test_generation_node(mock_generate):
    mock_generate.return_value = "Grounded answer"
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "current_query": "query",
        "chunks": [],
        "answer": None,
    }
    res = await generation_node(state)
    assert res["answer"] == "Grounded answer"


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.execute_claim_verification")
@pytest.mark.asyncio
async def test_verification_node_pass(mock_execute):
    mock_claims = [
        {"text": "Claim 1", "state": "SUPPORTED"},
        {"text": "Claim 2", "state": "SUPPORTED"},
    ]
    mock_execute.return_value = mock_claims

    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "answer": "Grounded answer text.",
        "chunks": [],
        "evidence_ids": [],
        "verdict_status": "FAIL",
        "claims": [],
    }

    res = await verification_node(state)
    assert res["verdict_status"] == "PASS"
    assert len(res["claims"]) == 2


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.execute_claim_verification")
@pytest.mark.asyncio
async def test_verification_node_fail(mock_execute):
    mock_claims = [
        {"text": "Claim 1", "state": "SUPPORTED"},
        {"text": "Claim 2", "state": "NEUTRAL"},  # 50% coverage, fails 80% threshold
    ]
    mock_execute.return_value = mock_claims

    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "answer": "Grounded answer text.",
        "chunks": [],
        "evidence_ids": [],
        "verdict_status": "FAIL",
        "claims": [],
    }

    res = await verification_node(state)
    assert res["verdict_status"] == "FAIL"


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.get_collection")
@patch("app.agent.graph.get_verification_model")
@pytest.mark.asyncio
async def test_recovery_node_rewrite(mock_model, mock_collection):
    # Mock LLM query rewrite
    mock_response = MagicMock()
    mock_response.content = "rewritten search query"
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_model.return_value = mock_llm

    mock_db = MagicMock()
    mock_db.insert_one = AsyncMock()
    mock_collection.return_value = mock_db

    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "query": "original",
        "current_query": "original",
        "answer": "answer",
        "claims": [{"text": "Claim", "state": "NEUTRAL"}],
        "attempts": 0,
        "recovery_strategy": None,
    }

    res = await recovery_node(state)
    assert res["attempts"] == 1
    assert res["current_query"] == "rewritten search query"
    assert res["recovery_strategy"] == "query_rewrite"
    mock_db.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_verification_node_abstain_triggers_recovery():
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "answer": "ABSTAIN",
        "chunks": [{"text": "some context"}],
        "evidence_ids": [],
        "verdict_status": "FAIL",
        "claims": [],
        "attempts": 0,
    }

    res = await verification_node(state)
    assert res["verdict_status"] == "FAIL"
    assert res["diagnosis_type"] == "RETRIEVAL_FAILURE"
    assert "insufficient information" in res["diagnosis_failures"][0].lower()


@pytest.mark.asyncio
async def test_verification_node_abstain_max_attempts_passes():
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "answer": "ABSTAIN",
        "chunks": [],
        "evidence_ids": [],
        "verdict_status": "FAIL",
        "claims": [],
        "attempts": 2,  # Reached max_recovery_attempts (2)
    }

    res = await verification_node(state)
    assert res["verdict_status"] == "PASS"
    assert res["diagnosis_type"] == "RETRIEVAL_FAILURE"
