"""
Tests for local LLM clients (Ollama and llama.cpp).
"""

import pytest
from pydantic import BaseModel

from app.core.local_llm import (
    ChatLlamaCppClient,
    ChatOllamaClient,
    check_llamacpp_status,
    check_ollama_status,
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
        assert ollama_llm.model == "granite4.2:3b-q4_K_M"

        llamacpp_llm = get_llm("llama_cpp")
        assert isinstance(llamacpp_llm, ChatLlamaCppClient)
        assert llamacpp_llm.model == "occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M"

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
    assert "granite4.2:3b-q4_K_M" in status["models"]
    assert "gemma3:1b" in status["models"]
    # LLM-only: embedding models must NOT appear in the selector list
    assert "embedding_models" not in status
    assert not any("embed" in m.lower() for m in status["models"])


@pytest.mark.asyncio
async def test_llamacpp_health_check():
    status = await check_llamacpp_status("http://127.0.0.1:8080/v1")
    assert "connected" in status
    assert status["provider"] == "llama_cpp"
    assert "occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M" in status["models"]
    assert "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M" in status["models"]
    assert not any("embed" in m.lower() for m in status["models"])


def test_embedding_model_local_providers():
    """Ollama/llama.cpp are LLM-only: embedding usage must fail loudly."""
    import pytest

    from app.core.exceptions import ConfigurationError
    from app.core.model_registry import get_embedding_model

    with pytest.raises(ConfigurationError, match="LLM-only"):
        get_embedding_model("ollama", "embeddinggemma:300m-qat-q8_0")

    with pytest.raises(ConfigurationError, match="LLM-only"):
        get_embedding_model("llamacpp", "ggml-org/embeddinggemma-300M-GGUF:Q8_0")
