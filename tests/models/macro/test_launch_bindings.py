# tests/models/macro/test_launch_bindings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The six Step 14 macro models bind every profile through the catalog, offline.

The providers are the catalog world's stand-ins (``catalog_world.py``): every
installed provider with its real metadata, answering each catalog candidate with a
synthetic frame of the right shape, so the resolver's gates, the concepts'
transforms and the binding layer run for real. This module lengthens their history
(the windows here reach 120 quarters and 40 years) and gives each series its own
wave, so the regressions have something to fit.
"""

from __future__ import annotations

import datetime as dt
import math
import zlib
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import catalog_world
import pytest
from catalog_support import month_end

from pyeconomics.core import AsOf, UnitKind, run_model
from pyeconomics.core.binding import REVISED_DATA, calculations
from pyeconomics.core.transforms import parse_transform
from pyeconomics.data import ObservationFrequency, Series, Table, catalog
from pyeconomics.data.bindings import bind_model
from pyeconomics.models.macro import (
    debt_dynamics,
    okun_law,
    output_gap,
    phillips_curve,
    recession_probability,
    solow_growth,
)

if TYPE_CHECKING:
    from pyeconomics.core import Model
    from pyeconomics.data.registry import ProviderRegistry

#: The evaluation date for the concepts that need one (the Treasury curves).
AS_OF = dt.date(2026, 3, 15)
#: A filter's frequency is an input, not data: each profile's frequency.
FREQUENCY = {"default": "quarterly"}

#: Net lending and interest as shares of a stand-in GDP of about 100, so the primary
#: balance is a deficit of about 3% of GDP rather than the size of GDP itself.
_FISCAL = {"bea:NIPA/T30200/Q/49": -0.05, "bea:NIPA/T30200/Q/33": 0.02}
#: The Treasury's par curves, which the stand-in would space 45 days apart.
_CURVES = {"treasury:par_nominal", "treasury:par_real"}

_original_dates = catalog_world._dates  # noqa: SLF001 - lengthened below
_original_frame = catalog_world._frame  # noqa: SLF001


def _long_dates(frequency: ObservationFrequency, year_end: int) -> list[dt.date]:
    def month_ends(
        first: tuple[int, int], last: tuple[int, int], step: int
    ) -> list[dt.date]:
        out, line = [], first[0] * 12 + first[1] - 1
        while line <= last[0] * 12 + last[1] - 1:
            year, month = divmod(line, 12)
            out.append(month_end(year, month + 1))
            line += step
        return out

    if frequency is ObservationFrequency.MONTHLY:
        return month_ends((1960, 1), (2026, 9), 1)
    if frequency is ObservationFrequency.QUARTERLY:
        return month_ends((1960, 3), (2026, 9), 3)
    if frequency is ObservationFrequency.ANNUAL:
        return month_ends((1950, year_end), (2025, year_end), 12)
    return _original_dates(frequency, year_end)


def _wave(
    values: tuple[float | None, ...], key: str, *, rate: bool
) -> tuple[float | None, ...]:
    """Give a series its own wave: additive for a rate, multiplicative otherwise."""
    phase = zlib.crc32(key.encode()) % 628 / 100
    out: list[float | None] = []
    for i, value in enumerate(values):
        if value is None:
            out.append(None)
            continue
        wave = math.sin(i / 4 + phase)
        out.append(value + 0.004 * wave if rate else value * (1 + 0.02 * wave))
    return tuple(out)


def _frame(
    info_id: str,
    terms: object,
    users: list[Any],
    series_key: str,
    *,
    vintaged: bool,
) -> Series | Table:
    frame = _original_frame(info_id, terms, users, series_key, vintaged=vintaged)
    key = f"{info_id}:{series_key}"
    if isinstance(frame, Table) and key in _CURVES:
        return _business_daily(frame)
    if any("changes_only" in t for _, c in users for t in c.transforms):
        return frame
    if isinstance(frame, Series):
        rate = frame.meta.unit.kind in {UnitKind.RATE, UnitKind.RATIO, UnitKind.RETURN}
        values = _wave(frame.values, key, rate=rate)
        scale = _FISCAL.get(key)
        if scale is not None:
            values = tuple(None if v is None else v * scale for v in values)
        return replace(frame, values=values)
    rate = frame.columns[0].unit.kind in {
        UnitKind.RATE,
        UnitKind.RATIO,
        UnitKind.RETURN,
    }
    columns = tuple(
        _wave(column, f"{key}:{n}", rate=rate) for n, column in enumerate(frame.data)
    )
    return replace(frame, data=columns)


def _business_daily(frame: Table) -> Table:
    """The Treasury curves: every business day (the stand-in spaces irregular data)."""
    days = tuple(
        day
        for day in (dt.date(2025, 1, 1) + dt.timedelta(days=i) for i in range(650))
        if day.weekday() < 5
    )
    data = tuple(
        tuple(
            0.03 + 0.0001 * i + 0.003 * math.sin(i / 20 + n) for i in range(len(days))
        )
        for n, _ in enumerate(frame.columns)
    )
    realtime = None if frame.realtime is None else (frame.realtime[0],) * len(days)
    return replace(frame, index=days, data=data, realtime=realtime)


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> ProviderRegistry:
    """Every installed provider's stand-in, with long, wavy histories."""
    monkeypatch.setattr(catalog_world, "_dates", _long_dates)
    monkeypatch.setattr(catalog_world, "_frame", _frame)
    return catalog_world.world_registry()


@pytest.fixture
def keys(isolated: Any) -> None:  # noqa: ANN401 - the isolation fixture
    """A throwaway key for each keyed provider, so its gate lets the request by."""
    import secrets  # noqa: PLC0415

    for provider in ("fred", "bls", "bea", "census"):
        isolated.keyring.set_password("pyeconomics", provider, secrets.token_hex(16))


def _overrides(
    model: Model[Any, Any], profile: str, calculation: str | None
) -> dict[str, Any]:
    given: dict[str, Any] = {}
    if calculation is not None:
        given["calculation"] = calculation
        member = calculations(model.spec.inputs)[calculation]
        if "frequency" in member.model_fields:
            given["frequency"] = FREQUENCY.get(profile, "annual")
        if "periods_per_year" in member.model_fields and profile == "default":
            given["periods_per_year"] = 4
    return given


def _cases() -> list[tuple[Model[Any, Any], str, str | None]]:
    cases = []
    for model in (
        output_gap,
        phillips_curve,
        okun_law,
        solow_growth,
        debt_dynamics,
        recession_probability,
    ):
        profiles = dict.fromkeys(b.profile for b in model.spec.bindings)
        family = calculations(model.spec.inputs)
        for profile in profiles:
            fields = {b.field for b in model.spec.bindings if b.profile == profile}
            for calculation in family or [None]:
                if calculation is not None:
                    taken = set(family[calculation].model_fields)
                    if not fields & taken:
                        continue  # the steady state binds no data
                cases.append((model, profile, calculation))
    return cases


@pytest.mark.parametrize(
    ("model", "profile", "calculation"),
    _cases(),
    ids=lambda value: getattr(value, "id", value),
)
@pytest.mark.usefixtures("keys")
def test_every_profile_binds_and_runs(
    model: Model[Any, Any],
    profile: str,
    calculation: str | None,
    world: ProviderRegistry,
) -> None:
    bound = bind_model(
        model,
        profile=profile,
        as_of=AS_OF if model is recession_probability else None,
        overrides=_overrides(model, profile, calculation),
        registry=world,
    )
    result = run_model(model, bound)
    expected = {b.field for b in model.spec.bindings if b.profile == profile}
    if calculation is not None:
        expected &= set(calculations(model.spec.inputs)[calculation].model_fields)
    assert {record.field for record in result.manifest.data_sources} == expected
    windows = [b for b in model.spec.bindings if b.profile == profile]
    ends: dict[str, set[dt.date | None]] = {}
    for binding in windows:
        if binding.as_of is not AsOf.WINDOW or binding.field not in expected:
            continue
        read = catalog.get(binding.concept).frequency.value
        if binding.transform is not None and binding.transform.startswith("convert"):
            read = parse_transform(binding.transform).arguments["to"]  # type: ignore[assignment]
        record = next(r for r in bound.sources if r.field == binding.field)
        ends.setdefault(str(read), set()).add(record.observation_end)
    for frequency, last in ends.items():
        assert len(last) == 1, f"{frequency} windows end apart: {last}"


@pytest.mark.usefixtures("keys")
def test_the_filters_read_120_quarters_of_real_gdp(world: ProviderRegistry) -> None:
    bound = bind_model(
        output_gap,
        overrides={"calculation": "hp", "frequency": "quarterly"},
        registry=world,
    )
    series = bound.values["series"]
    assert isinstance(series, tuple)
    assert len(series) == 120
    (record,) = bound.sources
    assert record.concept == "us.output.real_gdp"
    assert record.transforms[-1] == "window(count=120,date=2026-09-30)"
    assert result_gap(bound) is not None


def result_gap(bound: Any) -> float:  # noqa: ANN401 - a Bound
    return float(run_model(output_gap, bound).outputs.gap)


def test_the_recession_spread_reads_last_months_averages(
    world: ProviderRegistry,
) -> None:
    bound = bind_model(recession_probability, as_of=AS_OF, registry=world)
    by_field = {record.field: record for record in bound.sources}
    for field in ("ten_year_yield", "three_month_yield"):
        record = by_field[field]
        assert record.transforms[-2:] == (
            "convert(to=monthly,method=mean)",
            "asof(date=2026-03-15)",
        )
        assert record.observation_end == dt.date(2026, 2, 28)
        assert REVISED_DATA in record.warnings
    outputs = run_model(recession_probability, bound).outputs
    assert 0.0 < outputs.probability < 1.0
