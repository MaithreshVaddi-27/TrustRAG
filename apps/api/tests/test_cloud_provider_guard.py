"""The opt-in cloud extra must fail with an actionable configuration error."""

from __future__ import annotations

import builtins
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.llm import model_registry
from app.security.exceptions import ConfigurationError


def test_gemini_without_cloud_extra_is_actionable(monkeypatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "langchain_google_genai":
            raise ImportError("No module named 'langchain_google_genai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        model_registry,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key="test-key"),
    )

    with pytest.raises(ConfigurationError, match="cloud extra") as exc:
        model_registry._create_llm(
            provider="gemini",
            model="gemini-2.5-flash",
            temperature=0.0,
            max_tokens=16,
            timeout=1.0,
        )
    assert "pip install -e" in str(exc.value)


@pytest.mark.asyncio
async def test_configuration_error_is_not_converted_to_abstention(monkeypatch) -> None:
    from app.rag.generation import runtime

    def boom(**_kwargs):
        raise ConfigurationError("Gemini provider requires the optional cloud extra")

    monkeypatch.setattr(runtime, "get_llm", boom)
    chunks = [{"filename": "doc.txt", "page": 1, "text": "Factual segment content."}]

    with pytest.raises(ConfigurationError, match="cloud extra"):
        await runtime.generate_grounded_answer("question", chunks)


def test_cloud_probe_finishes_before_the_client_timeout() -> None:
    from app.llm.providers.cloud_probe import CLOUD_PROBE_TIMEOUT_SECONDS

    # apps/web/src/lib/api.js aborts requests after 10 s.
    assert CLOUD_PROBE_TIMEOUT_SECONDS <= 5.0


def test_verdict_preserves_generation_error_diagnosis() -> None:
    from app.rag.verification.verdict import DiagnosisType, Thresholds, verdict_from_state

    result = verdict_from_state(
        {
            "answer": "ABSTAIN",
            "claims": [],
            "query": "q",
            "diagnosis_type": "GENERATION_ERROR",
            "diagnosis_failures": ["Gemini provider requires the optional cloud extra"],
        },
        Thresholds(
            minimum_evidence_coverage=0.5,
            maximum_contradiction_rate=0.5,
            abstain_below=0.5,
        ),
    )
    assert result.diagnosis_type == DiagnosisType.GENERATION_ERROR
    assert "cloud extra" in result.diagnosis_failures[0]


@patch("app.rag.agent.graph.add_trace_event", AsyncMock())
@patch("app.rag.agent.graph.execute_claim_verification")
@pytest.mark.asyncio
async def test_verification_keeps_generation_config_error(mock_execute) -> None:
    from app.rag.agent.graph.nodes.verification import verification_node

    state = {
        "analysis_id": "64ee39d09c6292376e191983",
        "answer": "I cannot verify this against the retrieved segments.",
        "chunks": [{"text": "some context"}],
        "evidence_ids": [],
        "verdict_status": None,
        "claims": [],
        "attempts": 0,
        "diagnosis_type": "GENERATION_ERROR",
        "node_errors": [
            {
                "node": "generation",
                "message": "Gemini provider requires the optional cloud extra",
            }
        ],
    }

    result = await verification_node(state)

    mock_execute.assert_not_called()
    assert result["diagnosis_type"] == "GENERATION_ERROR"
    assert "cloud extra" in result["diagnosis_failures"][0]
    assert result["verdict_status"] == "FAIL"
