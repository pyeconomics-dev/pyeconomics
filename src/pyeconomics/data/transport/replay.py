# src/pyeconomics/data/transport/replay.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``ReplayTransport``: serve recorded responses, offline (ADR-0011 decision 17).

It answers a request from a cassette
(:mod:`~pyeconomics.data.transport.cassette`) by the request's key: method,
host and path, the sorted parameters and, for a request with a body, the SHA-256
of its canonical body (:func:`~pyeconomics.data.transport.base.request_key`). A
request no cassette records fails and names its key, which holds no credential.

It applies the same two refusals as the real transport, hosted mode and the host
allowlist, so a test through it exercises them too. It never opens a socket and
needs no key. The response carries the cassette's ``recorded_on`` as its
retrieval time, so an offline run is deterministic.

This is an I/O module only because it reads cassette files; it never writes one.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data.transport.base import Request, Response
>>> from pyeconomics.data.transport.cassette import Cassette
>>> when = dt.datetime(2026, 10, 15, tzinfo=dt.UTC)
>>> request = Request(host="api.example.org", path="/v1/x")
>>> replay = ReplayTransport(
...     [Cassette.from_exchanges("demo", when, [(request, Response(200, b"ok", when))],
...                              synthetic=True)]
... )
>>> replay.answer("demo", request).body
b'ok'

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pyeconomics.data import modes
from pyeconomics.data.errors import TransportError
from pyeconomics.data.transport.base import Request, Response, check_host, request_key
from pyeconomics.data.transport.cassette import Cassette

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import ProviderInfo

__all__ = ["ReplayTransport"]


class ReplayTransport:
    """A transport that replays cassettes.

    Parameters
    ----------
    cassettes
        The cassettes to serve. A request is looked up in the cassettes of its
        provider, in order; the first recording of its key answers.
    """

    def __init__(self, cassettes: Iterable[Cassette]) -> None:
        self._cassettes = tuple(cassettes)
        #: The keys of the requests served so far, for a test to inspect.
        self.served: list[str] = []

    @classmethod
    def from_file(cls, path: Path | str) -> ReplayTransport:
        """Load one cassette file."""
        return cls([Cassette.from_json(Path(path).read_bytes())])

    @classmethod
    def from_directory(cls, directory: Path | str) -> ReplayTransport:
        """Load every ``*.json`` cassette under a directory, in name order."""
        paths = sorted(Path(directory).rglob("*.json"))
        return cls(Cassette.from_json(path.read_bytes()) for path in paths)

    def answer(self, provider: str, request: Request) -> Response:
        """Return the recorded response to ``request`` for ``provider``.

        Raises
        ------
        TransportError
            If no cassette of the provider records the request; the message
            names its key.
        """
        for cassette in self._cassettes:
            if cassette.provider != provider:
                continue
            record = cassette.lookup(request)
            if record is not None:
                self.served.append(record.key)
                return Response(
                    record.response.status,
                    record.response.body,
                    cassette.recorded_on,
                    record.response.headers,
                )
        msg = f"no cassette of {provider} records the request {request_key(request)}"
        raise TransportError(msg, provider=provider)

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,  # noqa: ARG002 - replay needs no key
    ) -> Response:
        """Replay a request: refuse what hosted mode and the allowlist refuse."""
        modes.require_allowed(info.terms, provider=info.id)
        check_host(info, request)
        return self.answer(info.id, request)
