# tests/providers/fakes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fakes for the transport tests: a clock, and a connection pool that never connects.

``FakePool`` stands in for urllib3's ``PoolManager``: it records each request and
answers from a script of responses and exceptions. ``FakeClock`` is a monotonic
clock whose ``sleep`` only advances it, so a minute of rate-limited requests runs
in microseconds. No test through them opens a socket.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

__all__ = [
    "BANNED",
    "FIXED_NOW",
    "Call",
    "FakeClock",
    "FakePool",
    "FakeRaw",
    "Headers",
]

#: The time every response a fake-driven transport returns is stamped with.
FIXED_NOW = dt.datetime(2026, 10, 15, 15, 0, tzinfo=dt.UTC)


class Headers(dict[str, str]):
    """A header mapping with case-insensitive reads, as urllib3's has."""

    def __init__(self, items: Mapping[str, str] | None = None) -> None:
        super().__init__(
            {name.casefold(): value for name, value in (items or {}).items()}
        )

    def get(self, name: str, default: Any = None) -> Any:
        """Return a header by case-insensitive name."""
        return super().get(name.casefold(), default)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and super().__contains__(name.casefold())

    def __getitem__(self, name: str) -> str:
        return super().__getitem__(name.casefold())


class FakeClock:
    """A monotonic clock whose sleep advances it."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start
        self.slept: list[float] = []

    def monotonic(self) -> float:
        """Return the current fake time."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance the clock instead of waiting."""
        self.slept.append(seconds)
        self.now += seconds


@dataclass
class FakeRaw:
    """A urllib3-style response: status, headers and a streamable body."""

    status: int = 200
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)
    chunk_error: BaseException | None = None
    released: bool = False
    closed: bool = False

    def __post_init__(self) -> None:
        self.headers = Headers(self.headers)

    def stream(self, amt: int, decode_content: bool = True) -> Iterator[bytes]:  # noqa: FBT001, FBT002
        """Yield the body in chunks, then raise ``chunk_error`` if one is set."""
        for start in range(0, len(self.body), amt):
            yield self.body[start : start + amt]
        if self.chunk_error is not None:
            raise self.chunk_error

    def release_conn(self) -> None:
        """Record that the connection was returned to the pool."""
        self.released = True

    def close(self) -> None:
        """Record that the connection was closed."""
        self.closed = True


@dataclass(frozen=True)
class Call:
    """One request a fake pool received."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None


class _Banned:
    """A scripted outcome meaning: the pool must not be called."""


#: Script entry for a pool that must never be reached.
BANNED = _Banned()


class FakePool:
    """A connection pool that answers from a script.

    Each ``request`` pops the next entry: a :class:`FakeRaw` to return, an
    exception to raise, or a callable taking the :class:`Call`. An empty script
    fails the test, and so does the :data:`BANNED` entry.
    """

    def __init__(self, *script: FakeRaw | BaseException | _Banned | Any) -> None:
        self.script = list(script)
        self.calls: list[Call] = []

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Record the request and return or raise the next scripted outcome."""
        self.calls.append(
            Call(method, url, dict(kwargs.get("headers") or {}), kwargs.get("body"))
        )
        if not self.script:
            msg = f"unexpected request {method} {url.split('?', maxsplit=1)[0]}"
            raise AssertionError(msg)
        outcome = self.script.pop(0)
        if isinstance(outcome, _Banned):
            msg = "the pool must not be reached"
            raise AssertionError(msg)  # noqa: TRY004 - a test failure, not a type error
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            return outcome(self.calls[-1])
        return outcome

    def clear(self) -> None:
        """Mirror ``PoolManager.clear``."""
        self.script.clear()
