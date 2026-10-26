# tests/parity/parity_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""One session of every surface, and the answers the parity suite compares.

ADR-0012 decision 3: every surface returns the bytes ``Result.to_json()`` gives,
the command line followed by one newline, and an error reaches every surface as
the same problem from the error table. The parity suite (Phase 4 Step 10) asks
each surface the same question and compares what comes back as an
:class:`Answer`: the canonical bytes, or the problem's slug, HTTP status, exit
code and detail.

- :class:`Run`: a model, its inputs and, for a bound run, the date and profile;
- :func:`python_answer`: the Python API (``pyeconomics.run``, after
  ``pyeconomics.bind`` for a bound run);
- :class:`CliSession`: one command line application, built once, whose streams
  are emptied before each command line it runs (``cli.app.run_line``, the path
  ``main`` takes), and :func:`cli_answer`, ``models run ID --inputs -``;
- :func:`rest_answer`: ``POST /v1/models/<id>/run`` through a ``TestClient``
  over an inline pool (``server_support.client``);
- :class:`McpSession`: one SDK client connected to the MCP server in memory and
  held open on a blocking portal's event loop, and :func:`mcp_answers`,
  ``run_model``'s text block and the canonical JSON of its structured content;
- :func:`assert_same`: every answer equals the first, or the test fails naming
  each surface that differs and where.

Each answer function also hands everything its surface wrote (headers, every
content block and the ``_meta``, standard error) to an optional :class:`Sink`, a
``LeakCheck`` (tests/data/leakcheck.py) in the bound runs.

A parity failure is a bug in the surface that changed the bytes: no comparison
here is loosened to pass.
"""

from __future__ import annotations

import io
import json
from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, NoReturn, Protocol

import pytest
from anyio.from_thread import start_blocking_portal
from cli_support import Outcome
from mcp import Client
from server_support import problem

import pyeconomics
from pyeconomics.cli.app import build, run_line
from pyeconomics.cli.context import Context
from pyeconomics.cli.output import Streams
from pyeconomics.core.binding import DEFAULT_PROFILE
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces.problems import ROWS, TYPE_BASE, Problem, problem_for

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping

    from fastapi.testclient import TestClient
    from mcp import types
    from mcp.server import Server

    from pyeconomics.core.provenance import LlmUsePolicy

__all__ = [
    "Answer",
    "CliSession",
    "McpSession",
    "Run",
    "Sink",
    "assert_same",
    "cli_answer",
    "mcp_answers",
    "python_answer",
    "rest_answer",
]

#: Each slug's row of the error table: the status and exit code it stands for.
_ROW_OF: Final = {row.slug: row for row in ROWS}
#: How much of each side a byte difference shows.
_CONTEXT: Final = 60


class Sink(Protocol):
    """Where an answer function records what its surface wrote: a ``LeakCheck``."""

    def add(self, sink: str, payload: str | bytes) -> None:
        """Record what reached a sink."""
        ...


@dataclass(frozen=True, slots=True)
class Run:
    """One question for every surface: a model, its inputs, and what to bind."""

    model_id: str
    inputs: Mapping[str, object]
    as_of: dt.date | None = None
    profile: str | None = None

    @property
    def bound(self) -> bool:
        """Whether the run binds the model's data first."""
        return self.as_of is not None or self.profile is not None

    @property
    def body(self) -> bytes:
        """The inputs as canonical JSON: what a surface that reads JSON is sent."""
        return canonical_json(dict(self.inputs))


@dataclass(frozen=True, slots=True)
class Answer:
    """What a surface answered: canonical bytes, or a problem.

    A problem is its slug, HTTP status, exit code and detail; a surface that
    carries no status (the command line) or no exit code (the REST API, MCP)
    takes it from its slug's row of the error table.
    """

    body: bytes | None = None
    problem: tuple[str, int, int, str] | None = None

    @classmethod
    def of(cls, made: Problem) -> Answer:
        """Return the answer a problem from the error table makes."""
        return cls(problem=(made.slug, made.status, made.exit_code, made.detail))

    @classmethod
    def failed(
        cls,
        slug: str,
        detail: str,
        *,
        status: int | None = None,
        exit_code: int | None = None,
    ) -> Answer:
        """Return a problem answer, filling in what the surface does not carry.

        The status or exit code comes from the slug's row; an unknown slug gets
        ``-1``, which matches no row.
        """
        row = _ROW_OF.get(slug)
        if status is None:
            status = -1 if row is None else row.status
        if exit_code is None:
            exit_code = -1 if row is None else row.exit_code
        return cls(problem=(slug, status, exit_code, detail))


# --- the Python API ------------------------------------------------------------------


def python_answer(
    run: Run, *, llm_use: LlmUsePolicy | None = None, sink: Sink | None = None
) -> Answer:
    """Ask the Python API: ``pyeconomics.run``, after ``pyeconomics.bind`` if bound.

    ``llm_use`` is the policy of a surface that feeds a language model (the MCP
    server), which a bind applies (ADR-0012 decision 14).
    """
    overrides: dict[str, Any] = dict(run.inputs)
    try:
        if run.bound:
            bound = pyeconomics.bind(
                run.model_id,
                as_of=run.as_of,
                profile=run.profile or DEFAULT_PROFILE,
                llm_use=llm_use,
                **overrides,
            )
            result = pyeconomics.run(run.model_id, bound)
        else:
            result = pyeconomics.run(run.model_id, overrides)
    except Exception as error:  # noqa: BLE001 - every failure is an answer
        if sink is not None:
            sink.add("python:error", repr(error))
        return Answer.of(problem_for(error))
    body = result.to_json().encode("utf-8")
    if sink is not None:
        sink.add("python:result", body)
    return Answer(body=body)


# --- the command line ----------------------------------------------------------------


def _no_prompt(prompt: str) -> NoReturn:
    msg = f"the command asked for a hidden value: {prompt!r}"
    raise AssertionError(msg)


class CliSession:
    """One command line application, reused for every command line it runs.

    The application is built once around in-memory streams, which are emptied
    before each command line, so the consoles it holds stay valid; each command
    line then runs through :func:`~pyeconomics.cli.app.run_line`, as
    :func:`pyeconomics.cli.main` runs it.
    """

    def __init__(self) -> None:
        self.stdin, self.stdout, self.stderr = io.BytesIO(), io.BytesIO(), io.BytesIO()
        streams = Streams(
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
            ask_secret=_no_prompt,
        )
        self.context = Context(streams=streams)
        self.app = build(self.context)

    def __call__(self, *args: str, stdin: bytes = b"") -> Outcome:
        """Run ``pyeconomics <args>`` and return what it wrote."""
        for stream in (self.stdin, self.stdout, self.stderr):
            stream.seek(0)
            stream.truncate()
        self.stdin.write(stdin)
        self.stdin.seek(0)
        code = run_line(self.context, args, app=self.app)
        return Outcome(code, self.stdout.getvalue(), self.stderr.getvalue().decode())


def _bind_options(run: Run) -> list[str]:
    options = []
    if run.as_of is not None:
        options += ["--as-of", run.as_of.isoformat()]
    if run.profile is not None:
        options += ["--profile", run.profile]
    return options


def cli_answer(cli: CliSession, run: Run, *, sink: Sink | None = None) -> Answer:
    """Ask the command line: ``models run ID --inputs -``, the inputs on stdin.

    A success writes the canonical bytes and exactly one newline, and nothing on
    standard error; a failure writes its problem's ``slug: detail`` line there.
    """
    outcome = cli(
        "models",
        "run",
        run.model_id,
        "--inputs",
        "-",
        *_bind_options(run),
        stdin=run.body,
    )
    if sink is not None:
        sink.add("cli:stdout", outcome.stdout)
        sink.add("cli:stderr", outcome.stderr)
    if outcome.code == 0:
        assert outcome.stderr == "", outcome.stderr
        assert outcome.stdout.endswith(b"\n"), "the output does not end in a newline"
        return Answer(body=outcome.stdout[:-1])
    assert outcome.stdout == b"", "a failure wrote to standard output"
    slug, _, detail = outcome.stderr.removesuffix("\n").partition(": ")
    return Answer.failed(slug, detail, exit_code=outcome.code)


# --- the REST API --------------------------------------------------------------------


def rest_answer(api: TestClient, run: Run, *, sink: Sink | None = None) -> Answer:
    """Ask the REST API: the inputs as the body of a run's POST form."""
    params: dict[str, str] = {}
    if run.as_of is not None:
        params["as_of"] = run.as_of.isoformat()
    if run.profile is not None:
        params["profile"] = run.profile
    response = api.post(
        f"/v1/models/{run.model_id}/run", content=run.body, params=params
    )
    if sink is not None:
        sink.add("rest:body", response.content)
        sink.add("rest:headers", repr(sorted(response.headers.items())))
    if response.status_code == 200:
        assert response.headers["content-type"] == "application/json"
        return Answer(body=response.content)
    body = problem(response)
    slug = str(body["type"]).removeprefix(TYPE_BASE)
    return Answer.failed(slug, str(body["detail"]), status=response.status_code)


# --- MCP -----------------------------------------------------------------------------


class McpSession:
    """One SDK client connected to an MCP server in memory, open until closed.

    The client lives on a blocking portal's event loop in its own thread, so the
    tests, which are synchronous, share one connection.
    """

    def __init__(self, server: Server[Any]) -> None:
        self._stack = ExitStack()
        self.portal = self._stack.enter_context(start_blocking_portal())
        client = Client(server, mode="auto", raise_exceptions=False, cache=None)
        self.client = self._stack.enter_context(
            self.portal.wrap_async_context_manager(client)
        )

    def call(self, name: str, arguments: Mapping[str, Any]) -> types.CallToolResult:
        """Call one tool and return its result."""
        result: types.CallToolResult = self.portal.call(
            self.client.call_tool, name, dict(arguments)
        )
        return result

    def close(self) -> None:
        """Disconnect the client and stop the portal."""
        self._stack.close()


def _doubles(value: object) -> object:
    """Read every JSON number as the double RFC 8785 says it is.

    Python's ``json`` reads a whole number as an ``int``, and a double above
    2**53 printed without an exponent as an ``int`` canonical JSON refuses; as a
    ``float`` it writes the same text it was read from.
    """
    if isinstance(value, dict):
        return {key: _doubles(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_doubles(item) for item in value]
    if isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    return value


def _text(result: types.CallToolResult, index: int) -> str:
    block = result.content[index]
    assert block.type == "text"
    return block.text


def mcp_answers(
    mcp: McpSession, run: Run, *, sink: Sink | None = None
) -> tuple[Answer, Answer]:
    """Ask MCP's ``run_model``: its first text block, and its structured content.

    The structured content is compared as its canonical JSON; a tool error has
    none, and both answers are its problem.
    """
    arguments: dict[str, Any] = {
        "model_id": run.model_id,
        "inputs": json.loads(run.body),
    }
    if run.as_of is not None:
        arguments["as_of"] = run.as_of.isoformat()
    if run.profile is not None:
        arguments["profile"] = run.profile
    result = mcp.call("run_model", arguments)
    if sink is not None:
        sink.add("mcp:result", result.model_dump_json())
    if result.is_error:
        assert result.structured_content is None
        body = json.loads(_text(result, 0))
        slug = str(body["type"]).removeprefix(TYPE_BASE)
        failed = Answer.failed(slug, str(body["detail"]), status=int(body["status"]))
        return failed, failed
    structured = canonical_json(_doubles(result.structured_content))
    return Answer(body=_text(result, 0).encode("utf-8")), Answer(body=structured)


# --- comparing -----------------------------------------------------------------------


def _difference(expected: Answer, found: Answer) -> str:
    if expected.body is None or found.body is None:
        return f"expected {expected.problem or 'bytes'}, got {found.problem or 'bytes'}"
    first = next(
        (
            i
            for i, (a, b) in enumerate(zip(expected.body, found.body, strict=False))
            if a != b
        ),
        min(len(expected.body), len(found.body)),
    )
    start = max(0, first - _CONTEXT)
    return (
        f"{len(found.body)} bytes against {len(expected.body)}, first difference at "
        f"byte {first}: expected {expected.body[start : first + _CONTEXT]!r}, got "
        f"{found.body[start : first + _CONTEXT]!r}"
    )


def assert_same(answers: Mapping[str, Answer]) -> None:
    """Fail unless every answer equals the first, naming each that differs."""
    (reference, expected), *rest = answers.items()
    differing = [
        f"{name}: {_difference(expected, found)}"
        for name, found in rest
        if found != expected
    ]
    if differing:
        pytest.fail(
            f"the surfaces disagree with {reference}:\n" + "\n".join(differing),
            pytrace=False,
        )
