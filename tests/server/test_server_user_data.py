# tests/server/test_server_user_data.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The server keeps no value a caller sends (Phase 5 Step 9; ADR-0013 decision 11).

A model page's "use my own data" turns a user's file into the values of one
run, posted as its body (web/tests/e2e/user-data.spec.ts proves that nothing
else leaves the browser). This module proves the other end: the server reads a
run's body only to run it, and keeps none of it.

- The code (a static check of every module under src/pyeconomics/server): only
  the run route's ``_body`` reads a request body, through ``request.stream()``;
  no logging call is handed a body, a payload or inputs; and nothing writes a
  file but the OpenAPI writer, which no request reaches.
- A ``POST`` run answers ``Cache-Control: no-store`` and leaves the run cache
  empty, whether it succeeds or fails.
- No log record the server writes, the request log included, holds a value
  from a run's body; a problem a run on the caller's values became is logged by
  its slug, status and error type, without its detail, which can quote one of
  them, while the caller still reads the detail.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

import pytest
from server_support import LOOPBACK_ONLY, client, service_of, use_toys

from pyeconomics.core.canonical import canonical_json
from pyeconomics.server import logs
from pyeconomics.server.limits import RateLimits
from pyeconomics.server.run_cache import NO_STORE

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx2 import Response

pytestmark = LOOPBACK_ONLY

SERVER: Final = Path(__file__).resolve().parents[2] / "src" / "pyeconomics" / "server"
#: The one function that reads a request body, and the module it is in.
BODY_READER: Final = ("app.py", "_body")
#: The calls that read a request's body.
BODY_CALLS: Final = frozenset({"body", "stream", "json", "form"})
#: The names a body's bytes go by in the server.
BODY_NAMES: Final = frozenset({"body", "payload", "inputs", "content", "chunks"})
#: The logging methods.
LOG_CALLS: Final = frozenset(
    {"debug", "info", "warning", "error", "exception", "critical", "log"}
)
#: The calls that write a file, and the one place each may appear.
FILE_WRITES: Final = frozenset({"write_bytes", "write_text", "open", "mkdir"})
WRITERS_ALLOWED: Final = frozenset({("openapi.py", "write_openapi")})
#: A value no run would hold by chance, sent in a body.
MARKER: Final = 0.4321987654
RUN: Final = "/v1/models/foundations.toy_time_value/run"


def _modules() -> list[Path]:
    return sorted(SERVER.glob("*.py"))


def _functions(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    """Every function in a module, with the name of the outermost one it is in."""
    found: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found.append((node.name, node))
        elif isinstance(node, ast.ClassDef):
            found += [
                (f"{node.name}.{item.name}", item)
                for item in node.body
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
            ]
    return found


def _calls(node: ast.AST) -> list[ast.Call]:
    return [call for call in ast.walk(node) if isinstance(call, ast.Call)]


def _method(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _names(node: ast.AST) -> set[str]:
    found = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    found |= {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
    return found


@pytest.mark.parametrize("path", _modules(), ids=lambda path: path.name)
def test_only_the_run_route_reads_a_body_and_no_log_call_is_handed_one(
    path: Path,
) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for name, function in _functions(tree):
        for call in _calls(function):
            method = _method(call)
            receiver = call.func.value if isinstance(call.func, ast.Attribute) else None
            if (
                method in BODY_CALLS
                and isinstance(receiver, ast.Name)
                and receiver.id == "request"
            ):
                assert (path.name, name) == BODY_READER, (
                    f"{path.name}:{call.lineno} {name} reads a request body"
                )
            if method in LOG_CALLS and isinstance(receiver, ast.Name | ast.Call):
                handed = (
                    set().union(*(_names(arg) for arg in call.args))
                    if call.args
                    else set()
                )
                leaked = sorted(handed & BODY_NAMES)
                assert not leaked, f"{path.name}:{call.lineno} {name} logs {leaked}"
            if method in FILE_WRITES:
                assert (path.name, name) in WRITERS_ALLOWED, (
                    f"{path.name}:{call.lineno} {name} writes a file"
                )


def test_the_static_check_finds_the_body_reader_and_the_loggers() -> None:
    """The check above looks at code that exists, so a rename cannot empty it."""
    tree = ast.parse((SERVER / BODY_READER[0]).read_text(encoding="utf-8"))
    reader = dict(_functions(tree))[BODY_READER[1]]
    assert any(_method(call) == "stream" for call in _calls(reader))
    logged = [
        call
        for path in _modules()
        for call in _calls(ast.parse(path.read_text(encoding="utf-8")))
        if _method(call) in LOG_CALLS
    ]
    assert logged


def _posts(api: TestClient) -> list[Response]:
    good = {
        "calculation": "present_value",
        "rate": MARKER,
        "years": 10,
        "future_value": 100,
    }
    bad = {**good, "years": -MARKER}
    return [
        api.post(RUN, content=canonical_json(good)),
        api.post(RUN, content=canonical_json(bad)),
        api.post(
            "/v1/models/foundations.toy_fail/run",
            content=canonical_json(
                {"error": "InputError", "message": f"rate {MARKER} is above its bound"}
            ),
        ),
    ]


@pytest.mark.parametrize("mode", ["local", "hosted"])
def test_a_post_run_is_no_store_and_its_values_reach_no_log_and_no_cache(
    mode: Literal["local", "hosted"],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    use_toys(monkeypatch)
    # The test client logs its own request lines: they are not the server's.
    monkeypatch.setattr(logging.getLogger("httpx2"), "disabled", True)
    with (
        caplog.at_level(logging.DEBUG),
        client(mode=mode, rate_limits=RateLimits.off()) as api,
    ):
        responses = _posts(api)
        cached = len(service_of(api).cache)
    assert [response.status_code for response in responses] == [200, 422, 422]
    for response in responses:
        assert response.headers["cache-control"] == NO_STORE
    assert cached == 0
    assert str(MARKER) in responses[2].json()["detail"]
    lines = [record.getMessage() for record in caplog.records]
    assert any(record.name == logs.ACCESS_LOGGER for record in caplog.records)
    assert [line for line in lines if str(MARKER) in line or "4321987" in line] == []
    problems = [r.getMessage() for r in caplog.records if r.name == logs.LOGGER]
    assert problems == ["invalid-input (422, InputError)"] * 2


def test_a_problem_that_holds_no_caller_value_keeps_its_detail_in_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logs.LOGGER), client() as api:
        api.get("/v1/series/nowhere:SERIES")
    (line,) = [r.getMessage() for r in caplog.records if r.name == logs.LOGGER]
    assert line.startswith("provider-not-found (404, ProviderNotFoundError): ")
