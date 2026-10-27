# tests/ai/test_ai_leaks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""No key reaches any sink of the narrative (the Step 11 security gate).

A canary key sits in the chain for each provider, and the narrative runs
through the real :class:`~pyeconomics.data.transport.http.HttpTransport` over a
fake connection pool, so the key is really attached to the wire request. The
logs (at DEBUG), warnings, the narrative's repr and text, the prompt, a cassette
recorded from the exchange, and every failure's exception and problem are
searched for it; a positive control proves the key did reach the wire.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from ai_support import answer, black_scholes, enable, narrative_request, ok
from fakes import FakePool, FakeRaw
from leakcheck import LeakCheck, canary

from pyeconomics.ai import PROVIDERS, narrate
from pyeconomics.ai.prompt import render_prompt
from pyeconomics.data.transport.cassette import Cassette
from pyeconomics.data.transport.http import HttpTransport
from pyeconomics.surfaces.problems import problem_for

if TYPE_CHECKING:
    from config_isolation import Isolation

PROVIDER_IDS = sorted(PROVIDERS)


def _transport(*raws: FakeRaw) -> tuple[HttpTransport, FakePool]:
    pool = FakePool(*raws)
    return HttpTransport(pool=pool, sleep=lambda _seconds: None), pool


def _wire(pool: FakePool) -> list[str]:
    return [
        f"{call.url} {call.headers} {(call.body or b'').decode()}"
        for call in pool.calls
    ]


@pytest.mark.parametrize("provider", PROVIDER_IDS)
def test_a_narrative_carries_the_key_to_the_wire_and_nowhere_else(
    provider: str, isolated: Isolation
) -> None:

    planted = canary(provider)
    isolated.keyring.set_password("pyeconomics", provider, planted.value)
    enable()
    body = json.dumps(answer(provider)).encode()
    transport, pool = _transport(
        FakeRaw(200, body, {"content-type": "application/json"})
    )
    check = LeakCheck(planted)
    result = black_scholes()

    narrative = check.run(
        lambda: narrate(result, provider=provider, transport=transport)
    )

    assert narrative is not None
    check.add("narrative:render", narrative.render())
    check.add("narrative:repr", repr(narrative))
    check.add("prompt", render_prompt(result))
    recorded = Cassette.from_exchanges(
        provider,
        ok({}).retrieved_at,
        [(narrative_request(provider), ok(answer(provider)))],
        synthetic=True,
    )
    check.add("cassette", recorded.document())
    check.assert_clean()
    # The positive control: the key did reach the wire request, in a header.
    assert check.found_in({"wire": _wire(pool)}) == ["wire"]


@pytest.mark.parametrize("provider", PROVIDER_IDS)
@pytest.mark.parametrize("status", [401, 403, 429, 500, 400])
def test_a_failure_carries_no_key(
    provider: str, status: int, isolated: Isolation
) -> None:
    planted = canary(provider)
    isolated.keyring.set_password("pyeconomics", provider, planted.value)
    enable()
    echo = json.dumps({"error": {"message": f"bad key {planted.value}"}}).encode()
    transport, pool = _transport(
        *[FakeRaw(status, echo, {"content-type": "application/json"})] * 3
    )
    check = LeakCheck(planted)
    outcome = check.run(
        lambda: narrate(black_scholes(), provider=provider, transport=transport)
    )
    assert outcome is None
    caught = [name for name in check.sinks if name.startswith("exception:")]
    assert len(caught) == 1
    error_text = check.sinks[caught[0]][0]
    assert error_text  # the exception's message, collected above
    check.assert_clean()
    assert check.found_in({"wire": _wire(pool)}) == ["wire"]


@pytest.mark.parametrize("status", [401, 500])
def test_a_failures_problem_carries_no_key(status: int, isolated: Isolation) -> None:
    planted = canary("openai")
    isolated.keyring.set_password("pyeconomics", "openai", planted.value)
    enable()
    transport, _ = _transport(*[FakeRaw(status, planted.value.encode())] * 3)
    check = LeakCheck(planted)
    with pytest.raises(Exception) as caught:  # noqa: PT011 - any mapped failure
        narrate(black_scholes(), transport=transport)
    problem = problem_for(caught.value)
    check.add("problem:detail", problem.detail)
    check.add("problem:body", problem.to_json())
    check.add("problem:cli", problem.cli_message)
    check.assert_clean()
