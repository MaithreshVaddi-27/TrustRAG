"""
Pydantic schemas for Knowledge Bases and Documents.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KBCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)


class KBResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str
    user_id: str
    document_count: int = 0
    created_at: datetime
    # P0 FIX 2026-09-06: serialize_kb() already passes these, but the schema
    # silently dropped them (extra='ignore'), so delete_kb()'s kb.is_snapshot
    # raised AttributeError → DELETE /knowledge-bases/{id} always 500'd.
    version: str = "1.0"
    parent_kb_id: str | None = None
    is_snapshot: bool = False
    # Embedding space pin (set on first ingest). Analyses MUST query with this
    # model — cross-space queries return silent garbage. None = legacy KB.
    embedding_model: str | None = None
    embedding_provider: str | None = None
    embedding_dim: int | None = None


class DocResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    knowledge_base_id: str
    filename: str
    file_size: int
    content_hash: str
    ingestion_status: str  # pending, processing, completed, failed
    error_message: str | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    created_at: datetime
