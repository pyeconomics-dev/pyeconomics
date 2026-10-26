# tests/mcp/mcp_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Helpers the MCP server's tests share: in-memory clients and a data world.

Every test talks to the server through the SDK's own ``Client``, in memory (no
process, no port): ``mode="auto"`` speaks the 2026-07-28 revision statelessly,
``mode="legacy"`` the initialize handshake of the SDK's newest earlier revision.
The SDK's client validates every structured result against the tool's output
schema, so each call also checks the schema.

asyncio's event loop needs a socket pair, which ``--disable-socket`` refuses:
the tests carry :data:`LOOPBACK_ONLY`, as the server's do, so loopback sockets
are allowed and every other connection is still refused.

:func:`stub_world` makes the installed provider registry a stand-in for every
real provider (tests/data/catalog/catalog_world.py): each keeps its real
metadata (licence class, ``llm_use``, capabilities, keys), so the resolver's and
the gate's rules run for real, and answers from canned frames, starting in 2018.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING, Any, Final

import anyio
import catalog_world
import pytest
from mcp import Client

from pyeconomics.data import registry as data_registry

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from mcp import types
    from mcp.server import Server

    from pyeconomics.data.registry import ProviderRegistry

__all__ = [
    "LOOPBACK_ONLY",
    "call",
    "listed",
    "problem_of",
    "run_with",
    "stub_world",
    "text_of",
]

#: Sockets for the event loop, connections to loopback hosts only.
LOOPBACK_ONLY: Final = pytest.mark.allow_hosts(["127.0.0.1", "::1"])
#: Where the stand-in providers' daily data starts, so 2019 dates resolve.
WORLD_START: Final = dt.date(2018, 1, 1)


def run_with[T](
    server: Server[Any],
    work: Callable[[Client], Awaitable[T]],
    *,
    mode: str = "auto",
    raise_exceptions: bool = True,
) -> T:
    """Connect a client to the server in memory and return what ``work`` returns.

    ``raise_exceptions`` re-raises a server failure in the test, as the SDK's
    testing guide advises; turn it off to see the protocol error a client sees.
    """

    async def main() -> T:
        async with Client(
            server, mode=mode, raise_exceptions=raise_exceptions, cache=None
        ) as client:
            return await work(client)

    return anyio.run(main)


def call(
    server: Server[Any],
    name: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    mode: str = "auto",
    raise_exceptions: bool = True,
) -> types.CallToolResult:
    """Call one tool and return its result."""
    return run_with(
        server,
        lambda client: client.call_tool(name, dict(arguments or {})),
        mode=mode,
        raise_exceptions=raise_exceptions,
    )


def listed(server: Server[Any], *, mode: str = "auto") -> list[types.Tool]:
    """Return the server's tools as a client lists them."""

    async def work(client: Client) -> list[types.Tool]:
        return list((await client.list_tools()).tools)

    return run_with(server, work, mode=mode)


def text_of(result: types.CallToolResult, index: int = 0) -> str:
    """Return one text block of a result."""
    block = result.content[index]
    assert block.type == "text"
    return block.text


def problem_of(result: types.CallToolResult) -> dict[str, Any]:
    """Return a tool error's problem, from its first text block."""
    assert result.is_error
    problem: dict[str, Any] = json.loads(text_of(result))
    return problem


def stub_world(monkeypatch: pytest.MonkeyPatch) -> ProviderRegistry:
    """Make stand-ins for every installed provider the installed registry."""
    monkeypatch.setattr(catalog_world, "_FIRST_DAY", WORLD_START)
    world = catalog_world.world_registry()
    monkeypatch.setattr(data_registry._CACHE, "registry", world)  # noqa: SLF001
    return world
