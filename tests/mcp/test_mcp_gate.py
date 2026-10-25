# tests/mcp/test_mcp_gate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The ``llm_use`` gate through every MCP tool (Phase 4 Step 8; ROADMAP §5 7).

Against stand-ins for every real provider (each with its real ``llm_use``
class), every tool is called with every argument it accepts: every bound model
and profile through ``run_model``, as of a date and not, every catalog concept
and every provider series through ``get_series``, every headline tool. No
answer ever carries a ``forbidden`` record, and an ``unclear`` one only on a
server built with the opt-in. The opt-in is the user's configuration, read when
the server is built: no argument of any tool can set it, and changing the
configuration later changes nothing. Behind the resolver, the final check
withholds an answer that still carries such a record.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from mcp_support import LOOPBACK_ONLY, call, problem_of, stub_world, text_of

from pyeconomics import registry
from pyeconomics.core import LlmUsePolicy
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import catalog
from pyeconomics.data.catalog.definitions import Candidate
from pyeconomics.data.config import reset
from pyeconomics.mcp import build_server
from pyeconomics.mcp.headline import HEADLINE
from pyeconomics.mcp.tools import build_tools, tool_name

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from mcp import types

    from pyeconomics.core.model import Model
    from pyeconomics.core.provenance import LlmUsePolicy as Policy
    from pyeconomics.data.registry import ProviderRegistry
    from pyeconomics.surfaces.invoke import BindRequest

pytestmark = LOOPBACK_ONLY

PAST = "2019-06-28"
PERMITTED = {
    LlmUsePolicy.ALLOWED_ONLY: {"allowed"},
    LlmUsePolicy.ALLOW_UNCLEAR: {"allowed", "unclear"},
}


def _records(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    manifest = document.get("manifest") or {}
    return [*(manifest.get("data_sources") or ()), *(document.get("sources") or ())]


def _check(result: types.CallToolResult, policy: Policy) -> int:
    """Assert an answer carries only permitted records; return how many it has.

    A tool error carries a problem and no data, whatever the reason it failed.
    """
    if result.is_error:
        assert result.structured_content is None
        assert set(problem_of(result)) <= {
            "type",
            "title",
            "status",
            "detail",
            "errors",
            "licence",
            "terms",
            "retry_after",
        }
        return 0
    document = result.structured_content
    assert document is not None
    assert json.loads(text_of(result)) == document
    records = _records(document)
    assert {record["llm_use"] for record in records} <= PERMITTED[policy]
    return len(records)


def _bound_calls() -> Iterator[dict[str, Any]]:
    """run_model's arguments for every bound model, profile and calculation."""
    for model in registry.models():
        bindings = model.spec.bindings
        if not bindings:
            continue
        calculations = {
            str(example.inputs["calculation"])
            for example in model.spec.examples
            if "calculation" in example.inputs
        }
        for profile in sorted({binding.profile for binding in bindings}):
            choices: list[str | None] = [*sorted(calculations)] or [None]
            for calculation in choices:
                inputs = {} if calculation is None else {"calculation": calculation}
                for when in (PAST, None):
                    arguments: dict[str, Any] = {
                        "model_id": model.id,
                        "inputs": inputs,
                        "profile": profile,
                    }
                    if when is not None:
                        arguments["as_of"] = when
                    yield arguments


@pytest.fixture(scope="module")
def world() -> Iterator[ProviderRegistry]:
    with pytest.MonkeyPatch.context() as monkeypatch:
        yield stub_world(monkeypatch)


@pytest.mark.parametrize("policy", list(LlmUsePolicy))
@pytest.mark.usefixtures("world")
def test_no_run_of_any_bound_model_reaches_a_refused_source(policy: Policy) -> None:
    server = build_server(policy=policy)
    answered = records = 0
    for arguments in _bound_calls():
        result = call(server, "run_model", arguments)
        records += _check(result, policy)
        answered += not result.is_error
    assert answered > 10
    assert records > 20


@pytest.mark.parametrize("policy", list(LlmUsePolicy))
@pytest.mark.usefixtures("world")
def test_no_series_of_any_concept_reaches_a_refused_source(policy: Policy) -> None:
    server = build_server(policy=policy, series_limit=3)
    answered = 0
    for concept in catalog.concepts():
        arguments: dict[str, Any] = {"target": concept.id}
        if concept.parameters:
            continue  # its series name a parameter: get_series takes none
        if concept.needs_window:
            arguments |= {"start": "2025-01-01", "end": "2025-06-30"}
        for extra in ({}, {"as_of": "2025-06-30"}):
            result = call(server, "get_series", arguments | extra)
            _check(result, policy)
            answered += not result.is_error
    assert answered > 50


@pytest.mark.usefixtures("world")
def test_a_refused_provider_series_is_never_answered(world: ProviderRegistry) -> None:
    server = build_server(policy=LlmUsePolicy.ALLOWED_ONLY)
    refused = 0
    for provider_id in world.ids():
        info = world.provider_class(provider_id).info
        if info.terms.llm_use.value == "allowed":
            continue
        for concept in catalog.concepts():
            keys = [
                c.series
                for c in concept.candidates
                if isinstance(c, Candidate)
                and c.provider == provider_id
                and "{" not in c.series
            ]
            if keys:
                result = call(
                    server, "get_series", {"target": f"{provider_id}:{keys[0]}"}
                )
                assert problem_of(result)["type"].endswith("/llm-use-forbidden")
                refused += 1
                break
    assert refused >= 5


def test_the_headline_tools_read_no_data() -> None:
    server = build_server(policy=LlmUsePolicy.ALLOWED_ONLY)
    for model_id in HEADLINE:
        inputs = dict(registry.get(model_id).spec.examples[0].inputs)
        result = call(server, tool_name(model_id), inputs)
        assert _check(result, LlmUsePolicy.ALLOWED_ONLY) == 0


def test_no_tool_takes_an_argument_that_could_set_the_opt_in() -> None:
    for spec in build_tools():
        names = json.dumps(spec.input_schema).lower()
        if spec.model_id is None:
            assert "llm" not in names, spec.name
            assert "unclear" not in names, spec.name
        else:
            assert "llm_use" not in names, spec.name
    server = build_server(policy=LlmUsePolicy.ALLOWED_ONLY)
    sneaky = call(
        server,
        "run_model",
        {"model_id": "foundations.time_value", "llm_use": "allow-unclear"},
    )
    assert "takes no argument 'llm_use'" in problem_of(sneaky)["detail"]


def test_the_opt_in_is_read_when_the_server_is_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strict = build_server()
    monkeypatch.setenv("PYECONOMICS_ALLOW_UNCLEAR_LLM_USE", "1")
    reset()
    opted = build_server()
    entries = {
        name: {
            e["id"]: e["llm_permitted"]
            for e in (call(server, "list_sources", {}).structured_content or {})[
                "sources"
            ]
        }
        for name, server in (("strict", strict), ("opted", opted))
    }
    assert entries["strict"]["dbnomics"] is False
    assert entries["opted"]["dbnomics"] is True


class _Leaky:
    """An executor that returns a result carrying a forbidden record."""

    def __init__(self, use: str | None) -> None:
        self.use = use

    async def run(
        self,
        model: Model[Any, Any],
        inputs: Mapping[str, Any],
        bind: BindRequest | None,  # noqa: ARG002 - the executor's signature
        policy: Policy,  # noqa: ARG002
    ) -> bytes:
        from pyeconomics import run  # noqa: PLC0415

        document = json.loads(run(model.id, dict(inputs)).to_json())
        document["manifest"]["data_sources"] = [
            {
                "provider": "fred",
                "series_id": "UNRATE",
                "licence": "library-only",
                "llm_use": self.use,
                "terms_url": "https://fred.stlouisfed.org/docs/api/terms_of_use.html",
            }
        ]
        return canonical_json(document)

    async def series(
        self,
        target: str,  # noqa: ARG002 - the executor's signature
        options: Mapping[str, str],  # noqa: ARG002
        limit: int,  # noqa: ARG002
        policy: Policy,  # noqa: ARG002
    ) -> bytes:
        document = {"sources": [{"provider": "fred", "llm_use": self.use}]}
        return canonical_json(document)


@pytest.mark.parametrize("use", ["forbidden", "unclear", "nonsense", None])
def test_the_final_check_withholds_an_answer_that_carries_a_refused_record(
    use: str | None,
) -> None:
    server = build_server(policy=LlmUsePolicy.ALLOWED_ONLY, executor=_Leaky(use))
    inputs = dict(registry.get("foundations.time_value").spec.examples[0].inputs)
    for name, arguments in (
        ("foundations_time_value", inputs),
        ("run_model", {"model_id": "foundations.time_value", "inputs": inputs}),
        ("get_series", {"target": "us.unemployment.rate"}),
    ):
        result = call(server, name, arguments)
        problem = problem_of(result)
        assert problem["type"].endswith("/llm-use-forbidden")
        assert problem["status"] == 403
        assert "withheld" in problem["detail"]
        assert result.structured_content is None


def test_with_the_opt_in_an_unclear_record_passes_the_final_check() -> None:
    server = build_server(policy=LlmUsePolicy.ALLOW_UNCLEAR, executor=_Leaky("unclear"))
    inputs = dict(registry.get("foundations.time_value").spec.examples[0].inputs)
    result = call(server, "foundations_time_value", inputs)
    assert not result.is_error
    blocked = build_server(
        policy=LlmUsePolicy.ALLOW_UNCLEAR, executor=_Leaky("forbidden")
    )
    assert call(blocked, "foundations_time_value", inputs).is_error
