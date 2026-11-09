"""
TRUSTRAG — LangGraph generation node.

Encapsulates all answer-generation logic previously in graph.py's generation_node:
prompt rendering, LLM invocation, format handling, and answer assembly.
"""

from __future__ import annotations

from typing import cast

from app.config import get_model_config
from app.observability.logging import get_logger
from app.rag.agent.graph.state import AgentState
from app.rag.verification.verifier import is_refusal_answer

logger = get_logger(__name__)

__all__ = ["generation_node"]


async def generation_node(state: AgentState) -> AgentState:
    """Generate answer grounded in retrieved context with context management."""
    cfg = get_model_config()
    generation_timeout = cfg.llm_timeout_seconds

    async def _run_generation() -> AgentState:
        import app.rag.agent.graph as _graph_mod

        logger.info("Agent Generation Node starting")

        empty_kb_guard = state.get("diagnosis_failures") == [
            "Knowledge base contains 0 indexed chunks"
        ]
        outage_guard = state.get("diagnosis_type") == "RETRIEVAL_OUTAGE"
        if state.get("answer") and not state.get("chunks") and (empty_kb_guard or outage_guard):
            return state

        if (
            state.get("recovery_strategy") == "regenerate"
            and is_refusal_answer(state.get("answer"))
            and state.get("chunks")
        ):
            logger.info("Skipping futile regeneration (prior refusal on identical chunks)")
            await _graph_mod.add_trace_event(
                state["analysis_id"],
                "generation.skipped",
                {
                    "message": "Model already abstained on these segments — "
                    "skipping repeat generation",
                },
            )
            return state

        await _graph_mod.add_trace_event(
            state["analysis_id"],
            "generation.started",
            {"message": "Reasoning grounded answer from verified context"},
        )

        answer = await _graph_mod.generate_grounded_answer(
            state["current_query"],
            state["chunks"],
            provider=state.get("llm_provider"),
            model=state.get("llm_model"),
        )

        state["answer"] = answer
        return state

    fallback_state: AgentState = cast(
        AgentState,
        {
            **state,
            "answer": "ABSTAIN",
            "verdict_status": "FAIL",
            "diagnosis_type": "GENERATION_ERROR",
            "diagnosis_failures": ["Generation failed due to internal error"],
        },
    )

    from app.rag.agent.graph.build import _execute_with_fallback

    return await _execute_with_fallback(
        state=state,
        node_name="generation",
        operation=_run_generation,
        fallback_state=fallback_state,
        timeout_seconds=generation_timeout,
    )
