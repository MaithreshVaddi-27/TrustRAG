"""TRUSTRAG configuration package.

Deep paths: app.core.config.settings (env-sourced Settings),
app.core.config.model_config (models.yaml registry). The names below are
re-exported so existing `from app.core.config import X` imports and
`patch("app.core.config.*")` targets keep working.
"""

from app.core.config.model_config import (
    SUPPORTED_LLM_PROVIDERS,
    ModelConfig,
    get_model_config,
    normalize_provider,
)
from app.core.config.settings import (
    Settings,
    get_ports,
    get_settings,
)

__all__ = [
    "SUPPORTED_LLM_PROVIDERS",
    "ModelConfig",
    "Settings",
    "get_model_config",
    "get_ports",
    "get_settings",
    "normalize_provider",
]
