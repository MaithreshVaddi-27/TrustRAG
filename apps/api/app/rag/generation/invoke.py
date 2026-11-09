"""
TRUSTRAG — grounded answer generation: provider invoke kwargs.

Provider-aware LLM invoke kwargs. Local-only params (num_ctx, num_batch/n_batch,
keep_alive, max_tokens) must never reach cloud chat models: Gemini's
GenerateContentConfig rejects unknown fields.
"""

from __future__ import annotations

from typing import Any

from app.llm.local_llm import LOCAL_LLM_PROVIDERS, local_cap_kwargs

__all__ = ["_invoke_kwargs_for_provider"]


def _invoke_kwargs_for_provider(
    provider: str | None,
    max_tokens: int,
    *,
    num_ctx: int | None = None,
    num_batch: int | None = None,
    keep_alive: str | None = None,
) -> dict[str, Any]:
    """Build per-call LLM kwargs with the correct param names per provider.

    Local providers get local kwargs plus num_ctx/num_batch/keep_alive.
    Cloud providers (Gemini) get max_output_tokens only.
    """
    norm = (provider or "").strip().lower()
    if norm in LOCAL_LLM_PROVIDERS:
        kwargs: dict[str, Any] = dict(local_cap_kwargs(provider, max_tokens))
        if num_ctx is not None:
            kwargs["num_ctx"] = num_ctx
        if num_batch is not None:
            # Both spellings: Ollama reads num_batch, llama.cpp reads n_batch.
            kwargs["num_batch"] = num_batch
            kwargs["n_batch"] = num_batch
        if keep_alive is not None:
            kwargs["keep_alive"] = keep_alive
        return kwargs
    if norm in ("gemini", "google_genai"):
        return {"max_output_tokens": int(max_tokens)}

    raise ValueError(f"Unsupported LLM provider: {provider}")
