# src/pyeconomics/mcp/transport.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""How the MCP server is reached: stdio, and stateless Streamable HTTP.

- :func:`serve_stdio` serves one client over standard input and output, the
  transport ``pyeconomics mcp`` uses by default and every desktop client
  launches. Standard output carries the protocol alone: every log record goes
  to standard error.
- :class:`HttpEndpoint` is the Streamable HTTP endpoint, an ASGI app for one
  path, stateless and answering JSON (no session, no stream to resume), so any
  process of a server can answer any request. ``pyeconomics mcp --transport
  http`` serves it alone (:func:`http_app`) on 127.0.0.1;
  :func:`pyeconomics.server.create_app` mounts it at ``/mcp``, behind the REST
  server's host check, edge check and rate limits.

The endpoint refuses, with 403 and before the SDK reads the request, any
``Origin`` that is not this machine's (local mode) and any ``Origin`` at all
(hosted mode, which serves no browser): the specification's defence against DNS
rebinding. It takes ``POST`` only, answering 405 to ``GET`` and ``DELETE``: a
stateless server has no stream to open and no session to end, so no idle
connection is held open. Served alone, it also answers only requests addressed
to a loopback host name. Its request bodies are bounded as the REST API's are:
16 MiB locally, 1 MiB hosted.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import urlsplit

from pyeconomics.surfaces.budgets import HOSTED_BODY_LIMIT
from pyeconomics.surfaces.codec import MAX_INPUT_BYTES
from pyeconomics.surfaces.service import host_name, is_loopback

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from mcp.server import Server
    from starlette.applications import Starlette
    from starlette.types import Receive, Scope, Send

    from pyeconomics.mcp.server import McpMode

__all__ = ["MCP_PATH", "HttpEndpoint", "http_app", "origin_allowed", "serve_stdio"]

#: The path of the Streamable HTTP endpoint.
MCP_PATH: Final = "/mcp"
#: The JSON-RPC error code of a request the transport refuses.
_INVALID_REQUEST: Final = -32600


async def serve_stdio(server: Server[Any]) -> None:  # pragma: no cover - subprocess
    """Serve one client over standard input and output until it closes them.

    tests/mcp/test_mcp_cli.py runs it in the subprocess a stdio client starts,
    which coverage does not measure.
    """
    from mcp.server.stdio import stdio_server  # noqa: PLC0415 - the mcp extra

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def origin_allowed(origin: str | None, mode: McpMode) -> bool:
    """Say whether a request's ``Origin`` may reach the endpoint.

    A request without one (every client but a browser) may. Local mode admits
    an ``http`` or ``https`` origin on a loopback host; hosted mode, which serves
    no browser, admits none.

    Examples
    --------
    >>> origin_allowed(None, "hosted"), origin_allowed("http://127.0.0.1:6274", "local")
    (True, True)
    >>> origin_allowed("https://example.org", "local")
    False
    """
    if origin is None:
        return True
    if mode == "hosted":
        return False
    try:
        parts = urlsplit(origin)
        host = parts.hostname
    except ValueError:
        return False
    return parts.scheme in {"http", "https"} and host is not None and is_loopback(host)


def _headers(scope: Scope) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, value in scope.get("headers", ()):
        found.setdefault(name.decode("latin-1").lower(), value.decode("latin-1"))
    return found


async def _refuse(
    send: Send, status: int, message: str, *, allow: bytes | None = None
) -> None:
    body = json.dumps(
        {"jsonrpc": "2.0", "error": {"code": _INVALID_REQUEST, "message": message}}
    ).encode("utf-8")
    fields = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
    ]
    if allow is not None:
        fields.append((b"allow", allow))
    await send({"type": "http.response.start", "status": status, "headers": fields})
    await send({"type": "http.response.body", "body": body})


class HttpEndpoint:
    """The stateless Streamable HTTP endpoint of one server, as an ASGI app.

    The SDK's session manager runs only while :meth:`running` is entered, and a
    fresh one each time; the endpoint answers 503 outside it.

    Parameters
    ----------
    server
        The MCP server (:func:`~pyeconomics.mcp.server.build_server`).
    mode
        ``local`` or ``hosted``: which origins it admits and how large a body.
    check_host
        Answer only requests addressed to a loopback host name: for the
        endpoint served alone, since the REST server checks hosts itself.
    """

    def __init__(
        self, server: Server[Any], *, mode: McpMode, check_host: bool = False
    ) -> None:
        self.server = server
        self.mode: McpMode = mode
        self.check_host = check_host
        self.body_limit = HOSTED_BODY_LIMIT if mode == "hosted" else MAX_INPUT_BYTES
        self._manager: Any = None

    @asynccontextmanager
    async def running(self) -> AsyncGenerator[None]:
        """Run a session manager for the endpoint while the context is entered."""
        from mcp.server.streamable_http_manager import (  # noqa: PLC0415
            StreamableHTTPSessionManager,
        )
        from mcp.server.transport_security import (  # noqa: PLC0415
            TransportSecuritySettings,
        )

        manager = StreamableHTTPSessionManager(
            app=self.server,
            json_response=True,
            stateless=True,
            # The host and the origin are checked here, before the SDK runs.
            security_settings=TransportSecuritySettings(
                enable_dns_rebinding_protection=False
            ),
            max_request_body_size=self.body_limit,
        )
        async with manager.run():
            self._manager = manager
            try:
                yield
            finally:
                self._manager = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer one request, after the host and origin checks."""
        if scope["type"] != "http":  # pragma: no cover - a route sends http only
            return
        headers = _headers(scope)
        if self.check_host and not is_loopback(host_name(headers.get("host", ""))):
            await _refuse(
                send, 421, "this server answers only requests addressed to 127.0.0.1"
            )
            return
        if not origin_allowed(headers.get("origin"), self.mode):
            await _refuse(send, 403, "requests from this origin are refused")
            return
        if scope.get("method") != "POST":
            # Stateless: no stream to open with GET, no session to end with
            # DELETE. Every revision lets a server answer 405 to both.
            await _refuse(send, 405, "this endpoint takes POST only", allow=b"POST")
            return
        manager = self._manager
        if manager is None:
            await _refuse(send, 503, "the MCP endpoint is not running")
            return
        await manager.handle_request(scope, receive, send)


def http_app(server: Server[Any], *, check_host: bool = True) -> Starlette:
    """Return the local Streamable HTTP app: the endpoint at ``/mcp``, nothing else.

    It admits only this machine's origins and, unless ``check_host`` is false
    (``pyeconomics mcp --allow-remote``), answers only requests addressed to a
    loopback host name.
    """
    from starlette.applications import Starlette  # noqa: PLC0415 - the mcp extra
    from starlette.routing import Route  # noqa: PLC0415

    endpoint = HttpEndpoint(server, mode="local", check_host=check_host)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncGenerator[None]:
        async with endpoint.running():
            yield

    return Starlette(routes=[Route(MCP_PATH, endpoint=endpoint)], lifespan=lifespan)
