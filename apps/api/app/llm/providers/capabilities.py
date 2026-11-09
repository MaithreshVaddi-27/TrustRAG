"""
TRUSTRAG — Local LLM providers: capability helpers.

Task-sized output caps, small-model / reasoning-model detection, and the
`verification_cap_kwargs` / `local_cap_kwargs` functions shared across
providers and verification/generation callers.
"""

from __future__ import annotations

import re

from app.observability.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "LOCAL_LLM_PROVIDERS",
    "_is_embedding_model_name",
    "is_reasoning_model",
    "is_small_model",
    "local_cap_kwargs",
    "verification_cap_kwargs",
]

# Providers served by a local inference process (single-tenant, serial).
# Output caps and concurrency guards apply ONLY here — cloud chat models use
# different parameter names (e.g. max_output_tokens) and must not receive ours.
# "mlx" (mlx_lm.server, Apple Silicon) speaks the same OpenAI-compatible
# protocol as llama.cpp, so it shares the client, caps, and semaphore.
LOCAL_LLM_PROVIDERS = frozenset({"ollama", "llama_cpp", "llamacpp", "mlx"})


def local_cap_kwargs(provider: str | None, max_tokens: int) -> dict[str, int]:
    """Task-sized output caps for local inference servers only.

    A rewrite needs ~20 words, a single NLI verdict ~100 tokens — letting them
    inherit the 1024-token default grows per-call KV cache and wall time for
    nothing. Returns {} for cloud providers (foreign parameter names).
    """
    if (provider or "").strip().lower() in LOCAL_LLM_PROVIDERS:
        return {"max_tokens": int(max_tokens)}
    return {}


# Model ids whose thinking trace shares the completion budget with the answer.
REASONING_MODEL_KEYWORDS = (
    "glimmer",
    "gpt-oss",
    "reasoning",
    "deepseek-r1",
    "r1-",
    "qwen3",
    "qwq",
    "think",
)


def is_reasoning_model(model: str | None) -> bool:
    """True when the model id looks like a thinking/reasoning model."""
    name = (model or "").lower()
    return any(kw in name for kw in REASONING_MODEL_KEYWORDS)


# Models small enough that the full prompt stack measurably hurts them.
# Numeric markers are matched with a boundary so an 11B/21B/70B id cannot match
# the "1b"/"2b"/"3b" fragments.
_SMALL_MODEL_SIZE_RE = re.compile(
    r"(?<![0-9.])0\.5b|(?<![0-9.])[123](\.[0-9])?b(?![0-9])", re.IGNORECASE
)
_SMALL_MODEL_FAMILIES = ("tiny", "smol", "micro", "minicpm", "lapce")
_NEVER_SMALL_PROVIDERS = ("gemini", "google_genai", "google")


def is_small_model(model: str | None, provider: str | None = None) -> bool:
    """True for ≤3B-class models that need the compact prompt + two-step path."""
    if (provider or "").strip().lower() in _NEVER_SMALL_PROVIDERS:
        return False
    name = (model or "").lower()
    if not name:
        return False
    if _SMALL_MODEL_SIZE_RE.search(name):
        return True
    return any(fam in name for fam in _SMALL_MODEL_FAMILIES)


# Embedding model name keywords — used to exclude embedding models from LLM
# provider discovery (ollama list, llama-server --cache-list, MLX HF scan).
_EMBEDDING_NAME_KEYWORDS = (
    "embed",
    "bge",
    "nomic",
    "minilm",
    "gte",
    "mxbai",
    "snowflake",
    "arctic-embed",
    "e5-",
    "e5_",
    "/e5",
)


def _is_embedding_model_name(name: str) -> bool:
    """True when the model id looks like an embedding model (not a generative LLM)."""
    return any(kw in name.lower() for kw in _EMBEDDING_NAME_KEYWORDS)


def verification_cap_kwargs(
    provider: str | None, model: str | None, max_tokens: int
) -> dict[str, int]:
    """Task-sized output caps for verification calls on any provider.

    Direct-answer models keep the lean caps. Thinking models (local or cloud)
    get headroom with a 1024-token floor. Cloud providers are capped per call
    too, using each client's own parameter name.
    """
    norm = (provider or "").strip().lower()
    roomy = max(int(max_tokens) * 2, 1024)
    small = is_small_model(model, provider)
    cap = roomy if (is_reasoning_model(model) or small) else int(max_tokens)

    if norm in LOCAL_LLM_PROVIDERS:
        return {"max_tokens": cap}
    if norm in ("gemini", "google_genai"):
        return {"max_output_tokens": cap}
    # Unknown provider: inject nothing rather than risk a foreign kwarg.
    return {}
