# tests/mcp/test_mcp_discovery.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP server's discovery tools answer what the other surfaces do (Step 8).

``search_models`` returns the listing entries the command line and the REST API
return (a search, or a domain's models); ``describe_model`` returns
``registry.describe``'s document; ``list_sources`` returns each provider's
licence class, ``llm_use`` class, whether the server's policy permits it, its
attribution and its terms page, and in local mode only whether a key is
configured, never the key; ``get_series`` returns a series document of at most
the server's limit of observations, with its attributions.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from mcp_support import LOOPBACK_ONLY, call, problem_of, stub_world, text_of

from pyeconomics import registry
from pyeconomics.core import LlmUsePolicy
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import api
from pyeconomics.mcp import build_server
from pyeconomics.surfaces import listing
from pyeconomics.surfaces.documents import data_document

if TYPE_CHECKING:
    from pyeconomics.mcp.server import McpMode

pytestmark = LOOPBACK_ONLY

SERVER = build_server()


def test_a_search_returns_the_listings_entries_best_first() -> None:
    result = call(SERVER, "search_models", {"query": "bond duration", "limit": 3})
    assert result.structured_content == {
        "models": listing.search_models("bond duration", 3)
    }
    assert json.loads(text_of(result)) == result.structured_content


def test_a_search_within_a_domain_keeps_its_models_only() -> None:
    result = call(
        SERVER,
        "search_models",
        {"query": "rate", "domain": "fixed_income", "limit": 5},
    )
    assert result.structured_content is not None
    models = result.structured_content["models"]
    assert models
    assert {entry["domain"] for entry in models} == {"fixed_income"}
    assert len(models) <= 5


def test_without_a_query_the_domains_models_are_listed() -> None:
    result = call(SERVER, "search_models", {"domain": "macro"})
    assert result.structured_content == {"models": listing.list_models("macro")}
    every = call(SERVER, "search_models", {})
    assert every.structured_content == {"models": listing.list_models()}


@pytest.mark.parametrize(
    "arguments",
    [
        {"domain": "astrology"},
        {"query": "bond", "domain": "astrology"},
        {"query": "bond", "limit": 0},
        {"query": "bond", "limit": "5"},
        {"query": "bond", "limit": True},
        {"query": ""},
    ],
)
def test_a_search_refuses_what_the_listing_refuses(
    arguments: dict[str, object],
) -> None:
    assert problem_of(call(SERVER, "search_models", arguments))["status"] == 422


def test_a_description_is_registry_describe_and_is_kept() -> None:
    model_id = "fixed_income.duration"
    server = build_server()
    first = call(server, "describe_model", {"model_id": model_id})
    expected = json.loads(canonical_json(registry.describe(model_id)))
    assert first.structured_content == expected
    again = call(server, "describe_model", {"model_id": model_id})
    assert text_of(again) == text_of(first)


def test_describing_a_bound_model_works_and_an_unknown_one_is_not_found() -> None:
    bound = call(SERVER, "describe_model", {"model_id": "macro.policy_rule"})
    assert bound.structured_content is not None
    assert bound.structured_content["bindings"]
    missing = call(SERVER, "describe_model", {"model_id": "macro.no_such_model"})
    assert problem_of(missing)["type"].endswith("/model-not-found")


def _sources(
    server_mode: McpMode, policy: LlmUsePolicy
) -> dict[str, dict[str, object]]:
    server = build_server(mode=server_mode, policy=policy)
    result = call(server, "list_sources", {})
    assert result.structured_content is not None
    return {entry["id"]: entry for entry in result.structured_content["sources"]}


def test_sources_say_which_data_the_policy_lets_reach_the_assistant() -> None:
    strict = _sources("local", LlmUsePolicy.ALLOWED_ONLY)
    opted = _sources("local", LlmUsePolicy.ALLOW_UNCLEAR)
    assert strict["fred"]["llm_use"] == "forbidden"
    assert strict["fred"]["llm_permitted"] is False
    assert opted["fred"]["llm_permitted"] is False
    assert strict["dbnomics"]["llm_use"] == "unclear"
    assert strict["dbnomics"]["llm_permitted"] is False
    assert opted["dbnomics"]["llm_permitted"] is True
    assert strict["bls"]["llm_permitted"] is True
    for info in api.sources(check_keys=False):
        entry = strict[info.id]
        assert entry["attribution"] == info.attribution
        assert entry["terms_url"] == info.terms_url
        assert entry["licence"] == info.licence.value


def test_only_local_sources_say_whether_a_key_is_configured() -> None:
    local = _sources("local", LlmUsePolicy.ALLOWED_ONLY)
    hosted = _sources("hosted", LlmUsePolicy.ALLOWED_ONLY)
    configured = {s.id: s.key_configured for s in api.sources()}
    assert {pid: entry["has_key"] for pid, entry in local.items()} == configured
    assert all("has_key" not in entry for entry in hosted.values())


def test_a_series_is_the_data_document_at_most_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = stub_world(monkeypatch)
    server = build_server(series_limit=5)
    result = call(server, "get_series", {"target": "us.unemployment.rate"})
    assert not result.is_error, text_of(result)
    document = result.structured_content
    assert document is not None
    assert len(document["frame"]["index"]) <= 5
    expected = data_document(
        api.get(
            "us.unemployment.rate",
            max_observations=5,
            registry=world,
            llm_use=LlmUsePolicy.ALLOWED_ONLY,
        )
    )
    assert document["frame"] == json.loads(canonical_json(expected))["frame"]
    assert document["attributions"]
    assert text_of(result, 1).startswith("us.unemployment.rate: ")
    assert "Data from bls." in text_of(result, 1)


def test_a_series_window_and_options_reach_the_data_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_world(monkeypatch)
    result = call(
        SERVER,
        "get_series",
        {
            "target": "us.unemployment.rate",
            "start": "2019-01-01",
            "end": "2019-06-30",
            "provider": "bls",
        },
    )
    assert result.structured_content is not None
    index = result.structured_content["frame"]["index"]
    assert index[0] >= "2019-01-01"
    assert index[-1] <= "2019-06-30"
    bad = call(SERVER, "get_series", {"target": "us.unemployment.rate", "end": "x"})
    assert problem_of(bad)["status"] == 422
