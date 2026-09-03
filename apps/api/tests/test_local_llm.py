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
        model="gemma4:e2b",
        temperature=0.1,
    )
    assert client.model == "gemma4:e2b"
    assert client.base_url == "http://localhost:11434"
    assert client._llm_type == "ollama-client"


def test_llamacpp_client_initialization():
    client = ChatLlamaCppClient(
        base_url="http://localhost:8081/v1",
        model="gemma-4-E2B-it-qat-q4_0-gguf:Q4_0",
        temperature=0.1,
    )
    assert client.model == "gemma-4-E2B-it-qat-q4_0-gguf:Q4_0"
    assert client.base_url == "http://localhost:8081/v1"
    assert client._llm_type == "llama-cpp-client"


def test_model_registry_local_providers():
    ollama_llm = get_llm("ollama")
    assert isinstance(ollama_llm, ChatOllamaClient)
    assert ollama_llm.model == "gemma4:e2b"

    llamacpp_llm = get_llm("llama_cpp")
    assert isinstance(llamacpp_llm, ChatLlamaCppClient)
    assert llamacpp_llm.model == "gemma-4-E2B-it-qat-q4_0-gguf:Q4_0"

    v_ollama = get_verification_model("ollama")
    assert isinstance(v_ollama, ChatOllamaClient)
    assert v_ollama.temperature == 0.0

    v_llamacpp = get_verification_model("llama_cpp")
    assert isinstance(v_llamacpp, ChatLlamaCppClient)
    assert v_llamacpp.temperature == 0.0


@pytest.mark.asyncio
async def test_ollama_health_check():
    status = await check_ollama_status("http://localhost:11434")
    assert "connected" in status
    assert status["provider"] == "ollama"
    assert "granite4.2:3b-q4_K_M" in status["models"]
    assert "qwen3.5:4b" in status["models"]
    assert "embeddinggemma:300m-qat-q8_0" in status["embedding_models"]


@pytest.mark.asyncio
async def test_llamacpp_health_check():
    status = await check_llamacpp_status("http://localhost:8081/v1")
    assert "connected" in status
    assert status["provider"] == "llama_cpp"
    assert "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M" in status["models"]
    assert "psychopenguin/Qwen3.5-4B-Q4_K_M-GGUF:Q4_K_M" in status["models"]


def test_embedding_model_local_providers():
    from app.core.local_llm import LlamaCppEmbeddings, OllamaEmbeddings
    from app.core.model_registry import CachedEmbeddingsWrapper, get_embedding_model

    ollama_emb = get_embedding_model("ollama", "embeddinggemma:300m-qat-q8_0")
    assert isinstance(ollama_emb, (OllamaEmbeddings, CachedEmbeddingsWrapper))
    assert ollama_emb.model == "embeddinggemma:300m-qat-q8_0"

    llamacpp_emb = get_embedding_model("llamacpp", "ggml-org/embeddinggemma-300M-GGUF:Q8_0")
    assert isinstance(llamacpp_emb, (LlamaCppEmbeddings, CachedEmbeddingsWrapper))
    assert llamacpp_emb.model == "ggml-org/embeddinggemma-300M-GGUF:Q8_0"
