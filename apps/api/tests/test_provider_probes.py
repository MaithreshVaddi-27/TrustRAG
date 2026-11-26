"""
Regression tests for the provider status probes (audit change B3.1).

`GET /api/v1/models/providers` took **2.6 s** because three defects compounded:

1. `check_mlx_status` probed five ports **sequentially**.
2. `_fetch_json_with_retry` slept 0.5 s before re-raising — and because the
   `raise` sat *inside* the `except`, the retry never happened. The sleep was
   pure delay: five ports x 0.5 s = 2.5 s of sleeping for a provider that was
   simply not running.
3. The health checks used `async with _shared_http_client(...)`, and
   `httpx.AsyncClient.__aexit__` **closes** the client — so the shared
   connection pool was destroyed and rebuilt on every check.

These tests pin all three.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import httpx
import pytest

from app.llm.providers import health
from app.llm.providers.base import _shared_http_client


class _FakeClient:
    """Stands in for the pooled httpx client."""

    def __init__(self, handler=None):
        self._handler = handler
        self.requested: list[str] = []
        self.is_closed = False

    async def get(self, url):
        self.requested.append(url)
        if self._handler is not None:
            return await self._handler(url)
        raise httpx.ConnectError("All connection attempts failed")


def _refusing_client():
    async def _handler(_url):
        raise httpx.ConnectError("All connection attempts failed")

    return _FakeClient(_handler)


def _async_value(value):
    """An awaitable that returns `value` — stands in for an async discovery
    function without needing a full mock object."""

    async def _inner():
        return value

    return _inner


# ─── The retry ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_refused_connection_does_not_sleep_before_failing():
    """A server that is not running must fail fast, not after a 0.5 s nap.

    This is what made the MLX probe cost 2.5 s of pure sleeping.
    """
    sleeps: list[float] = []

    async def _record_sleep(delay):
        sleeps.append(delay)

    client = _refusing_client()
    with patch.object(health.asyncio, "sleep", _record_sleep):
        with pytest.raises(httpx.ConnectError):
            await health._fetch_json_with_retry("http://127.0.0.1:8080/v1/models", client)

    assert sleeps == [], f"a refused connection must not be retried, slept {sleeps}"


@pytest.mark.asyncio
async def test_a_timeout_is_retried_once():
    """A slow (not dead) server is worth one more attempt."""
    attempts = 0

    async def _handler(_url):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("too slow")
        return httpx.Response(200, json={"data": []})

    client = _FakeClient(_handler)
    sleeps: list[float] = []

    async def _record_sleep(delay):
        sleeps.append(delay)

    with patch.object(health.asyncio, "sleep", _record_sleep):
        res = await health._fetch_json_with_retry("http://127.0.0.1:8080/v1/models", client)

    assert res.status_code == 200
    assert attempts == 2
    assert sleeps == [0.5]


# ─── The MLX probe ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mlx_probe_does_not_sleep_between_refused_ports():
    """Five refused ports must not cost five sleeps."""
    sleeps: list[float] = []

    async def _record_sleep(delay):
        sleeps.append(delay)

    client = _refusing_client()
    with (
        patch.object(health, "_shared_http_client", lambda *a, **k: client),
        patch.object(health.asyncio, "sleep", _record_sleep),
    ):
        result = await health.check_mlx_status()

    assert result["connected"] is False
    assert len(client.requested) == 5, "the probe must still check every candidate port"
    assert sleeps == [], f"the probe slept {sleeps} for a provider that is not running"


@pytest.mark.asyncio
async def test_mlx_probe_checks_the_ports_concurrently():
    """Sequential probing cost five round trips; the ports are independent."""
    delay = 0.05

    async def _handler(_url):
        await asyncio.sleep(delay)
        raise httpx.ConnectError("All connection attempts failed")

    client = _FakeClient(_handler)
    with patch.object(health, "_shared_http_client", lambda *a, **k: client):
        t0 = time.perf_counter()
        await health.check_mlx_status()
        elapsed = time.perf_counter() - t0

    # Sequential would be 5 x delay; concurrent is ~1 x delay.
    assert elapsed < delay * 3, f"ports were probed sequentially ({elapsed:.3f}s for 5 x {delay}s)"


@pytest.mark.asyncio
async def test_mlx_probe_uses_one_pooled_client_for_every_port():
    """One client, five origins — httpx pools per origin inside the client."""
    seen: list[object] = []

    def _factory(*args, **kwargs):
        client = _refusing_client()
        seen.append(client)
        return client

    with patch.object(health, "_shared_http_client", _factory):
        await health.check_mlx_status()

    assert len(seen) == 1, "the probe created more than one HTTP client"
    assert len(seen[0].requested) == 5


# ─── The pooled client must survive the health checks ───────────────────────


@pytest.mark.asyncio
async def test_health_checks_do_not_close_the_pooled_client():
    """`async with` on an httpx client closes it — and with it the pool."""
    client = _FakeClient()

    async def _handler(url):
        return httpx.Response(200, json={"models": [], "data": []})

    client._handler = _handler

    with patch.object(health, "_shared_http_client", lambda *a, **k: client):
        await health.check_ollama_status()
        await health.check_llamacpp_status()

    assert client.is_closed is False, "the health check closed the shared client"


def test_shared_http_client_is_reused_and_not_closed_by_a_check():
    """The pool must survive across checks — that is the whole point of it."""
    first = _shared_http_client("http://127.0.0.1:11434", 120.0)
    second = _shared_http_client("http://127.0.0.1:11434", 120.0)
    assert first is second
    assert not first.is_closed


def test_shared_http_client_separates_connect_timeouts():
    """A probe (short connect timeout) must not share a pool with a long call."""
    probe = _shared_http_client("http://127.0.0.1:11434", 3.0, connect_timeout=1.5)
    call = _shared_http_client("http://127.0.0.1:11434", 3.0)
    assert probe is not call


# ─── The model list must not repeat itself ───────────────────────────────────


@pytest.mark.asyncio
async def test_the_ollama_model_list_has_no_duplicates():
    """The CLI listing and the server listing report the same models.

    Merging them verbatim listed every model twice, and the frontend renders
    this array as one <option> per entry — so the model dropdown showed every
    model twice, with duplicated React keys.
    """
    cli_models = ["gemma3:1b", "qwen3:1.7b"]

    async def _handler(_url):
        return httpx.Response(
            200,
            json={"models": [{"name": "gemma3:1b"}, {"name": "qwen3:1.7b"}]},
        )

    client = _FakeClient(_handler)

    with (
        patch.object(health, "_shared_http_client", lambda *a, **k: client),
        patch(
            "app.llm.local_llm.discover_ollama_cli_models",
            _async_value(cli_models),
        ),
    ):
        status = await health.check_ollama_status()

    assert status["models"] == cli_models, f"duplicated model list: {status['models']}"


@pytest.mark.asyncio
async def test_the_ollama_default_model_is_the_first_distinct_model():
    """The default is what the dropdown falls back to, so it must be a model
    that is actually in the list — not the second copy of the first one."""

    async def _handler(_url):
        return httpx.Response(200, json={"models": [{"name": "gemma3:1b"}]})

    client = _FakeClient(_handler)

    with (
        patch.object(health, "_shared_http_client", lambda *a, **k: client),
        patch(
            "app.llm.local_llm.discover_ollama_cli_models",
            _async_value(["gemma3:1b"]),
        ),
    ):
        status = await health.check_ollama_status()

    assert status["default_model"] == "gemma3:1b"
    assert status["default_model"] in status["models"]
