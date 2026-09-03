"""
TRUSTRAG — Analysis runs, claims, evidence, and execution trace service.
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
from app.core.config import get_model_config
from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.db.mongodb import Collections, get_collection
from app.services.kb_service import get_kb
from app.verification.verdict import (
    ReliabilityStatus,
    Thresholds,
    compute_verdict,
    verdict_from_state,
)

logger = get_logger(__name__)

# ─── In-process SSE Pub/Sub ──────────────────────────────────────────────────
# Maps analysis_id -> set of asyncio.Queue subscribers
_analysis_subscribers: dict[str, set[asyncio.Queue]] = {}
_subscribers_lock = asyncio.Lock()


async def _subscribe_to_analysis(analysis_id: str) -> asyncio.Queue:
    """Subscribe to real-time events for an analysis."""
    queue: asyncio.Queue = asyncio.Queue()
    async with _subscribers_lock:
        if analysis_id not in _analysis_subscribers:
            _analysis_subscribers[analysis_id] = set()
        _analysis_subscribers[analysis_id].add(queue)
    return queue


async def _unsubscribe_from_analysis(analysis_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from analysis events."""
    async with _subscribers_lock:
        if analysis_id in _analysis_subscribers:
            _analysis_subscribers[analysis_id].discard(queue)
            if not _analysis_subscribers[analysis_id]:
                del _analysis_subscribers[analysis_id]


async def _publish_analysis_event(
    analysis_id: str, event: str, data: dict[str, Any]
) -> None:
    """Publish an event to all subscribers of an analysis."""
    async with _subscribers_lock:
        if analysis_id in _analysis_subscribers:
            event_data = {
                "event": event,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": data,
            }
            for queue in _analysis_subscribers[analysis_id]:
                try:
                    queue.put_nowait(event_data)
                except asyncio.QueueFull:
                    logger.warning("SSE subscriber queue full, dropping event", analysis_id=analysis_id)


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
        embedding_provider=doc.get("embedding_provider"),
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
    timestamp = doc.get("timestamp") or datetime.now(UTC)
    return TraceEventResponse(
        event=doc.get("event", ""),
        timestamp=timestamp,
        data=doc.get("data", {}),
    )


async def create_analysis(
    schema: AnalysisCreate, user_id_str: str, background_tasks: BackgroundTasks
) -> AnalysisResponse:
    """
    Initiate an analysis run.
    Verifies that target KB exists and is owned by the user.
    """
    # Verify owner & existence of KB
    await get_kb(schema.knowledge_base_id, user_id_str)

    cfg = get_model_config()
    analysis_doc = {
        "user_id": ObjectId(user_id_str),
        "knowledge_base_id": ObjectId(schema.knowledge_base_id),
        "query": schema.query.strip(),
        "status": "pending",
        "answer": None,
        "reliability": {"score": None, "status": "PENDING"},
        "diagnosis": {"type": None, "failures": []},
        "created_at": datetime.now(UTC),
        "config_snapshot": cfg.as_snapshot(),
        "web_search_enabled": schema.enable_web_search,
        "web_search_provider": schema.web_search_provider,
        "llm_provider": schema.llm_provider,
        "llm_model": schema.llm_model,
        "embedding_provider": schema.embedding_provider,
        "embedding_model": schema.embedding_model,
    }

    result = await get_collection(Collections.ANALYSES).insert_one(analysis_doc)
    analysis_doc["_id"] = result.inserted_id

    # Emit initial started trace event
    await add_trace_event(
        analysis_id_str=str(result.inserted_id),
        event="analysis.started",
        data={
            "message": "Analysis run initiated",
            "provider": schema.llm_provider or cfg.llm_provider,
            "model": schema.llm_model or cfg.llm_model,
            "embedding_provider": schema.embedding_provider or cfg.embedding_provider,
            "embedding_model": schema.embedding_model or cfg.embedding_model,
        },
    )

    # Queue background RAG execution pipeline
    background_tasks.add_task(
        run_analysis_pipeline,
        analysis_id_str=str(result.inserted_id),
        kb_id_str=schema.knowledge_base_id,
        query=schema.query.strip(),
        user_id_str=user_id_str,
        web_search_enabled=schema.enable_web_search,
        web_search_provider=schema.web_search_provider,
        llm_provider=schema.llm_provider,
        llm_model=schema.llm_model,
        embedding_provider=schema.embedding_provider,
        embedding_model=schema.embedding_model,
    )

    return serialize_analysis(analysis_doc)


async def get_analysis(analysis_id_str: str, user_id_str: str) -> AnalysisResponse:
    """Get analysis run detail, enforcing ownership verification."""
    try:
        analysis_id = ObjectId(analysis_id_str)
    except Exception as exc:
        raise NotFoundError("Analysis not found", detail=str(exc)) from exc

    analysis = await get_collection(Collections.ANALYSES).find_one({"_id": analysis_id})
    if not analysis:
        raise NotFoundError("Analysis not found")

    if str(analysis["user_id"]) != user_id_str:
        raise AuthorizationError("Access denied", detail="You do not own this analysis record")

    return serialize_analysis(analysis)


async def list_analyses(user_id_str: str, limit: int = 50, skip: int = 0) -> list[AnalysisResponse]:
    """List analysis runs for the authenticated user with pagination."""
    analyses_coll = get_collection(Collections.ANALYSES)
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


async def get_analysis_claims(analysis_id_str: str, user_id_str: str) -> list[ClaimResponse]:
    """Fetch verified claims generated for an analysis."""
    await get_analysis(analysis_id_str, user_id_str)

    claims_coll = get_collection(Collections.CLAIMS)
    results = []
    async for c in claims_coll.find({"analysis_id": ObjectId(analysis_id_str)}).sort(
        "created_at", 1
    ):
        results.append(serialize_claim(c))
    return results


async def get_analysis_evidence(analysis_id_str: str, user_id_str: str) -> list[EvidenceResponse]:
    """Fetch evidence chunks associated with an analysis."""
    await get_analysis(analysis_id_str, user_id_str)

    evidence_coll = get_collection(Collections.EVIDENCE)
    results = []
    async for e in evidence_coll.find({"analysis_id": ObjectId(analysis_id_str)}).sort(
        "created_at", 1
    ):
        results.append(serialize_evidence(e))
    return results


async def get_analysis_trace(analysis_id_str: str, user_id_str: str) -> list[TraceEventResponse]:
    """Fetch execution trace events for audit/recovery inspection."""
    await get_analysis(analysis_id_str, user_id_str)

    trace_coll = get_collection(Collections.TRACE_EVENTS)
    results = []
    async for t in trace_coll.find({"analysis_id": ObjectId(analysis_id_str)}).sort("timestamp", 1):
        results.append(serialize_trace(t))
    return results


async def add_trace_event(
    analysis_id_str: str, event: str, data: dict[str, Any] | None = None
) -> TraceEventResponse:
    """Insert a new trace event into MongoDB and publish to SSE subscribers."""
    if data is None:
        data = {}
    trace_coll = get_collection(Collections.TRACE_EVENTS)
    evt_doc = {
        "analysis_id": ObjectId(analysis_id_str),
        "event": event,
        "timestamp": datetime.now(UTC),
        "data": data,
    }
    await trace_coll.insert_one(evt_doc)

    # Publish to in-process SSE subscribers (replaces MongoDB polling)
    await _publish_analysis_event(analysis_id_str, event, data)

    return serialize_trace(evt_doc)


async def sse_event_generator(
    analysis_id_str: str, user_id_str: str
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Generator yielding trace events as Server-Sent Events (SSE) via in-process pub/sub.

    Frontend relies on this for real-time trace logging.
    If the connection drops, trace history is fully stored in MongoDB
    and retrieved via the get_analysis_trace function.
    """
    # Verify access permission first
    await get_analysis(analysis_id_str, user_id_str)

    # Subscribe to real-time events
    queue = await _subscribe_to_analysis(analysis_id_str)

    try:
        no_event_ticks = 0
        while no_event_ticks < 120:
            try:
                # Wait for event with timeout (1 second)
                event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                no_event_ticks = 0
                yield event_data

                # Terminal event checks
                if event_data["event"] in ["analysis.completed", "analysis.abstained", "analysis.failed"]:
                    return
            except asyncio.TimeoutError:
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


# Hardware-aware global concurrency limiter to protect system resources
_analysis_semaphore: asyncio.Semaphore | None = None
_semaphore_init_lock: asyncio.Lock | None = None


def _get_semaphore_init_lock() -> asyncio.Lock:
    """Return the module-level asyncio lock for semaphore initialization (lazy, event-loop-safe)."""
    global _semaphore_init_lock
    if _semaphore_init_lock is None:
        _semaphore_init_lock = asyncio.Lock()
    return _semaphore_init_lock


async def _get_concurrency_semaphore() -> asyncio.Semaphore:
    """Return the global analysis semaphore, initializing it exactly once under a lock."""
    global _analysis_semaphore
    if _analysis_semaphore is not None:
        return _analysis_semaphore
    async with _get_semaphore_init_lock():
        # Double-check after acquiring lock to handle concurrent waiters
        if _analysis_semaphore is None:
            try:
                from app.core.hardware import detect_hardware_profile

                profile = detect_hardware_profile()
                max_conc = profile.get("recommendations", {}).get("max_concurrency", 2)
            except Exception:
                max_conc = 2
            _analysis_semaphore = asyncio.Semaphore(max_conc)
    return _analysis_semaphore



async def run_analysis_pipeline(
    analysis_id_str: str,
    kb_id_str: str,
    query: str,
    user_id_str: str | None = None,
    web_search_enabled: bool = False,
    web_search_provider: str = "both",
    llm_provider: str | None = None,
    llm_model: str | None = None,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
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
    analysis_id = ObjectId(analysis_id_str)
    analyses_coll = get_collection(Collections.ANALYSES)
    sem = await _get_concurrency_semaphore()

    try:
        async with sem:
            # Mark status as processing
            await analyses_coll.update_one(
                {"_id": analysis_id},
                {"$set": {"status": "processing", "updated_at": datetime.now(UTC)}},
            )

            # 1. Execute Agentic LangGraph workflow (retrieval, NLI verify, and recovery loop)
            from app.agent.graph import execute_agentic_rag_flow

            final_state = await execute_agentic_rag_flow(
                analysis_id_str=analysis_id_str,
                kb_id_str=kb_id_str,
                query=query,
                user_id_str=user_id_str,
                web_search_enabled=web_search_enabled,
                web_search_provider=web_search_provider,
                llm_provider=llm_provider,
                llm_model=llm_model,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
            )

        answer = final_state["answer"]
        cfg = get_model_config()

        thresholds = Thresholds(
            minimum_evidence_coverage=cfg.minimum_evidence_coverage,
            maximum_contradiction_rate=cfg.maximum_contradiction_rate,
            abstain_below=cfg.abstain_below,
        )

        verdict = verdict_from_state(final_state, thresholds)

        if verdict.reliability_status == ReliabilityStatus.ABSTAINED:
            await add_trace_event(
                analysis_id_str,
                "analysis.abstained",
                {"message": "Agent reasoning resulted in abstention"},
            )
            status_value = "abstained"
        else:
            await add_trace_event(
                analysis_id_str,
                "analysis.completed",
                {"message": "Answer generation completed successfully"},
            )
            status_value = "completed"

        # Update final state in database
        await analyses_coll.update_one(
            {"_id": analysis_id},
            {
                "$set": {
                    "status": status_value,
                    "answer": answer,
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

    except Exception as exc:
        logger.error(
            "Analysis background execution pipeline failed",
            analysis_id=analysis_id_str,
            error=str(exc),
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
                "Inference timed out. The local model may still be loading or system is under heavy load."
            )
        else:
            client_msg = f"Pipeline execution error ({type(exc).__name__}). Check server logs."

        await add_trace_event(
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
    finally:
        try:
            import asyncio
            from app.core.memory import trim_memory

            await asyncio.to_thread(trim_memory)
        except Exception as trim_exc:
            logger.debug("Post-analysis memory compaction skipped", error=str(trim_exc))


async def list_all_user_evidence(
    user_id_str: str, limit: int = 50, skip: int = 0
) -> list[EvidenceResponse]:
    """Fetch all evidence chunks across all analyses for this user with pagination."""
    evidence_coll = get_collection(Collections.EVIDENCE)
    uid = ObjectId(user_id_str)

    query_filter: dict[str, Any] = {"user_id": uid}
    if await evidence_coll.count_documents(query_filter) == 0:
        analyses_coll = get_collection(Collections.ANALYSES)
        user_analyses = await analyses_coll.find({"user_id": uid}, {"_id": 1}).to_list(1000)
        analysis_ids = [a["_id"] for a in user_analyses]
        if not analysis_ids:
            return []
        query_filter = {"analysis_id": {"$in": analysis_ids}}

    results = []
    cursor = (
        evidence_coll.find(query_filter).sort("created_at", -1).skip(skip).limit(min(limit, 200))
    )
    async for e in cursor:
        results.append(serialize_evidence(e))
    return results


async def list_all_user_claims(
    user_id_str: str, limit: int = 50, skip: int = 0
) -> list[ClaimResponse]:
    """Fetch all verified claims across all analyses for this user with pagination."""
    claims_coll = get_collection(Collections.CLAIMS)
    uid = ObjectId(user_id_str)

    query_filter: dict[str, Any] = {"user_id": uid}
    if await claims_coll.count_documents(query_filter) == 0:
        analyses_coll = get_collection(Collections.ANALYSES)
        user_analyses = await analyses_coll.find({"user_id": uid}, {"_id": 1}).to_list(1000)
        analysis_ids = [a["_id"] for a in user_analyses]
        if not analysis_ids:
            return []
        query_filter = {"analysis_id": {"$in": analysis_ids}}

    results = []
    cursor = claims_coll.find(query_filter).sort("created_at", -1).skip(skip).limit(min(limit, 200))
    async for c in cursor:
        results.append(serialize_claim(c))
    return results


async def list_all_user_conflicts(
    user_id_str: str, limit: int = 50, skip: int = 0
) -> list[dict[str, Any]]:
    """Fetch all detected conflicts across all analyses for this user with pagination."""
    analyses_coll = get_collection(Collections.ANALYSES)
    user_analyses = await analyses_coll.find(
        {"user_id": ObjectId(user_id_str)}, {"_id": 1, "query": 1}
    ).to_list(1000)
    if not user_analyses:
        return []

    analysis_map = {str(a["_id"]): a.get("query", "") for a in user_analyses}
    a_ids = [a["_id"] for a in user_analyses]

    claims_coll = get_collection(Collections.CLAIMS)
    evidence_coll = get_collection(Collections.EVIDENCE)

    conflicts = []

    # 1. Contradicted claims
    cursor_claims = (
        claims_coll.find({"analysis_id": {"$in": a_ids}, "state": "CONTRADICTED"})
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(limit, 100))
    )
    async for c in cursor_claims:
        conflicts.append(
            {
                "id": str(c["_id"]),
                "type": "claim_contradiction",
                "title": "Claim Contradicted by Retrieved Evidence",
                "claim": c["text"],
                "explanation": c.get("explanation") or "Evidence contradicts this assertion.",
                "analysis_id": str(c["analysis_id"]),
                "query": analysis_map.get(str(c["analysis_id"]), ""),
                "created_at": (
                    c["created_at"].isoformat()
                    if hasattr(c["created_at"], "isoformat")
                    else str(c["created_at"])
                ),
            }
        )

    # 2. Corrupted / compromised evidence
    cursor_evidence = (
        evidence_coll.find(
            {"analysis_id": {"$in": a_ids}, "integrity_status": {"$nin": ["VERIFIED", None]}}
        )
        .sort("created_at", -1)
        .skip(skip)
        .limit(min(limit, 100))
    )
    async for e in cursor_evidence:
        conflicts.append(
            {
                "id": str(e["_id"]),
                "type": "integrity_compromise",
                "title": f"Evidence Integrity Compromised: {e.get('integrity_status')}",
                "claim": (e["text"][:200] + "...") if len(e["text"]) > 200 else e["text"],
                "explanation": f"Integrity check flagged status: {e.get('integrity_status')}",
                "analysis_id": str(e["analysis_id"]),
                "query": analysis_map.get(str(e["analysis_id"]), ""),
                "created_at": (
                    e["created_at"].isoformat()
                    if hasattr(e["created_at"], "isoformat")
                    else str(e["created_at"])
                ),
            }
        )

    return conflicts


async def export_analysis_dossier(
    analysis_id_str: str, user_id_str: str, export_format: str = "jsonld"
) -> dict[str, Any]:
    """
    Export full compliance and audit package for an analysis run.

    Includes answer, verified claim assertions (with triples), retrieved evidence
    with SHA-256 provenance hashes, and reliability diagnosis.
    """
    analysis = await get_analysis(analysis_id_str, user_id_str)
    claims = await get_analysis_claims(analysis_id_str, user_id_str)
    evidence = await get_analysis_evidence(analysis_id_str, user_id_str)

    created_at_str = (
        analysis.created_at.isoformat()
        if hasattr(analysis.created_at, "isoformat")
        else str(analysis.created_at)
    )

    if export_format.lower() == "jsonld":
        return {
            "@context": {
                "@vocab": "https://schema.org/",
                "trustrag": "https://trustrag.dev/ontology/",
                "Claim": "trustrag:Claim",
                "Evidence": "trustrag:Evidence",
                "reliabilityScore": "trustrag:reliabilityScore",
                "integrityStatus": "trustrag:integrityStatus",
                "contentHash": "trustrag:contentHash",
            },
            "@type": "Report",
            "@id": f"urn:trustrag:analysis:{analysis.id}",
            "name": f"TRUSTRAG Verification Audit — {analysis.id}",
            "dateCreated": created_at_str,
            "about": {"@type": "Question", "text": analysis.query},
            "text": analysis.answer,
            "reliability": {
                "score": analysis.reliability.score,
                "status": analysis.reliability.status,
            },
            "diagnosis": {
                "type": analysis.diagnosis.type,
                "failures": analysis.diagnosis.failures,
            },
            "claims": [
                {
                    "@type": "Claim",
                    "text": c.text,
                    "subject": c.subject,
                    "predicate": c.predicate,
                    "object": c.object,
                    "verdict": c.state,
                    "explanation": c.explanation,
                    "evidenceIds": c.evidence_ids,
                }
                for c in claims
            ],
            "evidence": [
                {
                    "@type": "DigitalDocument",
                    "text": e.text,
                    "filename": e.filename,
                    "documentId": e.document_id,
                    "integrityStatus": e.integrity_status,
                    "retrievalScore": e.retrieval_score,
                    "rerankScore": e.rerank_score,
                }
                for e in evidence
            ],
        }

    return {
        "analysis": analysis.model_dump(),
        "claims": [c.model_dump() for c in claims],
        "evidence": [e.model_dump() for e in evidence],
    }
