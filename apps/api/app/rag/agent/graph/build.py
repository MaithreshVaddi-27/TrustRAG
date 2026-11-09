"""
TRUSTRAG — LangGraph builder.

Assembles the Agentic RAG workflow graph from its nodes and edges.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any, cast

from langgraph.graph import StateGraph

import app.rag.agent.graph as _graph_mod
from app.observability.logging import get_logger
from app.llm.llm_ledger import llm_budget_exhausted
from app.rag.agent.graph.edges import should_end, should_recover
from app.rag.agent.graph.nodes.generation import generation_node
from app.rag.agent.graph.nodes.recovery import recovery_node
from app.rag.agent.graph.nodes.retrieval import retrieval_node
from app.rag.agent.graph.nodes.verification import verification_node
from app.rag.agent.graph.state import AgentState

logger = get_logger(__name__)

__all__ = ["_execute_with_fallback", "build_graph"]


async def _execute_with_fallback(
    state: AgentState,
    node_name: str,
    operation: Callable[[], Any],
    fallback_state: AgentState | None = None,
    timeout_seconds: int | None = None,
) -> AgentState:
    """
    Execute a node operation with standardized error handling and fallback.
    """
    # Budget guard: if cloud cap is exhausted, don't start another paid call
    if _graph_mod.llm_budget_exhausted():
        state["verdict_status"] = "FAIL"
        state.setdefault("node_errors", []).append(
            {"error_type": "RECOVERY_BUDGET_EXHAUSTED", "node": node_name}
        )
        state["diagnosis_type"] = "RECOVERY_BUDGET_EXHAUSTED"
        await _graph_mod.add_trace_event(
            state["analysis_id"],
            f"{node_name}.skipped_budget_exhausted",
            {"message": f"{node_name} skipped — LLM call budget exhausted"},
        )
        return state

    started_at = time.monotonic()
    await _graph_mod.add_trace_event(
        state["analysis_id"],
        f"{node_name}.started",
        {"message": f"Starting {node_name} node"},
    )

    try:
        if timeout_seconds:
            result = await asyncio.wait_for(operation(), timeout=timeout_seconds)
        else:
            result = await operation()

        await _graph_mod.add_trace_event(
            state["analysis_id"],
            f"{node_name}.completed",
            {
                "message": f"{node_name} completed successfully",
                "latency_ms": int((time.monotonic() - started_at) * 1000),
            },
        )
        return cast(AgentState, result)

    except Exception as exc:
        logger.warning(f"{node_name} node failed", error=str(exc))
        if fallback_state is not None:
            return fallback_state
        state["verdict_status"] = "FAIL"
        error_type = type(exc).__name__
        # Detect dead credentials (401/403) as terminal outage
        if getattr(exc, "status_code", None) in (401, 403):
            error_type = "LLM_UNAVAILABLE"
            state["diagnosis_type"] = "LLM_UNAVAILABLE"
            state["reliability_score"] = 0.0
            state["answer"] = (
                "The language model provider is currently unavailable, "
                "so this analysis could not be completed."
            )
            # Force graph termination by exhausting recovery attempts
            cfg = _graph_mod.get_model_config()
            state["attempts"] = cfg.max_recovery_attempts
        state.setdefault("node_errors", []).append(
            {"error_type": error_type, "node": node_name, "message": str(exc)}
        )
        return state


def build_graph() -> StateGraph:
    """Build the Agentic RAG StateGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("recovery", recovery_node)

    workflow.add_edge("retrieval", "generation")
    workflow.add_edge("generation", "verification")
    workflow.add_conditional_edges(
        "verification", should_recover, {"recover": "recovery", "end": "__end__"}
    )
    workflow.add_conditional_edges(
        "recovery", should_end, {"retrieve": "retrieval", "end": "__end__"}
    )

    workflow.set_entry_point("retrieval")
    return workflow
