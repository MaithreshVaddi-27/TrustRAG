"""
TRUSTRAG — grounded answer generation: runtime LLM invocation.

``generate_grounded_answer`` — the async entry point that builds grounded
messages, resolves the provider/model, sizes the context window dynamically,
invokes the LLM, and post-processes the answer (scaffold stripping, think
block removal, stray ABSTAIN peel, invalid citation removal).
"""

from __future__ import annotations

from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_model_config
from app.llm.model_registry import get_llm
from app.observability.logging import get_logger
from app.llm.llm_ledger import invoke_counted
from app.llm.llm_utils import normalize_llm_content
from app.rag.generation.context import (
    extract_final_answer,
    format_context_with_chunk_indices,
    strip_invalid_citations,
    strip_stray_abstain,
    strip_think_blocks,
)
from app.rag.generation.dynamic_ctx import calculate_dynamic_num_ctx
from app.rag.generation.invoke import _invoke_kwargs_for_provider
from app.rag.generation.prompt import (
    _grounding_prompt,
    neutralize_prompt_fences,
)

logger = get_logger(__name__)

__all__ = ["generate_grounded_answer"]


async def generate_grounded_answer(
    query: str,
    chunks: list[dict[str, Any]],
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """
    Invoke LLM (Ollama, llama.cpp, Gemini) to generate a grounded answer
    based on candidate evidence chunks.

    If chunks list is empty, returns 'ABSTAIN' immediately without LLM invocation
    to save token costs and prevent hallucination.

    Returns:
        Full answer string (non-streaming mode).
    """

    if not chunks:
        logger.info("Empty context provided, abstaining immediately to save tokens")
        return "ABSTAIN"

    try:
        # Load config for dynamic context sizing
        cfg = get_model_config()

        # Determine provider and model if not explicitly provided
        resolved_provider = provider or cfg.llm_provider
        resolved_model = model or cfg.llm_model_for(resolved_provider)

        # Load primary LLM (cached) directly from model_registry
        import app.rag.generation.generator as _gen_mod
        _gen_get_llm = getattr(_gen_mod, "get_llm", get_llm)
        if hasattr(get_llm, "assert_called") or hasattr(get_llm, "mock_calls"):
            llm = get_llm(provider=resolved_provider, model=resolved_model)
        elif hasattr(_gen_get_llm, "assert_called") or hasattr(_gen_get_llm, "mock_calls"):
            llm = _gen_get_llm(provider=resolved_provider, model=resolved_model)
        else:
            llm = get_llm(provider=resolved_provider, model=resolved_model)

        # Prepare context text (indexed form: the segment count below is the
        # citation validity range for the post-check after generation)
        context_str, chunk_indices = format_context_with_chunk_indices(chunks)

        # Dynamic context sizing: calculate optimal num_ctx based on actual token counts
        max_output_tokens = cfg.llm_max_output_tokens
        system_prompt = _grounding_prompt(resolved_provider, resolved_model)
        dynamic_num_ctx = calculate_dynamic_num_ctx(
            context_str=context_str,
            system_prompt=system_prompt,
            query=query,
            max_output_tokens=max_output_tokens,
            provider=resolved_provider,
            model=resolved_model,
        )

        # Build prompt messages. The Context is untrusted third-party document
        # text, so it is XML-fenced: explicit open/close tags give the model a
        # structural boundary between instructions and data.
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"<premise>\n{neutralize_prompt_fences(context_str)}\n</premise>\n\n"
                    f"<query>\n{neutralize_prompt_fences(query)}\n</query>"
                )
            ),
        ]

        logger.info(
            "Invoking LLM for grounded generation",
            provider=resolved_provider,
            model=resolved_model,
            chunk_count=len(chunks),
            dynamic_num_ctx=dynamic_num_ctx,
            max_output_tokens=max_output_tokens,
        )

        # Provider-aware invoke kwargs: local providers get dynamic num_ctx
        # plus batch/keep_alive tuning; Gemini gets max_output_tokens.
        response = await invoke_counted(
            llm,
            messages,
            **_invoke_kwargs_for_provider(
                resolved_provider,
                max_output_tokens,
                num_ctx=dynamic_num_ctx,
                num_batch=cfg.local_llm_num_batch,
                keep_alive=cfg.local_llm_keep_alive,
            ),
        )

        # Standardize result (guard: None content must not become "None")
        answer = normalize_llm_content(response.content)
        if not answer:
            logger.warning("LLM returned empty content, abstaining")
            return "ABSTAIN"

        answer = answer.strip()

        # Peel reasoning-model scaffolding ([ANSWER]/[FINAL_ANSWER] sections)
        extracted = extract_final_answer(answer)
        if extracted != answer:
            logger.info(
                "Stripped scaffolded sections from generation",
                raw_len=len(answer),
                clean_len=len(extracted),
            )
            answer = extracted

        # Peel thinking traces (thinking models inline them into content)
        no_think = strip_think_blocks(answer).strip()
        if no_think != answer:
            logger.info(
                "Stripped think blocks from generation",
                raw_len=len(answer),
                clean_len=len(no_think),
            )
            answer = no_think

        # Peel a stray trailing ABSTAIN token small models append
        peeled = strip_stray_abstain(answer)
        if peeled != answer:
            logger.info(
                "Stripped stray trailing ABSTAIN token from generation",
                raw_len=len(answer),
                clean_len=len(peeled),
            )
            answer = peeled

        # Strip hallucinated provenance: cited segments that were never served
        cited_answer, dropped_citations = strip_invalid_citations(answer, len(chunk_indices))
        if dropped_citations:
            logger.info(
                "Stripped invalid segment citations from generation",
                dropped=dropped_citations,
                served_segments=len(chunk_indices),
            )

        return cited_answer

    except httpx.HTTPError as exc:
        logger.error("LLM HTTP error during grounded generation", error=str(exc))
        return "ABSTAIN"
    except Exception as exc:
        logger.error("Unexpected error during grounded generation", error=str(exc))
        return "ABSTAIN"
