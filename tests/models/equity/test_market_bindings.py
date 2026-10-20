# tests/models/equity/test_market_bindings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The four Step 15 models bind every profile through the catalog, offline.

The providers are the catalog world's stand-ins (``catalog_world.py``): every
installed provider with its real metadata, answering each catalog candidate with
a synthetic frame of the right shape, so the resolver's gates, the concepts and
the binding layer run for real. This module gives the stand-ins plausible
values: an upward-sloping Treasury curve every business day, Svensson parameters
of the Board's size, Damodaran's year-end index and cash, and a Shiller history
long enough for a 120-month window.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import catalog_world
import pytest
from catalog_support import month_end
from pydantic import BaseModel

from pyeconomics.core import AsOf, run_model
from pyeconomics.core.binding import REVISED_DATA, calculations
from pyeconomics.data import ObservationFrequency, Series, Table
from pyeconomics.data.bindings import bind_model
from pyeconomics.models.equity import cape, implied_risk_premium
from pyeconomics.models.fixed_income import curve_fitting, interest_rate_tree

if TYPE_CHECKING:
    from pyeconomics.core import Model
    from pyeconomics.data.registry import ProviderRegistry

#: The evaluation date: the Treasury curves answer for a window around it.
AS_OF = dt.date(2026, 3, 15)
#: Inputs that are not data, by model and calculation.
GIVEN: dict[tuple[str, str | None], dict[str, Any]] = {
    ("fixed_income.curve_fitting", "evaluate"): {},
    ("fixed_income.curve_fitting", "fit"): {"form": "nelson_siegel"},
    ("fixed_income.interest_rate_tree", "calibrate"): {"volatility": 0.1, "years": 10},
    ("fixed_income.interest_rate_tree", "value"): {
        "volatility": 0.1,
        "maturity_years": 10,
        "coupon_rate": 0.045,
        "option": "call",
        "exercise_years": [5],
        "exercise_prices": [100],
    },
    ("fixed_income.interest_rate_tree", "oas"): {
        "volatility": 0.1,
        "maturity_years": 5,
        "coupon_rate": 0.045,
        "price": 101.0,
    },
    ("fixed_income.interest_rate_tree", "effective"): {
        "volatility": 0.1,
        "maturity_years": 7,
        "coupon_rate": 0.04,
    },
    ("equity.implied_risk_premium", None): {},
    ("equity.cape", None): {},
}
#: Treasury's par curves: a level rising with the tenor, drifting by the day.
_CURVES = {"treasury:par_nominal": 0.035, "treasury:par_real": 0.015}
_GSW = {
    "BETA0": 0.045,
    "BETA1": -0.01,
    "BETA2": -0.02,
    "BETA3": 0.015,
    "TAU1": 1.5,
    "TAU2": 9.0,
}
_DAMODARAN = {
    "s_p_500_3": 5000.0,
    "dividends_buybacks_6": 160.0,
    "analyst_growth_estimate_14": 0.06,
}
_SHILLER = {"price": 1000.0, "earnings": 50.0, "cpi": 150.0}

_original_dates = catalog_world._dates  # noqa: SLF001 - lengthened below
_original_frame = catalog_world._frame  # noqa: SLF001


def _long_dates(frequency: ObservationFrequency, year_end: int) -> list[dt.date]:
    """Monthly data from 1990, so a window of 120 months, lagged, fits."""
    if frequency is ObservationFrequency.MONTHLY:
        return [month_end(1990 + k // 12, k % 12 + 1) for k in range(441)]
    return _original_dates(frequency, year_end)


def _business_days() -> tuple[dt.date, ...]:
    first = dt.date(2025, 1, 1)
    days = (first + dt.timedelta(days=i) for i in range(650))
    return tuple(day for day in days if day.weekday() < 5)


def _curve(frame: Table, level: float) -> Table:
    """A curve every business day: higher at longer tenors, drifting slowly."""
    days = _business_days()
    data = []
    for column in frame.columns:
        tenor = _source_tenor(column.name)
        shape = 0.012 * (1 - math.exp(-tenor / 6))
        data.append(tuple(level + shape + 1e-5 * i for i in range(len(days))))
    realtime = None if frame.realtime is None else (frame.realtime[0],) * len(days)
    return replace(frame, index=days, data=tuple(data), realtime=realtime)


def _source_tenor(name: str) -> float:
    """Read Treasury's column name (BC_3MONTH, TC_10YEAR) as years."""
    count = int("".join(ch for ch in name if ch.isdigit()))
    return count / 12 if name.endswith("MONTH") else float(count)


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
    if not isinstance(frame, Table):
        return frame
    if key in _CURVES:
        return _curve(frame, _CURVES[key])
    fixed = {**_GSW, **_DAMODARAN}
    data: list[tuple[float | None, ...]] = []
    for column, values in zip(frame.columns, frame.data, strict=True):
        if column.name in fixed:
            data.append(tuple(fixed[column.name] for _ in values))
        elif key == "shiller:us_equity" and column.name in _SHILLER:
            base = _SHILLER[column.name]
            data.append(tuple(base * (1 + 0.002 * i) for i in range(len(values))))
        else:
            data.append(values)
    return replace(frame, data=tuple(data))


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> ProviderRegistry:
    """Every installed provider's stand-in, with plausible market data."""
    monkeypatch.setattr(catalog_world, "_dates", _long_dates)
    monkeypatch.setattr(catalog_world, "_frame", _frame)
    return catalog_world.world_registry()


def _cases() -> list[tuple[Model[Any, Any], str, str | None]]:
    cases = []
    for model in (curve_fitting, interest_rate_tree, implied_risk_premium, cape):
        profiles = dict.fromkeys(b.profile for b in model.spec.bindings)
        family = calculations(model.spec.inputs)
        cases += [
            (model, profile, calculation)
            for profile in profiles
            for calculation in (family or [None])
        ]
    return cases


@pytest.mark.parametrize(
    ("model", "profile", "calculation"),
    _cases(),
    ids=lambda value: getattr(value, "id", value),
)
def test_every_profile_binds_and_runs(
    model: Model[Any, Any],
    profile: str,
    calculation: str | None,
    world: ProviderRegistry,
) -> None:
    given = dict(GIVEN[model.id, calculation])
    if calculation is not None:
        given["calculation"] = calculation
    bound = bind_model(
        model, profile=profile, as_of=AS_OF, overrides=given, registry=world
    )
    result = run_model(model, bound)
    members = (
        [calculations(model.spec.inputs)[calculation]]
        if calculation is not None
        else [
            m
            for m in model.spec.input_models
            if isinstance(m, type) and issubclass(m, BaseModel)
        ]
    )
    taken = {name for member in members for name in member.model_fields}
    expected: set[str] = set()
    for binding in model.spec.bindings:
        if binding.profile == profile and binding.field in taken:
            expected.add(binding.field)
            if binding.tenors is not None:
                expected.add(binding.tenors)
    assert {record.field for record in result.manifest.data_sources} == expected
    # Nothing these sources serve keeps vintages: every record says so.
    assert all(REVISED_DATA in r.warnings for r in result.manifest.data_sources)


def test_the_fit_reads_treasurys_tenors_as_years(world: ProviderRegistry) -> None:
    bound = bind_model(
        curve_fitting,
        as_of=AS_OF,
        overrides={"calculation": "fit"},
        registry=world,
    )
    tenors, yields = bound.values["maturities"], bound.values["yields"]
    assert isinstance(tenors, tuple)
    assert isinstance(yields, tuple)
    assert tenors[0] == 1 / 12
    assert tenors[-1] == 30.0
    assert len(tenors) == len(yields) == 13
    by_field = {r.field: r for r in bound.sources}
    assert by_field["yields"].observation_end == dt.date(2026, 3, 13)
    assert by_field["yields"].transforms[-1] == "asof(date=2026-03-15)"


def test_cape_reads_the_120_months_before_the_price(world: ProviderRegistry) -> None:
    bound = bind_model(cape, as_of=AS_OF, registry=world)
    by_field = {r.field: r for r in bound.sources}
    assert by_field["price"].observation_end == dt.date(2026, 2, 28)
    window = by_field["earnings"]
    assert window.transforms[-2:] == (
        "lag",
        "window(count=120,date=2026-02-28)",
    )
    earnings, cpi = bound.values["earnings"], bound.values["cpi"]
    assert isinstance(earnings, tuple)
    assert isinstance(cpi, tuple)
    assert len(earnings) == len(cpi) == 120
    binding = next(b for b in cape.spec.bindings if b.field == "earnings")
    assert binding.as_of is AsOf.WINDOW
