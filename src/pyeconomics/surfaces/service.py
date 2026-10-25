# src/pyeconomics/surfaces/service.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What a served surface refuses: routes, methods, hosts, floods and a full queue.

The REST API (Phase 4 Step 6) and the MCP server's HTTP app answer requests, and
some failures belong to serving rather than to a model or the data. Each is an
error class here, so the error table (:mod:`~pyeconomics.surfaces.problems`)
gives it a row and every surface reports it as the same problem:

- :class:`RouteNotFoundError`: no route matches the request (404);
- :class:`MethodNotAllowedError`: the route does not take the method (405);
- :class:`HostNotAllowedError`: a local server, which answers only requests
  addressed to a loopback name, received one addressed elsewhere (400), the
  defence against DNS rebinding;
- :class:`ServerBusyError`: every worker is busy and the queue is full (503);
- :class:`EdgeRefusedError`: a hosted server that trusts only its edge received a
  request without the edge's credential (403), with fixed text;
- :class:`TooManyRequestsError`: the client reached one of its rate limits
  (429), saying when to retry;
- :class:`LimitsUnavailableError`: the limits' storage cannot be reached, so a
  run or a series is refused rather than served unlimited (503).

:func:`is_loopback` says whether a host names this machine's loopback
interface: ``pyeconomics serve`` refuses to bind any other without
``--allow-remote``, and a local server refuses requests addressed to any other.
Nothing here imports a framework.

Examples
--------
>>> is_loopback("127.0.0.1"), is_loopback("localhost"), is_loopback("::1")
(True, True, True)
>>> is_loopback("0.0.0.0"), is_loopback("192.168.1.20"), is_loopback("example.org")
(False, False, False)
>>> host_name("[::1]:8000"), host_name("localhost:8000"), host_name("127.0.0.1")
('::1', 'localhost', '127.0.0.1')
"""

from __future__ import annotations

import ipaddress
import math
from typing import TYPE_CHECKING, Final

from pyeconomics.core.errors import PyeconomicsError

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "LOOPBACK_NAMES",
    "EdgeRefusedError",
    "HostNotAllowedError",
    "LimitsUnavailableError",
    "MethodNotAllowedError",
    "RouteNotFoundError",
    "ServerBusyError",
    "TooManyRequestsError",
    "host_name",
    "is_loopback",
]

#: The host names that always mean this machine; any loopback address does too.
LOOPBACK_NAMES: Final = frozenset({"localhost"})


def host_name(header: str) -> str:
    """Return the host of a ``Host`` header, without its port or IPv6 brackets."""
    text = header.strip().lower()
    if text.startswith("["):
        return text[1:].partition("]")[0]
    if text.count(":") == 1:
        return text.partition(":")[0]
    return text


def is_loopback(host: str) -> bool:
    """Say whether a host name or address names the loopback interface.

    ``localhost`` and every loopback address do (``127.0.0.0/8`` and ``::1``);
    ``0.0.0.0``, ``::`` and every other address or name do not.
    """
    name = host.strip().lower().removeprefix("[").removesuffix("]")
    if name in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


class RouteNotFoundError(PyeconomicsError):
    """No route of the API matches the request.

    Examples
    --------
    >>> print(RouteNotFoundError())
    no route of the API matches the request; the OpenAPI document lists them
    """

    def __init__(self) -> None:
        super().__init__(
            "no route of the API matches the request; the OpenAPI document lists them"
        )


class MethodNotAllowedError(PyeconomicsError):
    """The route exists but does not take the request's method.

    Parameters
    ----------
    allowed
        The methods it takes.

    Examples
    --------
    >>> print(MethodNotAllowedError(["POST"]))
    this route does not take that method; it takes POST
    """

    def __init__(self, allowed: Iterable[str]) -> None:
        self.allowed = tuple(sorted(allowed))
        super().__init__(
            "this route does not take that method; it takes "
            + (", ".join(self.allowed) or "no method")
        )


class HostNotAllowedError(PyeconomicsError):
    """A local server received a request addressed to a host it does not serve.

    A server started without ``--allow-remote`` answers only requests whose
    ``Host`` is a loopback name, so a web page that rebinds its own domain name
    to 127.0.0.1 cannot read its answers.

    Examples
    --------
    >>> print(HostNotAllowedError())  # doctest: +ELLIPSIS
    this server answers only requests addressed to 127.0.0.1, localhost or ::1; ...
    """

    def __init__(self) -> None:
        super().__init__(
            "this server answers only requests addressed to 127.0.0.1, localhost or "
            "::1; start it with --allow-remote to serve other names"
        )


class ServerBusyError(PyeconomicsError):
    """Every worker is busy and the queue of waiting requests is full.

    Parameters
    ----------
    queued
        How many requests the queue holds.

    Examples
    --------
    >>> print(ServerBusyError(8))
    the server is busy: 8 requests are already waiting; try again shortly
    """

    def __init__(self, queued: int) -> None:
        super().__init__(
            f"the server is busy: {queued} requests are already waiting; "
            "try again shortly"
        )
        self.queued = queued


class EdgeRefusedError(PyeconomicsError):
    """A request reached a server that trusts only its edge, without the credential.

    A hosted server configured with an edge credential answers its API only for
    requests its edge forwarded; the text is fixed, so it says nothing about
    what was sent or expected.

    Examples
    --------
    >>> print(EdgeRefusedError())
    this API answers only requests that come through its edge
    """

    def __init__(self) -> None:
        super().__init__("this API answers only requests that come through its edge")


class TooManyRequestsError(PyeconomicsError):
    """A client reached one of its rate limits.

    Parameters
    ----------
    limit
        The limit, such as ``60 per 1 minute``.
    retry_after
        The seconds until the limit takes a request again.

    Examples
    --------
    >>> error = TooManyRequestsError("60 per 1 minute", 12.2)
    >>> print(error)
    this client reached its limit of 60 per 1 minute; try again in 13 s
    >>> error.retry_after
    12.2
    """

    def __init__(self, limit: str, retry_after: float) -> None:
        super().__init__(
            f"this client reached its limit of {limit}; "
            f"try again in {math.ceil(retry_after)} s"
        )
        self.limit = limit
        self.retry_after = retry_after


class LimitsUnavailableError(PyeconomicsError):
    """The rate limits' storage cannot be reached, so a costly request is refused.

    Examples
    --------
    >>> print(LimitsUnavailableError())
    the server cannot check its rate limits just now; try again shortly
    """

    def __init__(self) -> None:
        super().__init__(
            "the server cannot check its rate limits just now; try again shortly"
        )
