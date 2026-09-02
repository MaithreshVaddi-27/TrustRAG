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
    enable_web_search: bool = Field(
        default=False,
        description="Whether to ground analysis using live web search via MCP",
    )
    web_search_provider: str = Field(
        default="both",
        description="Web search provider: 'tavily', 'duckduckgo', or 'both'",
    )
    llm_provider: str | None = Field(
        default=None,
        description="Active LLM provider override ('ollama', 'llama_cpp', 'gemini', 'nvidia')",
    )
    llm_model: str | None = Field(
        default=None,
        description="Specific model identifier override (e.g. 'gemma4:e2b')",
    )
    embedding_provider: str | None = Field(
        default=None,
        description="Active embedding provider override ('huggingface', 'ollama', 'google_genai', 'nvidia')",
    )
    embedding_model: str | None = Field(
        default=None,
        description="Specific embedding model identifier override (e.g. 'BAAI/bge-small-en-v1.5', 'embeddinggemma:300m-qat-q8_0')",
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
    web_search_enabled: bool = False
    web_search_provider: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None


class ClaimResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    analysis_id: str
    text: str
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    state: str  # SUPPORTED, CONTRADICTED, NEUTRAL
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
    url: str | None = None
    retrieval_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    method: str | None = None  # dense, sparse, hybrid
    integrity_status: str | None = None  # VERIFIED, CORRUPTED
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    created_at: datetime


class TraceEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event: str
    timestamp: datetime
    data: dict[str, Any] = {}
