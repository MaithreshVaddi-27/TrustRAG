"""
TRUSTRAG — Configuration Capability.

Centralized configuration management split from monolithic model_config.py:
- settings: Application settings from environment (.env)
- model_config: Model/AI configuration from models.yaml
- loader: YAML loading, mtime caching, validation
"""

from __future__ import annotations

from app.config.settings import get_settings, get_ports
from app.config.model_config import (
    get_model_config,
    clear_model_config_cache,
    ModelConfig,
    SUPPORTED_LLM_PROVIDERS,
    normalize_provider,
)
from app.config.loader import load_models_yaml, validate_models_yaml

__all__ = [
    "get_settings",
    "get_ports",
    "get_model_config",
    "clear_model_config_cache",
    "ModelConfig",
    "load_models_yaml",
    "validate_models_yaml",
    "SUPPORTED_LLM_PROVIDERS",
    "normalize_provider",
]