# tests/data/bindings/test_window_alignment.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Windows of one frequency end together; a monthly average asks for whole months.

Two contract additions of Phase 3 Step 14 (the Contract-change rule), each over
scripted providers with the real ids:

- a model that pairs window fields by position (a regression, a gap from actual
  and potential output) must read the same periods in each, so every window of
  one frequency ends at the earliest of their last observations on or before the
  date; windows of another frequency are left alone;
- a concept that answers for a window of dates (the Treasury curves) is asked for
  enough of them to cover the periods a ``convert`` binding finally reads, so a
  monthly average is never cut short.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Annotated, Any, cast

import pytest
from bound_support import REFERENCE
from catalog_support import HOSTED_TERMS, meta, period_ends
from pydantic import Field
from scripted import calls_of, registry_of, scripted

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    UnitKind,
    model,
)
from pyeconomics.data import (
    ColumnMeta,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    Table,
    TableMeta,
    UnitRecord,
)
from pyeconomics.data.bindings import bind_model
from pyeconomics.data.types import DateConvention

QUARTERLY = ObservationFrequency.QUARTERLY
DOLLARS = UnitRecord(text="Dollars", kind=UnitKind.MONEY, currency="USD")
RATE = UnitRecord(text="Decimal", kind=UnitKind.RATE)
_COMMON: dict[str, Any] = {
    "formula": (r"y = x",),
    "assumptions": ("A toy that pairs windows by position.",),
    "limitations": ("It models nothing.",),
    "references": (REFERENCE,),
    "evidence": Evidence.PRACTITIONER,
    "cost": CostClass.INSTANT,
    "changelog": (ChangelogEntry(version=1, note="First version."),),
    "invariants": (Invariant(id="toy", statement="A toy."),),
}

_Levels = Annotated[tuple[Annotated[Money, Field(gt=0, le=1e15)], ...], ARRAY_INPUT]
_Rates = Annotated[tuple[Annotated[Rate, Field(ge=0, le=1)], ...], ARRAY_INPUT]


class PairedInputs(ModelInputs):
    actual: _Levels = Field(max_length=8, description="Real output")
    potential: _Levels = Field(max_length=8, description="Potential output")
    unemployment: _Rates = Field(max_length=8, description="Monthly unemployment")


class PairedOutputs(ModelOutputs):
    periods: Annotated[int, Field(ge=0, le=8, description="Paired periods")]


@model(
    id="macro.toy_paired_windows",
    version=1,
    title="Toy paired windows",
    summary="Reads actual and potential output as windows and pairs them.",
    examples=(
        Example(
            name="two",
            inputs={
                "actual": [1.0, 2.0],
                "potential": [1.0, 2.0],
                "unemployment": [0.04],
            },
        ),
    ),
    bindings=(
        Binding("actual", "us.output.real_gdp", as_of=AsOf.WINDOW, window=4),
        Binding("potential", "us.output.potential_gdp", as_of=AsOf.WINDOW, window=4),
        Binding("unemployment", "us.unemployment.rate", as_of=AsOf.WINDOW, window=3),
    ),
    **_COMMON,
)
def paired(inputs: PairedInputs) -> PairedOutputs:
    return PairedOutputs(periods=len(inputs.actual))


def _quarterly(provider: str, base: float, count: int) -> Series:
    """Quarterly levels from 2022 Q1, rising by 100 a quarter from ``base``."""
    return Series(
        period_ends(QUARTERLY, (2022, 3), count),
        tuple(base + 100.0 * i for i in range(count)),
        meta(
            QUARTERLY,
            provider=provider,
            series_id=provider,
            unit=DOLLARS,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
        ),
    )


def _world() -> Any:  # noqa: ANN401 - a provider registry
    # Real GDP ends with 2024 Q4; CBO's potential runs years ahead, to 2026 Q4;
    # unemployment is monthly, to May 2025.
    bea = scripted("bea", {"NIPA/T10106/Q/1": _quarterly("bea", 20_000.0, 12)})
    cbo = scripted(
        "cbo", {"quarterly:real_potential_gdp": _quarterly("cbo", 20_050.0, 20)}
    )
    months = period_ends(ObservationFrequency.MONTHLY, (2024, 1), 17)
    bls = scripted(
        "bls",
        {
            "LNS14000000": Series(
                months,
                tuple(0.04 + 0.001 * i for i in range(17)),
                meta(
                    ObservationFrequency.MONTHLY,
                    provider="bls",
                    series_id="LNS14000000",
                    unit=RATE,
                    seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
                ),
            )
        },
    )
    return registry_of(bea, cbo, bls)


def test_windows_of_one_frequency_end_together() -> None:
    bound = bind_model(paired, registry=_world())
    by_field = {record.field: record for record in bound.sources}
    for field in ("actual", "potential"):
        record = by_field[field]
        assert record.observation_end == dt.date(2024, 12, 31), field
        assert record.transforms[-1] == "window(count=4,date=2024-12-31)"
    assert bound.values["potential"] == (20_850.0, 20_950.0, 21_050.0, 21_150.0)
    assert bound.values["actual"] == (20_800.0, 20_900.0, 21_000.0, 21_100.0)


def test_a_window_of_another_frequency_is_left_alone() -> None:
    bound = bind_model(paired, registry=_world())
    record = {r.field: r for r in bound.sources}["unemployment"]
    assert record.observation_end == dt.date(2025, 5, 31)
    assert bound.values["unemployment"] == pytest.approx((0.054, 0.055, 0.056))


def test_an_evaluation_date_caps_the_shared_end() -> None:
    bound = bind_model(paired, as_of=dt.date(2024, 7, 15), registry=_world())
    ends = {r.field: r.observation_end for r in bound.sources}
    assert ends["actual"] == ends["potential"] == dt.date(2024, 6, 30)
    assert ends["unemployment"] == dt.date(2024, 6, 30)


# --- a monthly average of a daily curve --------------------------------------------


class YieldInputs(ModelInputs):
    ten_year: Annotated[Rate, Field(ge=-1, le=1, description="A monthly average")]


class YieldOutputs(ModelOutputs):
    level: Annotated[Rate, Field(ge=-1, le=1, description="The yield")]


@model(
    id="macro.toy_monthly_yield",
    version=1,
    title="Toy monthly yield",
    summary="Reads the month's average of a daily Treasury yield.",
    examples=(Example(name="four", inputs={"ten_year": 0.04}),),
    bindings=(
        Binding(
            "ten_year",
            "us.treasury.nominal_10y",
            transform="convert(to=monthly,method=mean)",
        ),
    ),
    **_COMMON,
)
def monthly_yield(inputs: YieldInputs) -> YieldOutputs:
    return YieldOutputs(level=inputs.ten_year)


def _curve() -> Table:
    days = tuple(
        day
        for day in (dt.date(2025, 11, 3) + dt.timedelta(days=i) for i in range(130))
        if day.weekday() < 5
    )
    return Table(
        days,
        (
            ColumnMeta(
                name="BC_10YEAR",
                unit=RATE,
                seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
            ),
        ),
        (tuple(0.04 + (0.001 if day.month == 2 else 0.0) for day in days),),
        TableMeta(
            provider="treasury",
            table_id="par_nominal",
            title="Scripted par curve",
            frequency=ObservationFrequency.IRREGULAR,
            source_dating=DateConvention.PERIOD_END,
            terms=HOSTED_TERMS,
        ),
    )


def test_a_monthly_average_asks_a_windowed_source_for_whole_months() -> None:
    treasury = scripted("treasury", {"par_nominal": _curve()})
    day = dt.date(2026, 3, 15)
    bound = bind_model(monthly_yield, as_of=day, registry=registry_of(treasury))
    (query,) = calls_of(treasury)
    # Two months and a margin: the month before the date is always whole.
    assert query.start == day - dt.timedelta(days=93)
    (record,) = bound.sources
    assert record.observation_end == dt.date(2026, 2, 28)
    assert bound.values["ten_year"] == pytest.approx(0.041, rel=1e-14)


# --- a window passes over a source with too short a history -------------------------


class HistoryInputs(ModelInputs):
    rates: _Rates = Field(max_length=12, description="A year of monthly rates")


class HistoryOutputs(ModelOutputs):
    last: Annotated[Rate, Field(ge=0, le=1, description="The latest rate")]


@model(
    id="macro.toy_rate_history",
    version=1,
    title="Toy rate history",
    summary="Reads a year of the unemployment rate as a window.",
    examples=(Example(name="flat", inputs={"rates": [0.04] * 12}),),
    bindings=(Binding("rates", "us.unemployment.rate", as_of=AsOf.WINDOW, window=12),),
    **_COMMON,
)
def rate_history(inputs: HistoryInputs) -> HistoryOutputs:
    return HistoryOutputs(last=inputs.rates[-1])


def _monthly(provider: str, series_id: str, count: int) -> Series:
    return Series(
        period_ends(ObservationFrequency.MONTHLY, (2025, 13 - count), count)
        if count <= 12
        else period_ends(ObservationFrequency.MONTHLY, (2024, 1), count),
        tuple(0.04 + 0.0001 * i for i in range(count)),
        meta(
            ObservationFrequency.MONTHLY,
            provider=provider,
            series_id=series_id,
            unit=RATE,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
        ),
    )


def test_a_window_passes_over_an_originator_with_too_short_a_history() -> None:
    # BLS's API answers a request with no years for the last few only; FRED,
    # the aggregator, holds the history the window needs.
    bls = scripted("bls", {"LNS14000000": _monthly("bls", "LNS14000000", 10)})
    fred = scripted("fred", {"UNRATE": _monthly("fred", "UNRATE", 24)})
    bound = bind_model(rate_history, registry=registry_of(bls, fred))
    (record,) = bound.sources
    assert record.provider == "fred"
    assert record.fallback_chain == ("bls", "fred")
    assert "skipped_bls_no_observations" in record.warnings
    rates = bound.values["rates"]
    assert isinstance(rates, tuple)
    assert len(rates) == 12


class GapInputs(ModelInputs):
    gaps: _Rates = Field(max_length=8, description="Output gaps")


@model(
    id="macro.toy_gap_window",
    version=1,
    title="Toy gap window",
    summary="Reads four quarters of the output gap.",
    examples=(Example(name="none", inputs={"gaps": [0.0]}),),
    bindings=(
        Binding("gaps", "us.output_gap.real_potential", as_of=AsOf.WINDOW, window=4),
    ),
    **_COMMON,
)
def gap_window(inputs: GapInputs) -> HistoryOutputs:
    return HistoryOutputs(last=max(0.0, inputs.gaps[-1]))


def test_a_derived_window_asks_its_operands_for_the_history() -> None:
    # Real GDP over potential: CBO's file starts late, so potential falls to
    # FRED's GDPPOT, and the gap holds the four quarters the window asks for.
    bea = scripted("bea", {"NIPA/T10106/Q/1": _quarterly("bea", 20_000.0, 12)})
    cbo = scripted("cbo", {"quarterly:real_potential_gdp": _quarterly("cbo", 1.0, 2)})
    fred = scripted("fred", {"GDPPOT": _quarterly("fred", 20_050.0, 12)})
    bound = bind_model(gap_window, registry=registry_of(bea, cbo, fred))
    assert {record.provider for record in bound.sources} == {"bea", "fred"}
    gaps = bound.values["gaps"]
    assert isinstance(gaps, tuple)
    assert len(gaps) == 4


class LongPairInputs(ModelInputs):
    actual: _Levels = Field(max_length=8, description="Real output")
    potential: _Levels = Field(max_length=8, description="Potential output")


@model(
    id="macro.toy_long_pair",
    version=1,
    title="Toy long pair",
    summary="Reads eight quarters of actual and potential output.",
    examples=(Example(name="one", inputs={"actual": [1.0], "potential": [1.0]}),),
    bindings=(
        Binding("actual", "us.output.real_gdp", as_of=AsOf.WINDOW, window=8),
        Binding("potential", "us.output.potential_gdp", as_of=AsOf.WINDOW, window=8),
    ),
    **_COMMON,
)
def long_pair(inputs: LongPairInputs) -> PairedOutputs:
    return PairedOutputs(periods=len(inputs.actual))


def _quarters_from(provider: str, first: tuple[int, int], count: int) -> Series:
    return replace(
        _quarterly(provider, 20_000.0, count),
        index=period_ends(QUARTERLY, first, count),
    )


def test_a_projection_short_before_the_shared_end_gives_way() -> None:
    # CBO's file holds twenty quarters, but sixteen of them are projections past
    # real GDP's last quarter: up to 2024 Q4 it has four, not the eight asked
    # for, so the bind asks again up to that quarter and FRED's GDPPOT answers.
    bea = scripted("bea", {"NIPA/T10106/Q/1": _quarters_from("bea", (2022, 3), 12)})
    cbo = scripted(
        "cbo", {"quarterly:real_potential_gdp": _quarters_from("cbo", (2024, 3), 20)}
    )
    fred = scripted("fred", {"GDPPOT": _quarters_from("fred", (2020, 3), 28)})
    bound = bind_model(long_pair, registry=registry_of(bea, cbo, fred))
    potential = {r.field: r for r in bound.sources}["potential"]
    assert potential.provider == "fred"
    assert potential.observation_end == dt.date(2024, 12, 31)
    assert "skipped_cbo_no_observations" in potential.warnings


def test_windows_on_different_calendars_are_not_aligned() -> None:
    # A fiscal year ending in September and a calendar year are other periods:
    # pulling one to the other's end would pair FY2024 with CY2023.
    from types import SimpleNamespace  # noqa: PLC0415

    from pyeconomics.data.bindings import _window_ends  # noqa: PLC0415

    def annual(year_end: int) -> Series:
        day = 30 if year_end == 9 else 31
        index = tuple(dt.date(year, year_end, day) for year in range(2020, 2025))
        return Series(
            index,
            (1.0,) * 5,
            replace(meta(ObservationFrequency.ANNUAL), year_ends_in=year_end),
        )

    fiscal = Binding("a", "x.y.z", as_of=AsOf.WINDOW, window=3)
    calendar = Binding("b", "x.y.w", as_of=AsOf.WINDOW, window=3)
    # Stand-ins: the alignment reads only each fetched binding's series.
    fetched = cast(
        "dict[Binding, Any]",
        {
            fiscal: SimpleNamespace(series=annual(9)),
            calendar: SimpleNamespace(series=annual(12)),
        },
    )
    ends = _window_ends(
        fetched,
        None,
    )
    assert ends == {}


def test_a_window_through_an_upsampling_convert_asks_for_fewer_periods() -> None:
    from pyeconomics.data import catalog  # noqa: PLC0415
    from pyeconomics.data.bindings import _needed  # noqa: PLC0415

    quarterly = catalog.get("us.unemployment.noncyclical_rate")
    monthly = catalog.get("us.unemployment.rate")
    up = Binding(
        "a",
        quarterly.id,
        transform="convert(to=monthly,method=period_end)",
        as_of=AsOf.WINDOW,
        window=7,
    )
    down = Binding(
        "a",
        monthly.id,
        transform="convert(to=quarterly,method=last)",
        as_of=AsOf.WINDOW,
        window=7,
    )
    change = Binding(
        "a", monthly.id, transform="pct_change(periods=3)", as_of=AsOf.WINDOW, window=7
    )
    assert _needed(quarterly, up) == 3  # seven months span three quarters
    assert _needed(monthly, down) == 21
    assert _needed(monthly, change) == 10
    assert _needed(monthly, Binding("a", monthly.id)) is None
