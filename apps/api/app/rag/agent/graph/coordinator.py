"""
TRUSTRAG — Agentic RAG coordinator.

High-level entry point previously exposed as ``execute_agentic_rag_flow`` from
graph.py. Wraps graph building, state initialization, execution, and
deadline/outage handling so callers stay thin.
"""

from __future__ import annotations

import asyncio
import time
from typing import cast

import app.rag.agent.graph as _graph_mod
from app.observability.logging import get_logger
from app.core.system import memory
from app.rag.agent.graph.build import build_graph
from app.rag.agent.graph.state import AgentState, initial_state

logger = get_logger(__name__)

__all__ = [
    "_analysis_deadline",
    "execute_agentic_rag_flow",
]


def _analysis_deadline(cfg) -> float | None:
    """Absolute monotonic deadline for this run, or None when unbounded."""
    try:
        budget = int(getattr(cfg, "max_analysis_seconds", 0) or 0)
    except (TypeError, ValueError):
        return None
    return (time.monotonic() + budget) if budget > 0 else None


async def execute_agentic_rag_flow(
    *,
    analysis_id_str: str,
    kb_id_str: str,
    query: str,
    user_id_str: str | None = None,
    web_search_enabled: bool = False,
    web_search_provider: str = "both",
    llm_provider: str | None = None,
    llm_model: str | None = None,
    analysis_deadline_monotonic: float | None = None,
) -> AgentState:
    """Compile and execute the full agent graph pipeline."""
    # Import lazily to avoid a circular import: `graph/__init__.py` imports
    # this module's names at module level.
    from app.rag.agent.graph import build_agent_graph

    graph = build_agent_graph()
    cfg = _graph_mod.get_model_config()

    if analysis_deadline_monotonic is None:
        analysis_deadline_monotonic = _analysis_deadline(cfg)

    state = initial_state(
        analysis_id_str=analysis_id_str,
        kb_id_str=kb_id_str,
        query=query,
        user_id_str=user_id_str,
        web_search_enabled=web_search_enabled,
        web_search_provider=web_search_provider,
        llm_provider=llm_provider,
        llm_model=llm_model,
        analysis_deadline_monotonic=analysis_deadline_monotonic,
    )

    logger.info("Executing Agentic RAG Flow graph", analysis_id=analysis_id_str)

    # Open a per-analysis LLM ledger so every provider call made below is
    # counted and bounded (audit B-4). ContextVar-scoped, so concurrent
    # analyses do not share a budget.
    ledger_token = _graph_mod.begin_analysis()
    analysis_started = time.monotonic()
    try:
        final_state = await graph.ainvoke(state)

        # Record real wall-clock so the trace can attribute latency, and warn
        # when the deadline cut the run short (audit L-1).
        elapsed_ms = int((time.monotonic() - analysis_started) * 1000)
        final_state["analysis_elapsed_ms"] = elapsed_ms
        try:
            budget = int(getattr(cfg, "max_analysis_seconds", 0) or 0)
        except (TypeError, ValueError):
            budget = 0
        if budget and elapsed_ms > budget * 1000:
            logger.warning(
                "Analysis exceeded its latency budget",
                analysis_id=analysis_id_str,
                elapsed_ms=elapsed_ms,
                budget_ms=budget * 1000,
            )

        return cast(AgentState, final_state)
    finally:
        # Close out the per-analysis LLM ledger before releasing memory.
        ledger = _graph_mod.current_ledger()
        if ledger is not None:
            logger.info(
                "LLM usage for analysis",
                analysis_id=analysis_id_str,
                calls=ledger.calls,
                input_tokens=ledger.input_tokens,
                output_tokens=ledger.output_tokens,
                by_model=ledger.by_model,
            )
        _graph_mod.end_analysis(ledger_token)
        await asyncio.to_thread(memory.trim_memory)
