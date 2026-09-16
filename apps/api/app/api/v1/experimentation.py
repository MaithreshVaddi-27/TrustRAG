"""
TRUSTRAG API — Feature Flags & Experiments.

Provides API endpoints for feature flag management and A/B experiment
configuration and retrieval.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.experimentation import get_feature_flag_manager

router = APIRouter(prefix="/experimentation", tags=["experimentation"])


@router.get(
    "/flags",
    response_model=dict,
    summary="List all feature flags",
)
async def list_feature_flags(
    current_user: Mapping[str, Any] = Depends(get_current_user),
) -> dict:
    """List all feature flags with their current state."""
    manager = get_feature_flag_manager()
    await manager.initialize()
    flags = manager.get_all_flags()
    return {
        key: {
            "enabled": flag.enabled,
            "rollout_percentage": flag.rollout_percentage,
            "targeting_rules": flag.targeting_rules,
            "description": flag.description,
        }
        for key, flag in flags.items()
    }
