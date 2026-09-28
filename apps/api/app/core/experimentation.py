"""
TRUSTRAG — Feature flag storage and lookup.

Backs `GET /api/v1/experimentation/flags`. Flags live in the `feature_flags`
collection and are cached in memory after the first successful load.

An earlier version of this module also carried an A/B experiment framework
(ExperimentManager, MetricsCollector, run_with_experiment_tracking, ~340
lines). None of it was ever reachable: the only importer of this module wanted
get_feature_flag_manager. It was removed. Note that its create_experiment wrote
A/B documents into Collections.EXPERIMENTS — the same collection the live
evaluation-experiment service uses for a different schema — so reviving that
code as-is would have corrupted real data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.db.mongodb import Collections, get_collection

logger = get_logger(__name__)


# ─── Feature Flags ────────────────────────────────────────────────────────────


@dataclass
class FeatureFlag:
    """Feature flag definition."""

    key: str
    enabled: bool = False
    rollout_percentage: float = 0.0  # 0.0 to 1.0
    targeting_rules: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FeatureFlagManager:
    """Manages feature flags with targeting and rollout."""

    def __init__(self):
        self._flags: dict[str, FeatureFlag] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Load feature flags from database.

        On failure this leaves ``_initialized`` False so a later call retries.
        An earlier version set it to True inside the except branch to avoid
        re-querying Mongo on every request, but a single transient error then
        silenced feature flags for the life of the process — the endpoint
        returned ``{}`` until restart, with only a warning to explain it.
        """
        if self._initialized:
            return

        try:
            flags_coll = get_collection(Collections.FEATURE_FLAGS)
            cursor = flags_coll.find({})
            async for doc in cursor:
                flag = FeatureFlag(
                    key=doc["key"],
                    enabled=doc.get("enabled", False),
                    rollout_percentage=doc.get("rollout_percentage", 0.0),
                    targeting_rules=doc.get("targeting_rules", []),
                    description=doc.get("description", ""),
                    created_at=doc.get("created_at", datetime.now(UTC)),
                    updated_at=doc.get("updated_at", datetime.now(UTC)),
                )
                self._flags[flag.key] = flag

            self._initialized = True
            logger.info("Feature flags loaded", count=len(self._flags))
        except Exception:
            # Left retryable on purpose. Logging at error with a traceback
            # because an empty flag set silently changes runtime behaviour.
            logger.exception("Failed to load feature flags; will retry on next call")

    async def set_flag(self, flag: FeatureFlag) -> None:
        """Create or update a feature flag."""
        flag.updated_at = datetime.now(UTC)
        self._flags[flag.key] = flag

        flags_coll = get_collection(Collections.FEATURE_FLAGS)
        await flags_coll.update_one(
            {"key": flag.key},
            {
                "$set": {
                    "key": flag.key,
                    "enabled": flag.enabled,
                    "rollout_percentage": flag.rollout_percentage,
                    "targeting_rules": flag.targeting_rules,
                    "description": flag.description,
                    "updated_at": flag.updated_at,
                },
                "$setOnInsert": {"created_at": flag.created_at},
            },
            upsert=True,
        )

    async def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        if key not in self._flags:
            return False

        del self._flags[key]
        flags_coll = get_collection(Collections.FEATURE_FLAGS)
        result = await flags_coll.delete_one({"key": key})
        return result.deleted_count > 0

    def get_all_flags(self) -> dict[str, FeatureFlag]:
        """Get all feature flags."""
        return self._flags.copy()


# Global feature flag manager
_feature_flag_manager: FeatureFlagManager | None = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get the global feature flag manager."""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager
