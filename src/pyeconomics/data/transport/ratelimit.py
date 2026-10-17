# src/pyeconomics/data/transport/ratelimit.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Per-provider limiters that keep a transport inside a source's published limits.

A provider declares its limits as
:class:`~pyeconomics.data.providers.base.RateLimit` values: so many requests per
second, minute or day. :class:`ProviderLimiter` keeps, for each declared limit,
a log of the last N grant times and grants a request only when fewer than N
grants fall in the window that ends with it. At most N requests are therefore
ever sent in any window of that length, which is what a hard limit such as the
SEC's ten requests per second needs. (A token bucket that starts full lets
through up to twice that in one window: the whole bucket, then its refill.)

A request that must wait is *reserved* a grant time under a lock, so threads
share the allowance without a thundering herd, and grants never run backwards.
A wait longer than :attr:`ProviderLimiter.max_wait` (a daily allowance that is
spent, say) is not slept through: it raises
:class:`~pyeconomics.data.errors.RateLimitError` carrying the seconds to wait,
and reserves nothing.

The clock and the sleep are passed in, so a test runs a minute of requests on a
fake clock in microseconds. This module reads no clock itself.

Examples
--------
>>> from pyeconomics.data.providers.base import RateLimit
>>> now = [0.0]
>>> slept = []
>>> limiter = ProviderLimiter(
...     "demo", (RateLimit(requests=2, per="second"),), lambda: now[0]
... )
>>> [limiter.acquire(slept.append) for _ in range(3)]
[0.0, 0.0, 1.0]
>>> slept
[1.0]

"""

from __future__ import annotations

import threading
from collections import deque
from typing import TYPE_CHECKING, Final

from pyeconomics.data.errors import RateLimitError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pyeconomics.data.providers.base import ProviderInfo, RateLimit

__all__ = ["DEFAULT_MAX_WAIT", "ProviderLimiter", "RateLimiters"]

#: The longest wait, in seconds, a limiter sleeps through before it refuses.
DEFAULT_MAX_WAIT: Final = 60.0


class _Window:
    """The last ``requests`` grant times of one limit."""

    def __init__(self, limit: RateLimit) -> None:
        self.size = limit.requests
        self.span = float(limit.window_seconds)
        self.keyless_only = limit.without_key is True
        self.grants: deque[float] = deque(maxlen=limit.requests)

    def applies(self, *, keyed: bool) -> bool:
        """Whether a request counts against this limit."""
        return not (keyed and self.keyless_only)

    def earliest(self) -> float:
        """Return the first time another grant keeps the window within its limit."""
        if len(self.grants) < self.size:
            return float("-inf")
        return self.grants[0] + self.span


class ProviderLimiter:
    """The limit windows of one provider's declared limits.

    Parameters
    ----------
    provider
        The provider id, for messages.
    limits
        The provider's rate limits; none means no waiting.
    clock
        A monotonic clock in seconds.
    max_wait
        The longest wait to sleep through, in seconds.
    """

    def __init__(
        self,
        provider: str,
        limits: Sequence[RateLimit],
        clock: Callable[[], float],
        *,
        max_wait: float = DEFAULT_MAX_WAIT,
    ) -> None:
        self.provider = provider
        self.max_wait = max_wait
        self._clock = clock
        self._lock = threading.Lock()
        self._windows = tuple(_Window(limit) for limit in limits)
        self._last = float("-inf")

    def acquire(
        self,
        sleep: Callable[[float], None],
        *,
        keyed: bool = False,
        max_wait: float | None = None,
    ) -> float:
        """Reserve the next grant time within every limit, and sleep until it.

        A limit that holds only without a key (``RateLimit.without_key``) does
        not count a request sent with one (``keyed``).

        Returns
        -------
        float
            The seconds slept (zero when the request could go at once).

        Raises
        ------
        RateLimitError
            If the wait would exceed :attr:`max_wait`; nothing is reserved.
        """
        ceiling = self.max_wait if max_wait is None else max_wait
        windows = [w for w in self._windows if w.applies(keyed=keyed)]
        with self._lock:
            now = self._clock()
            grant = max(now, self._last, *(window.earliest() for window in windows))
            wait = grant - now
            if wait > ceiling:
                msg = (
                    f"{self.provider}'s rate limit is spent; the next request "
                    f"could go in {wait:.0f} seconds"
                )
                raise RateLimitError(msg, provider=self.provider, retry_after=wait)
            for window in windows:
                window.grants.append(grant)
            self._last = grant
        if wait > 0.0:
            sleep(wait)
        return wait


class RateLimiters:
    """One :class:`ProviderLimiter` per provider, created on first use.

    A transport owns one of these, so the allowance of a provider is shared by
    every thread that uses the transport.
    """

    def __init__(
        self, clock: Callable[[], float], *, max_wait: float = DEFAULT_MAX_WAIT
    ) -> None:
        self._clock = clock
        self._max_wait = max_wait
        self._lock = threading.Lock()
        self._limiters: dict[
            tuple[str, tuple[tuple[int, str, bool], ...]], ProviderLimiter
        ]
        self._limiters = {}

    def for_provider(self, info: ProviderInfo) -> ProviderLimiter:
        """Return the limiter for a provider's declared limits."""
        limits = tuple(info.rate_limits)
        key = (
            info.id,
            tuple((limit.requests, limit.per, limit.without_key) for limit in limits),
        )
        with self._lock:
            limiter = self._limiters.get(key)
            if limiter is None:
                limiter = ProviderLimiter(
                    info.id, limits, self._clock, max_wait=self._max_wait
                )
                self._limiters[key] = limiter
            return limiter
