"""
Tests for the graph entrypoints (audit B-12).

`build_agent_graph()` (`graph.py:1397-1422`) and `execute_agentic_rag_flow()`
(`graph.py:1428-1554`) are the module's *public* surface — every analysis in the
product goes through the second one — and both were 100% untested. A broken
edge map or a bad initial state would therefore not fail a single test.

These cover the parts that decide behaviour rather than restating the code:
graph topology, the singleton, initial-state construction, the semantic-cache
gates (answer reuse vs. PASS-only store vs. web-search bypass), the async-embed
fallback, and the per-analysis LLM ledger being closed out.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent import graph as graph_mod
from app.agent.graph import build_agent_graph, execute_agentic_rag_flow

KB_ID = "64ee39d09c6292376e191982"
ANALYSIS_ID = "64ee39d09c6292376e1919ab"
USER_ID = "64ee39d09c6292376e191981"

_QVEC = [0.1, 0.2, 0.3]


def _cfg_stub(**overrides) -> MagicMock:
    from app.core.config import get_model_config

    real = get_model_config()
    stub = MagicMock()
    stub.embedding_model = real.embedding_model
    stub.llm_provider = real.llm_provider
    for k, v in overrides.items():
        setattr(stub, k, v)
    return stub


def _embed_model() -> MagicMock:
    emb = MagicMock()
    emb.aembed_query = AsyncMock(return_value=_QVEC)
    emb.embed_query = MagicMock(return_value=_QVEC)
    return emb


# ─── build_agent_graph ───────────────────────────────────────────────────────


def test_graph_has_the_four_expected_nodes():
    """A missing node would raise at compile time in production but silently
    break routing if the name were misspelled in one place only."""
    graph = build_agent_graph()
    assert set(graph.get_graph().nodes) >= {"retrieval", "generation", "verification", "recovery"}


def test_graph_topology_matches_the_documented_pipeline():
    """Pin the whole edge map. The pipeline must start at retrieval (grounding
    before generation), run retrieval -> generation -> verification, and be able
    to loop verification -> recovery -> retrieval for adaptive recovery. Losing
    any one of these changes analysis behaviour without raising.
    """
    g = build_agent_graph().get_graph()
    edges = {(getattr(e, "source", None), getattr(e, "target", None)) for e in g.edges}

    assert set(g.nodes) == {
        "__start__",
        "retrieval",
        "generation",
        "verification",
        "recovery",
        "__end__",
    }
    # Ground first: never generate before retrieving.
    assert ("__start__", "retrieval") in edges, f"pipeline does not start at retrieval: {edges}"
    assert ("retrieval", "generation") in edges, f"retrieval must feed generation: {edges}"
    assert ("generation", "verification") in edges, f"generation must be verified: {edges}"
    # Adaptive recovery: the conditional edge is what makes recovery possible
    # at all; without it every analysis silently becomes single-shot.
    assert ("verification", "__end__") in edges, f"no clean exit from verification: {edges}"
    assert ("verification", "recovery") in edges, f"no recovery branch: {edges}"
    # The loop must close back to retrieval, or recovery is a dead end.
    assert ("recovery", "retrieval") in edges, f"recovery does not loop back: {edges}"


def test_graph_is_a_cached_singleton():
    """Rebuilding per call would recompile the graph on every analysis."""
    with patch.object(graph_mod, "_compiled_graph", None):
        first = build_agent_graph()
        second = build_agent_graph()
    assert first is second


# ─── execute_agentic_rag_flow: initial state ─────────────────────────────────


@pytest.mark.asyncio
async def test_initial_state_is_complete_and_carries_request_args():
    """The graph contract depends on these keys. A missing `chunks` or a None
    `verdict_status` would make a node fail deep in the run, far from the cause."""
    captured: dict = {}

    async def _fake_ainvoke(state):
        captured.update(state)
        return state

    fake_graph = MagicMock()
    fake_graph.ainvoke = _fake_ainvoke

    with (
        patch.object(graph_mod, "build_agent_graph", return_value=fake_graph),
        patch.object(graph_mod, "get_model_config", return_value=_cfg_stub()),
        patch.object(graph_mod, "begin_analysis", return_value=None),
        patch.object(graph_mod, "end_analysis", MagicMock()),
        patch.object(graph_mod, "current_ledger", return_value=None),
        patch("app.core.memory.trim_memory", MagicMock()),
        patch("app.core.semantic_cache.check_semantic_cache", return_value=None),
    ):
        await execute_agentic_rag_flow(
            analysis_id_str=ANALYSIS_ID,
            kb_id_str=KB_ID,
            query="What is the token lifetime?",
            user_id_str=USER_ID,
            llm_provider="ollama",
            llm_model="granite4.2:3b-q4_K_M",
        )

    assert captured["analysis_id"] == ANALYSIS_ID
    assert captured["kb_id"] == KB_ID
    assert captured["user_id"] == USER_ID
    assert captured["query"] == "What is the token lifetime?"
    # current_query must be seeded or the retrieval node starts on None.
    assert captured["current_query"] == "What is the token lifetime?"
    assert captured["chunks"] == []
    assert captured["evidence_ids"] == []
    assert captured["claims"] == []
    assert captured["attempts"] == 0
    # Fail-closed default: a run that never reaches verification must not
    # be able to report success.
    assert captured["verdict_status"] == "FAIL"
    assert captured["cache_hit"] is False
    assert captured["llm_provider"] == "ollama"
    assert captured["llm_model"] == "granite4.2:3b-q4_K_M"


# ─── Semantic cache ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_semantic_cache_hit_seeds_answer_and_marks_cache_hit():
    """On a cache hit generation must be skipped but retrieval/NLI still rerun,
    so the returned state carries a prior answer *and* cache_hit=True."""
    cached = {"answer": "Records are available within 30 days."}
    seen: dict = {}

    async def _fake_ainvoke(state):
        seen.update(state)
        return state

    fake_graph = MagicMock()
    fake_graph.ainvoke = _fake_ainvoke

    with (
        patch.object(graph_mod, "build_agent_graph", return_value=fake_graph),
        patch.object(graph_mod, "get_model_config", return_value=_cfg_stub()),
        patch.object(graph_mod, "begin_analysis", return_value=None),
        patch.object(graph_mod, "end_analysis", MagicMock()),
        patch.object(graph_mod, "current_ledger", return_value=None),
        patch("app.core.memory.trim_memory", MagicMock()),
        patch("app.core.model_registry.get_embedding_model", return_value=_embed_model()),
        patch("app.core.semantic_cache.check_semantic_cache", return_value=cached),
        patch.object(graph_mod, "add_trace_event", AsyncMock()) as trace,
    ):
        await execute_agentic_rag_flow(
            analysis_id_str=ANALYSIS_ID, kb_id_str=KB_ID, query="token lifetime?"
        )

    assert seen["answer"] == cached["answer"]
    assert seen["cache_hit"] is True
    # The hit must be auditable — a cache hit with no trace event is invisible.
    events = [c.args[1] for c in trace.call_args_list]
    assert "cache.hit" in events, f"no cache.hit trace event: {events}"


@pytest.mark.asyncio
async def test_semantic_cache_is_bypassed_when_web_search_is_enabled():
    """Web-grounded answers depend on live results, so reusing a cached answer
    would be wrong regardless of similarity."""
    checked = MagicMock(return_value={"answer": "STALE"})
    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(side_effect=lambda s: s)

    with (
        patch.object(graph_mod, "build_agent_graph", return_value=fake_graph),
        patch.object(graph_mod, "get_model_config", return_value=_cfg_stub()),
        patch.object(graph_mod, "begin_analysis", return_value=None),
        patch.object(graph_mod, "end_analysis", MagicMock()),
        patch.object(graph_mod, "current_ledger", return_value=None),
        patch("app.core.memory.trim_memory", MagicMock()),
        patch("app.core.model_registry.get_embedding_model", return_value=_embed_model()),
        patch("app.core.semantic_cache.check_semantic_cache", checked),
        patch.object(graph_mod, "add_trace_event", AsyncMock()),
    ):
        state = await execute_agentic_rag_flow(
            analysis_id_str=ANALYSIS_ID,
            kb_id_str=KB_ID,
            query="q",
            web_search_enabled=True,
        )

    assert checked.call_count == 0, "cache was consulted for a web-grounded run"
    assert state["cache_hit"] is False
    assert state["answer"] is None


@pytest.mark.asyncio
async def test_semantic_cache_stores_only_passed_non_abstain_answers():
    """A FAIL or ABSTAIN answer must never be cached, or a bad answer becomes
    permanently sticky and is replayed as a 'hit'."""

    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(side_effect=lambda s: s)

    for verdict, answer, expect_store in (
        ("PASS", "Records retained for 30 days.", True),
        ("PASS", "ABSTAIN", False),
        ("FAIL", "Some answer", False),
    ):
        with (
            patch.object(graph_mod, "build_agent_graph", return_value=fake_graph),
            patch.object(graph_mod, "get_model_config", return_value=_cfg_stub()),
            patch.object(graph_mod, "begin_analysis", return_value=None),
            patch.object(graph_mod, "end_analysis", MagicMock()),
            patch.object(graph_mod, "current_ledger", return_value=None),
            patch("app.core.memory.trim_memory", MagicMock()),
            patch("app.core.model_registry.get_embedding_model", return_value=_embed_model()),
            patch("app.core.semantic_cache.check_semantic_cache", MagicMock(return_value=None)),
            patch("app.core.semantic_cache.store_semantic_cache", MagicMock()) as store,
            patch.object(graph_mod, "add_trace_event", AsyncMock()),
        ):
            fake_graph.ainvoke = AsyncMock(
                side_effect=lambda s, v=verdict, a=answer: {
                    **s,
                    "verdict_status": v,
                    "answer": a,
                }
            )
            await execute_agentic_rag_flow(analysis_id_str=ANALYSIS_ID, kb_id_str=KB_ID, query="q")
        assert store.call_count == (1 if expect_store else 0), (
            f"verdict={verdict} answer={answer!r} stored={store.call_count}"
        )


@pytest.mark.asyncio
async def test_async_embed_falls_back_to_sync_on_failure():
    """A provider without native async embedding must still work; the old code
    would have propagated the error and skipped the cache entirely."""
    emb = MagicMock()
    emb.aembed_query = AsyncMock(side_effect=RuntimeError("no async support"))
    emb.embed_query = MagicMock(return_value=_QVEC)

    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(side_effect=lambda s: s)

    with (
        patch.object(graph_mod, "build_agent_graph", return_value=fake_graph),
        patch.object(graph_mod, "get_model_config", return_value=_cfg_stub()),
        patch.object(graph_mod, "begin_analysis", return_value=None),
        patch.object(graph_mod, "end_analysis", MagicMock()),
        patch.object(graph_mod, "current_ledger", return_value=None),
        patch("app.core.memory.trim_memory", MagicMock()),
        patch("app.core.model_registry.get_embedding_model", return_value=emb),
        patch(
            "app.core.semantic_cache.check_semantic_cache",
            MagicMock(return_value={"answer": "cached"}),
        ),
        patch.object(graph_mod, "add_trace_event", AsyncMock()),
    ):
        state = await execute_agentic_rag_flow(
            analysis_id_str=ANALYSIS_ID, kb_id_str=KB_ID, query="q"
        )

    assert emb.embed_query.called, "sync fallback never ran"
    assert state["cache_hit"] is True


@pytest.mark.asyncio
async def test_cache_failure_never_breaks_the_run():
    """A broken cache must degrade to a normal analysis, not fail the request."""
    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(side_effect=lambda s: {**s, "verdict_status": "PASS"})

    with (
        patch.object(graph_mod, "build_agent_graph", return_value=fake_graph),
        patch.object(graph_mod, "get_model_config", return_value=_cfg_stub()),
        patch.object(graph_mod, "begin_analysis", return_value=None),
        patch.object(graph_mod, "end_analysis", MagicMock()),
        patch.object(graph_mod, "current_ledger", return_value=None),
        patch("app.core.memory.trim_memory", MagicMock()),
        patch("app.core.model_registry.get_embedding_model", return_value=_embed_model()),
        patch(
            "app.core.semantic_cache.check_semantic_cache",
            MagicMock(side_effect=RuntimeError("redis down")),
        ),
        patch.object(graph_mod, "add_trace_event", AsyncMock()),
    ):
        state = await execute_agentic_rag_flow(
            analysis_id_str=ANALYSIS_ID, kb_id_str=KB_ID, query="q"
        )

    assert state["verdict_status"] == "PASS", "cache failure aborted the analysis"


# ─── LLM ledger lifecycle ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ledger_is_closed_even_when_the_graph_raises():
    """The ledger is a ContextVar budget. If it is not released on the error
    path, the *next* analysis in the same task inherits a spent budget and
    fails with RECOVERY_BUDGET_EXHAUSTED."""
    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph blew up"))

    with (
        patch.object(graph_mod, "build_agent_graph", return_value=fake_graph),
        patch.object(graph_mod, "get_model_config", return_value=_cfg_stub()),
        patch.object(graph_mod, "begin_analysis", return_value="tok"),
        patch.object(graph_mod, "end_analysis", MagicMock()) as end,
        patch.object(graph_mod, "current_ledger", return_value=None),
        patch("app.core.memory.trim_memory", MagicMock()),
    ):
        with pytest.raises(RuntimeError, match="graph blew up"):
            await execute_agentic_rag_flow(analysis_id_str=ANALYSIS_ID, kb_id_str=KB_ID, query="q")

    end.assert_called_once_with("tok")


# ─── Analysis-wide latency budget (audit L-1) ────────────────────────────────


def test_should_recover_ends_when_analysis_deadline_spent():
    """A spent wall-clock budget must end the loop, not start another round."""
    from app.agent.graph import should_recover

    state = {
        "verdict_status": "FAIL",
        "attempts": 0,
        "analysis_deadline_monotonic": time.monotonic() - 1.0,  # already past
        "diagnosis_type": "LOW_COVERAGE",
        "diagnosis_failures": [],
    }
    assert should_recover(state) == "end"
    # The run must not be reported as a clean pass just because it stopped.
    assert state["diagnosis_type"] == "RECOVERY_BUDGET_EXHAUSTED"
    assert state["diagnosis_failures"]


def test_should_recover_continues_while_budget_remains():
    from app.agent.graph import should_recover

    state = {
        "verdict_status": "FAIL",
        "attempts": 0,
        "analysis_deadline_monotonic": time.monotonic() + 600.0,
        "diagnosis_type": "LOW_COVERAGE",
        "diagnosis_failures": [],
    }
    assert should_recover(state) == "recover"


def test_should_recover_unbounded_when_no_deadline_configured():
    """max_analysis_seconds: 0 disables the bound entirely."""
    from app.agent.graph import should_recover

    state = {
        "verdict_status": "FAIL",
        "attempts": 0,
        "analysis_deadline_monotonic": None,
        "diagnosis_type": "LOW_COVERAGE",
        "diagnosis_failures": [],
    }
    assert should_recover(state) == "recover"


def test_analysis_deadline_is_set_from_config():
    """A positive budget produces a real monotonic deadline."""
    from app.agent.graph import _analysis_deadline

    cfg = _cfg_stub(max_analysis_seconds=120)
    deadline = _analysis_deadline(cfg)
    assert deadline is not None
    assert deadline > time.monotonic()
    assert _analysis_deadline(_cfg_stub(max_analysis_seconds=0)) is None


def test_analysis_deadline_survives_garbage_config():
    """A malformed budget disables the bound instead of failing the analysis."""
    from app.agent.graph import _analysis_deadline

    assert _analysis_deadline(_cfg_stub(max_analysis_seconds="not-a-number")) is None
    assert _analysis_deadline(_cfg_stub(max_analysis_seconds=None)) is None
