"""Guards for the frontend/backend contract validator itself.

A broken path constant used to make WEB_DIR point at apps/apps/web, so the
extractor found zero frontend calls and the integration check reported
success without checking anything. These tests keep the validator honest.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
VALIDATOR = API_DIR / "scripts" / "verify" / "validate_integration.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_integration_under_test", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validator_points_at_the_real_repo_and_web_root():
    mod = _load_validator()
    assert mod.REPO.is_dir()
    assert (mod.REPO / ".git").exists() or (mod.REPO / "README.md").is_file()
    assert mod.WEB_DIR.is_dir(), f"WEB_DIR does not exist: {mod.WEB_DIR}"
    assert (mod.WEB_DIR / "src" / "services" / "api.js").is_file()


def test_validator_extracts_real_frontend_calls():
    mod = _load_validator()
    calls = mod._frontend_calls()
    total = sum(len(paths) for paths in calls.values())
    # The shipped frontend has ~25 distinct calls; a handful means the globs
    # or the WEB_DIR constant drifted again and the check became meaningless.
    assert total >= 20, f"only {total} frontend API calls extracted"
    assert {"GET", "POST"} <= set(calls)
    assert any("/api/v1/analyses" in p for p in calls["GET"])
