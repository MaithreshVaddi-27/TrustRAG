"""
Pydantic schemas for Experiment tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class ExperimentCreate(BaseModel):
    config_name: str = Field(..., description="Configuration being evaluated")
    description: str = Field("", description="A short summary of the experiment objective")


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    user_id: str
    config_name: str
    description: str
    metrics: dict[str, Any] = {}
    created_at: datetime
