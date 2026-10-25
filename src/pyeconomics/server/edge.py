# src/pyeconomics/server/edge.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Edge trust: the origin credential, and the client address it unlocks.

ADR-0012 decision 20 puts a Cloudflare Worker in front of the hosted API. The
Worker adds a shared secret to every request it forwards, in the
``X-Pyeconomics-Edge`` header, and passes the caller's address in
``CF-Connecting-IP``. The server trusts neither header by itself:

- with no credential configured (local mode, tests, a container run by hand),
  every route is open and the client address is the connection's peer;
- with ``PYECONOMICS_EDGE_CREDENTIAL`` set, every route but ``/healthz`` and
  ``/version`` requires the header to match the credential, compared in constant
  time; a request without it is refused with
  :class:`~pyeconomics.surfaces.service.EdgeRefusedError` (403, fixed text), and
  only a request whose header matched has its client address read from
  ``CF-Connecting-IP``. A request sent straight to the origin can therefore
  neither reach the API nor choose the address its rate limits are keyed by.

The credential is a secret: it is read from the environment (which Cloud Run
fills from Secret Manager), registered with :mod:`~pyeconomics.data.redaction`
so no log record or message can carry it, and then held only as its SHA-256
digest. It is never logged, echoed or put in a problem.

:func:`client_key` turns an address into the key the rate limits count by: an
IPv4 address as it is, an IPv6 address by its ``/64`` network (one subscriber's
allocation), so a client cannot dodge its limit by rotating addresses within it.

Examples
--------
>>> edge = Edge(None)
>>> edge.configured, edge.admits("/v1/models", None)
(False, True)
>>> client_key("2001:db8:1:2:3:4:5:6"), client_key("192.0.2.7")
('2001:db8:1:2::/64', '192.0.2.7')
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
from typing import TYPE_CHECKING, Final

from pyeconomics.surfaces.service import EdgeRefusedError

if TYPE_CHECKING:
    from starlette.types import Scope

__all__ = [
    "CLIENT_ADDRESS_HEADER",
    "CREDENTIAL_VARIABLE",
    "EDGE_HEADER",
    "MIN_CREDENTIAL_LENGTH",
    "OPEN_PATHS",
    "Edge",
    "client_key",
]

#: The environment variable that holds the edge's origin credential.
CREDENTIAL_VARIABLE: Final = "PYECONOMICS_EDGE_CREDENTIAL"
#: The header the edge carries the credential in (lower case, as ASGI gives it).
EDGE_HEADER: Final = "x-pyeconomics-edge"
#: The header the edge carries the caller's address in.
CLIENT_ADDRESS_HEADER: Final = "cf-connecting-ip"
#: The routes that stay open without the credential: the health probes.
OPEN_PATHS: Final = frozenset({"/healthz", "/version"})
#: The shortest credential accepted, in characters.
MIN_CREDENTIAL_LENGTH: Final = 32
#: The longest credential accepted, in characters.
MAX_CREDENTIAL_LENGTH: Final = 512
_IPV6_NETWORK: Final = 64


def _usable(value: str) -> bool:
    """Whether a credential is long enough and fits in an HTTP header."""
    return MIN_CREDENTIAL_LENGTH <= len(value) <= MAX_CREDENTIAL_LENGTH and all(
        "!" <= character <= "~" for character in value
    )


class Edge:
    """The origin credential, held as its digest, and the checks that use it.

    Parameters
    ----------
    credential
        The credential, or ``None`` for a server that trusts no edge.

    Raises
    ------
    ConfigError
        If the credential is shorter than :data:`MIN_CREDENTIAL_LENGTH`
        characters, longer than :data:`MAX_CREDENTIAL_LENGTH`, or holds a
        space or a character an HTTP header cannot carry. The message names
        the variable, never the value.
    """

    __slots__ = ("_digest",)

    def __init__(self, credential: str | None) -> None:
        self._digest: bytes | None = None
        if credential is None:
            return
        from pyeconomics.data import redaction  # noqa: PLC0415 - registers the secret
        from pyeconomics.data.errors import ConfigError  # noqa: PLC0415

        if not _usable(credential):
            msg = (
                f"{CREDENTIAL_VARIABLE} must be {MIN_CREDENTIAL_LENGTH} to "
                f"{MAX_CREDENTIAL_LENGTH} printable characters with no spaces"
            )
            raise ConfigError(msg)
        redaction.register(credential)
        self._digest = hashlib.sha256(credential.encode("ascii")).digest()

    @classmethod
    def from_environment(cls) -> Edge:
        """Return the edge ``PYECONOMICS_EDGE_CREDENTIAL`` configures, if set."""
        value = os.environ.get(CREDENTIAL_VARIABLE, "").strip()
        return cls(value or None)

    def __repr__(self) -> str:
        """Say whether a credential is configured, never what it is."""
        return f"Edge(configured={self.configured})"

    @property
    def configured(self) -> bool:
        """Whether the server requires the edge's credential."""
        return self._digest is not None

    def matches(self, header: str | None) -> bool:
        """Whether a request's ``X-Pyeconomics-Edge`` value is the credential.

        Both sides are compared as SHA-256 digests with :func:`hmac.compare_digest`,
        so the time taken says nothing about the credential, its length included.
        """
        if self._digest is None or header is None:
            return False
        sent = hashlib.sha256(header.encode("utf-8", "surrogateescape")).digest()
        return hmac.compare_digest(sent, self._digest)

    def admits(self, path: str, header: str | None) -> bool:
        """Whether a request for ``path`` may proceed: open, or its header matched."""
        return not self.configured or path in OPEN_PATHS or self.matches(header)

    def check(self, scope: Scope) -> str:
        """Admit or refuse a request, and return its client address.

        Raises
        ------
        EdgeRefusedError
            If the server requires the credential and the request lacks it.
        """
        headers = _headers(scope)
        sent = headers.get(EDGE_HEADER)
        if not self.admits(scope.get("path", ""), sent):
            raise EdgeRefusedError
        peer = scope.get("client")
        address = str(peer[0]) if peer else "unknown"
        if self.matches(sent):
            forwarded = headers.get(CLIENT_ADDRESS_HEADER, "").strip()
            if _is_address(forwarded):
                address = forwarded
        return address


def _headers(scope: Scope) -> dict[str, str]:
    """Return a request's headers by lower-case name, the first of each kept."""
    found: dict[str, str] = {}
    for name, value in scope.get("headers", ()):
        found.setdefault(name.decode("latin-1").lower(), value.decode("latin-1"))
    return found


def _is_address(text: str) -> bool:
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return False
    return True


def client_key(address: str) -> str:
    """Return what a client's rate limits count by: its address, IPv6 by ``/64``.

    An IPv4-mapped IPv6 address counts as its IPv4 address; anything that is not
    an address (a test client's name) counts as itself.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return address
    if isinstance(parsed, ipaddress.IPv6Address):
        if parsed.ipv4_mapped is not None:
            return str(parsed.ipv4_mapped)
        return str(ipaddress.ip_network(f"{parsed}/{_IPV6_NETWORK}", strict=False))
    return str(parsed)
