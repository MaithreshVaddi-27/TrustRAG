"""
TRUSTRAG — Analysis service: execution pipeline.

Background RAG pipeline (``run_analysis_pipeline``) and analysis-run entry
point (``create_analysis``). Extracted from ``analysis_service.py`` during the
services/ restructure.

Names that tests patch via ``app.services.analysis_service.X`` (e.g.
``get_collection``, ``get_kb``, ``get_model_config``, ``add_trace_event``,
``serialize_analysis``) are resolved through ``_svc_mod`` (a lazy reference
to the analysis_service shim) so monkeypatch targets take effect inside this
module at call time.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Mapping
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi import BackgroundTasks

from app.api.v1.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    ClaimResponse,
    DiagnosisSummary,
    EvidenceResponse,
    ReliabilitySummary,
    TraceEventResponse,
)
from app.config.settings import get_settings
from app.observability.logging import get_logger
from app.observability.metrics import (
    estimate_tokens,
    record_analysis_completed,
    record_analysis_created,
    record_budget_rejection,
    record_tokens_estimated,
)
from app.security.exceptions import AuthorizationError, InputValidationError, NotFoundError
from app.core.system import memory as memory_mod
from app.persistence.mongodb import Collections
from app.llm import local_llm as local_llm_mod
from app.rag.generation.generator import strip_citation_markers
from app.rag.verification.verdict import (
    ReliabilityStatus,
    Thresholds,
    VerdictResult,
    verdict_from_state,
)
from app.services.claims_evidence import list_analysis_claims, list_analysis_evidence
from app.services.degenerate import _UNVERIFIED_ANSWER, _looks_like_scaffold_echo
from app.services.sse import (
    _publish_analysis_event,
    _subscribe_to_analysis,
    _unsubscribe_from_analysis,
)

logger = get_logger(__name__)

# Lazy reference to the analysis_service shim (set at module bottom). Used to
# resolve names tests patch via app.services.analysis_service.X at call time.
_svc_mod = None


def _ensure_svc():
    global _svc_mod
    if _svc_mod is None:
        import app.services.analysis_service as _m

        _svc_mod = _m
    return _svc_mod


def _get_collection(name):
    return _ensure_svc().get_collection(name)


def _get_kb(kb_id, user_id):
    return _ensure_svc().get_kb(kb_id, user_id)


def _get_model_config():
    return _ensure_svc().get_model_config()


# ─── Grounding gate ──────────────────────────────────────────────────────────


def _presentable_answer(
    answer: str | None,
    verdict_result: VerdictResult,
) -> str | None:
    """Return answer text that is safe to show a user, else None.

    GROUNDING GATE (audit G-1): the verdict engine already decides how much of
    a generated answer the evidence supports. This function is the single place
    where that decision is applied to what the user actually reads.

    Only ``TRUSTED`` verdicts may present the model's own text. Everything else
    is replaced with the abstention message, so the reliability badge can never
    contradict the prose beside it.
    """
    if verdict_result.reliability_status == ReliabilityStatus.TRUSTED:
        return answer
    return _UNVERIFIED_ANSWER


def _record_completed(status: str) -> None:
    """Record terminal analysis status; metrics must never break the pipeline."""
    try:
        record_analysis_completed(status)
    except Exception:  # noqa: S110 - telemetry is best-effort
        pass


# ─── Serialization helpers ───────────────────────────────────────────────────


def serialize_analysis(doc: Mapping[str, Any]) -> AnalysisResponse:
    """Helper to convert MongoDB Analysis document to Pydantic AnalysisResponse."""
    rel = doc.get("reliability", {})
    diag = doc.get("diagnosis", {})
    created_at = doc.get("created_at") or doc.get("started_at") or datetime.now(UTC)
    return AnalysisResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        knowledge_base_id=str(doc["knowledge_base_id"]),
        query=doc.get("query", ""),
        status=doc.get("status", "pending"),
        answer=doc.get("answer"),
        answer_cited=doc.get("answer_cited"),
        answer_withheld=doc.get("answer_withheld"),
        reliability=ReliabilitySummary(
            score=rel.get("score"),
            status=rel.get("status", "PENDING"),
        ),
        diagnosis=DiagnosisSummary(
            type=diag.get("type"),
            failures=diag.get("failures", []),
        ),
        created_at=created_at,
        config_snapshot=doc.get("config_snapshot"),
        web_search_enabled=bool(doc.get("web_search_enabled", False)),
        web_search_provider=doc.get("web_search_provider"),
        llm_provider=doc.get("llm_provider"),
        llm_model=doc.get("llm_model"),
        embedding_provider="onnx",
        embedding_model=doc.get("embedding_model"),
    )


def serialize_claim(doc: Mapping[str, Any]) -> ClaimResponse:
    """Helper to convert MongoDB Claim document to Pydantic ClaimResponse."""
    created_at = doc.get("created_at") or datetime.now(UTC)
    return ClaimResponse(
        id=str(doc["_id"]),
        analysis_id=str(doc["analysis_id"]),
        text=doc.get("text", ""),
        subject=doc.get("subject"),
        predicate=doc.get("predicate"),
        object=doc.get("object"),
        state=doc.get("state", "UNKNOWN"),
        explanation=doc.get("explanation"),
        evidence_ids=[str(eid) for eid in doc.get("evidence_ids", [])],
        created_at=created_at,
    )


def serialize_evidence(doc: Mapping[str, Any]) -> EvidenceResponse:
    """Helper to convert MongoDB Evidence document to Pydantic EvidenceResponse."""
    created_at = doc.get("created_at") or datetime.now(UTC)
    return EvidenceResponse(
        id=str(doc["_id"]),
        analysis_id=str(doc["analysis_id"]),
        text=doc.get("text", ""),
        document_id=str(doc["document_id"]) if doc.get("document_id") else "",
        filename=doc.get("filename"),
        url=doc.get("url"),
        retrieval_score=doc.get("retrieval_score"),
        fusion_score=doc.get("fusion_score"),
        rerank_score=doc.get("rerank_score"),
        method=doc.get("method"),
        integrity_status=doc.get("integrity_status"),
        effective_from=doc.get("effective_from"),
        effective_until=doc.get("effective_until"),
        created_at=created_at,
    )


def serialize_trace(doc: Mapping[str, Any]) -> TraceEventResponse:
    """Helper to convert MongoDB TraceEvent document to Pydantic TraceEventResponse."""
    created_at = doc.get("created_at") or datetime.now(UTC)
    return TraceEventResponse(
        id=str(doc["_id"]),
        analysis_id=str(doc["analysis_id"]),
        event=doc.get("event", ""),
        timestamp=created_at,
        data=doc.get("data", {}),
    )


# ─── Create analysis ─────────────────────────────────────────────────────────


async def create_analysis(
    schema: AnalysisCreate, user_id_str: str, background_tasks: BackgroundTasks
) -> AnalysisResponse:
    """
    Initiate an analysis run.
    Verifies that target KB exists and is owned by the user.
    """
    svc = _ensure_svc()

    # Verify owner & existence of KB
    kb = await _get_kb(schema.knowledge_base_id, user_id_str)

    cfg = _get_model_config()

    # EMBEDDING-SPACE GUARD 2026-09-06: a KB's vectors live in exactly one
    # embedding space (pinned at first ingest). Querying with another model
    # returns plausible-looking garbage → verification fails → recovery spiral
    # (heat + minutes of wasted local inference). Fail fast with a message
    # that tells the user exactly how to fix it.
    if kb.embedding_model:
        effective_model = cfg.embedding_model
        # Model ids are case-sensitive upstream, but a casing/whitespace-only
        # difference is never a different embedding space — normalize the compare.
        if effective_model.strip().lower() != kb.embedding_model.strip().lower():
            raise InputValidationError(
                f"Embedding mismatch: knowledge base '{kb.name}' was indexed "
                f"with '{kb.embedding_model}' ({kb.embedding_dim or '?'}d), "
                f"but the server runs '{effective_model}'. "
                f"Re-upload the documents to re-index with the current model.",
                detail=f"kb_pin={kb.embedding_model} requested={effective_model}",
            )
        # Dimension pin: same model name at a different output width (e.g. a
        # changed EMBEDDING_DIM Matryoshka override) is a different space.
        if kb.embedding_dim and cfg.embedding_dimensionality != kb.embedding_dim:
            raise InputValidationError(
                f"Embedding dimension mismatch: knowledge base '{kb.name}' was indexed "
                f"at {kb.embedding_dim}d, but the server is configured for "
                f"{cfg.embedding_dimensionality}d. Re-upload the documents to re-index.",
                detail=f"kb_dim={kb.embedding_dim} server_dim={cfg.embedding_dimensionality}",
            )

    # Pre-request token budget enforcement (zero LLM calls).
    # Estimate query cost up front; reject absurd inputs with 422 instead of
    # burning embedding/retrieval/generation on a request that cannot fit.
    query_text = schema.query.strip()
    query_tokens = estimate_tokens(query_text)
    record_tokens_estimated(query_tokens)
    # Pre-request query guard. NOTE (audit B-4): this used to compare the query
    # against `cost_controls.max_input_tokens` (100000), which can never be
    # exceeded because pydantic already caps the query at 2000 characters
    # (~500 tokens) — dead code whose comment claimed to be a per-call limit.
    # The per-analysis spend ceiling is now `max_llm_calls_per_analysis`,
    # enforced by the LLM ledger; this check is a separate, query-scoped bound.
    cfg2 = _get_model_config()
    if cfg2.pre_request_budget_enforcement and query_tokens > cfg2.max_query_tokens:
        record_budget_rejection("max_query_tokens")
        raise InputValidationError(
            f"Query too large: estimated {query_tokens} tokens exceeds the "
            f"per-request query budget of {cfg2.max_query_tokens} tokens. "
            "Shorten the query and try again.",
            detail=f"estimated_tokens={query_tokens} budget={cfg2.max_query_tokens}",
        )

    # Resolve EFFECTIVE engine now: the persisted doc (and every downstream
    # consumer: HUD chips, trace, export dossier) must name what will actually
    # run — not the raw nullable request fields (previously stored "" → the UI
    # rendered "DEFAULT" and audits couldn't tell granite from EXAONE).
    # Normalize the provider to its canonical spelling: the request validator
    # already does this, so persisting the raw value stored "google_genai" /
    # "llamacpp" while the allowlist check ran against "gemini" /
    # "llama_cpp" (audit B-15/B-18).
    from app.config import normalize_provider

    effective_llm_provider = normalize_provider(schema.llm_provider or cfg.llm_provider or "")
    effective_llm_model = schema.llm_model or cfg.llm_model_for(effective_llm_provider)
    effective_embedding_model = cfg.embedding_model

    # LOCAL-LLM PREFLIGHT: when the effective provider is a local inference
    # server, verify it answers in ~3s. Without this, a stopped ollama /
    # llama-server burns minutes of 120s timeouts across ~9 sequential calls
    # before the pipeline abstains or fails. Raises LLMUnavailableError → 503
    # with the exact start command so the UI can alert instead of hanging.
    if effective_llm_provider in ("ollama", "llama_cpp", "llamacpp", "mlx"):
        settings = get_settings()
        if effective_llm_provider == "ollama":
            llm_base_url = settings.ollama_base_url
            probe_provider = "ollama"
        elif effective_llm_provider == "mlx":
            llm_base_url = settings.mlx_base_url
            probe_provider = "mlx"
        else:
            llm_base_url = settings.llamacpp_base_url
            probe_provider = "llama_cpp"
        await local_llm_mod.probe_local_llm_server(probe_provider, llm_base_url)
    elif effective_llm_provider in ("gemini"):
        await local_llm_mod.probe_cloud_llm(effective_llm_provider, effective_llm_model)
    analysis_doc = {
        "user_id": ObjectId(user_id_str),
        "knowledge_base_id": ObjectId(schema.knowledge_base_id),
        "query": schema.query.strip(),
        "estimated_input_tokens": query_tokens,
        "status": "pending",
        "answer": None,
        "reliability": {"score": None, "status": "PENDING"},
        "diagnosis": {"type": None, "failures": []},
        "created_at": datetime.now(UTC),
        "config_snapshot": cfg.as_snapshot(),
        "web_search_enabled": schema.enable_web_search,
        "web_search_provider": schema.web_search_provider,
        "llm_provider": effective_llm_provider,
        "llm_model": effective_llm_model,
        "embedding_provider": "onnx",
        "embedding_model": effective_embedding_model,
    }

    result = await _get_collection(Collections.ANALYSES).insert_one(analysis_doc)
    analysis_doc["_id"] = result.inserted_id
    record_analysis_created()

    # Emit initial started trace event
    await svc.add_trace_event(
        analysis_id_str=str(result.inserted_id),
        event="analysis.started",
        data={
            "message": "Analysis run initiated",
            "provider": effective_llm_provider,
            "model": effective_llm_model,
            "embedding_provider": "onnx",
            "embedding_model": effective_embedding_model,
        },
    )

    # Queue background RAG execution pipeline (resolved via the shim so
    # tests that patch app.services.analysis_service.run_analysis_pipeline
    # take effect here).
    background_tasks.add_task(
        _svc_mod.run_analysis_pipeline,
        analysis_id_str=str(result.inserted_id),
        kb_id_str=schema.knowledge_base_id,
        query=schema.query.strip(),
        user_id_str=user_id_str,
        web_search_enabled=schema.enable_web_search,
        web_search_provider=schema.web_search_provider,
        llm_provider=effective_llm_provider,
        llm_model=effective_llm_model,
    )

    return svc.serialize_analysis(analysis_doc)


# ─── Reads ───────────────────────────────────────────────────────────────────


async def get_analysis(analysis_id_str: str, user_id_str: str) -> AnalysisResponse:
    """Get analysis run detail, enforcing ownership verification."""
    svc = _ensure_svc()
    try:
        analysis_id = ObjectId(analysis_id_str)
    except Exception as exc:
        raise NotFoundError("Analysis not found") from exc

    analysis = await _get_collection(Collections.ANALYSES).find_one({"_id": analysis_id})
    if not analysis:
        raise NotFoundError("Analysis not found")

    if str(analysis["user_id"]) != user_id_str:
        raise AuthorizationError("Access denied", detail="You do not own this analysis record")

    return svc.serialize_analysis(analysis)


async def list_analyses(user_id_str: str, limit: int = 50, skip: int = 0) -> list[AnalysisResponse]:
    """List analysis runs for the authenticated user with pagination."""
    analyses_coll = _get_collection(Collections.ANALYSES)
    results = []
    cursor = (
        analyses_coll.find({"user_id": ObjectId(user_id_str)})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(limit, 200))
    )
    async for a in cursor:
        results.append(serialize_analysis(a))
    return results


async def _fetch_claims(analysis_id_str: str) -> list[dict[str, Any]]:
    """Fetch claims for a single analysis (internal, no ownership check)."""
    from app.services.claims_evidence import list_analysis_claims

    return await list_analysis_claims(analysis_id_str)


async def _fetch_evidence(analysis_id_str: str) -> list[dict[str, Any]]:
    """Fetch evidence for a single analysis (internal, no ownership check)."""
    from app.services.claims_evidence import list_analysis_evidence

    return await list_analysis_evidence(analysis_id_str)


async def _fetch_trace(analysis_id_str: str) -> list[dict[str, Any]]:
    """Fetch trace events for a single analysis."""
    trace_coll = _get_collection(Collections.TRACE_EVENTS)
    cursor = trace_coll.find({"analysis_id": ObjectId(analysis_id_str)}).sort("timestamp", 1)
    results = []
    async for t in cursor:
        results.append(serialize_trace(t))
    return results


async def get_analysis_claims(analysis_id_str: str, user_id_str: str) -> list[ClaimResponse]:
    """Get claims for an analysis, enforcing ownership verification."""
    svc = _ensure_svc()
    await svc.get_analysis(analysis_id_str, user_id_str)
    return [serialize_claim(c) for c in await list_analysis_claims(analysis_id_str)]


async def get_analysis_evidence(analysis_id_str: str, user_id_str: str) -> list[EvidenceResponse]:
    """Get evidence for an analysis, enforcing ownership verification."""
    svc = _ensure_svc()
    await svc.get_analysis(analysis_id_str, user_id_str)
    return [serialize_evidence(e) for e in await list_analysis_evidence(analysis_id_str)]


async def get_analysis_trace(analysis_id_str: str, user_id_str: str) -> list[TraceEventResponse]:
    """Get trace events for an analysis, enforcing ownership verification."""
    svc = _ensure_svc()
    await svc.get_analysis(analysis_id_str, user_id_str)
    trace_coll = _get_collection(Collections.TRACE_EVENTS)
    cursor = trace_coll.find({"analysis_id": ObjectId(analysis_id_str)}).sort("timestamp", 1)
    results = []
    async for t in cursor:
        results.append(serialize_trace(t))
    return results


async def get_analysis_detail(analysis_id_str: str, user_id_str: str) -> dict[str, Any]:
    """Fetch analysis + claims + evidence + trace in one round trip.

    Single ownership check, then the three collections fan out concurrently.
    Replaces four sequential HTTP calls from the workbench finalize path.
    """
    svc = _ensure_svc()
    analysis = await svc.get_analysis(analysis_id_str, user_id_str)
    claims, evidence, trace = await asyncio.gather(
        _fetch_claims(analysis_id_str),
        _fetch_evidence(analysis_id_str),
        _fetch_trace(analysis_id_str),
    )
    return {
        "analysis": analysis,
        "claims": claims,
        "evidence": evidence,
        "trace": trace,
    }


# ─── Trace events & SSE ──────────────────────────────────────────────────────


async def add_trace_event(
    analysis_id_str: str, event: str, data: dict[str, Any] | None = None
) -> TraceEventResponse:
    """Insert a new trace event into MongoDB and publish to SSE subscribers."""
    svc = _ensure_svc()
    if data is None:
        data = {}
    trace_coll = _get_collection(Collections.TRACE_EVENTS)
    evt_doc = {
        "analysis_id": ObjectId(analysis_id_str),
        "event": event,
        "timestamp": datetime.now(UTC),
        "data": data,
    }
    await trace_coll.insert_one(evt_doc)

    # Publish to in-process SSE subscribers (replaces MongoDB polling)
    await _publish_analysis_event(analysis_id_str, {"event": event, "data": data})

    return svc.serialize_trace(evt_doc)


async def sse_event_generator(
    analysis_id_str: str, user_id_str: str
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Generator yielding trace events as Server-Sent Events (SSE) via in-process pub/sub.

    Frontend relies on this for real-time trace logging.
    If the connection drops, trace history is fully stored in MongoDB
    and retrieved via the get_analysis_trace function.
    """
    svc = _ensure_svc()
    # Verify access permission first
    await svc.get_analysis(analysis_id_str, user_id_str)

    # Subscribe to real-time events
    queue = await _subscribe_to_analysis(analysis_id_str)

    try:
        no_event_ticks = 0
        terminal_events = {
            "analysis.completed",
            "analysis.abstained",
            "analysis.failed",
            # The pipeline has already exited when it emits an outage, so nothing
            # further will ever be published. Without this the generator spins on
            # heartbeats until no_event_ticks hits 360 (~6 minutes), holding the
            # subscriber queue for an analysis that is definitively over.
            "analysis.outage",
        }
        # Local 3B pipelines can run 3-5 min with recovery; keep the stream
        # open past the worst case (frontend also runs fallback polling).
        while no_event_ticks < 360:
            try:
                # Wait for event with timeout (1 second)
                event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                no_event_ticks = 0
                yield event_data

                # Terminal event checks
                if event_data["event"] in terminal_events:
                    return
            except TimeoutError:
                no_event_ticks += 1
                # Periodic heartbeat ping keeps reverse proxies (Render/Cloudflare) alive
                if no_event_ticks % 3 == 0:
                    yield {
                        "event": "ping",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "data": {},
                    }
    finally:
        await _unsubscribe_from_analysis(analysis_id_str, queue)


# ─── Pipeline execution ──────────────────────────────────────────────────────


async def run_analysis_pipeline(
    analysis_id_str: str,
    kb_id_str: str,
    query: str,
    user_id_str: str | None = None,
    web_search_enabled: bool = False,
    web_search_provider: str = "both",
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> None:
    """
    Execute RAG retrieval and generation pipeline in the background.

    Phases:
      1. Retrieve segments using hybrid (dense + sparse) matching
      2. Ground with live MCP web search (Tavily / DuckDuckGo) if enabled
      3. Apply temporal filters using parent document dates
      4. Rerank top matches using CrossEncoder
      5. Persist segments as Evidence models in MongoDB
      6. Generate answer using active LLM, grounded in retrieved context
      7. Decompose claims & verify through NLI
      8. Update status and save answer in MongoDB
    """
    svc = _ensure_svc()
    analysis_id = ObjectId(analysis_id_str)
    analyses_coll = _get_collection(Collections.ANALYSES)

    try:
        # Mark status as processing
        await analyses_coll.update_one(
            {"_id": analysis_id},
            {"$set": {"status": "processing", "updated_at": datetime.now(UTC)}},
        )

        # 1. Execute Agentic LangGraph workflow (retrieval, NLI verify, and recovery loop)
        from app.rag.agent.graph import execute_agentic_rag_flow

        final_state = await execute_agentic_rag_flow(
            analysis_id_str=analysis_id_str,
            kb_id_str=kb_id_str,
            query=query,
            user_id_str=user_id_str,
            web_search_enabled=web_search_enabled,
            web_search_provider=web_search_provider,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )

        if final_state.get("diagnosis_type") == "RETRIEVAL_OUTAGE":
            # Retrieval infrastructure outage — never present this as
            # "no evidence found" / abstention. Store as failed with the
            # outage detail so operators and users can tell it apart.
            outage_failures = final_state.get("diagnosis_failures") or [
                "Retrieval service unavailable"
            ]
            outage_answer = final_state.get("answer") or (
                "The knowledge base search service is temporarily unavailable, "
                "so I could not search for evidence. Please wait a few minutes "
                "and try again — this is not a finding of 'no evidence'."
            )
            await analyses_coll.update_one(
                {"_id": analysis_id},
                {
                    "$set": {
                        "status": "failed",
                        "answer": outage_answer,
                        "error_message": outage_failures[0],
                        "reliability": {"score": 0.0, "status": "FAILED"},
                        "diagnosis": {
                            "type": "RETRIEVAL_OUTAGE",
                            "failures": outage_failures,
                        },
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            await svc.add_trace_event(
                analysis_id_str,
                "analysis.outage",
                {"message": outage_failures[0]},
            )
            _record_completed("failed")
            return

        answer = final_state["answer"]
        cfg = _get_model_config()

        thresholds = Thresholds(
            minimum_evidence_coverage=cfg.minimum_evidence_coverage,
            maximum_contradiction_rate=cfg.maximum_contradiction_rate,
            abstain_below=cfg.abstain_below,
        )

        verdict = _svc_mod.verdict_from_state(final_state, thresholds)

        if verdict.reliability_status == ReliabilityStatus.ABSTAINED:
            # Never store the bare "ABSTAIN" token as the user-facing answer.
            stored_abstain = (
                answer if answer and answer.strip() != "ABSTAIN" else _UNVERIFIED_ANSWER
            )
            # Update database first, then publish trace event
            await analyses_coll.update_one(
                {"_id": analysis_id},
                {
                    "$set": {
                        "status": "abstained",
                        "answer": stored_abstain,
                        "reliability": {
                            "score": verdict.reliability_score,
                            "status": verdict.reliability_status.value,
                        },
                        "diagnosis": {
                            "type": verdict.diagnosis_type.value,
                            "failures": verdict.diagnosis_failures,
                        },
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            await svc.add_trace_event(
                analysis_id_str,
                "analysis.abstained",
                {"message": "Agent reasoning resulted in abstention"},
            )
            _record_completed("abstained")
        else:
            # GROUNDING GATE (audit G-1). The verdict engine has already decided
            # how much of the generated answer the evidence supports; this is
            # where that decision is applied to what the user actually reads.
            # Only TRUSTED may present the model's own text. Previously
            # FAILED/UNCERTAIN answers fell through to `status: "completed"`
            # with the raw prose, so the pipeline detected ungrounded content
            # and then displayed it anyway.
            stored_answer = _presentable_answer(answer, verdict)
            stored_status = "completed"
            gated = stored_answer is not answer
            if gated:
                logger.warning(
                    "Unverified answer withheld from user",
                    analysis_id=analysis_id_str,
                    reliability=verdict.reliability_status.value,
                    score=verdict.reliability_score,
                    diagnosis=verdict.diagnosis_type.value,
                )
                await svc.add_trace_event(
                    analysis_id_str,
                    "analysis.grounding_gate",
                    {
                        "message": (
                            "Answer was not fully supported by retrieved evidence "
                            f"({verdict.reliability_status.value}, "
                            f"score={verdict.reliability_score:.2f}); "
                            "presenting abstention instead of ungrounded text."
                        ),
                        "reliability_status": verdict.reliability_status.value,
                        "reliability_score": verdict.reliability_score,
                    },
                )
            # DEGENERATE-STUB GUARD 2026-09-06: when verification fails with zero
            # claims, the stored "answer" can be a context-overflow stub (e.g. the
            # single word "The"). Presenting that as a synthesis is dishonest —
            # store a clean abstention sentence instead (score/diagnosis kept).
            # Extended: small local models may echo prompt scaffolding or loop a
            # block until max tokens — also never a synthesis, whatever claims say.
            scaffold_echo = _looks_like_scaffold_echo(answer)
            if scaffold_echo:
                logger.warning(
                    "Degenerate prompt-echo generation detected, abstaining",
                    analysis_id=analysis_id_str,
                )
                await svc.add_trace_event(
                    analysis_id_str,
                    "generation.degenerate",
                    {"message": "Model echoed prompt scaffolding; answer discarded"},
                )
            if scaffold_echo or (
                verdict.reliability_status == ReliabilityStatus.FAILED
                and not (final_state.get("claims") or [])
                and (answer or "").strip() != "ABSTAIN"
                and len((answer or "").split()) < 5
            ):
                stored_answer = _UNVERIFIED_ANSWER
            if scaffold_echo or gated:
                # A withheld or degenerate answer is not a completed synthesis.
                stored_status = "abstained"
            # USER-FACING CLEANUP: verification already consumed the [Segment N]
            # markers (claims carry their own evidence_ids; the Evidence tab is
            # unaffected), so the stored prose drops them — readers see normal
            # text instead of bracket noise. No-op for marker-free answers.
            # `answer_cited` keeps the marker-bearing form for the audit dossier
            # and the baseline-eval provenance check, which must still be able
            # to see which segments the model actually cited.
            answer_cited = stored_answer
            if stored_answer:
                stored_answer = strip_citation_markers(stored_answer)
            # Update database first, then publish trace event with answer
            await analyses_coll.update_one(
                {"_id": analysis_id},
                {
                    "$set": {
                        "status": stored_status,
                        "answer": stored_answer,
                        "answer_cited": answer_cited,
                        "answer_withheld": answer if (gated or scaffold_echo) else None,
                        "reliability": {
                            "score": verdict.reliability_score,
                            "status": verdict.reliability_status.value,
                        },
                        "diagnosis": {
                            "type": verdict.diagnosis_type.value,
                            "failures": verdict.diagnosis_failures,
                        },
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            await svc.add_trace_event(
                analysis_id_str,
                "analysis.abstained" if stored_status == "abstained" else "analysis.completed",
                {
                    "message": "Answer generation completed successfully",
                    "answer": stored_answer,
                    "verdict": verdict.diagnosis_type.value,
                },
            )
            _record_completed(stored_status)

    except Exception as exc:
        logger.error(
            "Analysis background execution pipeline failed",
            analysis_id=analysis_id_str,
            error=str(exc),
            exc_info=True,
        )

        err_str = str(exc).lower()
        if "connect" in err_str or "connection" in err_str or "refused" in err_str:
            client_msg = (
                f"Inference server connection error. Ensure {llm_provider or 'local'} "
                "server is running and accessible."
            )
        elif "not found" in err_str:
            client_msg = (
                f"Model '{llm_model}' not found on {llm_provider or 'local'} server. "
                "Please ensure the model is pulled or loaded."
            )
        elif "timeout" in err_str or "timed out" in err_str:
            client_msg = (
                "Inference timed out. The local model may still be loading "
                "or system is under heavy load."
            )
        else:
            client_msg = f"Pipeline execution error ({type(exc).__name__}). Check server logs."

        await svc.add_trace_event(
            analysis_id_str,
            "analysis.failed",
            {"message": client_msg},
        )

        await analyses_coll.update_one(
            {"_id": analysis_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": client_msg,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        _record_completed("failed")
    finally:
        try:
            await asyncio.to_thread(memory_mod.trim_memory)
        except Exception as trim_exc:
            logger.debug("Post-analysis memory compaction skipped", error=str(trim_exc))


# Set the lazy shim reference after all definitions are complete.
import app.services.analysis_service as _svc_mod  # noqa: E402
