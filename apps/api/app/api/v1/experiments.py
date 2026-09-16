"""
TRUSTRAG API — Experiment evaluation routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.api.v1.schemas.experiment import ExperimentCreate, ExperimentResponse
from app.services import experiment_service

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record experiment run",
)
async def create_experiment_endpoint(
    schema: ExperimentCreate, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> ExperimentResponse:
    """Record a new evaluation experiment configuration."""
    return await experiment_service.create_experiment(schema, str(current_user["_id"]))


@router.get("", response_model=list[ExperimentResponse], summary="List all experiment runs")
async def list_experiments_endpoint(
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> list[ExperimentResponse]:
    """List all experiment runs submitted by the logged-in user."""
    return await experiment_service.list_experiments(str(current_user["_id"]))


@router.get("/{exp_id}", response_model=ExperimentResponse, summary="Get experiment details")
async def get_experiment_endpoint(
    exp_id: str, current_user: Mapping[str, Any] = Depends(get_current_user)
) -> ExperimentResponse:
    """Fetch details and metrics for a specific experiment run."""
    return await experiment_service.get_experiment(exp_id, str(current_user["_id"]))
