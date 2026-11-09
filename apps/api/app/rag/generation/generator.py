"""
TRUSTRAG — grounded answer generation using local LLMs and Gemini.

This module is a backward-compatible re-export shim. All implementation has
been split into focused sub-modules:

- ``generation/invoke`` — provider-aware invoke kwargs
- ``generation/context`` — context formatting, pruning, citation extraction
- ``generation/prompt`` — grounding system prompt
- ``generation/dynamic_ctx`` — dynamic num_ctx calculation

Existing imports (``from app.rag.generation.generator import ...``) continue
to work unchanged.
"""

from __future__ import annotations

from app.llm.model_registry import get_llm
from app.rag.generation.context import (
    extract_citations,
    extract_final_answer,
    format_context,
    format_context_with_chunk_indices,
    prune_context_tokens,
    strip_citation_markers,
    strip_invalid_citations,
    strip_scaffold_tags,
    strip_stray_abstain,
    strip_think_blocks,
)
from app.rag.generation.dynamic_ctx import (
    calculate_dynamic_num_ctx,
    encode_tokens,
)
from app.rag.generation.invoke import (
    _invoke_kwargs_for_provider,
)
from app.rag.generation.prompt import (
    GROUNDING_SYSTEM_PROMPT,
    GROUNDING_SYSTEM_PROMPT_SMALL,
    _grounding_prompt,
    neutralize_prompt_fences,
)
from app.rag.generation.runtime import (
    generate_grounded_answer,
)

__all__ = [
    "GROUNDING_SYSTEM_PROMPT",
    "GROUNDING_SYSTEM_PROMPT_SMALL",
    "_grounding_prompt",
    "_invoke_kwargs_for_provider",
    "calculate_dynamic_num_ctx",
    "encode_tokens",
    "extract_citations",
    "extract_final_answer",
    "format_context",
    "format_context_with_chunk_indices",
    "generate_grounded_answer",
    "get_llm",
    "neutralize_prompt_fences",
    "prune_context_tokens",
    "strip_citation_markers",
    "strip_invalid_citations",
    "strip_scaffold_tags",
    "strip_stray_abstain",
    "strip_think_blocks",
]
