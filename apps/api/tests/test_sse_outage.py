"""
SSE termination on the retrieval-outage path (audit finding).

`sse_event_generator` returns only when it observes a terminal event. The
outage path emits `analysis.outage` and then the pipeline is finished — but
`analysis.outage` was not in the terminal set, so the generator spun on
heartbeats until its 360-tick bound (~6 minutes), holding the subscriber queue
for an analysis that was definitively over.

The frontend falls back to polling, so the user eventually sees the result, but
every outage burned a six-minute idle connection per subscriber.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services import analysis_service


def _terminal_events() -> set[str]:
    """Read the terminal set the generator actually compares against.

    Parsed from the source rather than duplicated, so this test cannot pass by
    agreeing with a stale copy of the list.
    """
    import inspect
    import re

    src = inspect.getsource(analysis_service.sse_event_generator)
    match = re.search(r"terminal_events\s*=\s*\{(.*?)\}", src, re.S)
    assert match, "could not locate terminal_events in sse_event_generator"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def test_outage_is_a_terminal_event():
    """The pipeline is finished when it emits an outage, so the stream must end."""
    assert "analysis.outage" in _terminal_events(), (
        "analysis.outage is not terminal: the SSE generator will heartbeat until "
        "its tick bound expires instead of closing"
    )


@pytest.mark.parametrize(
    "event", ["analysis.completed", "analysis.abstained", "analysis.failed", "analysis.outage"]
)
def test_every_pipeline_end_is_terminal(event):
    """Every way the pipeline can finish must close the stream. Missing one is
    exactly the outage bug."""
    assert event in _terminal_events()


async def _collect(agen):
    return [event async for event in agen]


@pytest.mark.asyncio
async def test_generator_returns_promptly_on_outage():
    """End-to-end: an outage event must close the generator immediately rather
    than after ~360 one-second heartbeats."""
    queue: asyncio.Queue = asyncio.Queue()
    await queue.put({"event": "analysis.outage", "data": {"message": "qdrant down"}})

    async def _fake_subscribe(_analysis_id):
        return queue

    with (
        patch.object(analysis_service, "_subscribe_to_analysis", _fake_subscribe),
        patch.object(analysis_service, "get_analysis", AsyncMock(return_value={})),
    ):
        agen = analysis_service.sse_event_generator("a" * 24, "u" * 24)
        started = asyncio.get_running_loop().time()
        # Bound the collection so a non-terminal outage event fails in seconds
        # instead of hanging for the full 360-tick (~6 min) heartbeat budget.
        events = await asyncio.wait_for(_collect(agen), timeout=10.0)
        elapsed = asyncio.get_running_loop().time() - started

    assert len(events) == 1
    assert events[0]["event"] == "analysis.outage"
    # The 360-tick bound would take ~6 minutes; anything near that means the
    # generator is still spinning after the pipeline ended.
    assert elapsed < 5, f"generator took {elapsed:.1f}s to close after a terminal event"
