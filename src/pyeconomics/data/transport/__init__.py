# src/pyeconomics/data/transport/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Transports: the only code that opens a socket (ADR-0011 decisions 10 and 13).

A provider builds :class:`~pyeconomics.data.transport.base.Request` values; a
transport sends them:

- :class:`~pyeconomics.data.transport.http.HttpTransport`: urllib3 and the
  operating system's trust store, HTTPS only, with host allowlists, timeouts,
  size caps, retries with backoff, per-provider rate limits and scrubbed errors.
  It is the one place a key is revealed and the one place a URL is built.
- :class:`~pyeconomics.data.transport.replay.ReplayTransport`: serves recorded
  cassettes (:mod:`~pyeconomics.data.transport.cassette`) offline, for tests.

This package imports neither urllib3 nor truststore: :func:`default_transport`
imports the HTTP transport when it first needs one, so the data layer imports
in Pyodide and wherever the network is never used.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Final

from pyeconomics.data.transport.base import (
    DEFAULT_MAX_RESPONSE_BYTES,
    Request,
    Response,
    Transport,
    request_key,
    request_path,
)

if TYPE_CHECKING:
    from pyeconomics.data.transport.base import Transport as TransportProtocol

__all__ = [
    "DEFAULT_MAX_RESPONSE_BYTES",
    "Request",
    "Response",
    "Transport",
    "default_transport",
    "request_key",
    "request_path",
]

_LOCK: Final = threading.Lock()
_DEFAULT: dict[str, TransportProtocol] = {}


def default_transport() -> Transport:
    """Return the process's HTTPS transport, creating it on first use.

    One :class:`~pyeconomics.data.transport.http.HttpTransport`, so its
    connection pool and each provider's rate-limit buckets are shared by every
    thread in the process.
    """
    with _LOCK:
        transport = _DEFAULT.get("http")
        if transport is None:
            from pyeconomics.data.transport.http import (  # noqa: PLC0415 - lazy
                HttpTransport,
            )

            transport = _DEFAULT["http"] = HttpTransport()
        return transport
