"""
Pydantic schemas for Analysis runs, claims, and evidence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreate(BaseModel):
    knowledge_base_id: str = Field(..., description="Target knowledge base")
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User question (max 2000 characters to bound token cost)",
    )


class ReliabilitySummary(BaseModel):
    score: float | None = None
    status: str = "PENDING"  # TRUSTED, UNCERTAIN, ABSTAINED, FAILED, PENDING


class DiagnosisSummary(BaseModel):
    type: str | None = None  # RETRIEVAL_FAILURE, EVIDENCE_FAILURE, etc.
    failures: list[str] = []


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    user_id: str
    knowledge_base_id: str
    query: str
    status: str  # pending, running, completed, failed, abstained
    answer: str | None = None
    reliability: ReliabilitySummary
    diagnosis: DiagnosisSummary
    created_at: datetime
    config_snapshot: dict[str, Any] | None = None


class ClaimResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    analysis_id: str
    text: str
    state: str  # SUPPORTED, CONTRADICTED, UNSUPPORTED, UNKNOWN
    explanation: str | None = None
    evidence_ids: list[str] = []
    created_at: datetime


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    analysis_id: str
    text: str
    document_id: str
    filename: str | None = None
    retrieval_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    method: str | None = None  # dense, sparse, hybrid
    integrity_status: str | None = None  # ok, conflict, etc.
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    created_at: datetime


class TraceEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event: str
    timestamp: datetime
    data: dict[str, Any] = {}
