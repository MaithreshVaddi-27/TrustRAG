"""
TRUSTRAG — Evaluation Experiment tracking and serialization.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.api.v1.schemas.experiment import ExperimentCreate, ExperimentResponse
from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.mongodb import Collections, get_collection


def serialize_experiment(doc: Mapping[str, Any]) -> ExperimentResponse:
    """Helper to convert MongoDB Experiment document to Pydantic ExperimentResponse."""
    return ExperimentResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        config_name=doc["config_name"],
        description=doc.get("description", ""),
        metrics=doc.get("metrics", {}),
        created_at=doc["created_at"],
    )


async def create_experiment(schema: ExperimentCreate, user_id_str: str) -> ExperimentResponse:
    """Record a new evaluation experiment run."""
    exp_coll = get_collection(Collections.EXPERIMENTS)
    exp_doc = {
        "user_id": ObjectId(user_id_str),
        "config_name": schema.config_name.strip(),
        "description": schema.description.strip(),
        "metrics": schema.metrics,
        "created_at": datetime.now(UTC),
    }

    result = await exp_coll.insert_one(exp_doc)
    exp_doc["_id"] = result.inserted_id
    return serialize_experiment(exp_doc)


async def get_experiment(exp_id_str: str, user_id_str: str) -> ExperimentResponse:
    """Get experiment details and verify ownership."""
    try:
        exp_id = ObjectId(exp_id_str)
    except Exception as exc:
        raise NotFoundError("Experiment not found", detail=str(exc)) from exc

    exp = await get_collection(Collections.EXPERIMENTS).find_one({"_id": exp_id})
    if not exp:
        raise NotFoundError("Experiment not found")

    if str(exp["user_id"]) != user_id_str:
        raise AuthorizationError("Access denied", detail="You do not own this experiment record")

    return serialize_experiment(exp)


async def list_experiments(user_id_str: str) -> list[ExperimentResponse]:
    """List experiment records run by user."""
    exp_coll = get_collection(Collections.EXPERIMENTS)
    results = []
    async for e in exp_coll.find({"user_id": ObjectId(user_id_str)}).sort("created_at", -1):
        results.append(serialize_experiment(e))
    return results
