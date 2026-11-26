"""
Tests for the cloud LLM probe and its call site (audit change B2.1).

The Gemini provider path was completely broken: ``create_analysis`` called
``probe_cloud_llm`` with two positional arguments against a keyword-only
signature, so every Gemini analysis died with

    TypeError: probe_cloud_llm() takes 0 positional arguments but 2 were given

*before* the analysis document was written — a 500 with no run, no trace and
nothing to retry. On top of that, the probe itself spoke an OpenAI-shaped
``/v1/chat/completions`` contract that Gemini does not accept; it now speaks
Gemini's native ``generateContent`` contract, the same one
``langchain-google-genai`` uses at runtime.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from bson import ObjectId

from app.security.exceptions import LLMUnavailableError

ANALYSIS_ID = "64ee39d09c6292376e191983"


# ─── The probe contract ──────────────────────────────────────────────────────


def test_probe_contract_is_unchanged():
    """The cloud probe keeps its keyword-only signature (call sites rely on it)."""
    from app.llm.providers.health import probe_cloud_llm

    params = inspect.signature(probe_cloud_llm).parameters
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())
    assert set(params) == {"norm", "model", "base_url", "timeout", "hint"}


def test_cloud_probe_is_re_exported_from_the_health_module():
    """Existing importers (``app.llm.local_llm``) must keep working."""
    from app.llm.local_llm import probe_cloud_llm as via_local_llm
    from app.llm.providers import probe_cloud_llm as via_providers
    from app.llm.providers.health import probe_cloud_llm as via_health

    assert via_local_llm is via_health
    assert via_providers is via_health


# ─── The Gemini request contract ─────────────────────────────────────────────


class _RecordingClient:
    """Minimal stand-in for ``httpx.AsyncClient`` that records the request."""

    def __init__(self, response: httpx.Response, captured: dict):
        self._response = response
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        self._captured["url"] = url
        self._captured["headers"] = headers or {}
        self._captured["json"] = json or {}
        return self._response


def test_cloud_probe_uses_the_gemini_generate_content_contract():
    """The Gemini probe must speak Gemini's own REST contract."""
    from app.llm.providers import cloud_probe

    captured: dict = {}
    response = httpx.Response(
        200,
        json={"candidates": []},
        request=httpx.Request("POST", "https://example.invalid"),
    )

    with (
        patch.object(
            cloud_probe.httpx,
            "AsyncClient",
            MagicMock(return_value=_RecordingClient(response, captured)),
        ),
        patch.object(cloud_probe, "_gemini_api_key", return_value="test-key"),
    ):
        asyncio.run(
            cloud_probe.probe_cloud_llm(
                norm="gemini",
                model="gemini-3.5-flash-lite",
                base_url=cloud_probe.GEMINI_BASE_URL,
                timeout=5.0,
                hint="Check GEMINI_API_KEY.",
            )
        )

    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.5-flash-lite:generateContent"
    )
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["json"]["contents"][0]["parts"][0]["text"]
    assert captured["json"]["generationConfig"]["maxOutputTokens"] > 0
    # Never leak the credential into the URL.
    assert "test-key" not in captured["url"]


def test_cloud_probe_reports_a_missing_credential():
    """A missing API key must fail fast with an actionable message."""
    from app.llm.providers import cloud_probe

    with patch.object(cloud_probe, "_gemini_api_key", return_value=""):
        with pytest.raises(LLMUnavailableError) as excinfo:
            asyncio.run(
                cloud_probe.probe_cloud_llm(
                    norm="gemini",
                    model="gemini-3.5-flash-lite",
                    base_url=cloud_probe.GEMINI_BASE_URL,
                    timeout=5.0,
                    hint="Check GEMINI_API_KEY.",
                )
            )
    assert "GEMINI_API_KEY" in excinfo.value.message


def test_cloud_probe_classifies_an_unknown_model():
    """A 404 from Gemini must name the model, not leak a stack trace."""
    from app.llm.providers import cloud_probe

    captured: dict = {}
    response = httpx.Response(
        404,
        json={"error": {"message": "not found"}},
        request=httpx.Request("POST", "https://example.invalid"),
    )

    with (
        patch.object(
            cloud_probe.httpx,
            "AsyncClient",
            MagicMock(return_value=_RecordingClient(response, captured)),
        ),
        patch.object(cloud_probe, "_gemini_api_key", return_value="test-key"),
    ):
        with pytest.raises(LLMUnavailableError) as excinfo:
            asyncio.run(
                cloud_probe.probe_cloud_llm(
                    norm="gemini",
                    model="gemini-does-not-exist",
                    base_url=cloud_probe.GEMINI_BASE_URL,
                    timeout=5.0,
                    hint="Check GEMINI_API_KEY.",
                )
            )
    assert "not found" in excinfo.value.message
    assert "gemini-does-not-exist" in excinfo.value.message


def test_cloud_probe_classifies_rejected_credentials():
    """A 401/403 must be reported as a credential problem."""
    from app.llm.providers import cloud_probe

    captured: dict = {}
    response = httpx.Response(
        403,
        json={"error": {"message": "denied"}},
        request=httpx.Request("POST", "https://example.invalid"),
    )

    with (
        patch.object(
            cloud_probe.httpx,
            "AsyncClient",
            MagicMock(return_value=_RecordingClient(response, captured)),
        ),
        patch.object(cloud_probe, "_gemini_api_key", return_value="test-key"),
    ):
        with pytest.raises(LLMUnavailableError) as excinfo:
            asyncio.run(
                cloud_probe.probe_cloud_llm(
                    norm="gemini",
                    model="gemini-3.5-flash-lite",
                    base_url=cloud_probe.GEMINI_BASE_URL,
                    timeout=5.0,
                    hint="Check GEMINI_API_KEY.",
                )
            )
    assert "rejected credentials" in excinfo.value.message
    # The credential itself must never appear in the user-facing message.
    assert "test-key" not in excinfo.value.message


def test_status_code_is_read_from_the_httpx_response():
    """``httpx.HTTPStatusError`` carries the code on ``.response``."""
    from app.llm.providers.cloud_probe import _status_code_of

    response = httpx.Response(
        429,
        json={},
        request=httpx.Request("POST", "https://example.invalid"),
    )
    exc = httpx.HTTPStatusError("rate limited", request=response.request, response=response)
    assert _status_code_of(exc) == 429


# ─── The call site ───────────────────────────────────────────────────────────


@pytest.fixture
def mock_user_doc():
    return {
        "_id": ObjectId("64ee39d09c6292376e191981"),
        "email": "test@example.com",
        "hashed_password": "hashed-stuff",
        "full_name": "Test User",
        "is_active": True,
        "created_at": "2026-08-27T10:00:00Z",
    }


@pytest.fixture
def mock_kb_doc():
    return {
        "_id": ObjectId("64ee39d09c6292376e191982"),
        "name": "API Limits",
        "description": "API limit schedules",
        "user_id": ObjectId("64ee39d09c6292376e191981"),
        "created_at": "2026-08-27T10:00:00Z",
    }


def test_create_analysis_calls_the_cloud_probe_with_keyword_arguments(mock_user_doc, mock_kb_doc):
    """The Gemini preflight must not raise ``TypeError`` any more.

    The call used to be ``probe_cloud_llm(provider, model)`` against a
    keyword-only signature, so every Gemini analysis died before the analysis
    document was written.
    """
    from fastapi.testclient import TestClient

    from app.api.deps import get_current_user
    from app.api.v1.schemas.kb import KBResponse
    from app.main import app

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: mock_user_doc
    try:
        mock_kb = KBResponse(
            id=str(mock_kb_doc["_id"]),
            name=mock_kb_doc["name"],
            description=mock_kb_doc["description"],
            user_id=str(mock_kb_doc["user_id"]),
            created_at="2026-08-27T10:00:00Z",
        )
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId(ANALYSIS_ID))
        )

        probe = AsyncMock(return_value=None)
        with (
            patch("app.services.analysis_service.get_kb", return_value=mock_kb),
            patch("app.services.analysis_service.get_collection", return_value=mock_collection),
            patch("app.services.analysis_service.add_trace_event", AsyncMock()),
            patch("app.services.analysis_service.run_analysis_pipeline", AsyncMock()),
            patch("app.llm.local_llm.probe_cloud_llm", probe),
        ):
            response = client.post(
                "/api/v1/analyses",
                json={
                    "knowledge_base_id": str(mock_kb_doc["_id"]),
                    "query": "What is the reciprocal rank fusion constant?",
                    "llm_provider": "gemini",
                    "llm_model": "gemini-3.5-flash-lite",
                },
            )

        assert response.status_code == 201, response.text
        probe.assert_awaited_once()
        kwargs = probe.await_args.kwargs
        assert kwargs["norm"] == "gemini"
        assert kwargs["model"] == "gemini-3.5-flash-lite"
        assert kwargs["base_url"].startswith("https://generativelanguage.googleapis.com")
        assert kwargs["timeout"] > 0
        # Positional arguments would raise TypeError against the keyword-only
        # signature — that was the bug.
        assert not probe.await_args.args
    finally:
        app.dependency_overrides.clear()
