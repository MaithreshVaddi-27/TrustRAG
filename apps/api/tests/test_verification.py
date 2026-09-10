"""
Unit tests for the Claim Verification pipeline.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.verification.verifier import (
    ClaimDecomposition,
    NLIVerdict,
    decompose_answer_to_claims,
    execute_claim_verification,
    extract_claim_triple_heuristic,
    verify_claim_nli,
)


@patch("app.verification.verifier.get_verification_model")
@pytest.mark.asyncio
async def test_claim_decomposition(mock_get_model):
    # Mock structured output model response
    mock_response = ClaimDecomposition(
        claims=[
            "The refund policy allows returns within 30 days.",
            "Processing refunds takes 5 business days.",
        ]
    )
    mock_structured_llm = MagicMock()
    mock_structured_llm.ainvoke = AsyncMock(return_value=mock_response)

    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_llm)
    mock_get_model.return_value = mock_model

    claims = await decompose_answer_to_claims(
        "The refund policy allows returns within 30 days. Processing refunds takes 5 business days."
    )

    assert len(claims) == 2
    assert claims[0] == "The refund policy allows returns within 30 days."
    assert claims[1] == "Processing refunds takes 5 business days."


@patch("app.verification.verifier.get_verification_model")
@pytest.mark.asyncio
async def test_verify_claim_supported(mock_get_model):
    mock_verdict = NLIVerdict(
        verdict="SUPPORTED",
        supporting_segments=[1],
        explanation="The context explicitly supports 30 days return.",
    )
    mock_structured_nli = MagicMock()
    mock_structured_nli.ainvoke = AsyncMock(return_value=mock_verdict)

    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_nli)
    mock_get_model.return_value = mock_model

    chunks = [
        {"filename": "policy.txt", "page": 1, "text": "Customers can return items within 30 days."}
    ]
    res = await verify_claim_nli("The return window is 30 days.", chunks)

    assert res["verdict"] == "SUPPORTED"
    assert res["supporting_segments"] == [1]
    assert "supports 30 days" in res["explanation"]


@patch("app.verification.verifier.get_verification_model")
@pytest.mark.asyncio
async def test_verify_claim_contradicted(mock_get_model):
    mock_verdict = NLIVerdict(
        verdict="CONTRADICTED",
        supporting_segments=[1],
        explanation="The context states that returns are not allowed after 14 days.",
    )
    mock_structured_nli = MagicMock()
    mock_structured_nli.ainvoke = AsyncMock(return_value=mock_verdict)

    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_nli)
    mock_get_model.return_value = mock_model

    chunks = [{"filename": "policy.txt", "page": 1, "text": "All sales are final after 14 days."}]
    res = await verify_claim_nli("The return window is 30 days.", chunks)

    assert res["verdict"] == "CONTRADICTED"
    assert res["supporting_segments"] == [1]


@patch("app.verification.verifier.batch_verify_claims_nli")
@patch("app.verification.verifier.decompose_answer_to_claims")
@patch("app.db.mongodb.connect_db")
@patch("app.db.mongodb.create_indexes")
@pytest.mark.asyncio
async def test_execute_claim_verification(
    mock_create_indexes, mock_connect, mock_decompose, mock_batch_verify
):
    mock_decompose.return_value = ["Claim 1", "Claim 2"]
    mock_batch_verify.return_value = {
        1: {"verdict": "SUPPORTED", "supporting_segments": [1], "explanation": "Ok"},
        2: {"verdict": "NEUTRAL", "supporting_segments": [], "explanation": "Missing"},
    }

    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId("64ee39d09c6292376e191984"))
    )

    with patch("app.verification.verifier.get_collection", return_value=mock_collection):
        chunks = [{"text": "segment 1"}]
        evidence_ids = [ObjectId("64ee39d09c6292376e191985")]

        claims = await execute_claim_verification(
            analysis_id_str="64ee39d09c6292376e191983",
            answer="Claim 1. Claim 2.",
            chunks=chunks,
            evidence_ids=evidence_ids,
        )

        assert len(claims) == 2
        assert claims[0]["state"] == "SUPPORTED"
        assert claims[0]["evidence_ids"] == [evidence_ids[0]]
        assert claims[1]["state"] == "NEUTRAL"
        assert claims[1]["evidence_ids"] == []


@patch("app.verification.verifier.batch_verify_claims_nli")
@patch("app.verification.verifier.decompose_answer_to_claims")
@pytest.mark.asyncio
async def test_execute_claim_verification_maps_sorted_segments_to_original_evidence(
    mock_decompose, mock_batch_verify
):
    """Segment 1 belongs to the highest-scored context chunk, not chunks[0]."""
    mock_decompose.return_value = ["The policy permits refunds."]
    mock_batch_verify.return_value = {
        1: {"verdict": "SUPPORTED", "supporting_segments": [1], "explanation": "Supported"}
    }

    mock_collection = MagicMock()
    mock_collection.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=[ObjectId("64ee39d09c6292376e191986")])
    )

    low_rrf = {
        "text": "Revenue reporting follows the local fiscal calendar.",
        "filename": "finance.txt",
        "page": 1,
        "rrf_score": 0.1,
    }
    duplicate_low_rrf = dict(low_rrf)
    high_rrf = {
        "text": "The approved policy permits refunds within thirty days.",
        "filename": "policy.txt",
        "page": 2,
        "rrf_score": 0.9,
    }
    evidence_ids = [
        ObjectId("64ee39d09c6292376e191987"),
        ObjectId("64ee39d09c6292376e191988"),
        ObjectId("64ee39d09c6292376e191989"),
    ]

    with patch("app.verification.verifier.get_collection", return_value=mock_collection):
        claims = await execute_claim_verification(
            analysis_id_str="64ee39d09c6292376e191983",
            answer="The policy permits refunds.",
            chunks=[low_rrf, duplicate_low_rrf, high_rrf],
            evidence_ids=evidence_ids,
        )

    assert claims[0]["evidence_ids"] == [evidence_ids[2]]


@patch("app.verification.verifier.verify_claim_nli")
@patch("app.verification.verifier.batch_verify_claims_nli")
@patch("app.verification.verifier.decompose_answer_to_claims")
@pytest.mark.asyncio
async def test_batch_verification_retried_once_before_individual_fallback(
    mock_decompose, mock_batch_verify, mock_individual
):
    """A transient batch failure costs 1 retry call, not N individual calls."""
    from bson import ObjectId

    mock_decompose.return_value = ["The policy permits refunds within thirty days."]
    mock_batch_verify.side_effect = [
        Exception("truncated JSON"),
        {1: {"verdict": "SUPPORTED", "supporting_segments": [1], "explanation": "Ok"}},
    ]

    mock_collection = MagicMock()
    mock_collection.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=[ObjectId("64ee39d09c6292376e191986")])
    )
    with patch("app.verification.verifier.get_collection", return_value=mock_collection):
        claims = await execute_claim_verification(
            analysis_id_str="64ee39d09c6292376e191983",
            answer="The policy permits refunds within thirty days.",
            chunks=[{"text": "Refunds are permitted within thirty days."}],
            evidence_ids=[ObjectId("64ee39d09c6292376e191987")],
        )

    assert mock_batch_verify.call_count == 2
    mock_individual.assert_not_called()
    assert claims[0]["state"] == "SUPPORTED"


@patch("app.verification.verifier.verify_claim_nli")
@patch("app.verification.verifier.batch_verify_claims_nli")
@patch("app.verification.verifier.decompose_answer_to_claims")
@pytest.mark.asyncio
async def test_individual_nli_fallback_is_capped(
    mock_decompose, mock_batch_verify, mock_individual
):
    """Persistent batch failure → bounded individual calls, rest NEUTRAL (never inflated)."""
    from bson import ObjectId

    from app.core.config import get_model_config

    cap = int(get_model_config().max_individual_nli_fallback)
    assert cap > 0
    sentences = [
        f"The policy term number {i} permits refunds within thirty days." for i in range(8)
    ]
    mock_decompose.return_value = sentences
    mock_batch_verify.side_effect = Exception("structured output unsupported")
    mock_individual.return_value = {
        "verdict": "SUPPORTED",
        "supporting_segments": [1],
        "explanation": "Ok",
    }

    mock_collection = MagicMock()
    mock_collection.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=[ObjectId("64ee39d09c6292376e191986")] * 8)
    )
    with patch("app.verification.verifier.get_collection", return_value=mock_collection):
        claims = await execute_claim_verification(
            analysis_id_str="64ee39d09c6292376e191983",
            answer=" ".join(sentences),
            chunks=[{"text": "Refunds are permitted within thirty days."}],
            evidence_ids=[ObjectId("64ee39d09c6292376e191987")],
        )

    assert len(claims) == 8
    assert mock_individual.call_count == cap
    assert [c["state"] for c in claims[:cap]] == ["SUPPORTED"] * cap
    rest = claims[cap:]
    assert rest and all(c["state"] == "NEUTRAL" for c in rest)
    assert all("budget" in c["explanation"] for c in rest)


def test_extract_claim_triple_heuristics():
    # Standard predicate match
    subj, pred, obj = extract_claim_triple_heuristic(
        "The refund policy allows returns within 30 days."
    )
    assert subj == "The refund policy"
    assert pred == "allows"
    assert obj == "returns within 30 days"

    # Positional 4-word split
    s2, p2, o2 = extract_claim_triple_heuristic("Antigravity engine emits photon")
    assert s2 == "Antigravity engine"
    assert p2 == "emits"
    assert o2 == "photon"

    # Edge cases
    assert extract_claim_triple_heuristic("") == (None, None, None)
    assert extract_claim_triple_heuristic("   ") == (None, None, None)
    assert extract_claim_triple_heuristic("Warning") == ("Warning", None, None)
