# tests/mcp/test_mcp_cli.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics mcp``: stdio by default, local HTTP under serve's bind guard.

The command serves the MCP server over stdio, which a real subprocess proves
end to end through the SDK's own client in both eras; with ``--transport http``
it serves the Streamable HTTP app on a loopback address, refusing any other
unless ``--allow-remote`` is passed (and then it warns); it needs the ``mcp``
extra (exit code 8 without it); and bad numbers are usage errors.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import anyio
import pytest
from cli_support import cli
from mcp import Client, StdioServerParameters
from mcp_support import LOOPBACK_ONLY

from pyeconomics import registry, run
from pyeconomics.cli import mcp_command
from pyeconomics.mcp import transport

if TYPE_CHECKING:
    from mcp.server import Server

pytestmark = LOOPBACK_ONLY

TVM = dict(registry.get("foundations.time_value").spec.examples[0].inputs)


@dataclass
class Served:
    app: Any
    host: str
    port: int


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> list[Served]:
    calls: list[Served] = []

    def record(app: Any, host: str, port: int) -> None:  # noqa: ANN401 - an ASGI app
        calls.append(Served(app, host, port))

    monkeypatch.setattr(mcp_command, "run_server", record)
    return calls


@pytest.fixture
def stdio(monkeypatch: pytest.MonkeyPatch) -> list[Server[Any]]:
    servers: list[Server[Any]] = []

    async def record(server: Server[Any]) -> None:
        servers.append(server)

    monkeypatch.setattr(transport, "serve_stdio", record)
    return servers


def test_stdio_is_the_default(stdio: list[Server[Any]], served: list[Served]) -> None:
    outcome = cli("mcp")
    assert outcome.code == 0, outcome.stderr
    assert outcome.stdout == b""  # standard output carries the protocol alone
    (server,) = stdio
    assert server.name == "pyeconomics"
    assert served == []


@pytest.mark.usefixtures("stdio")
def test_the_data_layer_runs_in_library_mode() -> None:
    from pyeconomics.data import settings  # noqa: PLC0415

    assert cli("mcp").code == 0
    assert settings().mode == "library"


def test_http_serves_the_endpoint_on_loopback(served: list[Served]) -> None:
    outcome = cli("mcp", "--transport", "http")
    assert outcome.code == 0, outcome.stderr
    (call,) = served
    assert (call.host, call.port) == ("127.0.0.1", 8765)
    assert [route.path for route in call.app.routes] == ["/mcp"]


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20"])  # noqa: S104 # nosec B104 - never bound
def test_a_non_loopback_host_is_refused_without_allow_remote(
    served: list[Served], host: str
) -> None:
    outcome = cli("mcp", "--transport", "http", "--host", host)
    assert outcome.code == 2
    assert "--allow-remote" in outcome.stderr
    assert served == []


def test_allow_remote_serves_and_warns(
    served: list[Served], caplog: pytest.LogCaptureFixture
) -> None:
    everywhere = "0.0.0.0"  # noqa: S104 # nosec B104 - recorded, never bound
    with caplog.at_level(logging.WARNING, logger="pyeconomics.mcp"):
        outcome = cli(
            "mcp", "--transport", "http", "--host", everywhere, "--allow-remote"
        )
    assert outcome.code == 0
    assert served[0].host == "0.0.0.0"  # noqa: S104 # nosec B104 - recorded, never bound
    assert "not a loopback address" in outcome.stderr


@pytest.mark.parametrize("port", ["0", "70000"])
def test_a_port_out_of_range_is_a_usage_error(port: str) -> None:
    assert cli("mcp", "--port", port).code == 2


def test_mcp_needs_its_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "mcp", None)
    outcome = cli("mcp")
    assert outcome.code == 8
    assert outcome.stderr.startswith("missing-extra: ")
    assert "pyeconomics[mcp]" in outcome.stderr


def _over_stdio(mode: str) -> tuple[str, list[str], str]:
    """Run ``pyeconomics mcp`` as a subprocess and talk to it over stdio."""
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-c",
            "import sys; from pyeconomics.cli import main; sys.exit(main(['mcp']))",
        ],
        env=dict(os.environ),
    )

    async def main() -> tuple[str, list[str], str]:
        async with Client(params, mode=mode, cache=None) as client:
            tools = await client.list_tools()
            result = await client.call_tool("foundations_time_value", TVM)
            block = result.content[0]
            assert block.type == "text"
            return client.protocol_version, [t.name for t in tools.tools], block.text

    return anyio.run(main)


@pytest.mark.parametrize(
    ("mode", "version"), [("auto", "2026-07-28"), ("legacy", "2025-11-25")]
)
def test_a_client_talks_to_the_server_over_stdio(mode: str, version: str) -> None:
    protocol, names, text = _over_stdio(mode)
    assert protocol == version
    assert names == sorted(names)
    assert "run_model" in names
    assert text == run("foundations.time_value", TVM).to_json()
