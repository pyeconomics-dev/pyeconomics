# tests/mcp/test_mcp_runs.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP server's runs return the canonical result (Phase 4 Step 8).

For each headline model's first example, its headline tool and ``run_model``
answer ``Result.to_json()`` as their first text block and its parsed object as
structured content (which the SDK's client validated against the output
schema), and the shared one-line summary as their second block; both eras of
the protocol answer the same. A failure answers a tool error whose text is the
problem from the error table: invalid inputs, an unknown model, an unknown
argument; an unknown tool is a protocol error.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from mcp.shared.exceptions import MCPError
from mcp_support import LOOPBACK_ONLY, call, problem_of, run_with, text_of

from pyeconomics import registry, run
from pyeconomics.mcp import build_server
from pyeconomics.mcp.headline import HEADLINE
from pyeconomics.mcp.tools import tool_name
from pyeconomics.surfaces.envelope import summary_of

if TYPE_CHECKING:
    from mcp import Client

pytestmark = LOOPBACK_ONLY

SERVER = build_server()


def _first_example(model_id: str) -> dict[str, Any]:
    return dict(registry.get(model_id).spec.examples[0].inputs)


def _expected(model_id: str) -> str:
    return run(model_id, _first_example(model_id)).to_json()


@pytest.mark.parametrize("model_id", HEADLINE)
def test_a_headline_tool_returns_the_canonical_result(model_id: str) -> None:
    result = call(SERVER, tool_name(model_id), _first_example(model_id))
    expected = _expected(model_id)
    assert not result.is_error
    assert text_of(result) == expected
    assert result.structured_content == json.loads(expected)
    title = registry.get(model_id).spec.title
    assert text_of(result, 1) == summary_of(json.loads(expected), title)
    assert len(result.content) == 2


@pytest.mark.parametrize("model_id", HEADLINE)
def test_run_model_returns_the_canonical_result(model_id: str) -> None:
    arguments = {"model_id": model_id, "inputs": _first_example(model_id)}
    result = call(SERVER, "run_model", arguments)
    expected = _expected(model_id)
    assert text_of(result) == expected
    assert result.structured_content == json.loads(expected)


def test_a_legacy_client_receives_the_same_result() -> None:
    model_id = "fixed_income.duration"
    result = call(SERVER, tool_name(model_id), _first_example(model_id), mode="legacy")
    assert text_of(result) == _expected(model_id)
    assert result.structured_content == json.loads(_expected(model_id))


def test_invalid_inputs_answer_the_invalid_input_problem() -> None:
    inputs = {**_first_example("fixed_income.duration"), "coupon_rate": 5}
    result = call(SERVER, "fixed_income_duration", inputs)
    problem = problem_of(result)
    assert problem["type"].endswith("/invalid-input")
    assert problem["status"] == 422
    assert problem["errors"][0]["loc"][-1] == "coupon_rate"
    assert text_of(result, 1).startswith("invalid-input: ")
    assert result.structured_content is None


def test_an_unknown_model_answers_model_not_found() -> None:
    result = call(SERVER, "run_model", {"model_id": "fixed_income.no_such_model"})
    assert problem_of(result)["type"].endswith("/model-not-found")


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("run_model", {"model_id": "foundations.time_value", "code": "1"}),
        ("search_models", {"query": "bond", "url": "https://example.org"}),
        ("describe_model", {"model_id": "foundations.time_value", "path": "/etc"}),
        ("get_series", {"target": "us.unemployment.rate", "key": "x"}),
        ("list_sources", {"provider": "fred"}),
    ],
)
def test_an_argument_a_tool_does_not_take_is_refused(
    name: str, arguments: dict[str, Any]
) -> None:
    problem = problem_of(call(SERVER, name, arguments))
    assert problem["type"].endswith("/invalid-input")
    assert "takes no argument" in problem["detail"]


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"model_id": 7},
        {"model_id": "foundations.time_value", "inputs": [1, 2]},
        {"model_id": "foundations.time_value", "as_of": "2019-02-30"},
        {"model_id": "foundations.time_value", "concepts": "x"},
    ],
)
def test_run_model_refuses_malformed_arguments(arguments: dict[str, Any]) -> None:
    assert problem_of(call(SERVER, "run_model", arguments))["status"] == 422


def test_an_unknown_tool_is_a_protocol_error() -> None:
    async def work(client: Client) -> tuple[int, str]:
        try:
            await client.call_tool("no_such_tool", {})
        except MCPError as error:
            return error.error.code, error.error.message
        return 0, ""  # pragma: no cover - the call raises

    code, message = run_with(SERVER, work, raise_exceptions=False)
    assert (code, message) == (-32602, "Unknown tool: no_such_tool")


def test_a_run_on_inputs_alone_carries_no_data_record() -> None:
    result = call(
        SERVER, "foundations_time_value", _first_example("foundations.time_value")
    )
    assert result.structured_content is not None
    assert result.structured_content["manifest"]["data_sources"] == []
    assert "Data from" not in text_of(result, 1)
