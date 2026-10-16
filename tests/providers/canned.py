# tests/providers/canned.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A canned transport for the per-provider tests: each request answered by a route.

``Canned(route)`` checks the host as every transport does, records each request
and the key it was handed, and answers with ``route(request)``. ``ok`` builds a
JSON response stamped ``NOW``; ``http`` builds the real HTTPS transport over a
fake pool and a fake clock, for the tests that must see where a key went.
Nothing here opens a socket.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from fakes import FIXED_NOW, FakeClock, FakePool
from stubs import NOW

from pyeconomics.data.transport.base import Request, Response, check_host
from pyeconomics.data.transport.http import HttpTransport

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import ProviderInfo

__all__ = ["NOW", "Canned", "http", "ok", "param", "rounded"]


def ok(body: object, status: int = 200, **headers: str) -> Response:
    """Return a JSON response with ``body``, stamped ``NOW``."""
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return Response(status, raw, NOW, tuple(headers.items()))


def rounded(
    values: Iterable[float | None], places: int = 9
) -> tuple[float | None, ...]:
    """Round each value, so a test compares decimals without float noise."""
    return tuple(None if value is None else round(value, places) for value in values)


def param(request: Request, name: str) -> str | None:
    """Return one query parameter of a request."""
    return dict(request.params).get(name)


class Canned:
    """Answers each request with ``route(request)`` and remembers what it saw."""

    def __init__(self, route: Callable[[Request], Response]) -> None:
        self.route = route
        self.sent: list[Request] = []
        self.keys: list[Any] = []

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,
    ) -> Response:
        """Check the host, record the request, and answer it."""
        check_host(info, request)
        self.sent.append(request)
        self.keys.append(key)
        return self.route(request)


def http(pool: FakePool) -> HttpTransport:
    """Return the real HTTPS transport over a fake pool and clock."""
    clock = FakeClock()
    return HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        jitter=lambda ceiling: ceiling,
    )
