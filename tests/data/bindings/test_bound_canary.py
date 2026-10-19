# tests/data/bindings/test_bound_canary.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A bound run with a canary key leaves no trace in any sink (ADR-0011 decision 13).

A bound run is the longest path a key travels: the key chain, the transport's
request, the resolver, the binding layer, the manifest and every export. A random
canary key is planted for a keyed toy provider, a model is bound to a catalog
concept that provider answers, and the bound run goes through the real HTTP
transport (over a fake connection pool). The logs of every logger, the warnings,
the exceptions, the ``Bound`` and its records, the result's manifest and its
exports are searched for the key. A failing assertion names the sinks, never the
key.
"""

from __future__ import annotations

import datetime as dt
import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import bound_support as bs
import pytest
from fakes import FIXED_NOW, FakeClock, FakePool, FakeRaw
from leakcheck import LeakCheck, canary, log_urllib3_request
from toys import JSON_HOST, ToyJson

from pyeconomics.core import UnitKind, run_model
from pyeconomics.data import (
    ObservationFrequency,
    SeasonalAdjustment,
    bind_model,
    catalog,
)
from pyeconomics.data.catalog.definitions import Candidate, Concept
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.transport.http import HttpTransport

if TYPE_CHECKING:
    from pathlib import Path

CONCEPT = "us.toy.canary_rate"
SERIES = json.dumps(
    {
        "title": "Toy policy rate",
        "units": "Percent",
        "frequency": "monthly",
        "seasonal_adjustment": "NSA",
        "observations": [{"date": "2025-01-01", "value": "4.50"}],
    }
).encode()


class LoggingPool(FakePool):
    """A pool that writes the lines urllib3 would, with the URL it was given."""

    def request(self, method: str, url: str, **kwargs: Any) -> Any:  # noqa: ANN401
        log_urllib3_request(url[len("https://") + len(JSON_HOST) :], host=JSON_HOST)
        return super().request(method, url, **kwargs)


def wire(pool: FakePool) -> HttpTransport:
    clock = FakeClock()
    return HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        jitter=lambda ceiling: ceiling,
    )


@pytest.fixture(autouse=True)
def toy_concept(monkeypatch: pytest.MonkeyPatch) -> None:
    """Add a concept the keyed toy provider answers to the catalog, for the test."""
    concept = Concept(
        id=CONCEPT,
        title="A toy rate",
        definition="A rate a test fixture publishes with invented numbers.",
        unit_kind=UnitKind.RATE,
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        candidates=(Candidate(provider="toy_json", series="TOYRATE"),),
    )
    monkeypatch.setattr(catalog, "CONCEPTS", MappingProxyType({CONCEPT: concept}))


def ok() -> FakeRaw:
    return FakeRaw(200, SERIES, {"Content-Type": "application/json"})


def test_a_canary_key_reaches_no_sink_of_a_bound_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    held = canary("toy_json")
    monkeypatch.setenv("TOY_JSON_API_KEY", held.value)
    check = LeakCheck(held)
    model = bs.bound_to(CONCEPT)
    pool = LoggingPool(ok())

    bound = check.run(
        lambda: bind_model(
            model,
            as_of=dt.date(2025, 3, 31),
            registry=ProviderRegistry.from_providers(ToyJson),
            transport=wire(pool),
        )
    )

    assert bound is not None
    assert len(pool.calls) == 1  # the key was sent: the sinks below are searched
    sent = pool.calls[0]
    assert held.value in sent.url or held.value in str(sent.headers)
    assert bound.values["unemployment"] == 0.045
    (record,) = bound.sources
    assert (record.provider, record.concept) == ("toy_json", CONCEPT)
    assert "revised_data" in record.warnings  # the toy keeps no vintages
    check.bound(bound)
    result = run_model(model, bound)
    check.result(result, tmp_path)
    check.add("attributions", "\n".join(result.attributions()))
    check.add("card", result.card().to_markdown())
    check.assert_clean()


def test_a_failed_bound_run_leaves_the_canary_out_of_the_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    held = canary("toy_json")
    monkeypatch.setenv("TOY_JSON_API_KEY", held.value)
    check = LeakCheck(held)
    unauthorized = FakeRaw(401, b'{"message": "bad key"}')

    outcome = check.run(
        lambda: bind_model(
            bs.bound_to(CONCEPT),
            as_of=dt.date(2025, 3, 31),
            registry=ProviderRegistry.from_providers(ToyJson),
            transport=wire(LoggingPool(unauthorized)),
        )
    )

    assert outcome is None
    assert any(sink.startswith("exception:") for sink in check.sinks)
    check.assert_clean()
