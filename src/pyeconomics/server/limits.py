# src/pyeconomics/server/limits.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Per-client rate limits (ADR-0012 decision 12), with the ``limits`` library.

A hosted server counts each client's requests in three groups, each with its
own limit over a moving window (:data:`HOSTED_LIMITS`):

- ``runs``: a model's run, either form (60 a minute);
- ``series``: ``/v1/series/...``, each one an upstream fetch (30 a minute);
- ``metadata``: everything else but the health probes ``/healthz`` and
  ``/version``, which are never limited (120 a minute).

A client is its address (:func:`~pyeconomics.server.edge.client_key`: IPv6 by
its ``/64``), read from ``CF-Connecting-IP`` only when the edge's credential
matched. A request past its limit is answered with
:class:`~pyeconomics.surfaces.service.TooManyRequestsError` (429) and
``Retry-After``, the seconds until the window takes a request again.
Cloudflare's rate rule is the outer layer.

Where the counts live: in hosted mode, Redis at ``PYECONOMICS_RATELIMIT_URL``
(Upstash Redis over TLS; ``rediss://`` is required unless the host is a loopback
address), so every instance shares them; otherwise, and in hosted mode without
the variable, in the process's memory. The URL holds a password: it is read
from the environment, registered with :mod:`~pyeconomics.data.redaction`, and
never logged. If the storage cannot be reached, a run or a series is refused
with :class:`~pyeconomics.surfaces.service.LimitsUnavailableError` (503) rather
than served unlimited, while metadata, which costs nothing upstream, is served;
the outage and the recovery are each logged once, by the error's type name only.

Local mode has no limits unless :class:`~pyeconomics.server.settings.ServerSettings`
gives some: a user's own machine answers its own requests.

Examples
--------
>>> route_kind("/v1/models/foundations.time_value/run"), route_kind("/healthz")
('runs', None)
>>> str(RateLimits(runs="2/second").items()["runs"])
'2 per 1 second'
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Final, Literal

from pyeconomics.core.errors import InputError
from pyeconomics.server import logs
from pyeconomics.server.edge import OPEN_PATHS
from pyeconomics.surfaces.service import LimitsUnavailableError, TooManyRequestsError

if TYPE_CHECKING:
    from limits import RateLimitItem
    from limits.storage import Storage

__all__ = [
    "HOSTED_LIMITS",
    "STORAGE_VARIABLE",
    "Kind",
    "Limiter",
    "RateLimits",
    "open_storage",
    "route_kind",
]

#: A group of routes that share one limit.
Kind = Literal["runs", "series", "metadata"]
#: The environment variable that holds the Redis URL of hosted mode's limits.
STORAGE_VARIABLE: Final = "PYECONOMICS_RATELIMIT_URL"
#: How long a request waits for Redis, in seconds, before it counts as an outage.
STORAGE_TIMEOUT: Final = 2.0

_LOGGER: Final = logging.getLogger(logs.LOGGER)
_REDIS_SCHEMES: Final = frozenset({"redis", "rediss"})
_LOOPBACK_HOSTS: Final = frozenset({"localhost", "127.0.0.1", "::1"})


@dataclass(frozen=True, slots=True, kw_only=True)
class RateLimits:
    """Each group's limit, in the ``limits`` notation; ``None`` leaves it unlimited.

    Parameters
    ----------
    runs, series, metadata
        Such as ``60/minute`` or ``5 per second``.

    Raises
    ------
    InputError
        For a limit the ``limits`` library cannot parse.
    """

    runs: str | None = "60/minute"
    series: str | None = "30/minute"
    metadata: str | None = "120/minute"

    def __post_init__(self) -> None:
        """Check that each limit parses."""
        self.items()

    @classmethod
    def off(cls) -> RateLimits:
        """Return limits that limit nothing."""
        return cls(runs=None, series=None, metadata=None)

    @property
    def enabled(self) -> bool:
        """Whether any group is limited."""
        return any(getattr(self, field.name) is not None for field in fields(self))

    def items(self) -> dict[Kind, RateLimitItem]:
        """Return each limited group's parsed limit."""
        from limits import parse  # noqa: PLC0415 - the server extra

        found: dict[Kind, RateLimitItem] = {}
        kinds: tuple[Kind, ...] = ("runs", "series", "metadata")
        for kind in kinds:
            text = getattr(self, kind)
            if text is None:
                continue
            if not isinstance(text, str):
                msg = f"the {kind} limit is text such as '60/minute', not {text!r}"
                raise InputError(msg)
            try:
                found[kind] = parse(text)
            except ValueError:
                msg = f"the {kind} limit is not a rate such as '60/minute': {text!r}"
                raise InputError(msg) from None
        return found


#: Hosted mode's limits per client (chosen with the maintainer in Phase 4 Step 7).
HOSTED_LIMITS: Final = RateLimits()


def route_kind(path: str) -> Kind | None:
    """Return the group a request path counts against; ``None`` for the probes."""
    if path in OPEN_PATHS:
        return None
    if path.startswith("/v1/series/"):
        return "series"
    if path.startswith("/v1/models/") and path.endswith("/run"):
        return "runs"
    return "metadata"


def _redis_url(url: str) -> str:
    """Check a Redis URL and register its secrets; never put it in a message.

    redis-py parses it, as the storage will: no server module parses a URL a
    caller sent, and this one comes from the operator's environment.
    """
    from redis.connection import parse_url  # noqa: PLC0415 - the limits[redis] extra

    from pyeconomics.data import redaction  # noqa: PLC0415 - registers the secret
    from pyeconomics.data.errors import ConfigError  # noqa: PLC0415

    scheme = url.partition("://")[0].lower()
    parts: dict[str, object] = {}
    if scheme in _REDIS_SCHEMES:
        try:
            parts = dict(parse_url(url))  # type: ignore[no-untyped-call]
        except ValueError:
            parts = {}
    host = parts.get("host")
    if not isinstance(host, str) or not host:
        msg = f"{STORAGE_VARIABLE} must be a redis:// or rediss:// URL"
        raise ConfigError(msg)
    if scheme != "rediss" and host not in _LOOPBACK_HOSTS:
        msg = f"{STORAGE_VARIABLE} must use TLS (rediss://) for a remote Redis"
        raise ConfigError(msg)
    password = parts.get("password")
    for secret in (url, password):
        if isinstance(secret, str) and len(secret) >= redaction.MIN_SECRET_LENGTH:
            redaction.register(secret)
    return url


def open_storage(url: str | None) -> Storage:
    """Return the counts' storage: Redis at ``url``, or memory for ``None``.

    Nothing connects here: the first request does.

    Raises
    ------
    ConfigError
        For a URL that is not ``redis://`` or ``rediss://``, or that sends a
        remote host's counts without TLS.
    """
    from limits.storage import MemoryStorage, RedisStorage  # noqa: PLC0415

    if url is None:
        return MemoryStorage()
    return RedisStorage(
        _redis_url(url),
        wrap_exceptions=True,
        socket_timeout=STORAGE_TIMEOUT,
        socket_connect_timeout=STORAGE_TIMEOUT,
    )


class Limiter:
    """A moving-window limiter over one storage.

    Parameters
    ----------
    limits
        Each group's limit.
    storage
        Where the counts live (:func:`open_storage`).
    """

    def __init__(self, limits: RateLimits, storage: Storage) -> None:
        from limits.strategies import MovingWindowRateLimiter  # noqa: PLC0415

        self._items = limits.items()
        self._strategy = MovingWindowRateLimiter(storage)
        self._down = False

    @classmethod
    def for_mode(cls, limits: RateLimits, *, hosted: bool) -> Limiter | None:
        """Return the limiter of a server, or ``None`` when nothing is limited.

        Hosted mode keeps the counts in Redis when ``PYECONOMICS_RATELIMIT_URL``
        is set, and says once, at start, when it is not.
        """
        if not limits.enabled:
            return None
        url = None
        if hosted:
            url = os.environ.get(STORAGE_VARIABLE, "").strip() or None
        if hosted and url is None:
            _LOGGER.warning(
                "%s is not set: each process keeps its own rate-limit counts",
                STORAGE_VARIABLE,
            )
        return cls(limits, open_storage(url))

    async def check(self, kind: Kind | None, client: str) -> None:
        """Count a request against its group's limit, refusing it past the limit.

        Raises
        ------
        TooManyRequestsError
            If the client reached the group's limit.
        LimitsUnavailableError
            If the storage cannot be reached, for a run or a series.
        """
        item = None if kind is None else self._items.get(kind)
        if kind is None or item is None:
            return
        try:
            allowed = await asyncio.to_thread(self._strategy.hit, item, kind, client)
        except Exception as error:  # noqa: BLE001 - any storage failure is an outage
            self._outage(error)
            if kind == "metadata":
                return
            raise LimitsUnavailableError from None
        self._recovered()
        if allowed:
            return
        try:
            stats = await asyncio.to_thread(
                self._strategy.get_window_stats, item, kind, client
            )
            wait = stats.reset_time - time.time()
        except Exception:  # noqa: BLE001 - the window's length is a safe answer
            wait = float(item.get_expiry())
        raise TooManyRequestsError(str(item), max(wait, 0.0))

    def _outage(self, error: BaseException) -> None:
        if not self._down:
            self._down = True
            cause = getattr(error, "storage_error", None) or error
            _LOGGER.error(
                "the rate-limit storage is unavailable (%s): runs and series are "
                "refused until it answers",
                type(cause).__name__,
            )

    def _recovered(self) -> None:
        if self._down:
            self._down = False
            _LOGGER.warning("the rate-limit storage answers again")
