# tests/parity/test_parity_golden.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every golden case on every surface gives the same bytes (Phase 4 Step 10).

ADR-0012 decisions 2 and 3: every surface runs a model through
``surfaces.invoke`` and returns ``Result.to_json()``'s bytes. Each case of every
golden file (tests/golden/, read through its loader, so a new model's cases join
with no edit here) is asked of the Python API, the command line (its standard
output with its one newline removed), the REST API (a run's POST body) and MCP's
``run_model`` (its text block and the canonical JSON of its structured content),
and every answer must be the Python API's, byte for byte.

A case whose run fails (a model whose extra leaves its package out of this
Python, tests/extra_gaps.py) must fail the same way everywhere: the same
problem slug, HTTP status, exit code and detail. Each model also gets one case
that must fail on every cell: its first golden case with an input it does not
take.

One command line application, one REST app and one MCP client serve the whole
module, so the suite adds seconds, not minutes, to a cell.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from _loader import audit
from parity_support import (
    Answer,
    CliSession,
    McpSession,
    Run,
    assert_same,
    cli_answer,
    mcp_answers,
    python_answer,
    rest_answer,
)
from server_support import LOOPBACK_ONLY, client

from pyeconomics.core.registry import installed
from pyeconomics.mcp import build_server

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

pytestmark = LOOPBACK_ONLY

FILES = audit(installed()).files

#: Every golden case, by ``<model>::<case>``.
GOLDEN = [
    pytest.param(Run(golden.model, case.inputs), id=f"{golden.model}::{case.id}")
    for golden in FILES
    for case in golden.cases
]
#: One failing case per model: its first golden case, with an unknown input.
UNKNOWN_INPUT = [
    pytest.param(
        Run(golden.model, {**golden.cases[0].inputs, "not_an_input": 1}),
        id=f"{golden.model}::unknown_input",
    )
    for golden in FILES
]


@pytest.fixture(scope="module")
def cli() -> CliSession:
    return CliSession()


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    with client() as test_client:
        yield test_client


@pytest.fixture(scope="module")
def mcp() -> Iterator[McpSession]:
    session = McpSession(build_server())
    yield session
    session.close()


def _ask(run: Run, cli: CliSession, api: TestClient, mcp: McpSession) -> dict[str, Any]:
    text, structured = mcp_answers(mcp, run)
    return {
        "python": python_answer(run),
        "cli": cli_answer(cli, run),
        "rest": rest_answer(api, run),
        "mcp text": text,
        "mcp structured": structured,
    }


def test_a_surface_that_changes_a_byte_or_a_problem_is_named() -> None:
    with pytest.raises(pytest.fail.Exception, match=r"cli: .* at byte 11:"):
        assert_same(
            {
                "python": Answer(body=b'{"value":1.5}'),
                "rest": Answer(body=b'{"value":1.5}'),
                "cli": Answer(body=b'{"value":1.25}'),
            }
        )
    expected = Answer(problem=("invalid-input", 422, 3, "a detail"))
    with pytest.raises(pytest.fail.Exception, match="mcp text: expected"):
        assert_same(
            {
                "python": expected,
                "mcp text": Answer.failed("invalid-input", "another detail"),
            }
        )
    assert Answer.failed("invalid-input", "a detail") == expected


def test_every_registered_model_has_golden_cases_here() -> None:
    assert {golden.model for golden in FILES} == set(installed().ids())
    assert len(GOLDEN) >= 3 * len(FILES)


@pytest.mark.parametrize("run", GOLDEN)
def test_a_golden_case_gives_the_same_bytes_everywhere(
    run: Run, cli: CliSession, api: TestClient, mcp: McpSession
) -> None:
    assert_same(_ask(run, cli, api, mcp))


@pytest.mark.parametrize("run", UNKNOWN_INPUT)
def test_an_invalid_case_gives_the_same_problem_everywhere(
    run: Run, cli: CliSession, api: TestClient, mcp: McpSession
) -> None:
    answers = _ask(run, cli, api, mcp)
    assert answers["python"].problem is not None
    assert answers["python"].problem[:3] == ("invalid-input", 422, 3)
    assert_same(answers)
