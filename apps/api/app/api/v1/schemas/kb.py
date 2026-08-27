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


class DocResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    knowledge_base_id: str
    filename: str
    file_size: int
    content_hash: str
    ingestion_status: str  # pending, processing, completed, failed
    error_message: str | None = None
    created_at: datetime
