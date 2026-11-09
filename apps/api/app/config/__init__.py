"""
TRUSTRAG — Configuration Capability.

Centralized configuration management split from monolithic model_config.py:
- settings: Application settings from environment (.env)
- model_config: Model/AI configuration from models.yaml
- loader: YAML loading, mtime caching, validation
"""

from __future__ import annotations

from app.config.loader import load_models_yaml, validate_models_yaml
from app.config.model_config import (
    SUPPORTED_LLM_PROVIDERS,
    ModelConfig,
    clear_model_config_cache,
    get_model_config,
    normalize_provider,
)
from app.config.settings import get_ports, get_settings

__all__ = [
    "SUPPORTED_LLM_PROVIDERS",
    "ModelConfig",
    "clear_model_config_cache",
    "get_model_config",
    "get_ports",
    "get_settings",
    "load_models_yaml",
    "normalize_provider",
    "validate_models_yaml",
]
