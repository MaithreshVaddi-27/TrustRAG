"""
Tests for local LLM clients (Ollama and llama.cpp).
"""

from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

import app.core.local_llm as _llm_mod
from app.core.exceptions import ConfigurationError
from app.core.local_llm import (
    ChatLlamaCppClient,
    ChatOllamaClient,
    _shared_http_client,
    check_llamacpp_status,
    check_ollama_status,
    close_local_llm_clients,
)
from app.core.model_registry import get_llm, get_verification_model


class SampleExtraction(BaseModel):
    summary: str
    confidence: float


def test_ollama_client_initialization():
    client = ChatOllamaClient(
        base_url="http://localhost:11434",
        model="granite4.2:3b-q4_K_M",
        temperature=0.1,
    )
    assert client.model == "granite4.2:3b-q4_K_M"
    assert client.base_url == "http://localhost:11434"
    assert client._llm_type == "ollama-client"


def test_llamacpp_client_initialization():
    client = ChatLlamaCppClient(
        base_url="http://127.0.0.1:8080/v1",
        model="occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M",
        temperature=0.1,
    )
    assert client.model == "occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M"
    assert client.base_url == "http://127.0.0.1:8080/v1"
    assert client._llm_type == "llama-cpp-client"


@pytest.mark.asyncio
async def test_sync_generate_rejects_running_event_loop_without_leaking_coroutine():
    with pytest.raises(ConfigurationError, match="active event loop"):
        ChatOllamaClient()._generate([])


@pytest.mark.asyncio
async def test_local_llm_http_clients_are_reused_per_endpoint_and_loop():
    first = _shared_http_client("http://127.0.0.1:11434", 120.0)
    second = _shared_http_client("http://127.0.0.1:11434", 120.0)
    try:
        assert first is second
    finally:
        await close_local_llm_clients()


def test_model_registry_local_providers(monkeypatch):
    # Isolate from developer .env so local overrides can't flip expectations.
    for var in ("OLLAMA_MODEL", "LLAMACPP_MODEL", "LLAMA_CPP_MODEL", "LLM_MODEL", "GEMINI_MODEL"):
        monkeypatch.delenv(var, raising=False)
    from app.core.config import reload_settings
    from app.core.model_registry import clear_model_caches

    reload_settings()
    clear_model_caches()
    try:
        # Force the no-override path: Settings reads the .env FILE (not just
        # os.environ), so blank the model overrides on the singleton itself.
        from app.core.config import get_settings

        s = get_settings()
        monkeypatch.setattr(s, "ollama_model", "")
        monkeypatch.setattr(s, "llamacpp_model", "")
        monkeypatch.setattr(s, "mlx_model", "")
        ollama_llm = get_llm("ollama")
        assert isinstance(ollama_llm, ChatOllamaClient)
        assert ollama_llm.model == "gemma3:1b"

        llamacpp_llm = get_llm("llama_cpp")
        assert isinstance(llamacpp_llm, ChatLlamaCppClient)
        assert llamacpp_llm.model == "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M"

        mlx_llm = get_llm("mlx")
        assert isinstance(mlx_llm, ChatLlamaCppClient)
        assert mlx_llm.model == "mlx-community/Llama-3.2-1B-Instruct-4bit"
        assert mlx_llm.base_url == s.mlx_base_url

        v_ollama = get_verification_model("ollama")
        assert isinstance(v_ollama, ChatOllamaClient)
        assert v_ollama.temperature == 0.0

        v_llamacpp = get_verification_model("llama_cpp")
        assert isinstance(v_llamacpp, ChatLlamaCppClient)
        assert v_llamacpp.temperature == 0.0

        v_mlx = get_verification_model("mlx")
        assert isinstance(v_mlx, ChatLlamaCppClient)
        assert v_mlx.temperature == 0.0
    finally:
        clear_model_caches()
        reload_settings()


@pytest.mark.asyncio
async def test_ollama_health_check():
    status = await check_ollama_status("http://localhost:11434")
    assert "connected" in status
    assert status["provider"] == "ollama"
    assert isinstance(status["models"], list)
    # LLM-only: embedding models must NOT appear in the selector list
    assert "embedding_models" not in status
    assert not any("embed" in m.lower() for m in status["models"])


@pytest.mark.asyncio
async def test_llamacpp_health_check():
    status = await check_llamacpp_status("http://127.0.0.1:8080/v1")
    assert "connected" in status
    assert status["provider"] == "llama_cpp"
    assert isinstance(status["models"], list)
    assert not any("embed" in m.lower() for m in status["models"])
    # default_model should be set if models exist
    if status["models"]:
        assert status["default_model"] in status["models"] or status["default_model"] == ""


def test_embedding_model_local_providers():
    """Only local HuggingFace embeddings exist: anything else fails loudly."""
    import pytest

    from app.core.exceptions import ConfigurationError
    from app.core.model_registry import get_embedding_model

    with pytest.raises(ConfigurationError, match="local HuggingFace"):
        get_embedding_model("ollama", "embeddinggemma:300m-qat-q8_0")

    with pytest.raises(ConfigurationError, match="local HuggingFace"):
        get_embedding_model("llamacpp", "ggml-org/embeddinggemma-300M-GGUF:Q8_0")

    with pytest.raises(ConfigurationError, match="local HuggingFace"):
        get_embedding_model("google_genai", "models/gemini-embedding-001")

    with pytest.raises(ConfigurationError, match="local HuggingFace"):
        get_embedding_model("nvidia", "nvidia/nv-embedqa-e5-v5")


# ─── Discovery snapshot + seeding tests ───────────────────────────────────────


def _snapshot_save_restore(fn):
    """Decorator: save/restore global discovery cache around a test."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with _llm_mod._DISCOVERED_LLMS_LOCK:
            saved = {k: set(v) for k, v in _llm_mod._DISCOVERED_LLMS.items()}
            _llm_mod._DISCOVERED_LLMS.clear()
        try:
            return fn(*args, **kwargs)
        finally:
            with _llm_mod._DISCOVERED_LLMS_LOCK:
                _llm_mod._DISCOVERED_LLMS.clear()
                for k, v in saved.items():
                    _llm_mod._DISCOVERED_LLMS[k] = set(v)

    return wrapper


@_snapshot_save_restore
def test_snapshot_roundtrip(monkeypatch, tmp_path):
    snapshot_path = tmp_path / "discovered_models.json"
    monkeypatch.setattr(_llm_mod, "_DISCOVERY_SNAPSHOT_PATH", snapshot_path)

    _llm_mod.merge_discovered_llms("ollama", ["granite4.2:3b-q4_K_M", "nomic-embed-text"])
    _llm_mod.merge_discovered_llms("llama_cpp", ["huggingface/SmolLM3-3B-GGUF:Q4_K_M"])
    _llm_mod.save_discovery_snapshot()

    assert snapshot_path.exists()

    _llm_mod._DISCOVERED_LLMS.clear()
    _llm_mod.load_discovery_snapshot()

    # Embedding models filtered out of discovery cache
    assert _llm_mod.get_discovered_llms("ollama") == {"granite4.2:3b-q4_K_M"}
    assert _llm_mod.get_discovered_llms("llama_cpp") == {"huggingface/SmolLM3-3B-GGUF:Q4_K_M"}


@_snapshot_save_restore
def test_load_snapshot_missing_file_is_noop(monkeypatch, tmp_path):
    monkeypatch.setattr(_llm_mod, "_DISCOVERY_SNAPSHOT_PATH", tmp_path / "missing.json")
    _llm_mod.load_discovery_snapshot()  # should not raise
    assert _llm_mod.get_discovered_llms("llama_cpp") == frozenset()


@pytest.mark.asyncio
async def test_seed_local_model_discovery(monkeypatch, tmp_path):
    monkeypatch.setattr(_llm_mod, "_DISCOVERY_SNAPSHOT_PATH", tmp_path / "d.json")

    async def _fake_ollama():
        return ["granite4.2:3b-q4_K_M", "nomic-embed-text"]

    async def _fake_llamacpp():
        return ["huggingface/SmolLM3-3B-GGUF:Q4_K_M"]

    monkeypatch.setattr(_llm_mod, "discover_ollama_cli_models", _fake_ollama)
    monkeypatch.setattr(_llm_mod, "discover_llamacpp_cache_models", _fake_llamacpp)

    # Save/restore global cache to isolate from other tests
    with _llm_mod._DISCOVERED_LLMS_LOCK:
        saved = {k: set(v) for k, v in _llm_mod._DISCOVERED_LLMS.items()}
        _llm_mod._DISCOVERED_LLMS.clear()
    try:
        result = await _llm_mod.seed_local_model_discovery()

        # result contains ONLY generative models (embedding ids filtered out)
        assert result["ollama"] == ["granite4.2:3b-q4_K_M"]
        assert result["llama_cpp"] == ["huggingface/SmolLM3-3B-GGUF:Q4_K_M"]

        # Embedding model filtered from cache
        assert _llm_mod.get_discovered_llms("ollama") == {"granite4.2:3b-q4_K_M"}
        assert _llm_mod.get_discovered_llms("llama_cpp") == {"huggingface/SmolLM3-3B-GGUF:Q4_K_M"}

        assert (tmp_path / "d.json").exists()
    finally:
        with _llm_mod._DISCOVERED_LLMS_LOCK:
            _llm_mod._DISCOVERED_LLMS.clear()
            for k, v in saved.items():
                _llm_mod._DISCOVERED_LLMS[k] = set(v)


def test_local_cap_kwargs_only_for_local_providers():
    """Task-sized output caps must never leak to cloud APIs (foreign params)."""
    assert _llm_mod.local_cap_kwargs("llama_cpp", 128) == {"max_tokens": 128}
    assert _llm_mod.local_cap_kwargs("ollama", 384) == {"max_tokens": 384}
    assert _llm_mod.local_cap_kwargs("LLAMA_CPP", 384) == {"max_tokens": 384}
    assert _llm_mod.local_cap_kwargs("gemini", 384) == {}
    assert _llm_mod.local_cap_kwargs("nvidia", 384) == {}
    assert _llm_mod.local_cap_kwargs(None, 384) == {}
    assert _llm_mod.local_cap_kwargs("", 384) == {}


def test_verification_cap_kwargs_reasoning_headroom():
    """Verification caps: local stays lean, reasoning models get headroom
    (2x with a 1024 floor — live probes show ~475 reasoning tokens on
    trivia and a starved 256-token rewrite returning empty). Provider-
    correct param names throughout (thinking traces share the completion
    budget — without this, verdict JSON truncates)."""
    # Local direct-answer: identical to local_cap_kwargs (KV-saving, unchanged).
    assert _llm_mod.verification_cap_kwargs("ollama", "gemma3:1b", 384) == {"max_tokens": 384}
    assert _llm_mod.verification_cap_kwargs("llama_cpp", "any-model", 768) == {"max_tokens": 768}
    # Non-reasoning cloud: instance defaults ({}).
    assert _llm_mod.verification_cap_kwargs("nvidia", "google/gemma-4-31b-it", 384) == {}
    assert _llm_mod.verification_cap_kwargs("gemini", "gemini-3.5-flash-lite", 384) == {}
    assert _llm_mod.verification_cap_kwargs("nvidia", None, 384) == {}
    # Reasoning: 2x with 1024 floor, provider-correct names.
    assert _llm_mod.verification_cap_kwargs("nvidia", "meta/muse-glimmer-30b", 384) == {
        "max_tokens": 1024
    }
    assert _llm_mod.verification_cap_kwargs("nvidia", "openai/gpt-oss-20b", 512) == {
        "max_tokens": 1024
    }
    assert _llm_mod.verification_cap_kwargs("nvidia", "openai/gpt-oss-20b", 768) == {
        "max_tokens": 1536
    }
    assert _llm_mod.verification_cap_kwargs("gemini", "some-reasoning-model", 384) == {
        "max_output_tokens": 1024
    }


def test_is_reasoning_model_detection():
    assert _llm_mod.is_reasoning_model("meta/muse-glimmer-30b") is True
    assert _llm_mod.is_reasoning_model("openai/gpt-oss-20b") is True
    assert _llm_mod.is_reasoning_model("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning") is True
    assert _llm_mod.is_reasoning_model("qwen3:1.7b") is True
    assert _llm_mod.is_reasoning_model("google/gemma-4-31b-it") is False
    assert _llm_mod.is_reasoning_model("gemma3:1b") is False
    assert _llm_mod.is_reasoning_model(None) is False
    assert _llm_mod.is_reasoning_model("") is False


def test_verification_caps_cover_local_thinking_models():
    """Thinking traces share the budget on local servers too: qwen3 with a
    128-token rewrite cap returns empty → retry spiral. 1024 floor."""
    assert _llm_mod.verification_cap_kwargs("ollama", "qwen3:1.7b", 128) == {"max_tokens": 1024}
    assert _llm_mod.verification_cap_kwargs("ollama", "gemma3:1b", 128) == {"max_tokens": 128}


@pytest.mark.asyncio
async def test_ollama_stops_never_include_blank_line():
    """Regression: a '\\n\\n' stop decapitates thinking models (<think>\\n\\n)
    and truncates multi-paragraph answers. Only real EOS tokens allowed."""

    captured: dict = {}

    class _FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"message": {"content": "Paris."}}

    class _FakeClient:
        async def post(self, url: str, json: dict | None = None) -> _FakeResp:
            captured.update(json or {})
            return _FakeResp()

    with patch.object(_llm_mod, "_shared_http_client", return_value=_FakeClient()):
        client = ChatOllamaClient(base_url="http://localhost:11434", model="x", temperature=0.0)
        out = await client.ainvoke([HumanMessage(content="hi")])
    assert out.content == "Paris."
    stops = (captured.get("options", {}) or {}).get("stop") or []
    assert "\n\n" not in stops
    assert "<|endoftext|>" in stops  # early-exit EOS still active


# ─── Local-server preflight probe + discovery replace tests ───────────────────


class _FakeHTTPResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeHTTPClient:
    """Minimal async-context-manager stand-in for httpx.AsyncClient."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        raise AssertionError("test must override get()")


@pytest.mark.asyncio
async def test_probe_reaches_running_server(monkeypatch):
    from app.core.local_llm import probe_local_llm_server

    class _OK(_FakeHTTPClient):
        async def get(self, url):
            assert url.endswith("/api/tags")
            return _FakeHTTPResponse(200, {"models": []})

    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _OK)
    await probe_local_llm_server("ollama", "http://localhost:11434")  # must not raise


@pytest.mark.asyncio
async def test_probe_down_server_raises_actionable_error(monkeypatch):
    import httpx

    from app.core.exceptions import LLMUnavailableError
    from app.core.local_llm import probe_local_llm_server

    class _Down(_FakeHTTPClient):
        async def get(self, url):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _Down)
    with pytest.raises(LLMUnavailableError, match="not reachable"):
        await probe_local_llm_server("llama_cpp", "http://127.0.0.1:8080/v1")
    try:
        await probe_local_llm_server("llama_cpp", "http://127.0.0.1:8080/v1")
    except LLMUnavailableError as exc:
        assert "start_local_llm.sh" in exc.message


@pytest.mark.asyncio
async def test_probe_retries_slow_server_then_succeeds(monkeypatch):
    """One slow accept must not 503 the run — retry, then pass."""
    import httpx

    from app.core.local_llm import probe_local_llm_server

    calls = []

    class _Flaky(_FakeHTTPClient):
        async def get(self, url):
            calls.append(url)
            if len(calls) == 1:
                raise httpx.TimeoutException("slow first accept")
            return _FakeHTTPResponse(200, {"models": []})

    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _Flaky)
    await probe_local_llm_server("llama_cpp", "http://127.0.0.1:8080/v1")  # must not raise
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_probe_timeout_reports_overloaded_not_down(monkeypatch):
    """Persistent timeouts mean slow/overloaded — never 'not reachable'."""
    import httpx

    from app.core.exceptions import LLMUnavailableError
    from app.core.local_llm import probe_local_llm_server

    class _Slow(_FakeHTTPClient):
        async def get(self, url):
            raise httpx.TimeoutException("accept backlog full")

    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _Slow)
    with pytest.raises(LLMUnavailableError, match="not answering"):
        await probe_local_llm_server("llama_cpp", "http://127.0.0.1:8080/v1")


@pytest.mark.asyncio
async def test_ollama_status_retries_transient_timeout(monkeypatch):
    """A single blip must not flap the UI connected pill to Standby."""
    import httpx

    calls = []

    class _Flaky(_FakeHTTPClient):
        async def get(self, url):
            calls.append(url)
            if len(calls) == 1:
                raise httpx.TimeoutException("blip")
            return _FakeHTTPResponse(200, {"models": [{"name": "gemma3:1b"}]})

    async def _no_cli():
        return []

    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _Flaky)
    monkeypatch.setattr(_llm_mod, "discover_ollama_cli_models", _no_cli)
    with _llm_mod._DISCOVERED_LLMS_LOCK:
        saved = {k: set(v) for k, v in _llm_mod._DISCOVERED_LLMS.items()}
        _llm_mod._DISCOVERED_LLMS.clear()
    try:
        status = await _llm_mod.check_ollama_status("http://localhost:11434")
        assert status["connected"] is True
        assert status["models"] == ["gemma3:1b"]
        assert len(calls) == 2
    finally:
        with _llm_mod._DISCOVERED_LLMS_LOCK:
            _llm_mod._DISCOVERED_LLMS.clear()
            for k, v in saved.items():
                _llm_mod._DISCOVERED_LLMS[k] = set(v)


@_snapshot_save_restore
def test_merge_discovered_llms_replace_drops_uninstalled():
    _llm_mod.merge_discovered_llms("llama_cpp", ["a/Model-GGUF:Q4_K_M", "b/Old-GGUF:Q4_K_M"])
    assert _llm_mod.get_discovered_llms("llama_cpp") == {
        "a/Model-GGUF:Q4_K_M",
        "b/Old-GGUF:Q4_K_M",
    }
    # Fresh authoritative discovery replaces — uninstalled 'b' disappears.
    _llm_mod.merge_discovered_llms("llama_cpp", ["a/Model-GGUF:Q4_K_M"], replace=True)
    assert _llm_mod.get_discovered_llms("llama_cpp") == {"a/Model-GGUF:Q4_K_M"}
    # Empty refresh never wipes (transient failure must not break validation).
    _llm_mod.merge_discovered_llms("llama_cpp", [], replace=True)
    assert _llm_mod.get_discovered_llms("llama_cpp") == {"a/Model-GGUF:Q4_K_M"}


@pytest.mark.asyncio
async def test_llamacpp_connected_lists_only_loaded_model(monkeypatch):
    """A connected llama-server serves only --model; cache/HF blobs are phantoms."""

    async def _fake_cache():
        return ["stale/Cached-GGUF:Q4_K_M"]

    def _fake_hf():
        return ["stale/Cached-GGUF", "other/Downloaded-GGUF"]

    class _API(_FakeHTTPClient):
        async def get(self, url):
            return _FakeHTTPResponse(200, {"data": [{"id": "live/Loaded-GGUF:Q4_K_M"}]})

    monkeypatch.setattr(_llm_mod, "discover_llamacpp_cache_models", _fake_cache)
    monkeypatch.setattr(_llm_mod, "discover_hf_hub_gguf_models", _fake_hf)
    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _API)

    with _llm_mod._DISCOVERED_LLMS_LOCK:
        saved = {k: set(v) for k, v in _llm_mod._DISCOVERED_LLMS.items()}
        _llm_mod._DISCOVERED_LLMS.clear()
    try:
        status = await _llm_mod.check_llamacpp_status("http://127.0.0.1:8080/v1")
        assert status["connected"] is True
        assert status["models"] == ["live/Loaded-GGUF:Q4_K_M"]
        assert _llm_mod.get_discovered_llms("llama_cpp") == {"live/Loaded-GGUF:Q4_K_M"}
    finally:
        with _llm_mod._DISCOVERED_LLMS_LOCK:
            _llm_mod._DISCOVERED_LLMS.clear()
            for k, v in saved.items():
                _llm_mod._DISCOVERED_LLMS[k] = set(v)


def test_discover_mlx_cache_models_filters_non_mlx(monkeypatch, tmp_path):
    """HF-cache scan returns MLX weights only — GGUFs and unrelated models excluded."""

    path1 = (
        tmp_path
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--mlx-community--Llama-3.2-1B-Instruct-4bit"
    )
    path1.mkdir(parents=True)
    path2 = (
        tmp_path / ".cache" / "huggingface" / "hub" / "models--mlx-community--Qwen3-1.7B-MLX-8bit"
    )
    path2.mkdir(parents=True)
    path3 = tmp_path / ".cache" / "huggingface" / "hub" / "models--bartowski--Model-GGUF"
    path3.mkdir(parents=True)
    path4 = tmp_path / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-small-en-v1.5"
    path4.mkdir(parents=True)
    monkeypatch.setattr(_llm_mod.Path, "home", lambda: tmp_path)

    found = _llm_mod.discover_mlx_cache_models()
    assert "mlx-community/Llama-3.2-1B-Instruct-4bit" in found
    assert "mlx-community/Qwen3-1.7B-MLX-8bit" in found
    assert not any("gguf" in m.lower() or "bge" in m.lower() for m in found)


@pytest.mark.asyncio
async def test_mlx_connected_lists_only_loaded_model(monkeypatch):
    """A connected mlx server serves only --model; cache blobs are phantoms."""

    def _fake_cache():
        return ["mlx-community/Stale-Cached-4bit"]

    class _API(_FakeHTTPClient):
        async def get(self, url):
            return _FakeHTTPResponse(200, {"data": [{"id": "mlx-community/Live-Loaded-4bit"}]})

    monkeypatch.setattr(_llm_mod, "discover_mlx_cache_models", _fake_cache)
    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _API)

    with _llm_mod._DISCOVERED_LLMS_LOCK:
        saved = {k: set(v) for k, v in _llm_mod._DISCOVERED_LLMS.items()}
        _llm_mod._DISCOVERED_LLMS.clear()
    try:
        status = await _llm_mod.check_mlx_status("http://127.0.0.1:8080/v1")
        assert status["connected"] is True
        assert status["provider"] == "mlx"
        assert status["models"] == ["mlx-community/Live-Loaded-4bit"]
        assert _llm_mod.get_discovered_llms("mlx") == {"mlx-community/Live-Loaded-4bit"}
    finally:
        with _llm_mod._DISCOVERED_LLMS_LOCK:
            _llm_mod._DISCOVERED_LLMS.clear()
            for k, v in saved.items():
                _llm_mod._DISCOVERED_LLMS[k] = set(v)


@pytest.mark.asyncio
async def test_probe_mlx_hint_names_server_command(monkeypatch):
    """A down MLX server must tell the operator the mlx_lm.server command."""
    import httpx

    from app.core.exceptions import LLMUnavailableError
    from app.core.local_llm import probe_local_llm_server

    class _Down(_FakeHTTPClient):
        async def get(self, url):
            assert url.endswith("/v1/models")
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(_llm_mod.httpx, "AsyncClient", _Down)
    with pytest.raises(LLMUnavailableError, match="not reachable"):
        await probe_local_llm_server("mlx", "http://127.0.0.1:8080/v1")
    try:
        await probe_local_llm_server("mlx", "http://127.0.0.1:8080/v1")
    except LLMUnavailableError as exc:
        assert "mlx_lm.server" in exc.message
