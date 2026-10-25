# tests/server/test_server_hosted.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Hosted mode's refusals and pointers (Phase 4 Step 7; ADR-0012 decisions 10-11).

In hosted mode a series or a bound run on a source not classed hosted-safe or
user-supplied answers the licence problem (403) naming the class and the terms
page, and the source is never asked: one test per class, through a provider
series and through a bound run whose every candidate is refused. Hosted mode
has no route for keys or the cache, and its sources document says nothing about
keys. The ``disabled_providers`` switch answers ``source-disabled`` (503) before
any request. A body above the hosted limit (413) and a run stopped at its budget
(422) each give the command that runs the same locally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import bound_support as bs
import pytest
from catalog_support import monthly
from leakcheck import LeakCheck, canary
from scripted import calls_of, scripted
from server_support import LOOPBACK_ONLY, client, problem, use_providers

from pyeconomics.core import registry as core_registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import DataProvider, configure
from pyeconomics.server.pool import budget_exceeded
from pyeconomics.server.work import Task
from pyeconomics.surfaces.budgets import HOSTED_BODY_LIMIT

if TYPE_CHECKING:
    from fastapi import FastAPI

pytestmark = LOOPBACK_ONLY

DATA = [0.04 + i / 1000 for i in range(12)]
REFUSED = [LicenceClass.LIBRARY_ONLY, LicenceClass.BYOK, LicenceClass.PREMIUM_LOCAL]


def _classed(
    provider_id: str, series_id: str, licence: LicenceClass
) -> type[DataProvider]:
    frame = monthly(DATA, provider=provider_id, series_id=series_id)
    return scripted(provider_id, {series_id: frame}, licence=licence)


@pytest.mark.parametrize("licence", REFUSED, ids=lambda licence: licence.value)
def test_a_series_of_each_refused_class_is_403_and_never_asked(
    licence: LicenceClass, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _classed("alpha", "A", licence)
    use_providers(monkeypatch, provider)
    with client(mode="hosted") as api:
        response = api.get("/v1/series/alpha:A")
    assert response.status_code == 403
    body = problem(response)
    assert body["type"].endswith("/licence-refused")
    assert body["licence"] == licence.value
    assert body["terms"] == provider.info.terms.terms_url
    assert f"alpha is {licence.value}" in body["detail"]
    assert response.headers["cache-control"] == "no-store"
    assert calls_of(provider) == []


@pytest.mark.parametrize("licence", REFUSED, ids=lambda licence: licence.value)
def test_a_bound_run_on_a_refused_class_is_403_and_never_asks(
    licence: LicenceClass, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001
    originator = _classed("bls", "LNS14000000", licence)
    aggregator = bs.fred()
    use_providers(monkeypatch, originator, aggregator)
    with client(mode="hosted") as api:
        response = api.post(
            "/v1/models/macro.toy_unemployment/run?vintage=latest", content=b"{}"
        )
    assert response.status_code == 403
    body = problem(response)
    assert body["type"].endswith("/licence-refused")
    assert body["licence"] == licence.value
    assert body["terms"] == originator.info.terms.terms_url
    assert licence.value in body["detail"]
    assert "library-only" in body["detail"]  # the aggregator's class too
    assert calls_of(originator) == calls_of(aggregator) == []


def test_the_same_bound_run_answers_from_a_hosted_safe_originator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001
    use_providers(monkeypatch, bs.bls(), bs.fred())
    with client(mode="hosted") as api:
        response = api.post(
            "/v1/models/macro.toy_unemployment/run?vintage=latest", content=b"{}"
        )
    assert response.status_code == 200
    (record,) = response.json()["manifest"]["data_sources"]
    assert (record["provider"], record["licence"]) == ("bls", "hosted-safe")


def test_hosted_mode_has_no_route_for_keys_or_the_cache() -> None:
    with client(mode="hosted") as api:
        app = cast("FastAPI", api.app)
        paths = [getattr(route, "path", "") for route in app.routes]
        for path in ("/v1/keys", "/v1/keys/fred", "/v1/cache", "/v1/cache/clear"):
            assert api.get(path).status_code == 404
            assert api.post(path).status_code in {404, 405}
        sources = api.get("/v1/sources").json()
    assert not [path for path in paths if "key" in path or "cache" in path]
    assert sources
    assert {source["key_configured"] for source in sources} == {None}


def test_a_disabled_provider_is_source_disabled_before_any_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _classed("alpha", "A", LicenceClass.HOSTED_SAFE)
    use_providers(monkeypatch, provider)
    configure(disabled_providers=["alpha"])
    with client(mode="hosted") as api:
        response = api.get("/v1/series/alpha:A")
        sources = api.get("/v1/sources").json()
    assert response.status_code == 503
    assert problem(response)["type"].endswith("/source-disabled")
    assert calls_of(provider) == []
    assert [source["disabled"] for source in sources] == [True]


def test_an_oversized_hosted_body_points_to_the_local_command() -> None:
    with client(mode="hosted") as api:
        response = api.post(
            "/v1/models/foundations.time_value/run",
            content=b" " * (HOSTED_BODY_LIMIT + 1),
        )
    assert response.status_code == 413
    detail = problem(response)["detail"]
    assert "pyeconomics models run foundations.time_value --inputs FILE" in detail


def test_a_task_stopped_at_its_budget_names_the_local_command() -> None:
    run = budget_exceeded(Task(kind="run", target="risk.var", budget=2.0))
    series = budget_exceeded(
        Task(kind="series", target="us.unemployment.rate", budget=30.0)
    )
    assert str(run).endswith(
        "run it locally: pyeconomics models run risk.var --inputs FILE"
    )
    assert str(series).endswith(
        "run it locally: pyeconomics data get us.unemployment.rate"
    )
    assert (run.seconds, series.seconds) == (2.0, 30.0)


def test_a_planted_key_reaches_no_hosted_answer_or_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001
    use_providers(monkeypatch, bs.bls(), bs.fred(keyed=True))
    planted = canary("fred")
    monkeypatch.setenv("FRED_API_KEY", planted.value)
    check = LeakCheck(planted)
    with check.logs("pyeconomics.server"), client(mode="hosted") as api:
        for response in (
            api.post(
                "/v1/models/macro.toy_unemployment/run",
                params={"vintage": "latest"},
                content=canonical_json({"weight": 2.0}),
            ),
            api.get("/v1/series/fred:UNRATE"),
            api.get("/v1/sources"),
        ):
            check.add(f"body:{response.status_code}", response.content)
            check.add(f"headers:{response.status_code}", repr(response.headers))
    check.assert_clean()
