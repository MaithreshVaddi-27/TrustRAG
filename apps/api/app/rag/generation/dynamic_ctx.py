"""
TRUSTRAG — grounded answer generation: dynamic context sizing.

Calculates optimal num_ctx based on actual token counts for context, system
prompt, query, and max output tokens.
"""

from __future__ import annotations

import tiktoken

__all__ = ["calculate_dynamic_num_ctx", "encode_tokens"]


def encode_tokens(text: str) -> list[int]:
    """Encode text to token ids using cl100k_base encoding."""
    enc = tiktoken.get_encoding("cl100k_base")
    return enc.encode(text)


def calculate_dynamic_num_ctx(
    context_str: str,
    system_prompt: str,
    query: str,
    max_output_tokens: int,
    provider: str | None = None,
    model: str | None = None,
) -> int:
    """Calculate the optimal num_ctx for the LLM call."""
    total_input = (
        len(encode_tokens(context_str))
        + len(encode_tokens(system_prompt))
        + len(encode_tokens(query))
    )
    # Add headroom for output + safety margin
    num_ctx = total_input + max_output_tokens + 256
    # Round up to nearest power-of-two-friendly value
    return max(num_ctx, 2048)
