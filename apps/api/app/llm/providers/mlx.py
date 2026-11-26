"""
TRUSTRAG — Local LLM provider: MLX client.

MLX shares the ChatLlamaCppClient class (same OpenAI-compatible protocol),
but registers separately under the "mlx" provider with the MLX base URL.
This module is a thin shim re-exporting the llama.cpp client as MLX.
"""

from __future__ import annotations

from app.llm.providers.llama_cpp import ChatLlamaCppClient

__all__ = ["ChatLlamaCppClient"]

# MLX uses the same client class; registered under "mlx" provider in model_registry.py.
ChatMLXClient = ChatLlamaCppClient
