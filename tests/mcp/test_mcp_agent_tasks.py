# tests/mcp/test_mcp_agent_tasks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Two scripted agent tasks, as an assistant would run them (Phase 4 Step 8).

**Price a bond and report its duration.** The assistant searches the models,
describes the duration model to read its inputs, prices the bond with the
pricing tool and asks the duration tool (and ``run_model``) for its duration:
the answers are the Python API's.

**Run the Taylor rule for a past date.** ``run_model`` binds
``macro.policy_rule`` as of 2019-06-28 against stand-ins for every real
provider, each answering canned responses under its real metadata
(tests/data/catalog/catalog_world.py), since a cassette replays only its own
recorded query. FRED, whose terms forbid language models, is passed over by
the gate; every record of the result is allowed; and where no permitted source
keeps vintages, the data is revised and labelled so.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING, Any

from leakcheck import canary
from mcp_support import LOOPBACK_ONLY, call, run_with, stub_world, text_of

import pyeconomics
from pyeconomics.core import LlmUsePolicy
from pyeconomics.core.binding import REVISED_DATA
from pyeconomics.mcp import build_server
from pyeconomics.surfaces.invoke import BindRequest, invoke

if TYPE_CHECKING:
    import pytest
    from config_isolation import Isolation
    from mcp import Client

pytestmark = LOOPBACK_ONLY

BOND = {
    "settlement": "2026-01-15",
    "maturity": "2036-01-15",
    "coupon_rate": 0.045,
    "yield_to_maturity": 0.05,
}


def test_price_a_bond_and_report_its_duration() -> None:
    server = build_server()

    async def task(client: Client) -> dict[str, Any]:
        found = await client.call_tool("search_models", {"query": "bond duration"})
        ids = [entry["id"] for entry in (found.structured_content or {})["models"]]
        assert "fixed_income.duration" in ids[:3]
        assert "fixed_income.bond_pricing" in ids
        card = await client.call_tool("describe_model", {"model_id": ids[0]})
        schema = (card.structured_content or {})["input_schema"]
        assert "macaulay_modified" in json.dumps(schema)
        priced = await client.call_tool(
            "fixed_income_bond_pricing", {"calculation": "price_from_yield", **BOND}
        )
        duration = await client.call_tool(
            "fixed_income_duration", {"calculation": "macaulay_modified", **BOND}
        )
        again = await client.call_tool(
            "run_model",
            {
                "model_id": "fixed_income.duration",
                "inputs": {"calculation": "macaulay_modified", **BOND},
            },
        )
        return {
            "price": (priced.structured_content or {})["outputs"],
            "duration": (duration.structured_content or {})["outputs"],
            "again": (again.structured_content or {})["outputs"],
            "summary": text_of(duration, 1),
        }

    answers = run_with(server, task)
    expected = pyeconomics.run(
        "fixed_income.duration", {"calculation": "macaulay_modified", **BOND}
    ).outputs
    assert answers["duration"]["modified_duration"] == expected.modified_duration
    assert answers["duration"]["macaulay_duration"] == expected.macaulay_duration
    assert answers["again"] == answers["duration"]
    price = pyeconomics.run(
        "fixed_income.bond_pricing", {"calculation": "price_from_yield", **BOND}
    ).outputs
    assert answers["price"]["full_price"] == price.full_price
    assert answers["price"]["full_price"] < 100  # a yield above the coupon
    assert answers["duration"]["full_price"] == answers["price"]["full_price"]
    assert "modified_duration = " in answers["summary"]


def test_run_the_taylor_rule_for_a_past_date(
    monkeypatch: pytest.MonkeyPatch, isolated: Isolation
) -> None:
    world = stub_world(monkeypatch)
    # BEA's and FRED's APIs need keys: planted ones, which no stand-in sends.
    for provider in ("bea", "fred"):
        isolated.keyring.set_password("pyeconomics", provider, canary(provider).value)
    server = build_server(policy=LlmUsePolicy.ALLOWED_ONLY)
    arguments = {
        "model_id": "macro.policy_rule",
        "inputs": {"calculation": "taylor_1993"},
        "as_of": "2019-06-28",
    }
    result = call(server, "run_model", arguments)
    assert not result.is_error, text_of(result)
    document = result.structured_content
    assert document is not None
    records = document["manifest"]["data_sources"]
    assert records
    assert {record["llm_use"] for record in records} == {"allowed"}
    # FRED, the only source of those two that keeps vintages, is refused: so the
    # bind reads the latest data from the originators and labels it revised.
    assert "fred" not in {record["provider"] for record in records}
    by_field = {record["field"]: record for record in records}
    assert by_field["inflation"]["provider"] == "bea"
    assert by_field["unemployment"]["provider"] == "bls"
    revised = {r["field"] for r in records if REVISED_DATA in r["warnings"]}
    assert {"inflation", "unemployment"} <= revised
    kept = [r for r in records if r["vintage"] == "as_of:2019-06-28"]
    assert all(REVISED_DATA not in r["warnings"] for r in kept)
    assert REVISED_DATA in {w["code"] for w in document["warnings"]}
    summary = text_of(result, 1)
    assert f"Warnings: {REVISED_DATA}" in summary
    assert "fred" not in summary
    # The gate made the difference: without it the same bind reads FRED's vintages.
    from pyeconomics.data import bindings  # noqa: PLC0415

    real = bindings.bind_model

    def in_world(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401 - bind_model's
        kwargs["registry"] = world
        return real(*args, **kwargs)

    monkeypatch.setattr(bindings, "bind_model", in_world)
    ungated = invoke(
        "macro.policy_rule",
        {"calculation": "taylor_1993"},
        bind=BindRequest(as_of=dt.date(2019, 6, 28)),
    )
    assert "fred" in {r.provider for r in ungated.manifest.data_sources}
