"""Tests for the feature-flag manager and the /experimentation/flags endpoint.

The regression these exist for: `Collections.FEATURE_FLAGS` did not exist, so
`FeatureFlagManager.initialize()` raised AttributeError, which a bare
`except Exception` swallowed while still setting `_initialized = True`. The
endpoint then returned `{}` for the lifetime of the process and never retried,
with only a WARNING line to show for it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core import experimentation
from app.core.experimentation import FeatureFlag, FeatureFlagManager
from app.db.mongodb import Collections

pytestmark = pytest.mark.asyncio


def _flag_doc(key: str, enabled: bool = True, pct: float = 0.5) -> dict:
    return {
        "key": key,
        "enabled": enabled,
        "rollout_percentage": pct,
        "targeting_rules": [{"attribute": "tier", "op": "eq", "value": "pro"}],
        "description": "a flag",
    }


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        async def gen():
            for d in self._docs:
                yield d

        return gen()


class _FakeCollection:
    def __init__(self, docs):
        self._docs = docs
        self.updated = []
        self.deleted = []

    def find(self, *_a, **_kw):
        return _FakeCursor(self._docs)

    async def update_one(self, filt, update, **_kw):
        self.updated.append((filt, update))
        return AsyncMock()

    async def delete_one(self, filt):
        self.deleted.append(filt)
        return AsyncMock(deleted_count=1)


async def test_feature_flags_collection_name_exists():
    """The name the manager resolves must actually be defined.

    Referencing an undefined attribute is exactly how this broke, so the
    constant's existence is asserted directly rather than inferred.
    """
    assert Collections.FEATURE_FLAGS == "feature_flags"


async def test_initialize_loads_flags():
    manager = FeatureFlagManager()
    coll = _FakeCollection([_flag_doc("beta_ui")])
    with patch.object(experimentation, "get_collection", return_value=coll):
        await manager.initialize()

    assert "beta_ui" in manager.get_all_flags()
    assert manager.get_all_flags()["beta_ui"].enabled is True
    assert manager.get_all_flags()["beta_ui"].rollout_percentage == 0.5


async def test_initialize_retries_after_transient_failure():
    """A failed load must not permanently disable flags.

    Previously the except branch set `_initialized = True` ("don't retry on
    every call"), so one transient Mongo error silenced flags until restart.
    """
    manager = FeatureFlagManager()
    coll = _FakeCollection([_flag_doc("recovered")])

    calls = {"n": 0}

    def flaky(_name):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("mongo blip")
        return coll

    with patch.object(experimentation, "get_collection", side_effect=flaky):
        await manager.initialize()
        assert manager.get_all_flags() == {}, "first failure should load nothing"

        await manager.initialize()  # must not be a no-op

    assert "recovered" in manager.get_all_flags(), "second attempt should have loaded"


async def test_initialize_is_idempotent_once_successful():
    manager = FeatureFlagManager()
    coll = _FakeCollection([_flag_doc("a")])
    with patch.object(experimentation, "get_collection", return_value=coll) as gc:
        await manager.initialize()
        await manager.initialize()
    assert gc.call_count == 1, "should query mongo once after a successful load"


async def test_get_all_flags_returns_a_copy():
    """Callers must not be able to mutate the manager's internal dict."""
    manager = FeatureFlagManager()
    coll = _FakeCollection([_flag_doc("a")])
    with patch.object(experimentation, "get_collection", return_value=coll):
        await manager.initialize()
    snapshot = manager.get_all_flags()
    snapshot["injected"] = FeatureFlag(key="injected")
    assert "injected" not in manager.get_all_flags()


async def test_set_flag_upserts_and_delete_flag_round_trips():
    manager = FeatureFlagManager()
    coll = _FakeCollection([])
    with patch.object(experimentation, "get_collection", return_value=coll):
        await manager.set_flag(FeatureFlag(key="new_flag", enabled=True))
        assert coll.updated, "set_flag must persist"
        assert manager.get_all_flags()["new_flag"].enabled is True

        assert await manager.delete_flag("new_flag") is True
        assert coll.deleted == [{"key": "new_flag"}]
        assert "new_flag" not in manager.get_all_flags()

        assert await manager.delete_flag("absent") is False


async def test_flags_endpoint_returns_loaded_flags():
    """End-to-end through the real router function, not a mocked manager."""
    from app.api.v1.experimentation import list_feature_flags

    coll = _FakeCollection([_flag_doc("beta_ui", enabled=True, pct=0.25)])
    manager = FeatureFlagManager()
    with (
        patch.object(experimentation, "get_collection", return_value=coll),
        patch.object(experimentation, "get_feature_flag_manager", return_value=manager),
    ):
        out = await list_feature_flags(current_user={"sub": "u1"})

    assert out == {
        "beta_ui": {
            "enabled": True,
            "rollout_percentage": 0.25,
            "targeting_rules": [{"attribute": "tier", "op": "eq", "value": "pro"}],
            "description": "a flag",
        }
    }
