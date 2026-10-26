# tests/mcp/test_mcp_agent_tasks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Scripted agent tasks, as an assistant would run them (Phase 4 Steps 8 and 9).

The task set is scripts/mcp/agent_tasks.py, which the live evaluation
(scripts/mcp_agent_eval.py) also gives a real agent: discovery, three headline
tools, a bound run, a series with its attribution, the sources and a refusal.
:func:`test_scripted_task` runs each task's scripted calls against the server,
over stand-ins for every real provider (tests/data/catalog/catalog_world.py),
and checks the value they reach against the Python API's in the same world.

Two tasks are also told in full:

**Price a bond and report its duration.** The assistant searches the models,
describes the duration model to read its inputs, prices the bond with the
pricing tool and asks the duration tool (and ``run_model``) for its duration:
the answers are the Python API's.

**Run the Taylor rule for a past date.** ``run_model`` binds
``macro.policy_rule`` as of 2019-06-28 against stand-ins for every real
provider, each answering canned responses under its real metadata, since a
cassette replays only its own recorded query. FRED, whose terms forbid language
models, is passed over by the gate; every record of the result is allowed; and
where no permitted source keeps vintages, the data is revised and labelled so.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from leakcheck import canary
from mcp_support import LOOPBACK_ONLY, call, problem_of, run_with, stub_world, text_of

import pyeconomics
from pyeconomics.core import LlmUsePolicy
from pyeconomics.core.binding import REVISED_DATA
from pyeconomics.mcp import build_server
from pyeconomics.surfaces.invoke import BindRequest, invoke

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

    from config_isolation import Isolation
    from mcp import Client, types

pytestmark = LOOPBACK_ONLY


def _load_tasks() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "mcp" / "agent_tasks.py"
    spec = importlib.util.spec_from_file_location("mcp_agent_tasks", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through it
    spec.loader.exec_module(module)
    return module


agent_tasks = _load_tasks()
TASKS = agent_tasks.TASKS
#: Where the stand-ins' data starts for the task set, whose dates are in 2025.
TASK_WORLD_START = dt.date(2024, 7, 1)


def _in_order(wanted: Sequence[str], called: Sequence[str]) -> bool:
    remaining = iter(called)
    return all(name in remaining for name in wanted)


def _plant_keys(isolated: Isolation) -> None:
    # BEA's and FRED's APIs need keys: planted ones, which no stand-in sends.
    for provider in ("bea", "fred"):
        isolated.keyring.set_password("pyeconomics", provider, canary(provider).value)


def test_the_task_set_covers_what_step_9_names() -> None:
    assert len(TASKS) >= 8
    assert len({task.id for task in TASKS}) == len(TASKS)
    tools = [name for task in TASKS for name in task.tools]
    assert {"search_models", "describe_model", "get_series", "list_sources"} <= set(
        tools
    )
    assert len({name for name in tools if name not in agent_tasks.DISCOVERY}) >= 3
    bound = [task for task in TASKS if any("as_of" in c.arguments for c in task.calls)]
    assert bound
    assert any(task.mentions for task in TASKS if "get_series" in task.tools)
    assert [task.refusal for task in TASKS if task.refusal] == ["llm-use-forbidden"]


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.id)
def test_scripted_task(
    task: Any,  # noqa: ANN401 - agent_tasks.AgentTask, loaded from its file
    monkeypatch: pytest.MonkeyPatch,
    isolated: Isolation,
) -> None:
    stub_world(monkeypatch, TASK_WORLD_START)
    _plant_keys(isolated)
    server = build_server(policy=LlmUsePolicy.ALLOWED_ONLY)

    async def work(client: Client) -> list[types.CallToolResult]:
        return [
            await client.call_tool(step.tool, dict(step.arguments))
            for step in task.calls
        ]

    results = run_with(server, work)
    assert _in_order(task.tools, [step.tool for step in task.calls])
    *before, last = results
    assert not any(result.is_error for result in before)
    if task.refusal is not None:
        assert problem_of(last)["type"].endswith(f"/{task.refusal}")
        return
    assert not last.is_error, text_of(last)
    document = last.structured_content
    assert document is not None
    assert task.answer(document) == pytest.approx(task.expected(), rel=1e-12, abs=0)
    for text in task.mentions:
        assert any(text in attribution for attribution in document["attributions"])


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
