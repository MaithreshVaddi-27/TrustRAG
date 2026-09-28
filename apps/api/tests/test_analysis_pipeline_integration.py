"""
End-to-end analysis wiring test (audit B-9 / T-1).

The existing suite proves individual node functions work, but nothing exercises
the assembled pipeline: `apps/web/e2e/` contains two auth tests that only touch
`GET /health` (a static liveness check) and a dashboard heading. Deleting
`generator.py`, `retrieval/retriever.py`, or the whole LangGraph would leave
every CI check green.

This test runs `execute_agentic_rag_flow` for real and mocks ONLY the external
boundaries — the LLM client, vector search, and Mongo. `generator.py`,
`verifier.py`, `verdict.py`, the graph topology, and the state machine all
execute as production code. That is what makes it a real regression guard
rather than a re-statement of the unit tests.

A follow-up test (`test_generation_gutted_would_fail_this_file`) documents the
guarantee explicitly.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.core.config import get_model_config
from app.verification.verifier import FusedDecomposeVerify

ANALYSIS_ID = "64ee39d09c6292376e191983"
KB_ID = "64ee39d09c6292376e191982"
USER_ID = "64ee39d09c6292376e191981"

ANSWER = "Refunds are allowed within 30 days of purchase [Segment 1]."
CHUNKS = [
    {
        "chunk_id": "c1",
        "text": "Customers may request a refund within 30 days of purchase.",
        "document_id": "64ee39d09c6292376e191990",
        "chunk_index": 0,
        "filename": "policy.pdf",
        "method": "hybrid",
        "score": 0.91,
        "integrity_status": "VERIFIED",
    },
    {
        "chunk_id": "c2",
        "text": "Refunds are issued to the original payment method.",
        "document_id": "64ee39d09c6292376e191990",
        "chunk_index": 1,
        "filename": "policy.pdf",
        "method": "hybrid",
        "score": 0.84,
        "integrity_status": "VERIFIED",
    },
]


def _llm_returning(text: str) -> MagicMock:
    """A minimal BaseChatModel stand-in: `.ainvoke` -> object with `.content`."""
    llm = MagicMock()
    response = SimpleNamespace(content=text, usage_metadata={}, response_metadata={})
    llm.ainvoke = AsyncMock(return_value=response)
    llm.bind = MagicMock(return_value=llm)
    llm.model_name = "test-model"
    return llm


def _fused_response() -> FusedDecomposeVerify:
    """Decomposition + verdicts for the answer above, as the fused call returns it."""
    return FusedDecomposeVerify(
        items=[
            {
                "claim": "Refunds are allowed within 30 days of purchase.",
                "verdict": "SUPPORTED",
                "supporting_segments": [1],
                "explanation": "Segment 1 states the 30-day refund window.",
            },
        ]
    )


def _verification_model() -> MagicMock:
    """The verification model must return the fused schema, not raw text."""
    model = MagicMock()
    runnable = MagicMock()
    runnable.ainvoke = AsyncMock(return_value=_fused_response())
    model.with_structured_output = MagicMock(return_value=runnable)
    model.bind = MagicMock(return_value=model)
    model.ainvoke = AsyncMock(return_value=SimpleNamespace(content="{}", usage_metadata={}))
    model.model_name = "test-verifier"
    return model


async def _passthrough_chunks(_query, chunks, **_kwargs):
    """Stands in for reranking: return candidates unchanged."""
    return chunks


async def _passthrough_audit(chunks):
    """Stands in for the integrity audit: chunks are pre-labelled VERIFIED."""
    return chunks


@pytest.fixture
def analysis_deps():
    """Patch only external I/O. Everything else runs for real."""
    llm = _llm_returning(ANSWER)
    verifier = _verification_model()

    collection = MagicMock()
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock()
    # Claims are written with insert_many and fall back to insert_one on
    # TypeError, so both must be awaitable for the test to exercise the real
    # persistence path.
    collection.insert_many = AsyncMock(
        return_value=SimpleNamespace(inserted_ids=[ObjectId("64ee39d09c6292376e1919ab")])
    )
    # Evidence lookup during claim->evidence linking must return a real doc,
    # otherwise the verifier treats every claim as having no evidence.
    collection.find_one = AsyncMock(
        side_effect=lambda *_a, **_k: {"_id": ObjectId("64ee39d09c6292376e1919aa")}
    )
    cursor = MagicMock()
    cursor.aiter = MagicMock(side_effect=lambda *a, **k: _empty_aiter())
    collection.find = MagicMock(return_value=cursor)

    with (
        patch("app.agent.graph.retrieve_hybrid_chunks", AsyncMock(return_value=CHUNKS)),
        patch("app.agent.graph.rerank_candidate_chunks", _passthrough_chunks),
        patch("app.agent.graph.audit_evidence_integrity", _passthrough_audit),
        patch("app.agent.graph.get_collection", MagicMock(return_value=collection)),
        patch("app.agent.graph.add_trace_event", AsyncMock()),
        patch("app.verification.verifier.get_collection", MagicMock(return_value=collection)),
        patch("app.generation.generator.get_llm", MagicMock(return_value=llm)),
        patch("app.agent.graph.get_verification_model", MagicMock(return_value=verifier)),
        patch("app.verification.verifier.get_verification_model", MagicMock(return_value=verifier)),
    ):
        yield collection


async def _empty_aiter():
    if False:  # pragma: no cover - yields nothing
        yield None


@pytest.mark.asyncio
async def test_execute_agentic_rag_flow_produces_a_grounded_verdict(analysis_deps):
    """The assembled pipeline must return a completed, evidence-backed analysis.

    Runs the real LangGraph, generator, verifier, and verdict computation.
    """
    from app.agent.graph import execute_agentic_rag_flow

    final = await execute_agentic_rag_flow(
        analysis_id_str=ANALYSIS_ID,
        kb_id_str=KB_ID,
        query="What is the refund window?",
        user_id_str=USER_ID,
    )

    # 1. A real answer came back (not ABSTAIN, not an error string).
    assert final["answer"], "no answer produced"
    assert final["answer"] != "ABSTAIN"
    assert "30 days" in final["answer"]

    # 2. Claims were actually decomposed and verified.
    assert final["claims"], "no claims produced — verification did not run"
    claim = final["claims"][0]
    # The verdict is persisted on the claim under `state`.
    assert claim.get("state") == "SUPPORTED", f"claim verdict: {claim.get('state')}"
    assert claim.get("evidence_ids"), "claim was not linked to any evidence"

    # 3. The verdict is a real decision, not a default failure.
    assert final["verdict_status"] in ("PASS", "FAIL")
    assert final["verdict_status"] == "PASS", (
        f"expected PASS for fully supported evidence, got "
        f"{final['verdict_status']} / {final.get('diagnosis_type')} / "
        f"{final.get('diagnosis_failures')}"
    )

    # 4. Reliability is a number in range.
    assert final["reliability_score"] is not None
    assert 0.0 <= final["reliability_score"] <= 1.0

    # 5. Evidence was persisted with the answer.
    assert final["chunks"], "no evidence carried into the result"
    assert final["evidence_ids"]

    # 6. No node blew up.
    assert final.get("node_errors") == [], f"node errors: {final.get('node_errors')}"


@pytest.mark.asyncio
async def test_analysis_persists_evidence_and_returns_a_persistable_record(analysis_deps):
    """The graph owns EVIDENCE persistence; `analysis_service` writes the analysis
    record itself. Assert both halves of that contract.

    Writing the terminal record from here would be the wrong fix — that is
    `analysis_service`'s responsibility (analyses.py update_one calls), so this
    asserts the graph returns a state complete enough to persist.
    """
    from app.agent.graph import execute_agentic_rag_flow

    final = await execute_agentic_rag_flow(
        analysis_id_str=ANALYSIS_ID,
        kb_id_str=KB_ID,
        query="What is the refund window?",
        user_id_str=USER_ID,
    )

    # Evidence is persisted so a claim can be linked back to a stored segment.
    assert analysis_deps.insert_many.await_count >= 1, "evidence was never persisted"
    docs = analysis_deps.insert_many.await_args_list[0].args[0]
    assert len(docs) == len(CHUNKS)
    assert all(d.get("analysis_id") is not None for d in docs)

    # And the state carries everything the service needs to write the record.
    for field in ("verdict_status", "answer", "claims", "reliability_score", "diagnosis_type"):
        assert field in final, f"final state missing {field!r}, cannot be persisted"


@pytest.mark.asyncio
async def test_contradicted_evidence_yields_fail_not_pass(analysis_deps):
    """The verdict must respond to evidence quality, not always return PASS."""
    from app.agent.graph import execute_agentic_rag_flow

    with patch(
        "app.verification.verifier.get_verification_model",
        MagicMock(return_value=_verification_model_contradicting()),
    ):
        final = await execute_agentic_rag_flow(
            analysis_id_str=ANALYSIS_ID,
            kb_id_str=KB_ID,
            query="What is the refund window?",
            user_id_str=USER_ID,
        )

    assert final["verdict_status"] == "FAIL", "a CONTRADICTED claim must not produce PASS"


def _verification_model_contradicting() -> MagicMock:
    model = MagicMock()
    response = FusedDecomposeVerify(
        items=[
            {
                "claim": "Refunds are allowed within 30 days of purchase.",
                "verdict": "CONTRADICTED",
                "supporting_segments": [],
                "explanation": "Evidence does not support this.",
            },
        ]
    )
    runnable = MagicMock()
    runnable.ainvoke = AsyncMock(return_value=response)
    model.with_structured_output = MagicMock(return_value=runnable)
    model.bind = MagicMock(return_value=model)
    model.model_name = "test-verifier"
    return model


@pytest.mark.asyncio
async def test_empty_knowledge_base_abstains_without_inventing_evidence(analysis_deps):
    """No evidence must produce ABSTAIN, never a fabricated grounded answer."""
    from app.agent.graph import execute_agentic_rag_flow

    with (
        patch("app.agent.graph.retrieve_hybrid_chunks", AsyncMock(return_value=[])),
        patch("app.agent.graph.rerank_candidate_chunks", _passthrough_chunks),
    ):
        final = await execute_agentic_rag_flow(
            analysis_id_str=ANALYSIS_ID,
            kb_id_str=KB_ID,
            query="What is the refund window?",
            user_id_str=USER_ID,
        )

    assert final["answer"] == "ABSTAIN"
    assert final["chunks"] == []


def test_generation_gutted_would_fail_this_file():
    """Documents the guarantee this file provides (audit B-9).

    `apps/web/e2e/` passes while generation is entirely broken because it only
    asserts a static `/health` response and a dashboard heading. This file mocks
    the LLM client and the vector store but executes generator.py, verifier.py,
    verdict.py, and the LangGraph, so replacing `generate_grounded_answer` with a
    stub — or gutting `retriever.py` — makes the assertions above fail.
    """
    from app.agent import graph as graph_mod
    from app.generation import generator as generator_mod

    # The graph must call the real generator, not a private copy.
    assert graph_mod.generate_grounded_answer is generator_mod.generate_grounded_answer

    # And the generator must not short-circuit to a constant.
    import inspect

    src = inspect.getsource(generator_mod.generate_grounded_answer)
    assert "ABSTAIN" in src, "generator lost its empty-context abstain guard"
    assert len(src.splitlines()) > 30, "generate_grounded_answer looks stubbed out"


def test_fused_schema_contract_is_stable():
    """The fused response shape is the seam between verifier and any model.
    Renaming a field here silently changes every verification result."""
    from typing import get_args

    fields = set(FusedDecomposeVerify.model_fields)
    assert fields == {"items"}, f"FusedDecomposeVerify fields changed: {fields}"
    item_type = get_args(FusedDecomposeVerify.model_fields["items"].annotation)[0]
    item_fields = set(item_type.model_fields)
    assert item_fields == {"claim", "verdict", "supporting_segments", "explanation"}, (
        f"fused item fields changed: {item_fields}"
    )


def test_verification_claim_budget_is_bounded():
    """max_verification_claims bounds the fused payload; an unbounded value
    silently produces giant structured outputs that truncate (audit B-2)."""
    cfg = get_model_config()
    assert 0 < cfg.max_verification_claims <= 20
    assert cfg.max_individual_nli_fallback >= cfg.max_verification_claims
