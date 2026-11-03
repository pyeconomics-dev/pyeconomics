# tests/parity/test_parity_series.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A series gives the same bytes on every surface, transformed or not (Phase 5 Step 9).

One concept is read, over one window, with no transform and with each kind of
single-series transform, from the Python API (``data.get``, its document as
canonical JSON), the command line (``data get --format json``, one newline
removed), the REST API (``GET /v1/series/{target}``) and MCP's ``get_series``
(its text block and the canonical JSON of its structured content). The answers
must be the same bytes, and a transform must be recorded last in every source
record.

The MCP server reads under its ``llm_use`` policy and its observation limit, so
its answers are compared with the Python API's under the same policy and limit;
where neither changes the answer, that is the same document. Every surface
starts from an empty cache, as the bound runs do (test_parity_bound.py), and
every keyed provider has a canary key that no answer may hold.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from leakcheck import LeakCheck, canary
from parity_support import Answer, CliSession, McpSession, assert_same
from parity_world import parity_world
from server_support import LOOPBACK_ONLY, client

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import LlmUsePolicy
from pyeconomics.core.transforms import canonical_transform
from pyeconomics.data import api, cache
from pyeconomics.mcp import build_server
from pyeconomics.mcp.server import DEFAULT_SERIES_LIMIT
from pyeconomics.surfaces.documents import data_document
from pyeconomics.surfaces.series import series_arguments

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from config_isolation import Isolation
    from fastapi.testclient import TestClient
    from leakcheck import Canary

pytestmark = LOOPBACK_ONLY

#: A hosted-safe concept whose sources keep no vintages and allow storage.
CONCEPT = "us.unemployment.rate"
WINDOW = {"start": "2023-01-01", "end": "2025-12-31"}
#: No transform, then one of each kind a caller may ask for.
TRANSFORMS = [
    None,
    "yoy",
    "pct_change(periods=12)",
    "diff(periods=3)",
    "lag",
    "log",
    "convert(to=quarterly,method=mean)",
]
MCP_POLICY = LlmUsePolicy.ALLOW_UNCLEAR


class Planted:
    """The canary keys planted for a test."""

    def __init__(self, canaries: list[Canary]) -> None:
        self.canaries = canaries

    def needles(self) -> tuple[str, ...]:
        """Every key and the forms URL encoding gives it."""
        return tuple(n for planted in self.canaries for n in planted.needles())


@pytest.fixture(scope="module")
def cli() -> CliSession:
    return CliSession()


@pytest.fixture(scope="module")
def rest() -> Iterator[TestClient]:
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
    return Planted(canaries)


def _fresh[T](ask: Callable[[], T]) -> T:
    """Ask a surface from an empty cache."""
    cache.clear()
    return ask()


def _options(transform: str | None) -> dict[str, str]:
    return {**WINDOW, **({} if transform is None else {"transform": transform})}


def _python(transform: str | None, **extra: Any) -> Answer:  # noqa: ANN401
    resolved = api.get(CONCEPT, **series_arguments(_options(transform)), **extra)
    return Answer(body=canonical_json(data_document(resolved)))


def _cli(cli: CliSession, transform: str | None) -> Answer:
    flags = [
        f"--{name.replace('_', '-')}={value}"
        for name, value in _options(transform).items()
    ]
    outcome = cli("data", "get", CONCEPT, *flags, "--format", "json")
    assert (outcome.code, outcome.stderr) == (0, "")
    assert outcome.stdout.endswith(b"\n")
    return Answer(body=outcome.stdout[:-1])


def _rest(rest: TestClient, transform: str | None) -> Answer:
    response = rest.get(f"/v1/series/{CONCEPT}", params=_options(transform))
    assert response.status_code == 200, response.text
    return Answer(body=response.content)


def _mcp(mcp: McpSession, transform: str | None) -> tuple[Answer, Answer]:
    result = mcp.call("get_series", {"target": CONCEPT, **_options(transform)})
    assert not result.is_error
    block = result.content[0]
    assert block.type == "text"
    return (
        Answer(body=block.text.encode("utf-8")),
        Answer(body=canonical_json(result.structured_content)),
    )


@pytest.mark.parametrize("transform", TRANSFORMS, ids=lambda t: t or "none")
def test_a_series_gives_the_same_bytes_on_every_surface(
    transform: str | None,
    planted: Planted,
    cli: CliSession,
    rest: TestClient,
    mcp: McpSession,
) -> None:
    check = LeakCheck(planted)
    with check.logs(), check.warnings():
        answers = {
            "python": _fresh(lambda: _python(transform)),
            "cli": _fresh(lambda: _cli(cli, transform)),
            "rest": _fresh(lambda: _rest(rest, transform)),
        }
        under_policy = _fresh(
            lambda: _python(
                transform, llm_use=MCP_POLICY, max_observations=DEFAULT_SERIES_LIMIT
            )
        )
        text, structured = _fresh(lambda: _mcp(mcp, transform))
    assert_same(answers)
    assert_same(
        {
            "python under the MCP policy": under_policy,
            "mcp text": text,
            "mcp": structured,
        }
    )
    assert under_policy == answers["python"]
    for name, answer in {**answers, "mcp text": text}.items():
        check.add(name, answer.body or b"")
    check.assert_clean()
    # The check records warnings to search them; the suite still allows none.
    assert [sink for sink in check.sinks if sink.startswith("warning:")] == []
    document = json.loads(answers["python"].body or b"")
    assert document["sources"]
    for record in document["sources"]:
        assert not record["cache_hit"]
        if transform is not None:
            assert record["transforms"][-1] == canonical_transform(transform)
    notes = document["frame"]["meta"]["notes"]
    assert any(note.startswith("transformed: ") for note in notes) == (
        transform is not None
    )
