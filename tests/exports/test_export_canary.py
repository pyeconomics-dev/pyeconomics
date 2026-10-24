# tests/exports/test_export_canary.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""No export or bundle member holds a key (Phase 4 Step 5 security).

A random canary key is planted for the keyed toy provider, a model bound to a
concept that provider answers runs through the real HTTP transport (over a fake
connection pool, which proves the key was sent), and every export format of the
result, read back where it is compressed, and every member of its bundle are
searched for the key. The same holds for the user's paths: neither the working
directory nor the home directory reaches any of them. A failing assertion names
the sinks, never the key.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from types import MappingProxyType

import bound_support as bs
import pytest
from fakes import FIXED_NOW, FakeClock, FakePool, FakeRaw
from leakcheck import LeakCheck, Needles, canary
from toys import ToyJson

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
from pyeconomics.surfaces.invoke import BindRequest

CONCEPT = "us.toy.export_rate"
AS_OF = dt.date(2025, 3, 31)
SERIES = json.dumps(
    {
        "title": "Toy policy rate",
        "units": "Percent",
        "frequency": "monthly",
        "seasonal_adjustment": "NSA",
        "observations": [{"date": "2025-01-01", "value": "4.50"}],
    }
).encode()


@pytest.fixture(autouse=True)
def toy_concept(monkeypatch: pytest.MonkeyPatch) -> None:
    """Add a concept the keyed toy provider answers to the catalog."""
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


def wire(pool: FakePool) -> HttpTransport:
    clock = FakeClock()
    return HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        jitter=lambda ceiling: ceiling,
    )


class Paths:
    """The user's working and home directories, as needles."""

    def __init__(self, *paths: Path) -> None:
        self.paths = paths

    def needles(self) -> tuple[str, ...]:
        """Each path, written natively and with forward slashes."""
        found = {str(p) for p in self.paths} | {p.as_posix() for p in self.paths}
        return tuple(sorted(found))


def exported_sinks(check: LeakCheck) -> None:
    """Bind and run the toy model with the canary key, then collect its exports."""
    model = bs.bound_to(CONCEPT, model_id="macro.toy_export_canary")
    pool = FakePool(FakeRaw(200, SERIES, {"Content-Type": "application/json"}))
    bound = bind_model(
        model,
        as_of=AS_OF,
        registry=ProviderRegistry.from_providers(ToyJson),
        transport=wire(pool),
    )
    assert len(pool.calls) == 1  # the key was sent: the sinks below are searched
    result = run_model(model, bound)
    assert result.manifest.data_sources[0].provider == "toy_json"
    check.exports(result, BindRequest(as_of=AS_OF))


def test_a_canary_key_reaches_no_export_and_no_bundle_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    held = canary("toy_json")
    monkeypatch.setenv("TOY_JSON_API_KEY", held.value)
    check = LeakCheck(held)
    exported_sinks(check)
    assert {"export:csv", "export:xlsx", "export:parquet", "export:arrow"} <= set(
        check.sinks
    )
    assert "bundle:reproduce.py" in check.sinks
    check.assert_clean()


def test_no_export_or_bundle_member_holds_the_users_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOY_JSON_API_KEY", canary("toy_json").value)
    paths: Needles = Paths(Path.cwd(), Path.home())
    check = LeakCheck(paths)
    exported_sinks(check)
    check.assert_clean()
