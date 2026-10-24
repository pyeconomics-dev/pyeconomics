# tests/server/test_server_serve.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics serve``: the loopback guard, the extra and uvicorn (Step 6).

The server is never started: ``run_server`` is replaced by one that records the
app, host and port it was given, or uvicorn's ``Server`` by one that raises what
a real one would. A host that is not a loopback address must be refused (exit
code 2) unless ``--allow-remote`` is passed, which logs a warning; the command
needs the server extra (exit code 8); uvicorn trusts no forwarded header and
logs no request line, and its startup failure is a problem, never a traceback.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from cli_support import cli
from server_support import LOOPBACK_ONLY

from pyeconomics.cli import serve_command
from pyeconomics.core.errors import PyeconomicsError

if TYPE_CHECKING:
    from fastapi import FastAPI

pytestmark = LOOPBACK_ONLY


@dataclass
class Served:
    app: FastAPI
    host: str
    port: int


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> list[Served]:
    calls: list[Served] = []

    def record(app: FastAPI, host: str, port: int) -> None:
        logging.getLogger("uvicorn.error").info("Uvicorn running")
        calls.append(Served(app, host, port))

    monkeypatch.setattr(serve_command, "run_server", record)
    return calls


def test_serve_binds_loopback_by_default(served: list[Served]) -> None:
    outcome = cli("serve", "--workers", "0")
    assert outcome.code == 0
    (call,) = served
    assert (call.host, call.port) == ("127.0.0.1", 8000)
    service = call.app.state.service
    assert (service.mode, service.workers, service.settings.allow_remote) == (
        "local",
        0,
        False,
    )
    assert "INFO uvicorn.error: Uvicorn running" in outcome.stderr
    assert "WARNING" not in outcome.stderr


@pytest.mark.parametrize("host", ["localhost", "::1", "127.0.0.2"])
def test_every_loopback_host_needs_no_flag(served: list[Served], host: str) -> None:
    assert cli("serve", "--host", host, "--port", "8765", "--workers", "1").code == 0
    assert (served[0].host, served[0].port) == (host, 8765)
    assert served[0].app.state.service.workers == 1


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "::", "example.org"])  # noqa: S104 # nosec B104 - refused binds
def test_a_non_loopback_host_is_refused_without_allow_remote(
    served: list[Served], host: str
) -> None:
    outcome = cli("serve", "--host", host)
    assert outcome.code == 2
    assert outcome.stderr.startswith("usage-error: ")
    assert "--allow-remote" in outcome.stderr
    assert served == []


def test_allow_remote_serves_other_machines_and_warns(served: list[Served]) -> None:
    outcome = cli("serve", "--host", "0.0.0.0", "--allow-remote", "--workers", "0")  # noqa: S104 # nosec B104 - recorded, never bound
    assert outcome.code == 0
    (call,) = served
    assert call.host == "0.0.0.0"  # noqa: S104 # nosec B104 - a recorded value
    assert call.app.state.service.settings.allow_remote is True
    assert "WARNING pyeconomics.server: serving on 0.0.0.0" in outcome.stderr
    assert "exposed" in outcome.stderr


@pytest.mark.parametrize(
    "arguments",
    [("--port", "0"), ("--port", "65536"), ("--workers", "-1")],
    ids=["port-low", "port-high", "workers"],
)
def test_bad_numbers_are_usage_errors(
    served: list[Served], arguments: tuple[str, str]
) -> None:
    assert cli("serve", *arguments).code == 2
    assert served == []


@pytest.mark.parametrize("missing", ["fastapi", "uvicorn"])
def test_serve_needs_the_server_extra(
    served: list[Served], monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.setitem(sys.modules, missing, None)
    outcome = cli("serve")
    assert outcome.code == 8
    assert outcome.stderr.startswith("missing-extra: ")
    assert "pyeconomics[server]" in outcome.stderr
    assert served == []


def test_serve_leaves_logging_as_it_found_it(served: list[Served]) -> None:
    before = logging.getLogger("pyeconomics").handlers[:]
    assert cli("serve", "--workers", "0").code == 0
    assert served
    assert logging.getLogger("pyeconomics").handlers == before
    assert logging.getLogger("pyeconomics").propagate is True
    assert logging.getLogger("uvicorn").propagate is True


class _Server:
    """Stands in for uvicorn's Server: records its config, raises what it is told."""

    configs: list[Any] = []  # noqa: RUF012 - shared by the test that sets it
    outcome: BaseException | None = None

    def __init__(self, config: Any) -> None:  # noqa: ANN401 - uvicorn's Config
        _Server.configs.append(config)

    def run(self) -> None:
        if _Server.outcome is not None:
            raise _Server.outcome


@pytest.mark.parametrize(
    "outcome", [None, KeyboardInterrupt(), SystemExit(0)], ids=["stops", "ctrl-c", "0"]
)
def test_run_server_trusts_no_forwarded_header_and_returns(
    monkeypatch: pytest.MonkeyPatch, outcome: BaseException | None
) -> None:
    import uvicorn  # noqa: PLC0415

    monkeypatch.setattr(uvicorn, "Server", _Server)
    monkeypatch.setattr(_Server, "configs", [])
    monkeypatch.setattr(_Server, "outcome", outcome)
    app = object()
    serve_command.run_server(app, "127.0.0.1", 8123)
    (config,) = _Server.configs
    assert (config.app, config.host, config.port) == (app, "127.0.0.1", 8123)
    assert (config.access_log, config.proxy_headers, config.server_header) == (
        False,
        False,
        False,
    )
    assert config.log_config is None


def test_run_server_reports_a_failed_start(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn  # noqa: PLC0415

    monkeypatch.setattr(uvicorn, "Server", _Server)
    monkeypatch.setattr(_Server, "configs", [])
    monkeypatch.setattr(_Server, "outcome", SystemExit(3))
    with pytest.raises(PyeconomicsError, match="could not start"):
        serve_command.run_server(object(), "127.0.0.1", 8123)


def test_a_failed_start_exits_one_with_a_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import uvicorn  # noqa: PLC0415

    monkeypatch.setattr(uvicorn, "Server", _Server)
    monkeypatch.setattr(_Server, "configs", [])
    monkeypatch.setattr(_Server, "outcome", SystemExit(3))
    outcome = cli("serve", "--workers", "0")
    assert outcome.code == 1
    assert outcome.stderr.splitlines()[-1].startswith("pyeconomics-error: ")
    assert "Traceback" not in outcome.stderr
