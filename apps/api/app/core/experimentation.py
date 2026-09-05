"""
TRUSTRAG — A/B Testing & Feature Flag Framework.

Provides:
- Feature flag management with targeting rules
- A/B experiment assignment with consistent hashing
- Metrics collection for experiment evaluation
- Integration with analysis pipeline for agent configuration variants
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from collections.abc import Callable
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
        """Load feature flags from database."""
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
        except Exception as exc:
            logger.warning("Failed to load feature flags", error=str(exc))
            self._initialized = True  # Don't retry on every call

    def is_enabled(self, key: str, context: dict[str, Any] | None = None) -> bool:
        """
        Check if a feature flag is enabled for the given context.

        Args:
            key: Feature flag key
            context: User/request context for targeting (user_id, tier, region, etc.)

        Returns:
            True if feature is enabled for this context
        """
        flag = self._flags.get(key)
        if not flag:
            return False

        if not flag.enabled:
            return False

        # Check targeting rules first
        if flag.targeting_rules and context:
            for rule in flag.targeting_rules:
                if self._matches_rule(rule, context):
                    return True
            # If there are targeting rules but none matched, check rollout
            if flag.rollout_percentage >= 1.0:
                return True
            return False

        # Rollout percentage check using consistent hashing
        if flag.rollout_percentage > 0:
            user_id = context.get("user_id") if context else None
            if user_id:
                return self._in_rollout(user_id, flag.rollout_percentage)
            return False

        return flag.rollout_percentage >= 1.0

    def _matches_rule(self, rule: dict[str, Any], context: dict[str, Any]) -> bool:
        """Check if context matches a targeting rule."""
        # Rule format: {"attribute": "user_id", "operator": "in", "values": ["user1", "user2"]}
        attribute = rule.get("attribute")
        operator = rule.get("operator", "equals")
        values = rule.get("values", [])

        context_value = context.get(attribute)
        if context_value is None:
            return False

        if operator == "equals":
            return context_value in values
        elif operator == "in":
            return context_value in values
        elif operator == "contains":
            return any(v in str(context_value) for v in values)
        elif operator == "starts_with":
            return any(str(context_value).startswith(v) for v in values)
        elif operator == "gt":
            return float(context_value) > float(values[0]) if values else False
        elif operator == "lt":
            return float(context_value) < float(values[0]) if values else False

        return False

    def _in_rollout(self, user_id: str, percentage: float) -> bool:
        """Deterministic rollout check using consistent hashing."""
        hash_input = f"{user_id}:{percentage}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        # Normalize to 0-1 range
        normalized = (hash_value % 10000) / 10000.0
        return normalized < percentage

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

    def get_flag(self, key: str) -> FeatureFlag | None:
        """Get a specific feature flag."""
        return self._flags.get(key)


# Global feature flag manager
_feature_flag_manager: FeatureFlagManager | None = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get the global feature flag manager."""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager


# ─── A/B Experiments ─────────────────────────────────────────────────────────


@dataclass
class ExperimentVariant:
    """A variant in an A/B experiment."""

    name: str
    config: dict[str, Any]
    weight: float = 1.0  # Relative weight for assignment


@dataclass
class Experiment:
    """A/B experiment definition."""

    key: str
    name: str
    description: str
    variants: list[ExperimentVariant]
    status: str = "draft"  # draft, running, paused, completed
    start_time: datetime | None = None
    end_time: datetime | None = None
    targeting_rules: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ExperimentManager:
    """Manages A/B experiments with consistent assignment."""

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Load experiments from database."""
        if self._initialized:
            return

        try:
            exp_coll = get_collection(Collections.EXPERIMENTS)
            cursor = exp_coll.find({})
            async for doc in cursor:
                variants = [
                    ExperimentVariant(
                        name=v["name"],
                        config=v["config"],
                        weight=v.get("weight", 1.0),
                    )
                    for v in doc.get("variants", [])
                ]
                experiment = Experiment(
                    key=doc["key"],
                    name=doc["name"],
                    description=doc.get("description", ""),
                    variants=variants,
                    status=doc.get("status", "draft"),
                    start_time=doc.get("start_time"),
                    end_time=doc.get("end_time"),
                    targeting_rules=doc.get("targeting_rules", []),
                    created_at=doc.get("created_at", datetime.now(UTC)),
                    updated_at=doc.get("updated_at", datetime.now(UTC)),
                )
                self._experiments[experiment.key] = experiment

            self._initialized = True
            logger.info("Experiments loaded", count=len(self._experiments))
        except Exception as exc:
            logger.warning("Failed to load experiments", error=str(exc))
            self._initialized = True

    def get_variant(
        self,
        experiment_key: str,
        user_id: str,
        context: dict[str, Any] | None = None,
    ) -> ExperimentVariant | None:
        """
        Get the assigned variant for a user in an experiment.

        Uses consistent hashing for deterministic assignment.
        """
        experiment = self._experiments.get(experiment_key)
        if not experiment:
            return None

        if experiment.status != "running":
            return None

        # Check time bounds
        now = datetime.now(UTC)
        if experiment.start_time and now < experiment.start_time:
            return None
        if experiment.end_time and now > experiment.end_time:
            return None

        # Check targeting rules
        if experiment.targeting_rules and context:
            matches = False
            for rule in experiment.targeting_rules:
                if self._matches_rule(rule, context):
                    matches = True
                    break
            if not matches:
                return None

        # Consistent variant assignment
        return self._assign_variant(user_id, experiment)

    def _assign_variant(self, user_id: str, experiment: Experiment) -> ExperimentVariant | None:
        """Assign user to variant using consistent hashing."""
        if not experiment.variants:
            return None

        # Create hash from user_id + experiment_key for deterministic assignment
        hash_input = f"{user_id}:{experiment.key}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)

        # Calculate cumulative weights
        total_weight = sum(v.weight for v in experiment.variants)
        normalized_hash = (hash_value % 10000) / 10000.0

        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.weight / total_weight
            if normalized_hash < cumulative:
                return variant

        # Fallback to last variant
        return experiment.variants[-1]

    def _matches_rule(self, rule: dict[str, Any], context: dict[str, Any]) -> bool:
        """Check if context matches a targeting rule."""
        attribute = rule.get("attribute")
        operator = rule.get("operator", "equals")
        values = rule.get("values", [])

        context_value = context.get(attribute)
        if context_value is None:
            return False

        if operator == "equals":
            return context_value in values
        elif operator == "in":
            return context_value in values
        elif operator == "contains":
            return any(v in str(context_value) for v in values)
        elif operator == "starts_with":
            return any(str(context_value).startswith(v) for v in values)
        elif operator == "gt":
            return float(context_value) > float(values[0]) if values else False
        elif operator == "lt":
            return float(context_value) < float(values[0]) if values else False

        return False

    async def create_experiment(self, experiment: Experiment) -> None:
        """Create a new experiment."""
        experiment.updated_at = datetime.now(UTC)
        self._experiments[experiment.key] = experiment

        exp_coll = get_collection(Collections.EXPERIMENTS)
        await exp_coll.update_one(
            {"key": experiment.key},
            {
                "$set": {
                    "key": experiment.key,
                    "name": experiment.name,
                    "description": experiment.description,
                    "variants": [
                        {"name": v.name, "config": v.config, "weight": v.weight}
                        for v in experiment.variants
                    ],
                    "status": experiment.status,
                    "start_time": experiment.start_time,
                    "end_time": experiment.end_time,
                    "targeting_rules": experiment.targeting_rules,
                    "updated_at": experiment.updated_at,
                },
                "$setOnInsert": {"created_at": experiment.created_at},
            },
            upsert=True,
        )

    async def update_experiment_status(self, key: str, status: str) -> bool:
        """Update experiment status (running, paused, completed)."""
        if key not in self._experiments:
            return False

        self._experiments[key].status = status
        self._experiments[key].updated_at = datetime.now(UTC)

        exp_coll = get_collection(Collections.EXPERIMENTS)
        result = await exp_coll.update_one(
            {"key": key},
            {"$set": {"status": status, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0


_experiment_manager: ExperimentManager | None = None


def get_experiment_manager() -> ExperimentManager:
    """Get the global experiment manager."""
    global _experiment_manager
    if _experiment_manager is None:
        _experiment_manager = ExperimentManager()
    return _experiment_manager


# ─── Metrics Collection ─────────────────────────────────────────────────────


@dataclass
class ExperimentMetrics:
    """Metrics for an experiment variant."""

    experiment_key: str
    variant_name: str
    assignments: int = 0
    conversions: int = 0
    total_latency_ms: float = 0.0
    error_count: int = 0
    custom_metrics: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    @property
    def conversion_rate(self) -> float:
        if self.assignments == 0:
            return 0.0
        return self.conversions / self.assignments

    @property
    def avg_latency_ms(self) -> float:
        if self.assignments == 0:
            return 0.0
        return self.total_latency_ms / self.assignments


class MetricsCollector:
    """Collects and aggregates experiment metrics."""

    def __init__(self):
        self._metrics: dict[str, dict[str, ExperimentMetrics]] = defaultdict(dict)
        self._buffer: list[dict[str, Any]] = []
        self._flush_interval = 60  # seconds
        self._last_flush = time.time()

    def record_assignment(self, experiment_key: str, variant_name: str, user_id: str) -> None:
        """Record a user assignment to an experiment variant."""
        metrics_key = f"{experiment_key}:{variant_name}"
        if variant_name not in self._metrics[experiment_key]:
            self._metrics[experiment_key][variant_name] = ExperimentMetrics(
                experiment_key=experiment_key,
                variant_name=variant_name,
            )
        self._metrics[experiment_key][variant_name].assignments += 1

        # Buffer for persistence
        self._buffer.append(
            {
                "type": "assignment",
                "experiment_key": experiment_key,
                "variant_name": variant_name,
                "user_id": user_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        self._maybe_flush()

    def record_conversion(
        self,
        experiment_key: str,
        variant_name: str,
        user_id: str,
        conversion_value: float = 1.0,
    ) -> None:
        """Record a conversion event."""
        if experiment_key in self._metrics and variant_name in self._metrics[experiment_key]:
            self._metrics[experiment_key][variant_name].conversions += conversion_value

        self._buffer.append(
            {
                "type": "conversion",
                "experiment_key": experiment_key,
                "variant_name": variant_name,
                "user_id": user_id,
                "value": conversion_value,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        self._maybe_flush()

    def record_latency(self, experiment_key: str, variant_name: str, latency_ms: float) -> None:
        """Record latency for an experiment variant."""
        if experiment_key in self._metrics and variant_name in self._metrics[experiment_key]:
            self._metrics[experiment_key][variant_name].total_latency_ms += latency_ms

    def record_error(self, experiment_key: str, variant_name: str) -> None:
        """Record an error for an experiment variant."""
        if experiment_key in self._metrics and variant_name in self._metrics[experiment_key]:
            self._metrics[experiment_key][variant_name].error_count += 1

    def record_custom_metric(
        self,
        experiment_key: str,
        variant_name: str,
        metric_name: str,
        value: float,
    ) -> None:
        """Record a custom metric."""
        if experiment_key in self._metrics and variant_name in self._metrics[experiment_key]:
            self._metrics[experiment_key][variant_name].custom_metrics[metric_name] += value

    def get_metrics(self, experiment_key: str) -> dict[str, ExperimentMetrics]:
        """Get metrics for an experiment."""
        return self._metrics.get(experiment_key, {})

    def get_all_metrics(self) -> dict[str, dict[str, ExperimentMetrics]]:
        """Get all metrics."""
        return dict(self._metrics)

    def _maybe_flush(self) -> None:
        """Flush buffer to database periodically."""
        if time.time() - self._last_flush >= self._flush_interval and self._buffer:
            # In production, this would write to a time-series DB or analytics store
            self._buffer.clear()
            self._last_flush = time.time()

    async def flush(self) -> None:
        """Force flush buffer to database."""
        if self._buffer:
            # Persist to MongoDB
            try:
                metrics_coll = get_collection(Collections.EXPERIMENT_METRICS)
                if self._buffer:
                    await metrics_coll.insert_many(self._buffer)
                self._buffer.clear()
                self._last_flush = time.time()
            except Exception as exc:
                logger.error("Failed to flush metrics", error=str(exc))


_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# ─── Integration Helpers ────────────────────────────────────────────────────


def create_agent_config_from_experiment(
    experiment_key: str,
    user_id: str,
    base_config: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], ExperimentVariant | None]:
    """
    Create agent configuration from experiment variant.

    Returns tuple of (merged_config, variant) where variant is None if not in experiment.
    """
    exp_manager = get_experiment_manager()
    variant = exp_manager.get_variant(experiment_key, user_id, context)

    if not variant:
        return base_config, None

    # Record assignment
    metrics = get_metrics_collector()
    metrics.record_assignment(experiment_key, variant.name, user_id)

    # Merge variant config with base config
    merged_config = {**base_config, **variant.config}

    return merged_config, variant


async def run_with_experiment_tracking(
    experiment_key: str,
    variant_name: str,
    user_id: str,
    operation: Callable,
    *args,
    **kwargs,
) -> Any:
    """
    Run an operation with experiment tracking.

    Records latency, errors, and allows custom metrics.
    """
    start_time = time.perf_counter()
    metrics = get_metrics_collector()

    try:
        result = await operation(*args, **kwargs)
        latency_ms = (time.perf_counter() - start_time) * 1000
        metrics.record_latency(experiment_key, variant_name, latency_ms)
        return result
    except Exception:
        latency_ms = (time.perf_counter() - start_time) * 1000
        metrics.record_latency(experiment_key, variant_name, latency_ms)
        metrics.record_error(experiment_key, variant_name)
        raise


# ─── API Endpoints for Feature Flags & Experiments ──────────────────────────


async def setup_experimentation_router() -> None:
    """Set up API router for feature flags and experiments."""
    from collections.abc import Mapping

    from fastapi import APIRouter, Depends, HTTPException

    from app.api.deps import get_current_user

    router = APIRouter(prefix="/experimentation", tags=["experimentation"])

    # Feature Flag endpoints
    @router.get("/flags")
    async def list_feature_flags(current_user: Mapping[str, Any] = Depends(get_current_user)):
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

    @router.get("/flags/{key}")
    async def get_feature_flag(
        key: str, current_user: Mapping[str, Any] = Depends(get_current_user)
    ):
        manager = get_feature_flag_manager()
        await manager.initialize()
        flag = manager.get_flag(key)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        return {
            "key": flag.key,
            "enabled": flag.enabled,
            "rollout_percentage": flag.rollout_percentage,
            "targeting_rules": flag.targeting_rules,
            "description": flag.description,
        }

    @router.post("/flags")
    async def create_feature_flag(
        key: str,
        enabled: bool = False,
        rollout_percentage: float = 0.0,
        targeting_rules: list[dict[str, Any]] = None,
        description: str = "",
        current_user: Mapping[str, Any] = Depends(get_current_user),
    ):
        manager = get_feature_flag_manager()
        await manager.initialize()
        flag = FeatureFlag(
            key=key,
            enabled=enabled,
            rollout_percentage=rollout_percentage,
            targeting_rules=targeting_rules or [],
            description=description,
        )
        await manager.set_flag(flag)
        return {"status": "created", "key": key}

    @router.patch("/flags/{key}")
    async def update_feature_flag(
        key: str,
        enabled: bool | None = None,
        rollout_percentage: float | None = None,
        targeting_rules: list[dict[str, Any]] | None = None,
        description: str | None = None,
        current_user: Mapping[str, Any] = Depends(get_current_user),
    ):
        manager = get_feature_flag_manager()
        await manager.initialize()
        flag = manager.get_flag(key)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")

        if enabled is not None:
            flag.enabled = enabled
        if rollout_percentage is not None:
            flag.rollout_percentage = rollout_percentage
        if targeting_rules is not None:
            flag.targeting_rules = targeting_rules
        if description is not None:
            flag.description = description

        await manager.set_flag(flag)
        return {"status": "updated", "key": key}

    @router.delete("/flags/{key}")
    async def delete_feature_flag(
        key: str, current_user: Mapping[str, Any] = Depends(get_current_user)
    ):
        manager = get_feature_flag_manager()
        await manager.initialize()
        success = await manager.delete_flag(key)
        if not success:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        return {"status": "deleted", "key": key}

    # Experiment endpoints
    @router.get("/experiments")
    async def list_experiments(current_user: Mapping[str, Any] = Depends(get_current_user)):
        manager = get_experiment_manager()
        await manager.initialize()
        return {
            key: {
                "name": exp.name,
                "description": exp.description,
                "status": exp.status,
                "variants": [
                    {"name": v.name, "config": v.config, "weight": v.weight} for v in exp.variants
                ],
                "start_time": exp.start_time.isoformat() if exp.start_time else None,
                "end_time": exp.end_time.isoformat() if exp.end_time else None,
            }
            for key, exp in manager._experiments.items()
        }

    @router.post("/experiments")
    async def create_experiment(
        key: str,
        name: str,
        description: str,
        variants: list[dict[str, Any]],
        current_user: Mapping[str, Any] = Depends(get_current_user),
    ):
        manager = get_experiment_manager()
        await manager.initialize()

        exp_variants = [
            ExperimentVariant(name=v["name"], config=v["config"], weight=v.get("weight", 1.0))
            for v in variants
        ]

        experiment = Experiment(
            key=key,
            name=name,
            description=description,
            variants=exp_variants,
        )

        await manager.create_experiment(experiment)
        return {"status": "created", "key": key}

    @router.post("/experiments/{key}/start")
    async def start_experiment(
        key: str, current_user: Mapping[str, Any] = Depends(get_current_user)
    ):
        manager = get_experiment_manager()
        await manager.initialize()
        success = await manager.update_experiment_status(key, "running")
        if not success:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "started", "key": key}

    @router.post("/experiments/{key}/pause")
    async def pause_experiment(
        key: str, current_user: Mapping[str, Any] = Depends(get_current_user)
    ):
        manager = get_experiment_manager()
        await manager.initialize()
        success = await manager.update_experiment_status(key, "paused")
        if not success:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "paused", "key": key}

    @router.get("/experiments/{key}/metrics")
    async def get_experiment_metrics(
        key: str, current_user: Mapping[str, Any] = Depends(get_current_user)
    ):
        metrics_collector = get_metrics_collector()
        metrics = metrics_collector.get_metrics(key)
        return {
            variant_name: {
                "assignments": m.assignments,
                "conversions": m.conversions,
                "conversion_rate": m.conversion_rate,
                "avg_latency_ms": m.avg_latency_ms,
                "error_count": m.error_count,
                "custom_metrics": dict(m.custom_metrics),
            }
            for variant_name, m in metrics.items()
        }

    return router
