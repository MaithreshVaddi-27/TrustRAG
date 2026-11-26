"""
Regression tests for the settings cache (audit change B3.2).

`get_settings()` used to rebuild `Settings()` on every call, which made
pydantic-settings re-read and re-parse **five env files from disk** — 1.46 ms
per call at 29 call sites, including the per-request auth path
(`security._decode_jwt`).

The cache is keyed on a fingerprint of everything `Settings()` reads, so a
cache hit can never serve a stale value. These tests pin that guarantee: the
cache must exist, and an environment-variable change or an edited env file
must both be visible on the very next call.
"""

from __future__ import annotations

import os
import time

from app.config.settings import Settings, clear_settings_cache, get_settings


def test_repeated_calls_return_the_same_cached_instance():
    """The cache exists — otherwise there is nothing to prove."""
    clear_settings_cache()
    first = get_settings()
    second = get_settings()
    assert first is second


def test_an_environment_variable_change_is_picked_up(monkeypatch):
    """Env vars win over the env files, so they must invalidate the cache."""
    clear_settings_cache()
    monkeypatch.setenv("MONGODB_DATABASE", "cache_probe_db")
    assert get_settings().mongodb_database == "cache_probe_db"

    monkeypatch.setenv("MONGODB_DATABASE", "cache_probe_db_2")
    assert get_settings().mongodb_database == "cache_probe_db_2"

    monkeypatch.delenv("MONGODB_DATABASE", raising=False)
    assert get_settings().mongodb_database != "cache_probe_db_2"


def test_an_edited_env_file_is_picked_up(monkeypatch, tmp_path):
    """An operator editing `.env` must take effect without a restart."""
    clear_settings_cache()
    env_file = tmp_path / ".env"
    env_file.write_text("MONGODB_DATABASE=from_file_one\n")

    monkeypatch.setitem(Settings.model_config, "env_file", (str(env_file),))
    monkeypatch.delenv("MONGODB_DATABASE", raising=False)

    assert get_settings().mongodb_database == "from_file_one"

    # Rewrite the file and move its mtime forward, so the change is visible
    # even on a filesystem with a coarse timestamp resolution.
    env_file.write_text("MONGODB_DATABASE=from_file_two\n")
    stat = env_file.stat()
    os.utime(env_file, (stat.st_atime, stat.st_mtime + 10))

    assert get_settings().mongodb_database == "from_file_two"


def test_creating_a_new_env_file_is_picked_up(monkeypatch, tmp_path):
    """A file that did not exist yet must not be cached as "missing"."""
    clear_settings_cache()
    env_file = tmp_path / ".env"

    monkeypatch.setitem(Settings.model_config, "env_file", (str(env_file),))
    monkeypatch.delenv("MONGODB_DATABASE", raising=False)
    assert get_settings().mongodb_database != "from_new_file"

    env_file.write_text("MONGODB_DATABASE=from_new_file\n")
    assert get_settings().mongodb_database == "from_new_file"


def test_the_cache_is_much_cheaper_than_rebuilding():
    """The whole point: the fingerprint must be far cheaper than a rebuild."""
    clear_settings_cache()
    get_settings()  # warm the cache

    n = 200
    start = time.perf_counter()
    for _ in range(n):
        get_settings()
    cached_us = (time.perf_counter() - start) / n * 1e6

    start = time.perf_counter()
    for _ in range(20):
        Settings()  # type: ignore[call-arg]
    fresh_us = (time.perf_counter() - start) / 20 * 1e6

    assert cached_us < fresh_us / 5, (
        f"cached {cached_us:.0f}us vs fresh {fresh_us:.0f}us — the cache is not paying off"
    )
