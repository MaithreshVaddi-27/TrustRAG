"""
TRUSTRAG — Agentic RAG agent package.

This package replaces the flat ``graph.py`` module. It re-exports the public
surface so existing imports keep working:

- ``app.rag.agent.graph`` -> ``build_agent_graph``, ``execute_agentic_rag_flow``,
  ``should_recover``, ``_execute_with_fallback``, ``_analysis_deadline``,
  ``_compiled_graph``, ``add_trace_event``, etc.
- ``app.rag.agent.graph.state`` -> ``AgentState``, ``initial_state``,
  ``SELF_HEAL_BATCH_SIZE``
- ``app.rag.agent.graph.nodes`` -> node functions
"""

from __future__ import annotations

from app.config import get_model_config
from app.core.system import memory
from app.llm.llm_ledger import begin_analysis, current_ledger, end_analysis, llm_budget_exhausted
from app.llm.model_registry import get_embedding_model, get_verification_model
from app.observability.logging import get_logger
from app.persistence.mongodb import get_collection
from app.rag.agent.graph.build import _execute_with_fallback, build_graph
from app.rag.agent.graph.coordinator import _analysis_deadline, execute_agentic_rag_flow
from app.rag.agent.graph.edges import should_end, should_recover, should_verify
from app.rag.agent.graph.nodes.generation import generation_node
from app.rag.agent.graph.nodes.recovery import (
    _is_effectively_identical_query,
    _normalize_query_tokens,
    _sanitize_rewritten_query,
    _select_recovery_strategy,
    _terminal_llm_failure,
    recovery_node,
)
from app.rag.agent.graph.nodes.retrieval import retrieval_node
from app.rag.agent.graph.nodes.verification import verification_node
from app.rag.agent.graph.state import SELF_HEAL_BATCH_SIZE, AgentState, initial_state
from app.rag.generation.generator import generate_grounded_answer
from app.rag.retrieval.reranker import rerank_candidate_chunks
from app.rag.retrieval.retriever import retrieve_hybrid_chunks
from app.rag.verification.integrity import audit_evidence_integrity
from app.rag.verification.verifier import execute_claim_verification  # noqa: F401
from app.security.exceptions import RetrievalOutageError
from app.services.analysis_service import add_trace_event

# Module-level compiled graph singleton — built once, reused per request.
_compiled_graph: object = None

logger = get_logger(__name__)

__all__ = [
    "SELF_HEAL_BATCH_SIZE",
    "AgentState",
    "RetrievalOutageError",
    "_analysis_deadline",
    "_compiled_graph",
    "_execute_with_fallback",
    "_is_effectively_identical_query",
    "_normalize_query_tokens",
    "_sanitize_rewritten_query",
    "_select_recovery_strategy",
    "_terminal_llm_failure",
    "add_trace_event",
    "audit_evidence_integrity",
    "begin_analysis",
    "build_agent_graph",
    "current_ledger",
    "end_analysis",
    "execute_agentic_rag_flow",
    "generate_grounded_answer",
    "generation_node",
    "get_collection",
    "get_embedding_model",
    "get_model_config",
    "get_verification_model",
    "initial_state",
    "llm_budget_exhausted",
    "memory",
    "recovery_node",
    "rerank_candidate_chunks",
    "retrieval_node",
    "retrieve_hybrid_chunks",
    "should_end",
    "should_recover",
    "should_verify",
    "verification_node",
]


def build_agent_graph():
    """Assemble and compile LangGraph State Graph workflow (cached singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph
