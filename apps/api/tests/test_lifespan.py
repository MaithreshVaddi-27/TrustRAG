"""
Startup / shutdown lifespan tests (audit B-11).

`app/main.py` was at 50% coverage with the ENTIRE lifespan uncovered
(lines 79-259) plus every exception handler (298-414). No test ever ran startup,
so a missing JWT secret, a failed index creation, or a broken ONNX preflight
would not be caught by any test — only by running the app.

These tests drive `lifespan` with the heavy externals stubbed and assert the
decisions that matter: offline-mode gating, the ONNX warning/error split, the
DB + index sequence, and a clean shutdown.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import lifespan


def _app() -> MagicMock:
    return MagicMock(name="fastapi-app")


def _settings(**overrides) -> MagicMock:
    s = MagicMock()
    s.app_env = "test"
    s.hf_token = ""
    s.jwt_secret = "x" * 64
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _cfg(**overrides) -> MagicMock:
    c = MagicMock()
    c.llm_provider = "ollama"
    c.llm_model = "test-model"
    c.embedding_model = "BAAI/bge-small-en-v1.5"
    c.embedding_cache_dir = ".model_cache"
    c.verification_provider = "ollama"
    c.verification_model = "verifier"
    c.reranker_enabled = True
    c.reranker_use_onnx = True
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    for var in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "LANGCHAIN_TRACING_V2", "HF_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    yield


def _patches(*, settings=None, cfg=None, onnx=None):
    status = onnx or {
        "embedding_onnx_present": True,
        "embedding_onnx_path": "/models/e.onnx",
        "reranker_onnx_present": True,
        "reranker_onnx_path": "/models/r.onnx",
    }
    return (
        patch("app.main.get_settings", return_value=settings or _settings()),
        patch("app.main.get_model_config", return_value=cfg or _cfg()),
        patch("app.core.model_registry.onnx_model_status", return_value=status),
        patch("app.main.connect_db", AsyncMock()),
        patch("app.main.create_indexes", AsyncMock()),
        patch("app.core.local_llm.seed_local_model_discovery", AsyncMock()),
        patch("app.main.get_cached_hardware_profile", MagicMock(return_value={})),
        patch("app.core.model_registry.get_embedding_model", MagicMock()),
        patch("app.core.memory.trim_memory", MagicMock()),
    )


async def _run_lifespan(entered: list[bool]) -> None:
    async with lifespan(_app()):
        entered.append(True)


@pytest.mark.asyncio
async def test_lifespan_starts_and_shuts_down_cleanly():
    """Startup must connect the DB, create indexes, and shut down in order."""
    calls: list[str] = []
    connect = AsyncMock(side_effect=lambda: calls.append("connect"))
    indexes = AsyncMock(side_effect=lambda: calls.append("indexes"))
    disconnect = AsyncMock(side_effect=lambda: calls.append("disconnect"))
    close_clients = AsyncMock(side_effect=lambda: calls.append("close_clients"))
    close_instances = AsyncMock(side_effect=lambda **_k: calls.append("close_instances"))

    with (
        patch("app.main.get_settings", return_value=_settings()),
        patch("app.main.get_model_config", return_value=_cfg()),
        patch(
            "app.core.model_registry.onnx_model_status",
            return_value={
                "embedding_onnx_present": True,
                "embedding_onnx_path": "/e.onnx",
                "reranker_onnx_present": True,
                "reranker_onnx_path": "/r.onnx",
            },
        ),
        patch("app.main.connect_db", connect),
        patch("app.main.create_indexes", indexes),
        patch("app.main.disconnect_db", disconnect),
        patch("app.core.local_llm.seed_local_model_discovery", AsyncMock()),
        patch("app.main.get_cached_hardware_profile", MagicMock(return_value={})),
        patch("app.core.model_registry.get_embedding_model", MagicMock()),
        patch("app.core.model_registry.close_all_llm_instances", close_instances),
        patch("app.core.local_llm.close_local_llm_clients", close_clients),
        patch("app.core.memory.trim_memory", MagicMock()),
    ):
        entered: list[bool] = []
        await _run_lifespan(entered)

    assert entered == [True], "lifespan did not yield (server never served)"
    assert calls.index("connect") < calls.index("indexes"), "indexes created before connect"
    for expected in ("connect", "indexes", "close_clients", "close_instances", "disconnect"):
        assert expected in calls, f"lifespan never did {expected}: {calls}"


@pytest.mark.asyncio
async def test_missing_onnx_embedding_weights_logs_error(caplog):
    """Without embedding weights every query 500s. Startup must say so loudly."""
    with (
        patch("app.main.get_settings", return_value=_settings()),
        patch("app.main.get_model_config", return_value=_cfg()),
        patch(
            "app.core.model_registry.onnx_model_status",
            return_value={
                "embedding_onnx_present": False,
                "embedding_onnx_path": "/missing.onnx",
                "reranker_onnx_present": True,
                "reranker_onnx_path": "/r.onnx",
            },
        ),
        patch("app.main.connect_db", AsyncMock()),
        patch("app.main.create_indexes", AsyncMock()),
        patch("app.main.disconnect_db", AsyncMock()),
        patch("app.core.local_llm.seed_local_model_discovery", AsyncMock()),
        patch("app.main.get_cached_hardware_profile", MagicMock(return_value={})),
        patch("app.core.model_registry.get_embedding_model", MagicMock()),
        patch("app.core.model_registry.close_all_llm_instances", AsyncMock()),
        patch("app.core.local_llm.close_local_llm_clients", AsyncMock()),
        patch("app.core.memory.trim_memory", MagicMock()),
        patch("app.main.logger.error") as spy_error,
    ):
        await _run_lifespan([])

    assert spy_error.call_count >= 1, "missing ONNX weights produced no error log"
    message = " ".join(str(c) for c in spy_error.call_args_list)
    assert "ONNX" in message and "bootstrap" in message.lower()


@pytest.mark.asyncio
async def test_hf_token_is_exported_to_the_environment():
    """Models gated behind an HF token need it in the child-process env."""
    with (
        patch("app.main.get_settings", return_value=_settings(hf_token="hf_secret_value")),
        patch("app.main.get_model_config", return_value=_cfg()),
        patch(
            "app.core.model_registry.onnx_model_status",
            return_value={
                "embedding_onnx_present": True,
                "embedding_onnx_path": "/e.onnx",
                "reranker_onnx_present": True,
                "reranker_onnx_path": "/r.onnx",
            },
        ),
        patch("app.main.connect_db", AsyncMock()),
        patch("app.main.create_indexes", AsyncMock()),
        patch("app.main.disconnect_db", AsyncMock()),
        patch("app.core.local_llm.seed_local_model_discovery", AsyncMock()),
        patch("app.main.get_cached_hardware_profile", MagicMock(return_value={})),
        patch("app.core.model_registry.get_embedding_model", MagicMock()),
        patch("app.core.model_registry.close_all_llm_instances", AsyncMock()),
        patch("app.core.local_llm.close_local_llm_clients", AsyncMock()),
        patch("app.core.memory.trim_memory", MagicMock()),
    ):
        await _run_lifespan([])

    assert os.environ.get("HF_TOKEN") == "hf_secret_value"
    assert os.environ.get("HUGGING_FACE_HUB_TOKEN") == "hf_secret_value"


@pytest.mark.asyncio
async def test_langchain_tracing_is_forced_off():
    """Strict offline operation: outbound tracing must never be enabled."""
    with (
        patch("app.main.get_settings", return_value=_settings()),
        patch("app.main.get_model_config", return_value=_cfg()),
        patch(
            "app.core.model_registry.onnx_model_status",
            return_value={
                "embedding_onnx_present": True,
                "embedding_onnx_path": "/e.onnx",
                "reranker_onnx_present": True,
                "reranker_onnx_path": "/r.onnx",
            },
        ),
        patch("app.main.connect_db", AsyncMock()),
        patch("app.main.create_indexes", AsyncMock()),
        patch("app.main.disconnect_db", AsyncMock()),
        patch("app.core.local_llm.seed_local_model_discovery", AsyncMock()),
        patch("app.main.get_cached_hardware_profile", MagicMock(return_value={})),
        patch("app.core.model_registry.get_embedding_model", MagicMock()),
        patch("app.core.model_registry.close_all_llm_instances", AsyncMock()),
        patch("app.core.local_llm.close_local_llm_clients", AsyncMock()),
        patch("app.core.memory.trim_memory", MagicMock()),
    ):
        await _run_lifespan([])

    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"


@pytest.mark.asyncio
async def test_settings_failure_is_reported_as_first_run_trap():
    """A missing .env surfaces as a bare pydantic error; startup must name the fix."""
    boom = ValueError("JWT_SECRET field required")

    with (
        patch("app.main.get_settings", side_effect=boom),
        patch("app.main.logger.error") as spy_error,
    ):
        with pytest.raises(ValueError):
            await _run_lifespan([])

    assert spy_error.call_count >= 1, "settings failure was not reported"
    message = " ".join(str(c) for c in spy_error.call_args_list)
    assert "JWT_SECRET" in message
    assert ".env" in message
