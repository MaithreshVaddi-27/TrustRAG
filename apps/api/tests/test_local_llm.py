"""
Tests for local LLM clients (Ollama and llama.cpp).
"""

import pytest
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
        ollama_llm = get_llm("ollama")
        assert isinstance(ollama_llm, ChatOllamaClient)
        assert ollama_llm.model == "gemma3:1b"

        llamacpp_llm = get_llm("llama_cpp")
        assert isinstance(llamacpp_llm, ChatLlamaCppClient)
        assert llamacpp_llm.model == "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M"

        v_ollama = get_verification_model("ollama")
        assert isinstance(v_ollama, ChatOllamaClient)
        assert v_ollama.temperature == 0.0

        v_llamacpp = get_verification_model("llama_cpp")
        assert isinstance(v_llamacpp, ChatLlamaCppClient)
        assert v_llamacpp.temperature == 0.0
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
