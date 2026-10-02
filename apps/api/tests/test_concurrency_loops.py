"""
Cross-event-loop safety of the shared concurrency semaphore.

`asyncio.Semaphore` binds to the loop that first awaits it. The module held a
single global, so the moment a second loop touched it the acquire blew up with
"Semaphore is bound to a different event loop" — at the worst possible moment,
under concurrency, with a paid request already in flight.

The second loop is not hypothetical: the synchronous `.generate()` path wraps
its coroutine in `asyncio.run()`, which creates a fresh loop every call.

These tests drive two real loops and assert they each get a working semaphore of
the same capacity.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.system import concurrency
from app.core.system.concurrency import get_global_semaphore, reset_global_semaphore


@pytest.fixture(autouse=True)
def _reset():
    yield
    asyncio.run(reset_global_semaphore())


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


def test_two_loops_get_distinct_semaphores():
    """The core invariant: no object is shared across loops."""

    async def first():
        return get_global_semaphore()

    sem_a = asyncio.run(first())
    sem_b = asyncio.run(first())

    assert sem_a is not sem_b, (
        "the same semaphore object was handed to two event loops — the second "
        "loop will fail to acquire it"
    )


def test_semaphore_is_usable_from_a_second_loop():
    """The bug users would actually hit: RuntimeError on acquire.

    Contention is what makes it real. An uncontended acquire returns without
    touching the loop, so a shared-singleton semaphore stays invisible until the
    limiter saturates — exactly when a queued request is already waiting on a
    paid endpoint. Each loop here therefore has to become an actual *waiter*,
    which is what binds an asyncio primitive to its loop.
    """
    limit = concurrency._compute_concurrency()

    async def drain_and_wait():
        sem = get_global_semaphore()
        held = []
        for _ in range(limit):
            await sem.acquire()
            held.append(sem)
        # Become a real waiter, then immediately satisfy it. This is the call
        # that binds the semaphore to the running loop.
        waiter = asyncio.create_task(sem.acquire())
        await asyncio.sleep(0)
        sem.release()
        await asyncio.wait_for(waiter, timeout=2.0)
        for _ in held:
            sem.release()
        return "ok"

    assert asyncio.run(drain_and_wait()) == "ok"
    # A second, independent loop must be able to do the same.
    assert asyncio.run(drain_and_wait()) == "ok"


def test_same_loop_reuses_one_semaphore():
    """Within a loop it must still be a singleton, or the concurrency cap would
    be meaningless. Per-loop keying must not weaken the per-loop guarantee."""

    async def check():
        assert get_global_semaphore() is get_global_semaphore()

    asyncio.run(check())


def test_semaphore_actually_limits_concurrency():
    """A per-loop dict must not turn the limiter into a no-op."""
    limit = concurrency._compute_concurrency()
    observed: list[int] = []
    active = 0

    async def worker():
        nonlocal active
        async with get_global_semaphore():
            active += 1
            observed.append(active)
            await asyncio.sleep(0)
            active -= 1

    async def main():
        await asyncio.gather(*(worker() for _ in range(limit * 2)))

    asyncio.run(main())
    assert max(observed) <= limit, f"observed {max(observed)} concurrent, limit is {limit}"


def test_no_running_loop_does_not_raise():
    """Called from sync setup code, get_global_semaphore must not blow up on
    get_running_loop(). It cannot key on a loop that does not exist, so it hands
    back a detached semaphore that binds lazily when first awaited."""
    sem = get_global_semaphore()
    assert isinstance(sem, asyncio.Semaphore)

    # And that detached semaphore must still work once awaited inside a loop.
    async def use_it():
        async with sem:
            return "acquired"

    assert asyncio.run(use_it()) == "acquired"


def test_reset_clears_every_loop():
    async def grab():
        return get_global_semaphore()

    a = asyncio.run(grab())
    asyncio.run(reset_global_semaphore())
    b = asyncio.run(grab())
    assert a is not b, "reset did not clear the cached semaphores"
