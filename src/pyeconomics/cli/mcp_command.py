# src/pyeconomics/cli/mcp_command.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics mcp``: the MCP server for AI assistants (ADR-0012 decision 13).

It serves :func:`pyeconomics.mcp.build_server` in local mode, so an assistant
reaches every model, and every source the user can access, through the five
discovery tools and the headline tools:

- over standard input and output by default, the transport every desktop
  client launches (``uvx --from "pyeconomics[mcp]" pyeconomics mcp``): the
  protocol alone travels on standard output, and pyeconomics' log records go to
  standard error as single lines;
- with ``--transport http``, as stateless Streamable HTTP at ``/mcp`` on
  127.0.0.1 port 8765 by default, under ``pyeconomics serve``'s bind guard: a
  host that is not a loopback address is refused (exit code 2) unless
  ``--allow-remote`` is passed, and then the server logs a warning.

The data layer runs in library mode, configured once at start. The ``llm_use``
policy is read from the user's configuration then (``allow_unclear_llm_use`` in
``pyeconomics.toml``, or ``PYECONOMICS_ALLOW_UNCLEAR_LLM_USE``): no tool argument
changes it. The command needs the ``mcp`` extra (exit code 8 without it).
"""

import contextlib
import logging
from typing import Annotated, Final, Literal

from cyclopts import Parameter

from pyeconomics.cli.context import ContextParameter, UsageError
from pyeconomics.cli.output import Utf8Text
from pyeconomics.cli.serve_command import DEFAULT_HOST, run_server
from pyeconomics.core._optional import import_optional
from pyeconomics.surfaces.service import is_loopback

__all__ = ["DEFAULT_MCP_PORT", "mcp"]

#: The port ``pyeconomics mcp --transport http`` listens on by default.
DEFAULT_MCP_PORT: Final = 8765
_HIGHEST_PORT: Final = 65_535


def mcp(
    *,
    transport: Literal["stdio", "http"] = "stdio",
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_MCP_PORT,
    allow_remote: Annotated[bool, Parameter(negative="")] = False,
    context: ContextParameter,
) -> None:
    """Serve the models to an AI assistant over MCP, until the client stops.

    Over stdio by default, as desktop clients launch it; with --transport http,
    at http://127.0.0.1:8765/mcp.

    Parameters
    ----------
    transport
        stdio (the default) or http (Streamable HTTP at /mcp).
    host
        With --transport http, the address to listen on: a loopback address
        unless --allow-remote.
    port
        With --transport http, the port to listen on.
    allow_remote
        With --transport http, listen on an address other machines can reach.
        Every source this machine can access, with its keys, is then served to
        them.
    """
    if not 0 < port <= _HIGHEST_PORT:
        msg = f"--port is from 1 to {_HIGHEST_PORT}"
        raise UsageError(msg)
    local = is_loopback(host)
    if transport == "http" and not local and not allow_remote:
        msg = (
            f"{host} is not a loopback address, so other machines could reach "
            "every source this one can access; pass --allow-remote to serve it"
        )
        raise UsageError(msg)
    import_optional("mcp", extra="mcp")
    import anyio  # noqa: PLC0415 - the mcp extra

    from pyeconomics import data  # noqa: PLC0415 - the data layer loads here
    from pyeconomics.mcp.server import build_server  # noqa: PLC0415
    from pyeconomics.mcp.transport import http_app, serve_stdio  # noqa: PLC0415
    from pyeconomics.server import logs  # noqa: PLC0415 - imports no framework

    handler = logs.configure(Utf8Text(context.streams.stderr), logging.WARNING)
    try:
        data.configure(mode="library")
        server = build_server(mode="local")
        if transport == "stdio":
            # The client closing the streams, or Ctrl+C, stops the server.
            with contextlib.suppress(KeyboardInterrupt):
                anyio.run(serve_stdio, server)
            return
        if not local:
            logging.getLogger("pyeconomics.mcp").warning(
                "serving on %s, which is not a loopback address: every source "
                "this machine can access, with its keys, is exposed to whoever "
                "can reach it",
                host,
            )
        run_server(http_app(server, check_host=local), host, port)
    finally:
        logs.release(handler)
