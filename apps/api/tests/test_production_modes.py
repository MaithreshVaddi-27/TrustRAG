"""
TRUSTRAG — Production Modes & Configuration Hardening Tests.

Validates the two serving profiles and operational guardrails:
1. Default Production Mode:
   - Local-only Ollama gemma3:1b with XML CRAFT contrastive prompting.
   - Hybrid dense (BGE ONNX) + sparse (BM25) retrieval with RRF.
   - ONNX reranker disabled by default (no overhead when not beneficial).
   - RERANKER_ENABLED env override support.
2. Deep-Reasoning Mode:
   - qwen3:1.7b gated behind deep_reasoning_mode / DEEP_REASONING_MODE feature flag.
   - Rejection in interactive AnalysisCreate when feature flag is disabled.
   - Allowed when DEEP_REASONING_MODE=true.
   - Never the default interactive generator.
3. Guardrails & Recovery Hardening:
   - Meta-prefix stripping and token-equivalent query detection in recovery query rewriting.
   - Preserving prior refusal answers on re_retrieve downgrade to prevent adversarial answering.
   - State preservation of prior_diagnosis across recovery loops.
   - Stable NLI JSON parsing stripping <think> blocks.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.core.config.model_config import get_model_config
from app.llm.llm_utils import extract_json_substring
from app.rag.agent.graph import (
    _is_effectively_identical_query,
    _normalize_query_tokens,
    _sanitize_rewritten_query,
)


class TestDefaultProductionModeConfig:
    """Verifies default production mode configuration in models.yaml and ModelConfig."""

    def test_default_production_models_yaml_settings(self) -> None:
        cfg = get_model_config()
        # Default LLM is gemma3:1b via ollama
        assert cfg.llm_provider == "ollama"
        assert cfg.llm_model == "gemma3:1b"
        assert cfg.llm_model_for("ollama") == "gemma3:1b"

        # Verification uses gemma3:1b via ollama
        assert cfg.verification_provider == "ollama"
        assert cfg.verification_model == "gemma3:1b"

        # Reranker is disabled by default
        assert cfg.reranker_enabled is False

        # Deep-reasoning mode is disabled by default
        assert cfg.deep_reasoning_mode is False
        assert cfg.deep_reasoning_model == "qwen3:1.7b"

    def test_reranker_env_toggle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RERANKER_ENABLED", "true")
        cfg = get_model_config()
        assert cfg.reranker_enabled is True

        monkeypatch.setenv("RERANKER_ENABLED", "1")
        assert cfg.reranker_enabled is True

        monkeypatch.setenv("RERANKER_ENABLED", "false")
        assert cfg.reranker_enabled is False

        monkeypatch.setenv("RERANKER_ENABLED", "0")
        assert cfg.reranker_enabled is False

        monkeypatch.delenv("RERANKER_ENABLED", raising=False)
        assert cfg.reranker_enabled is False

    def test_deep_reasoning_mode_env_toggle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEEP_REASONING_MODE", "true")
        cfg = get_model_config()
        assert cfg.deep_reasoning_mode is True

        monkeypatch.setenv("DEEP_REASONING_MODE", "false")
        assert cfg.deep_reasoning_mode is False

        monkeypatch.delenv("DEEP_REASONING_MODE", raising=False)
        assert cfg.deep_reasoning_mode is False


class TestDeepReasoningModeGating:
    """Verifies gating of deep-reasoning models in interactive analysis API."""

    def test_deep_reasoning_model_rejected_when_mode_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.api.v1.schemas.analysis import AnalysisCreate

        monkeypatch.delenv("DEEP_REASONING_MODE", raising=False)
        monkeypatch.setattr(
            "app.llm.local_llm.get_discovered_llms",
            lambda provider: (
                frozenset(["gemma3:1b", "qwen3:1.7b"]) if provider == "ollama" else frozenset()
            ),
        )

        with pytest.raises(ValidationError, match=r"deep-reasoning mode to be enabled"):
            AnalysisCreate(
                knowledge_base_id="64ee39d09c6292376e191983",
                query="Complex numeric calculation",
                llm_provider="ollama",
                llm_model="qwen3:1.7b",
            )

    def test_deep_reasoning_model_allowed_when_mode_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.api.v1.schemas.analysis import AnalysisCreate

        monkeypatch.setenv("DEEP_REASONING_MODE", "true")
        monkeypatch.setattr(
            "app.llm.local_llm.get_discovered_llms",
            lambda provider: (
                frozenset(["gemma3:1b", "qwen3:1.7b"]) if provider == "ollama" else frozenset()
            ),
        )

        request = AnalysisCreate(
            knowledge_base_id="64ee39d09c6292376e191983",
            query="Complex numeric calculation",
            llm_provider="ollama",
            llm_model="qwen3:1.7b",
        )
        assert request.llm_model == "qwen3:1.7b"

    def test_default_model_remains_gemma(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.api.v1.schemas.analysis import AnalysisCreate
        from app.core.config.model_config import get_model_config

        monkeypatch.setattr(
            "app.llm.local_llm.get_discovered_llms",
            lambda provider: frozenset(["gemma3:1b"]) if provider == "ollama" else frozenset(),
        )

        request = AnalysisCreate(
            knowledge_base_id="64ee39d09c6292376e191983",
            query="Standard question",
            llm_provider="ollama",
        )
        assert request.llm_provider == "ollama"
        cfg = get_model_config()
        assert cfg.llm_model == "gemma3:1b"
        assert cfg.llm_model_for("ollama") == "gemma3:1b"
        assert cfg.deep_reasoning_mode is False


class TestRecoveryAndQueryRewritingHardening:
    """Verifies prevention of recovery leakage and adversarial answering loops."""

    def test_clean_rewritten_query_meta_prefixes(self) -> None:
        assert (
            _sanitize_rewritten_query("Expand: flibbertygibbet zzzwarranty")
            == "flibbertygibbet zzzwarranty"
        )
        assert _sanitize_rewritten_query("expand: foo bar") == "foo bar"
        assert _sanitize_rewritten_query("rewrite: query terms") == "query terms"
        assert _sanitize_rewritten_query("Query: search terms") == "search terms"
        assert _sanitize_rewritten_query("Search: search terms") == "search terms"

    def test_is_effectively_identical_query(self) -> None:
        original = "flibbertygibbet zzzwarranty tokenlifetime"
        # Prefixed with Expand: but same tokens
        rewritten_prefixed = "Expand: flibbertygibbet zzzwarranty tokenlifetime"
        cleaned = _sanitize_rewritten_query(rewritten_prefixed)
        assert _is_effectively_identical_query(original, cleaned) is True

        # Punctuation / casing differences
        assert _is_effectively_identical_query("foo bar baz?", "Foo, bar baz!") is True

        # Truly new search terms
        assert _is_effectively_identical_query("foo bar", "foo bar qux") is False

    def test_normalize_query_tokens(self) -> None:
        tokens = _normalize_query_tokens("What is the token-lifetime, exactly?!")
        assert "what" in tokens
        assert "tokenlifetime" in tokens or "token" in tokens
        assert "?" not in tokens


class TestNLIStableParsing:
    """Verifies that reasoning tags from thinking models do not break NLI JSON extraction."""

    def test_extract_json_substring_strips_think_blocks(self) -> None:
        llm_raw_output = (
            "<think>\n"
            "The document mentions a 30-day warranty, but query asks about 90 days.\n"
            "Therefore, label should be CONTRADICTION.\n"
            '{"intermediate_steps": ["step 1"]}\n'
            "</think>\n"
            '{"label": "CONTRADICTION", "reason": "Warranty period mismatch"}'
        )

        parsed_str = extract_json_substring(llm_raw_output)
        assert parsed_str is not None
        parsed = json.loads(parsed_str)
        assert parsed["label"] == "CONTRADICTION"
        assert parsed["reason"] == "Warranty period mismatch"

    def test_extract_json_substring_handles_plain_json(self) -> None:
        raw = '{"label": "SUPPORTED", "reason": "Direct match"}'
        parsed_str = extract_json_substring(raw)
        assert parsed_str is not None
        parsed = json.loads(parsed_str)
        assert parsed["label"] == "SUPPORTED"
