# src/pyeconomics/mcp/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP server (ADR-0012 decisions 13 and 14), in the ``mcp`` extra.

``pip install "pyeconomics[mcp]"`` adds the official MCP SDK, and ``pyeconomics
mcp`` serves every model to an AI assistant over stdio (or, with ``--transport
http``, over Streamable HTTP on 127.0.0.1); the REST server mounts the same
server at ``/mcp``. :func:`build_server` builds it from the registry:

- :mod:`~pyeconomics.mcp.server`: the server, its tool calls and their answers;
- :mod:`~pyeconomics.mcp.tools`: the five discovery tools and the headline
  tools, with their names and descriptions;
- :mod:`~pyeconomics.mcp.headline`: the ids of the models with a tool of their
  own, which is data;
- :mod:`~pyeconomics.mcp.schemas`: every tool's input and output schemas;
- :mod:`~pyeconomics.mcp.execution`: where a run or a series executes;
- :mod:`~pyeconomics.mcp.transport`: stdio and the Streamable HTTP endpoint.

The names here are imported on first use, so reading the headline tuple loads
no SDK.

Examples
--------
>>> from pyeconomics.mcp import build_server
>>> build_server().name
'pyeconomics'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyeconomics.mcp.server import build_server

__all__ = ["build_server"]


def __getattr__(name: str) -> Any:  # noqa: ANN401 - the exported name
    """Import :func:`build_server` when first asked for."""
    if name == "build_server":
        from pyeconomics.mcp.server import build_server  # noqa: PLC0415

        return build_server
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
