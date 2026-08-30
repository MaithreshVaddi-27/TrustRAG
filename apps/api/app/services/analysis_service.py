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

logger = get_logger(__name__)


def serialize_analysis(doc: Mapping[str, Any]) -> AnalysisResponse:
    """Helper to convert MongoDB Analysis document to Pydantic AnalysisResponse."""
    rel = doc.get("reliability", {})
    diag = doc.get("diagnosis", {})
    return AnalysisResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        knowledge_base_id=str(doc["knowledge_base_id"]),
        query=doc["query"],
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
        created_at=doc["created_at"],
        config_snapshot=doc.get("config_snapshot"),
    )


def serialize_claim(doc: Mapping[str, Any]) -> ClaimResponse:
    """Helper to convert MongoDB Claim document to Pydantic ClaimResponse."""
    return ClaimResponse(
        id=str(doc["_id"]),
        analysis_id=str(doc["analysis_id"]),
        text=doc["text"],
        subject=doc.get("subject"),
        predicate=doc.get("predicate"),
        object=doc.get("object"),
        state=doc.get("state", "UNKNOWN"),
        explanation=doc.get("explanation"),
        evidence_ids=[str(eid) for eid in doc.get("evidence_ids", [])],
        created_at=doc["created_at"],
    )


def serialize_evidence(doc: Mapping[str, Any]) -> EvidenceResponse:
    """Helper to convert MongoDB Evidence document to Pydantic EvidenceResponse."""
    return EvidenceResponse(
        id=str(doc["_id"]),
        analysis_id=str(doc["analysis_id"]),
        text=doc["text"],
        document_id=str(doc["document_id"]) if doc.get("document_id") else "",
        filename=doc.get("filename"),
        retrieval_score=doc.get("retrieval_score"),
        fusion_score=doc.get("fusion_score"),
        rerank_score=doc.get("rerank_score"),
        method=doc.get("method"),
        integrity_status=doc.get("integrity_status"),
        effective_from=doc.get("effective_from"),
        effective_until=doc.get("effective_until"),
        created_at=doc["created_at"],
    )


def serialize_trace(doc: Mapping[str, Any]) -> TraceEventResponse:
    """Helper to convert MongoDB TraceEvent document to Pydantic TraceEventResponse."""
    return TraceEventResponse(
        event=doc["event"],
        timestamp=doc["timestamp"],
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
    }

    result = await get_collection(Collections.ANALYSES).insert_one(analysis_doc)
    analysis_doc["_id"] = result.inserted_id

    # Emit initial started trace event
    await add_trace_event(
        analysis_id_str=str(result.inserted_id),
        event="analysis.started",
        data={"message": "Analysis run initiated"},
    )

    # Queue background RAG execution pipeline
    background_tasks.add_task(
        run_analysis_pipeline,
        analysis_id_str=str(result.inserted_id),
        kb_id_str=schema.knowledge_base_id,
        query=schema.query.strip(),
        user_id_str=user_id_str,
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
    """Insert a new trace event into MongoDB."""
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
    return serialize_trace(evt_doc)


async def sse_event_generator(
    analysis_id_str: str, user_id_str: str
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Generator yielding trace events as Server-Sent Events (SSE).
    Frontend relies on this for real-time trace logging.

    If the connection drops, trace history is fully stored in MongoDB
    and retrieved via the get_analysis_trace function.
    """
    # Verify access permission first
    await get_analysis(analysis_id_str, user_id_str)

    last_seen_id = None
    trace_coll = get_collection(Collections.TRACE_EVENTS)

    # Loop until terminal event or 120 seconds of no new trace events
    no_event_ticks = 0
    while no_event_ticks < 120:
        query = {"analysis_id": ObjectId(analysis_id_str)}
        if last_seen_id:
            query["_id"] = {"$gt": last_seen_id}

        cursor = trace_coll.find(query).sort("timestamp", 1)
        has_new = False
        async for doc in cursor:
            has_new = True
            no_event_ticks = 0
            last_seen_id = doc["_id"]
            yield {
                "event": doc["event"],
                "timestamp": doc["timestamp"].isoformat(),
                "data": doc.get("data", {}),
            }

            # Terminal event checks
            if doc["event"] in ["analysis.completed", "analysis.abstained", "analysis.failed"]:
                return

        if not has_new:
            no_event_ticks += 1

        await asyncio.sleep(1.0)


async def run_analysis_pipeline(
    analysis_id_str: str, kb_id_str: str, query: str, user_id_str: str | None = None
) -> None:
    """
    Execute RAG retrieval and generation pipeline in the background.

    Phases:
      1. Retrieve segments using hybrid (dense + sparse) matching
      2. Apply temporal filters using parent document dates
      3. Rerank top matches using CrossEncoder
      4. Persist segments as Evidence models in MongoDB
      5. Generate answer using Gemini, grounded in retrieved context
      6. Update status and save answer in MongoDB
    """
    analysis_id = ObjectId(analysis_id_str)
    analyses_coll = get_collection(Collections.ANALYSES)

    try:
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
        )

        answer = final_state["answer"]
        score = final_state.get("reliability_score")
        cfg = get_model_config()

        if answer == "ABSTAIN":
            await add_trace_event(
                analysis_id_str,
                "analysis.abstained",
                {"message": "Agent reasoning resulted in abstention"},
            )
            status_value = "abstained"
            reliability_status = "ABSTAINED"
        else:
            await add_trace_event(
                analysis_id_str,
                "analysis.completed",
                {"message": "Answer generation completed successfully"},
            )
            status_value = "completed"
            if final_state["verdict_status"] == "PASS":
                reliability_status = "TRUSTED"
            elif score is not None and score >= cfg.abstain_below:
                reliability_status = "UNCERTAIN"
            else:
                reliability_status = "FAILED"

        # Update final state in database
        await analyses_coll.update_one(
            {"_id": analysis_id},
            {
                "$set": {
                    "status": status_value,
                    "answer": answer,
                    "reliability": {"score": score, "status": reliability_status},
                    "diagnosis": {
                        "type": final_state.get("diagnosis_type"),
                        "failures": final_state.get("diagnosis_failures", []),
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

        await add_trace_event(
            analysis_id_str,
            "analysis.failed",
            # Do NOT expose raw exception details to users — log internally only
            {"message": "Analysis execution failed. Check server logs for details."},
        )

        # Store generic error type — NOT str(exc) which leaks internal details
        error_type = type(exc).__name__
        await analyses_coll.update_one(
            {"_id": analysis_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": f"Pipeline error ({error_type}). See server logs.",
                    "updated_at": datetime.now(UTC),
                }
            },
        )


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
