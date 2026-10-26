# tests/parity/test_parity_bound.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every bound model gives the same bytes on every surface (Phase 4 Step 10).

Each model with bindings is bound with its default profile, once per calculation
the profile serves, as of :data:`~parity_world.AS_OF`, over the parity world's
stand-ins for every real provider (tests/parity/parity_world.py), offline. The
Python API (``pyeconomics.bind``, then ``pyeconomics.run``), the command line
(``--as-of`` and ``--profile``), the REST API (``?as_of=`` and ``?profile=``) and
MCP's ``run_model`` must answer the same bytes, data records included.

The MCP server binds under its ``llm_use`` policy (ADR-0012 decision 14), so its
answers are compared with the Python API's under that same policy; where the
policy refuses no source, that is the same answer. The server here has the
user's opt-in to ``unclear`` sources, the widest policy it takes, so all but a
few runs return bytes there too; tests/mcp/test_mcp_gate.py holds the refusals.

Every surface starts from an empty cache: a source whose terms allow storage
would otherwise be read from the cache by the next surface, which its record
says (``cache_hit``). Every keyed provider has a canary key in the test's
keyring, and ``LeakCheck`` finds it in nothing any surface wrote or logged.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from extra_gaps import excluded_gap
from leakcheck import Canary, LeakCheck, canary
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
from parity_world import AS_OF, bound_cases, inputs_for, parity_world
from server_support import LOOPBACK_ONLY, client

from pyeconomics import registry
from pyeconomics.core.binding import DEFAULT_PROFILE
from pyeconomics.core.provenance import LicenceClass, LlmUsePolicy
from pyeconomics.data import cache
from pyeconomics.mcp import build_server

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from config_isolation import Isolation
    from fastapi.testclient import TestClient
    from parity_world import BoundCase

pytestmark = LOOPBACK_ONLY

#: The MCP server's policy: the opt-in to ``unclear`` sources.
MCP_POLICY = LlmUsePolicy.ALLOW_UNCLEAR

CASES = [
    pytest.param(case, id=f"{case[0]}::{case[1] or 'run'}") for case in bound_cases()
]


class Planted:
    """Every canary key planted for a test, searched for together."""

    def __init__(self, canaries: list[Canary]) -> None:
        self.canaries = canaries

    def needles(self) -> tuple[str, ...]:
        """Every key and the forms URL encoding gives it."""
        return tuple(n for planted in self.canaries for n in planted.needles())


@pytest.fixture(scope="module")
def cli() -> CliSession:
    return CliSession()


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    with client() as test_client:
        yield test_client


@pytest.fixture(scope="module")
def mcp() -> Iterator[McpSession]:
    session = McpSession(build_server(policy=MCP_POLICY))
    yield session
    session.close()


@pytest.fixture
def planted(isolated: Isolation, monkeypatch: pytest.MonkeyPatch) -> Planted:
    """The parity world, with a canary key for each keyed provider."""
    world = parity_world(monkeypatch)
    canaries = []
    for info in world.infos():
        if info.key_variable is not None:
            key = canary(info.id)
            isolated.keyring.set_password("pyeconomics", info.id, key.value)
            canaries.append(key)
    assert canaries
    return Planted(canaries)


def _fresh[T](ask: Callable[[], T]) -> T:
    """Ask a surface from an empty cache."""
    cache.clear()
    return ask()


def _records(answer: Answer) -> list[dict[str, Any]]:
    assert answer.body is not None
    records: list[dict[str, Any]] = json.loads(answer.body)["manifest"]["data_sources"]
    return records


def test_every_bound_model_has_a_case() -> None:
    bound = {model.id for model in registry.models() if model.spec.bindings}
    assert {model_id for model_id, _ in bound_cases()} == bound


@pytest.mark.parametrize("case", CASES)
def test_a_bound_model_gives_the_same_bytes_everywhere(
    case: BoundCase,
    planted: Planted,
    cli: CliSession,
    api: TestClient,
    mcp: McpSession,
) -> None:
    run = Run(case[0], inputs_for(case), as_of=AS_OF, profile=DEFAULT_PROFILE)
    check = LeakCheck(planted)
    with check.logs(), check.warnings():
        answers = {
            "python": _fresh(lambda: python_answer(run, sink=check)),
            "cli": _fresh(lambda: cli_answer(cli, run, sink=check)),
            "rest": _fresh(lambda: rest_answer(api, run, sink=check)),
        }
        under_policy = {
            "python under the MCP policy": _fresh(
                lambda: python_answer(run, llm_use=MCP_POLICY, sink=check)
            ),
        }
        text, structured = _fresh(lambda: mcp_answers(mcp, run, sink=check))
    check.assert_clean()
    # The check records warnings to search them; the suite still allows none.
    assert [sink for sink in check.sinks if sink.startswith("warning:")] == []
    if excluded_gap(registry.get(run.model_id)) is None:
        records = _records(answers["python"])
        assert any(r["licence"] != LicenceClass.USER_SUPPLIED.value for r in records)
        assert not any(r["cache_hit"] for r in records)
    assert_same(answers)
    assert_same({**under_policy, "mcp text": text, "mcp structured": structured})
