"""
TRUSTRAG — Configuration and settings unit tests.

Tests for Phase 1:
  - models.yaml loads and validates correctly
  - ModelConfig exposes correct values
  - Settings rejects invalid/missing required fields
  - No secrets leaked in config snapshot
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# ─── Path to actual models.yaml ───────────────────────────────────────────────

_API_ROOT = Path(__file__).resolve().parents[1]
_MODELS_YAML = _API_ROOT / "config" / "models.yaml"


# ─── ModelConfig tests ────────────────────────────────────────────────────────


class TestModelsYaml:
    def test_models_yaml_exists(self) -> None:
        assert _MODELS_YAML.exists(), f"models.yaml not found at {_MODELS_YAML}"

    def test_models_yaml_is_valid_yaml(self) -> None:
        with _MODELS_YAML.open() as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "models.yaml must be a YAML mapping"

    def test_required_sections_present(self) -> None:
        with _MODELS_YAML.open() as f:
            data = yaml.safe_load(f)

        required = [
            "llm",
            "embedding",
            "verification",
            "retrieval",
            "reliability",
            "recovery",
            "runtime",
        ]
        for section in required:
            assert section in data, f"Missing required section '{section}' in models.yaml"

    def test_no_secrets_in_models_yaml(self) -> None:
        """Ensure no API keys or credentials are present in models.yaml."""
        with _MODELS_YAML.open() as f:
            content = f.read()

        forbidden_patterns = [
            "api_key",
            "API_KEY",
            "password",
            "secret",
            "mongodb+srv",
            "AIza",  # Google API key prefix
        ]
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"Potential secret found in models.yaml: '{pattern}'. Secrets belong in .env only."
            )

    def test_embedding_dimensionality_is_positive_int(self) -> None:
        with _MODELS_YAML.open() as f:
            data = yaml.safe_load(f)
        dim = data["embedding"]["output_dimensionality"]
        assert isinstance(dim, int) and dim > 0

    def test_reliability_thresholds_in_range(self) -> None:
        with _MODELS_YAML.open() as f:
            data = yaml.safe_load(f)
        r = data["reliability"]
        assert 0 < r["minimum_evidence_coverage"] <= 1.0
        assert 0 <= r["maximum_contradiction_rate"] < 1.0
        assert 0 < r["abstain_below"] < 1.0

    def test_recovery_max_attempts_positive(self) -> None:
        with _MODELS_YAML.open() as f:
            data = yaml.safe_load(f)
        assert data["recovery"]["max_recovery_attempts"] > 0

    def test_config_version_present(self) -> None:
        with _MODELS_YAML.open() as f:
            data = yaml.safe_load(f)
        assert "config_version" in data["runtime"]
        assert data["runtime"]["config_version"]  # Not empty


class TestModelConfig:
    """Tests for the ModelConfig wrapper."""

    def _make_config(self):
        from app.core.config import ModelConfig

        with _MODELS_YAML.open() as f:
            data = yaml.safe_load(f)
        return ModelConfig(data)

    def test_llm_model_not_empty(self) -> None:
        cfg = self._make_config()
        assert cfg.llm_model and len(cfg.llm_model) > 0

    def test_embedding_model_not_empty(self) -> None:
        cfg = self._make_config()
        assert cfg.embedding_model and len(cfg.embedding_model) > 0

    def test_embedding_dimensionality_matches_yaml(self) -> None:
        cfg = self._make_config()
        # all-MiniLM-L6-v2 produces 384-dim vectors
        assert cfg.embedding_dimensionality == 384

    def test_abstain_below_is_float(self) -> None:
        cfg = self._make_config()
        assert isinstance(cfg.abstain_below, float)

    def test_snapshot_contains_no_secrets(self) -> None:
        cfg = self._make_config()
        snapshot = cfg.as_snapshot()
        forbidden = {"api_key", "secret", "password", "token"}
        for key in snapshot:
            assert key.lower() not in forbidden, f"Sensitive key '{key}' in snapshot"

    def test_snapshot_contains_config_version(self) -> None:
        cfg = self._make_config()
        snapshot = cfg.as_snapshot()
        assert "config_version" in snapshot
        assert snapshot["config_version"]

    def test_missing_required_key_raises(self) -> None:
        from app.core.config import ModelConfig

        incomplete = {"runtime": {"config_version": "1.0"}}
        cfg = ModelConfig(incomplete)
        with pytest.raises(KeyError):
            _ = cfg.llm_model

    def test_max_recovery_attempts_bounded(self) -> None:
        cfg = self._make_config()
        # Spec: prevent infinite loops — must be a small positive number
        assert 0 < cfg.max_recovery_attempts <= 10


# ─── Settings tests ───────────────────────────────────────────────────────────


class TestSettings:
    """Tests for pydantic Settings validation."""

    def _make_settings(self, **overrides):
        """Create Settings with test values, bypassing .env file."""
        from app.core.config import Settings

        base = {
            "jwt_secret": "a" * 64,
            "gemini_api_key": "test-key",
            "mongodb_uri": "mongodb://localhost:27017",
            "app_env": "development",
            "cors_origins": "http://localhost:5173",
        }
        base.update(overrides)
        # Override env_file to prevent loading actual .env
        with patch.dict(os.environ, base, clear=False):
            return Settings(**base)

    def test_valid_settings_construct(self) -> None:
        settings = self._make_settings()
        assert settings.app_env == "development"

    def test_cors_origins_list_parsed(self) -> None:
        settings = self._make_settings(cors_origins="http://localhost:5173,https://app.example.com")
        origins = settings.cors_origins_list
        assert len(origins) == 2
        assert "http://localhost:5173" in origins

    def test_short_jwt_secret_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="JWT_SECRET must be at least"):
            self._make_settings(jwt_secret="short")

    def test_invalid_app_env_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            self._make_settings(app_env="invalid")

    def test_invalid_log_level_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            self._make_settings(log_level="VERBOSE")

    def test_log_level_uppercased(self) -> None:
        settings = self._make_settings(log_level="info")
        assert settings.log_level == "INFO"

    def test_is_development(self) -> None:
        settings = self._make_settings(app_env="development")
        assert settings.is_development()
        assert not settings.is_production()
