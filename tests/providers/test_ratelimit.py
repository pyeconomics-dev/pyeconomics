# tests/providers/test_ratelimit.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The limiter never lets more than N requests into any window of a declared limit."""

from __future__ import annotations

import threading
from typing import Final

import pytest
from fakes import FakeClock
from hypothesis import given
from hypothesis import strategies as st
from stubs import stub_info

from pyeconomics.data import RateLimit, RateLimitError
from pyeconomics.data.transport.ratelimit import (
    DEFAULT_MAX_WAIT,
    ProviderLimiter,
    RateLimiters,
)

SECOND: Final = "second"
MINUTE: Final = "minute"
DAY: Final = "day"


def limiter(
    *limits: RateLimit, clock: FakeClock | None = None, **kw: float
) -> tuple[ProviderLimiter, FakeClock]:
    clock = clock or FakeClock(0.0)
    return ProviderLimiter("demo", limits, clock.monotonic, **kw), clock


def grants(unit: ProviderLimiter, clock: FakeClock, gaps: list[float]) -> list[float]:
    """Acquire after each gap and return the time each request was granted."""
    times: list[float] = []
    for gap in gaps:
        clock.now += gap
        times.append(clock.now + unit.acquire(clock.sleep))
    return times


def test_a_burst_up_to_the_limit_goes_at_once_and_the_rest_wait_for_the_window() -> (
    None
):
    unit, clock = limiter(RateLimit(requests=2, per=SECOND))
    waits = [unit.acquire(clock.sleep) for _ in range(5)]
    assert waits == [0.0, 0.0, 1.0, 0.0, 1.0]  # grants at 0, 0, 1, 1, 2
    assert clock.now == 2.0


def test_no_limits_never_wait() -> None:
    unit, clock = limiter()
    assert [unit.acquire(clock.sleep) for _ in range(1_000)] == [0.0] * 1_000
    assert clock.slept == []


def test_a_request_after_the_window_has_passed_goes_at_once() -> None:
    unit, clock = limiter(RateLimit(requests=1, per=SECOND))
    unit.acquire(clock.sleep)
    clock.now += 5.0
    assert unit.acquire(clock.sleep) == 0.0


def test_the_slowest_limit_governs() -> None:
    unit, clock = limiter(
        RateLimit(requests=5, per=SECOND), RateLimit(requests=2, per=MINUTE)
    )
    assert [unit.acquire(clock.sleep) for _ in range(2)] == [0.0, 0.0]
    assert unit.acquire(clock.sleep) == 60.0


def test_a_wait_longer_than_the_cap_raises_and_reserves_nothing() -> None:
    unit, clock = limiter(RateLimit(requests=1, per=DAY))
    unit.acquire(clock.sleep)
    with pytest.raises(RateLimitError) as caught:
        unit.acquire(clock.sleep)
    assert caught.value.retry_after == 86_400.0
    assert caught.value.provider == "demo"
    assert clock.slept == []
    clock.now += 86_400.0  # the window passes: the refused request reserved nothing
    assert unit.acquire(clock.sleep) == 0.0


def test_a_wait_exactly_at_the_cap_is_slept() -> None:
    unit, clock = limiter(RateLimit(requests=1, per=MINUTE))
    unit.acquire(clock.sleep)
    assert unit.acquire(clock.sleep) == 60.0
    assert DEFAULT_MAX_WAIT == 60.0
    tight, tight_clock = limiter(RateLimit(requests=1, per=MINUTE), max_wait=59.0)
    tight.acquire(tight_clock.sleep)
    with pytest.raises(RateLimitError):
        tight.acquire(tight_clock.sleep)


def test_a_clock_that_stands_still_still_spaces_requests() -> None:
    unit, clock = limiter(RateLimit(requests=1, per=SECOND))
    assert [unit.acquire(lambda _s: None) for _ in range(4)] == [0.0, 1.0, 2.0, 3.0]
    assert clock.now == 0.0


@given(
    gaps=st.lists(st.floats(min_value=0.0, max_value=5.0), min_size=1, max_size=80),
    limits=st.lists(
        st.tuples(st.integers(1, 6), st.sampled_from([SECOND, MINUTE])),
        min_size=1,
        max_size=3,
        unique_by=lambda item: item[1],
    ),
)
def test_no_window_ever_holds_more_than_its_limit(
    gaps: list[float], limits: list[tuple[int, str]]
) -> None:
    declared = tuple(RateLimit(requests=n, per=per) for n, per in limits)  # type: ignore[arg-type]
    unit, clock = limiter(*declared, max_wait=1e9)
    times = grants(unit, clock, gaps)
    assert times == sorted(times)
    for limit in declared:
        for first, later in zip(times, times[limit.requests :], strict=False):
            assert later - first >= limit.window_seconds - 1e-6


def test_threads_share_one_allowance() -> None:
    unit, _ = limiter(RateLimit(requests=3, per=SECOND), max_wait=1e9)
    granted: list[float] = []
    lock = threading.Lock()

    def worker() -> None:
        for _ in range(10):
            wait = unit.acquire(lambda _s: None)  # the clock is fixed at 0
            with lock:
                granted.append(wait)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    times = sorted(granted)
    assert len(times) == 80
    assert all(
        later - first >= 1.0 - 1e-9
        for first, later in zip(times, times[3:], strict=False)
    )


def test_limiters_are_kept_per_provider_and_per_declared_limits() -> None:
    clock = FakeClock(0.0)
    limiters = RateLimiters(clock.monotonic)
    info = stub_info()
    assert limiters.for_provider(info) is limiters.for_provider(info)
    other = stub_info(id="other")
    assert limiters.for_provider(other) is not limiters.for_provider(info)
    changed = stub_info(rate_limits=(RateLimit(requests=1, per=DAY),))
    assert limiters.for_provider(changed) is not limiters.for_provider(info)


def test_the_max_wait_reaches_the_limiters_it_makes() -> None:
    clock = FakeClock(0.0)
    limiters = RateLimiters(clock.monotonic, max_wait=5.0)
    unit = limiters.for_provider(
        stub_info(rate_limits=(RateLimit(requests=1, per=MINUTE),))
    )
    unit.acquire(clock.sleep)
    with pytest.raises(RateLimitError):
        unit.acquire(clock.sleep)


def test_the_hourly_window_refuses_the_sixty_first_request_until_it_expires() -> None:
    unit, clock = limiter(RateLimit(requests=60, per="hour"), max_wait=0.0)
    for _ in range(60):
        assert unit.acquire(clock.sleep) == 0.0
    with pytest.raises(RateLimitError) as caught:
        unit.acquire(clock.sleep)
    assert caught.value.retry_after == 3600.0
    assert clock.slept == []
    clock.now = 3600.0
    assert unit.acquire(clock.sleep) == 0.0
