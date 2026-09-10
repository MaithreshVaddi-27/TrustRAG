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
from app.core.exceptions import RetrievalOutageError


def test_should_recover_router():
    # Ceilings follow live config (max_recovery_attempts), not a hardcoded
    # value, so the router test stays valid when the budget is retuned.
    from app.core.config import get_model_config

    max_recovery = get_model_config().max_recovery_attempts

    # Pass status ends graph
    state_pass = {"verdict_status": "PASS", "attempts": 0}
    assert should_recover(state_pass) == "end"

    # Fail status under attempts ceiling triggers recover
    state_fail = {"verdict_status": "FAIL", "attempts": max_recovery - 1}
    assert should_recover(state_fail) == "recover"

    # Exceeding attempts ceiling ends graph
    state_max = {"verdict_status": "FAIL", "attempts": max_recovery}
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
@patch("app.agent.graph.generate_grounded_answer")
@pytest.mark.asyncio
async def test_generation_node_reuses_cached_answer_without_llm_call(mock_generate):
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "current_query": "query",
        "chunks": [{"text": "fresh evidence"}],
        "answer": "Previously generated answer",
        "cache_hit": True,
    }

    res = await generation_node(state)

    assert res["answer"] == "Previously generated answer"
    mock_generate.assert_not_called()


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.generate_grounded_answer")
@pytest.mark.asyncio
async def test_generation_node_skips_futile_regenerate_after_abstain(mock_generate):
    """Regenerate retry on identical chunks after ABSTAIN must not burn an LLM call."""
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "current_query": "query",
        "chunks": [{"text": "same evidence"}],
        "answer": "ABSTAIN",
        "recovery_strategy": "regenerate",
    }

    res = await generation_node(state)

    assert res["answer"] == "ABSTAIN"
    mock_generate.assert_not_called()


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.generate_grounded_answer")
@pytest.mark.asyncio
async def test_generation_node_regenerates_after_failed_answer(mock_generate):
    """Regenerate retry after a real (non-ABSTAIN) failed answer still retries."""
    mock_generate.return_value = "Second attempt answer"
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "current_query": "query",
        "chunks": [{"text": "same evidence"}],
        "answer": "First attempt answer",
        "recovery_strategy": "regenerate",
    }

    res = await generation_node(state)

    assert res["answer"] == "Second attempt answer"
    mock_generate.assert_called_once()


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
        "cache_hit": True,
    }

    res = await recovery_node(state)
    assert res["attempts"] == 1
    assert res["current_query"] == "rewritten search query"
    assert res["recovery_strategy"] == "query_rewrite"
    assert res["cache_hit"] is False
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


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.audit_evidence_integrity")
@patch("app.agent.graph.rerank_candidate_chunks")
@patch("app.agent.graph.retrieve_hybrid_chunks")
@patch("app.agent.graph.get_collection")
@pytest.mark.asyncio
async def test_retrieval_node_outage_is_distinct_from_no_evidence(
    mock_collection, mock_retrieve, mock_rerank, mock_audit
):
    from app.core.config import get_model_config

    mock_retrieve.side_effect = RetrievalOutageError("Vector store unavailable: down")
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
    assert res["diagnosis_type"] == "RETRIEVAL_OUTAGE"
    assert res["diagnosis_type"] != "RETRIEVAL_FAILURE"
    assert res["verdict_status"] == "FAIL"
    assert res["chunks"] == []
    assert "temporarily unavailable" in res["answer"]
    assert res["attempts"] == get_model_config().max_recovery_attempts
    mock_rerank.assert_not_called()
    mock_audit.assert_not_called()


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.audit_evidence_integrity")
@patch("app.agent.graph.rerank_candidate_chunks")
@patch("app.agent.graph.retrieve_hybrid_chunks")
@patch("app.agent.graph.get_collection")
@pytest.mark.asyncio
async def test_retrieval_node_self_heal_batches_doc_lookup(
    mock_collection, mock_retrieve, mock_rerank, mock_audit
):
    """Self-heal must fetch filenames with ONE $in query, not N+1 find_one calls."""
    from bson import ObjectId

    doc_id_1 = ObjectId("64ee39d09c6292376e191981")
    doc_id_2 = ObjectId("64ee39d09c6292376e191982")

    # First retrieval round finds nothing → self-heal; second round finds candidates.
    mock_retrieve.side_effect = [
        [],
        [{"text": "reindexed segment", "document_id": str(doc_id_1)}],
    ]
    mock_rerank.side_effect = lambda _q, c, **kw: c
    mock_audit.side_effect = lambda c: [{**seg, "integrity_status": "VERIFIED"} for seg in c]

    stored_chunks = [
        {
            "document_id": doc_id_1,
            "chunk_index": 0,
            "text": "chunk one",
            "zone": "body",
            "user_id": "u1",
            "page": 1,
            "character_offset": 0,
        },
        {
            "document_id": doc_id_2,
            "chunk_index": 1,
            "text": "chunk two",
            "zone": "body",
            "user_id": "u1",
            "page": 1,
            "character_offset": 0,
        },
    ]

    class _FakeCursor:
        def __init__(self, docs):
            self._docs = docs

        def __aiter__(self):
            async def _gen():
                for d in self._docs:
                    yield d

            return _gen()

    chunks_coll = MagicMock()
    chunks_coll.count_documents = AsyncMock(return_value=2)
    chunks_coll.find.return_value.sort.return_value.to_list = AsyncMock(return_value=stored_chunks)
    docs_coll = MagicMock()
    docs_coll.find = MagicMock(
        return_value=_FakeCursor(
            [
                {"_id": doc_id_1, "filename": "one.txt"},
                {"_id": doc_id_2, "filename": "two.txt"},
            ]
        )
    )
    evidence_coll = MagicMock()
    evidence_coll.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=[ObjectId("64ee39d09c6292376e191985")])
    )

    def fake_get_collection(name):
        return {
            "document_chunks": chunks_coll,
            "documents": docs_coll,
            "evidence": evidence_coll,
        }[str(name).split(".")[-1]]

    mock_collection.side_effect = fake_get_collection

    mock_qdrant = MagicMock()
    mock_qdrant.collection_exists = AsyncMock(return_value=True)
    mock_qdrant.get_collection = AsyncMock(return_value=MagicMock(points_count=0))
    mock_qdrant.upsert = AsyncMock()

    mock_embed = MagicMock()
    mock_embed.embed_documents = MagicMock(return_value=[[0.1] * 8, [0.1] * 8])

    with (
        patch("app.db.qdrant.get_qdrant_client", AsyncMock(return_value=mock_qdrant)),
        patch("app.db.qdrant.init_kb_collection", AsyncMock()),
        patch("app.core.model_registry.get_embedding_model", return_value=mock_embed),
        patch(
            "app.ingestion.sparse_vector.generate_sparse_vector",
            return_value={"indices": [1], "values": [0.5]},
        ),
        patch("app.ingestion.pipeline.hashlib_qdrant_id", return_value="point-id"),
    ):
        state = {
            "analysis_id": "64ee39d09c6292376e191983",
            "kb_id": "64ee39d09c6292376e191984",
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

    # Filenames resolved via a single batched query covering both documents.
    docs_coll.find.assert_called_once()
    in_clause = docs_coll.find.call_args[0][0]["_id"]["$in"]
    assert {str(i) for i in in_clause} == {str(doc_id_1), str(doc_id_2)}
    assert getattr(docs_coll, "find_one", MagicMock()).call_count == 0
    assert len(res["chunks"]) == 1
    assert res["chunks"][0]["integrity_status"] == "VERIFIED"


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.generate_grounded_answer")
@pytest.mark.asyncio
async def test_generation_node_preserves_outage_answer(mock_generate):
    outage_msg = (
        "The knowledge base search service is temporarily unavailable, "
        "so I could not search for evidence."
    )
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "current_query": "query",
        "chunks": [],
        "answer": outage_msg,
        "diagnosis_type": "RETRIEVAL_OUTAGE",
        "diagnosis_failures": ["Vector store unavailable: down"],
        "cache_hit": False,
    }

    res = await generation_node(state)
    assert res["answer"] == outage_msg
    mock_generate.assert_not_called()


@patch("app.agent.graph.add_trace_event", AsyncMock())
@patch("app.agent.graph.execute_claim_verification")
@pytest.mark.asyncio
async def test_verification_node_outage_fast_path_skips_verification(mock_execute):
    from app.core.config import get_model_config

    outage_msg = (
        "The knowledge base search service is temporarily unavailable, "
        "so I could not search for evidence."
    )
    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "answer": outage_msg,
        "chunks": [],
        "evidence_ids": [],
        "verdict_status": "FAIL",
        "diagnosis_type": "RETRIEVAL_OUTAGE",
        "claims": [],
        "attempts": 0,
    }

    res = await verification_node(state)
    mock_execute.assert_not_called()
    assert res["diagnosis_type"] == "RETRIEVAL_OUTAGE"
    assert res["answer"] == outage_msg
    assert res["verdict_status"] == "FAIL"
    assert res["attempts"] == get_model_config().max_recovery_attempts
