"""
TRUSTRAG — Analysis service: SSE pub/sub.

In-process Server-Sent Events publisher/subscriber for real-time analysis
progress updates.
"""

from __future__ import annotations

import asyncio

__all__ = [
    "_analysis_subscribers",
    "_publish_analysis_event",
    "_subscribe_to_analysis",
    "_subscribers_lock",
    "_unsubscribe_from_analysis",
]

# Maps analysis_id -> set of asyncio.Queue subscribers
_analysis_subscribers: dict[str, set[asyncio.Queue]] = {}
_subscribers_lock = asyncio.Lock()


async def _subscribe_to_analysis(analysis_id: str) -> asyncio.Queue:
    """Subscribe to real-time events for an analysis."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    async with _subscribers_lock:
        if analysis_id not in _analysis_subscribers:
            _analysis_subscribers[analysis_id] = set()
        _analysis_subscribers[analysis_id].add(queue)
    return queue


async def _unsubscribe_from_analysis(analysis_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from analysis events."""
    async with _subscribers_lock:
        if analysis_id in _analysis_subscribers:
            _analysis_subscribers[analysis_id].discard(queue)


async def _publish_analysis_event(analysis_id: str, event: dict) -> None:
    """Publish an event to all subscribers of an analysis."""
    async with _subscribers_lock:
        queues = list(_analysis_subscribers.get(analysis_id, set()))
    for queue in queues:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
