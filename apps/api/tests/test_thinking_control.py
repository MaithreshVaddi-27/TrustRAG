"""
Tests for the thinking control (audit change B4).

A thinking model spends most of its wall-clock writing the reasoning trace.
Measured on qwen3:1.7b, the trace bought nothing for two of the pipeline's
three LLM tasks and cost 4-16x the time:

| Task | With thinking | Without |
|---|---|---|
| NLI — one claim vs the premise | 5687 ms | 1299 ms |
| Fused decompose + verify | 6369 ms | 1213 ms |
| Recovery query rewrite | ~16.5 s | ~0.3 s |

The switch is only sent to models that actually think (a non-thinking model
rejects the field), and the verifier's use of it is a config value.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.providers.capabilities import verification_cap_kwargs


def test_think_is_added_for_a_reasoning_model():
    kwargs = verification_cap_kwargs("ollama", "qwen3:1.7b", max_tokens=384, think=False)
    assert kwargs["think"] is False


def test_think_is_not_added_for_a_non_reasoning_model():
    """A non-thinking model rejects the field, so it must not be sent."""
    kwargs = verification_cap_kwargs("ollama", "gemma3:1b", max_tokens=384, think=False)
    assert "think" not in kwargs


def test_think_is_omitted_when_not_requested():
    kwargs = verification_cap_kwargs("ollama", "qwen3:1.7b", max_tokens=384)
    assert "think" not in kwargs


def test_think_is_never_added_to_a_cloud_provider():
    """Gemini rejects foreign parameters, so the switch must not leak."""
    kwargs = verification_cap_kwargs("gemini", "gemini-3.5-flash-lite", max_tokens=384, think=False)
    assert kwargs == {"max_output_tokens": 384}


def test_the_verification_thinking_setting_defaults_to_off():
    """The measured setting: the trace is not worth its cost."""
    from app.config import get_model_config

    assert get_model_config().verification_thinking is False


@pytest.mark.asyncio
async def test_the_ollama_client_sends_the_think_switch():
    """The switch has to reach the wire, not just the kwargs."""
    from app.llm.providers.ollama import ChatOllamaClient

    captured: dict = {}

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"message": {"content": "OK"}}

        def raise_for_status(self):
            return None

    class _FakeClient:
        async def post(self, endpoint, json=None):
            captured["payload"] = json
            return _FakeResponse()

    client = ChatOllamaClient(base_url="http://127.0.0.1:11434", model="qwen3:1.7b")
    with patch("app.llm.providers.ollama.get_global_semaphore", MagicMock()):
        with patch(
            "app.llm.providers.ollama._get_shared_http_client",
            MagicMock(return_value=MagicMock(return_value=_FakeClient())),
        ):
            await client._agenerate(
                [("user", "hello")],  # type: ignore[arg-type]
                think=False,
            )

    assert captured["payload"]["think"] is False
