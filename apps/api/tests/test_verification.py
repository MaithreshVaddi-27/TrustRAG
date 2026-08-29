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

