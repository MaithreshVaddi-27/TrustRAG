"""
Tests for the canonical port registry (repo-root config/ports.yaml).
"""

from __future__ import annotations

import pytest


def test_ports_yaml_loads_with_required_keys() -> None:
    from app.core.config import get_ports

    ports = get_ports()
    for key in (
        "backend",
        "frontend",
        "ollama",
        "llamacpp",
        "mongodb",
        "qdrant_http_host",
        "qdrant_http_container",
        "qdrant_grpc_host",
        "qdrant_grpc_container",
    ):
        assert key in ports, f"ports.yaml missing key: {key}"
        assert 1 <= ports[key] <= 65535


def test_ports_reserved_allocation() -> None:
    """8080 belongs to llama-server; the backend must never claim it."""
    from app.core.config import get_ports

    ports = get_ports()
    assert ports["llamacpp"] == 8080
    assert ports["backend"] != 8080
    assert ports["backend"] == 8000


def test_model_config_urls_honor_ports_yaml(monkeypatch) -> None:
    """Without explicit env URLs, provider base URLs derive from ports.yaml."""
    for var in (
        "OLLAMA_BASE_URL",
        "OLLAMA_HOST",
        "LLAMACPP_BASE_URL",
        "LLAMA_CPP_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)
    from app.core.config import get_model_config, get_ports, reload_ports

    reload_ports()
    cfg = get_model_config()
    ports = get_ports()
    assert cfg.ollama_base_url == f"http://localhost:{ports['ollama']}"
    assert cfg.llamacpp_base_url == f"http://127.0.0.1:{ports['llamacpp']}/v1"


def test_llm_discovery_excludes_embedding_models() -> None:
    from app.core.local_llm import _is_embedding_model_name

    assert _is_embedding_model_name("embeddinggemma:300m-qat-q8_0")
    assert _is_embedding_model_name("nomic-embed-text")
    assert _is_embedding_model_name("BAAI/bge-small-en-v1.5")
    assert _is_embedding_model_name("ggml-org/embeddinggemma-300M-GGUF:Q8_0")
    assert not _is_embedding_model_name("granite4.2:3b-q4_K_M")
    assert not _is_embedding_model_name("qwen3.5:4b")
    assert not _is_embedding_model_name("ibm-granite/granite-4.2-3b-GGUF:Q4_K_M")


@pytest.mark.asyncio
async def test_ollama_llm_discovery_is_llm_only(monkeypatch) -> None:
    """`ollama list` output must not leak embedding models into the LLM list."""
    import app.core.local_llm as local_llm

    async def fake_discover():
        return ["granite4.2:3b-q4_K_M", "embeddinggemma:300m-qat-q8_0", "qwen3.5:4b"]

    monkeypatch.setattr(local_llm, "discover_ollama_cli_models", fake_discover)
    status = await local_llm.check_ollama_status("http://localhost:11434")
    assert "embedding_models" not in status
    assert "embeddinggemma:300m-qat-q8_0" not in status["models"]
    assert "granite4.2:3b-q4_K_M" in status["models"]
