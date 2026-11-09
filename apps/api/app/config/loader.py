"""
TRUSTRAG — models.yaml loading and validation.

Internal helpers for parsing models.yaml. Public API is in model_config.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.config.settings import _MODELS_YAML_PATH

__all__ = [
    "load_models_yaml",
    "validate_models_yaml",
]


def load_models_yaml() -> dict[str, Any]:
    """Load and parse config/models.yaml. Fails loudly on missing/malformed file."""
    if not _MODELS_YAML_PATH.exists():
        raise FileNotFoundError(
            f"models.yaml not found at {_MODELS_YAML_PATH}. "
            "This file must exist — it is the centralized config registry."
        )
    with _MODELS_YAML_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"models.yaml must be a YAML mapping. Got: {type(data)}")
    return data


def validate_models_yaml(data: dict[str, Any]) -> None:
    """Validate required sections exist in models.yaml.

    Raises:
        KeyError: If a required top-level section is missing.
        ValueError: If a section has invalid structure.
    """
    required_sections = [
        "runtime",
        "llm",
        "embedding",
        "verification",
        "reranker",
        "onnx",
        "retrieval",
        "ingestion",
        "reliability",
        "recovery",
        "cost_controls",
        "local_llm",
        "optimization",
    ]
    for section in required_sections:
        if section not in data:
            raise KeyError(f"Required section '{section}' missing from models.yaml")

    # Validate embedding section
    emb = data.get("embedding", {})
    if "model" not in emb:
        raise KeyError("Required key 'embedding.model' missing from models.yaml")
    if "output_dimensionality" not in emb:
        raise KeyError("Required key 'embedding.output_dimensionality' missing from models.yaml")
    if "version" not in emb:
        raise KeyError("Required key 'embedding.version' missing from models.yaml")

    # Validate llm section
    llm = data.get("llm", {})
    if "provider" not in llm:
        raise KeyError("Required key 'llm.provider' missing from models.yaml")
    if "model" not in llm:
        raise KeyError("Required key 'llm.model' missing from models.yaml")
    if "supported_models_gemini" not in llm:
        raise KeyError("Required key 'llm.supported_models_gemini' missing from models.yaml")

    # Validate verification section
    ver = data.get("verification", {})
    if "model" not in ver:
        raise KeyError("Required key 'verification.model' missing from models.yaml")

    # Validate reranker section
    rerank = data.get("reranker", {})
    if "model" not in rerank:
        raise KeyError("Required key 'reranker.model' missing from models.yaml")
