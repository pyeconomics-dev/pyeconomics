# tests/server/test_server_routes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The generic routes: listing, describe, sources, health, version (Step 6).

Each answers canonical JSON with the value the Python API returns for the same
question, so the API shows what the command line prints: the listing entries,
``registry.describe``, ``data.sources``. Unknown or repeated query parameters
are refused, an alias redirects to its model, the OpenAPI document is served as
canonical JSON, and the interactive documentation exists in local mode only.
"""

from __future__ import annotations

import pytest
import toy_models as toys
from server_support import (
    LOOPBACK_ONLY,
    client,
    openapi_of,
    problem,
    service_of,
    use_toys,
)

from pyeconomics import __version__, registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces import listing
from pyeconomics.surfaces.documents import jsonable

pytestmark = LOOPBACK_ONLY

SHA = "0123456789abcdef0123456789abcdef01234567"


def test_healthz_says_ok() -> None:
    with client() as api:
        response = api.get("/healthz")
    assert (response.status_code, response.content) == (200, b'{"status":"ok"}')
    assert response.headers["content-type"] == "application/json"


@pytest.mark.parametrize(
    ("given", "expected"),
    [(SHA, SHA), (SHA[:7], SHA[:7]), (None, "unknown"), ("not a sha", "unknown")],
)
def test_version_names_the_package_the_commit_and_the_mode(
    given: str | None, expected: str
) -> None:
    with client(git_sha=given) as api:
        body = api.get("/version").json()
    assert body == {"git_sha": expected, "mode": "local", "pyeconomics": __version__}


def test_version_reads_the_commit_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYECONOMICS_GIT_SHA", SHA)
    with client(mode="hosted") as api:
        body = api.get("/version").json()
    assert (body["git_sha"], body["mode"]) == (SHA, "hosted")


def test_the_listing_is_the_surfaces_listing() -> None:
    with client() as api:
        everything = api.get("/v1/models")
        one_domain = api.get("/v1/models", params={"domain": "macro"})
    assert everything.content == canonical_json(listing.list_models())
    assert one_domain.content == canonical_json(listing.list_models("macro"))


def test_a_search_ranks_and_limits_and_filters_by_domain() -> None:
    with client() as api:
        found = api.get("/v1/models", params={"q": "bond yield", "limit": "3"})
        within = api.get(
            "/v1/models", params={"q": "present value", "domain": "fixed_income"}
        )
    assert found.content == canonical_json(listing.search_models("bond yield", 3))
    matches = listing.search_models("present value", listing.MAX_SEARCH_RESULTS)
    expected = [entry for entry in matches if entry["domain"] == "fixed_income"]
    assert within.json() == expected[:20]
    assert within.json()


@pytest.mark.parametrize(
    "params",
    [
        {"domain": "astrology"},
        {"q": "bond", "domain": "astrology"},
        {"q": "bond", "limit": "0"},
        {"q": "bond", "limit": "many"},
        {"limit": "3"},
        {"q": ""},
        {"colour": "blue"},
    ],
    ids=[
        "domain",
        "search-domain",
        "limit-range",
        "limit-text",
        "limit-alone",
        "q",
        "unknown",
    ],
)
def test_a_bad_listing_query_is_invalid_input(params: dict[str, str]) -> None:
    with client() as api:
        response = api.get("/v1/models", params=params)
    assert response.status_code == 422
    assert problem(response)["type"].endswith("/invalid-input")


def test_a_repeated_query_parameter_is_refused() -> None:
    with client() as api:
        response = api.get("/v1/models?domain=macro&domain=risk")
    assert response.status_code == 422
    assert "more than once" in problem(response)["detail"]


def test_describe_answers_registry_describe_and_caches_it() -> None:
    model_id = "foundations.time_value"
    with client() as api:
        first = api.get(f"/v1/models/{model_id}")
        second = api.get(f"/v1/models/{model_id}")
        cached = service_of(api).documents
    assert first.status_code == 200
    assert first.content == canonical_json(registry.describe(model_id))
    assert second.content == first.content
    assert f"model:{model_id}" in cached


def test_describe_an_unknown_model_is_model_not_found() -> None:
    with client() as api:
        response = api.get("/v1/models/foundations.time_valu")
        refused = api.get("/v1/models/foundations.time_value?verbose=1")
    assert response.status_code == 404
    body = problem(response)
    assert body["type"].endswith("/model-not-found")
    assert "foundations.time_value" in body["detail"]
    assert refused.status_code == 422


def test_an_alias_redirects_to_its_model(monkeypatch: pytest.MonkeyPatch) -> None:
    use_toys(monkeypatch)
    with client() as api:
        described = api.get("/v1/models/foundations.toy_tvm", follow_redirects=False)
        run = api.post(
            "/v1/models/foundations.toy_tvm/run?format=csv",
            content=b"{}",
            follow_redirects=False,
        )
    assert described.status_code == 308
    assert described.headers["location"] == f"/v1/models/{toys.time_value.id}"
    assert run.status_code == 308
    assert run.headers["location"] == f"/v1/models/{toys.time_value.id}/run?format=csv"


def test_sources_is_the_data_apis_list_without_key_lookups() -> None:
    from pyeconomics.data import api as data_api  # noqa: PLC0415

    with client() as api:
        response = api.get("/v1/sources")
        again = api.get("/v1/sources")
    expected = canonical_json(jsonable(data_api.sources(check_keys=False)))
    assert response.content == expected == again.content
    assert all(source["key_configured"] is None for source in response.json())


def test_the_openapi_document_is_served_as_canonical_json() -> None:
    with client() as api:
        response = api.get("/openapi.json")
        document = openapi_of(api)
    assert response.content == canonical_json(document)
    assert document["openapi"] == "3.1.0"


def test_the_interactive_documentation_is_local_only() -> None:
    with client() as api:
        docs = api.get("/docs")
        redoc = api.get("/redoc")
    assert (docs.status_code, redoc.status_code) == (200, 200)
    assert "/openapi.json" in docs.text
    assert docs.headers["content-type"].startswith("text/html")
    with client(mode="hosted") as api:
        hidden = api.get("/docs")
        still = api.get("/openapi.json")
    assert hidden.status_code == 404
    assert problem(hidden)["type"].endswith("/route-not-found")
    assert still.status_code == 200
