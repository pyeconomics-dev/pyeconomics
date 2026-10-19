# tests/models/macro/test_policy_rule_bindings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.policy_rule``'s profiles, bound offline as of a past date.

The scripted providers carry the real ids, so the resolver's gates run for real:
``fred`` keeps every vintage, ALFRED's way (each row with the real-time period it
was the published value in), and ``nyfed``, like the New York Fed's r* files,
keeps none. A real-time bind therefore reads every FRED series as published on
the date, and the r* as revised data, labelled so; a ``LATEST`` bind reads every
field as revised data. The data is invented: monthly core PCE prices and
unemployment, each month first published soon after it ends and revised on
2024-09-01; CBO's natural rate in two vintages; a fortnight of the funds rate.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, Final

import pytest
from catalog_support import LIBRARY_TERMS, meta, month_end, period_ends
from scripted import calls_of, registry_of, scripted

from pyeconomics.core import InputError, UnitKind, run_model
from pyeconomics.core.binding import REVISED_DATA
from pyeconomics.data import (
    Capability,
    ColumnMeta,
    DataError,
    LicenceClass,
    ObservationFrequency,
    RealtimePeriod,
    SeasonalAdjustment,
    Series,
    Table,
    TableMeta,
    UnitRecord,
    VintagePolicy,
)
from pyeconomics.data.bindings import bind_model
from pyeconomics.data.types import DateConvention
from pyeconomics.models.macro import neutral_rate, policy_rule

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core.binding import Bound
    from pyeconomics.core.provenance import DataSource
    from pyeconomics.data.providers.base import DataProvider
    from pyeconomics.data.registry import ProviderRegistry

PAST: Final = dt.date(2024, 6, 15)
REVISION: Final = dt.date(2024, 9, 1)
RATE: Final = UnitRecord(text="Decimal", kind=UnitKind.RATE)
INDEX: Final = UnitRecord(text="Index 2017=100", kind=UnitKind.INDEX_LEVEL)
MONTHS: Final = period_ends(ObservationFrequency.MONTHLY, (2022, 1), 29)  # to 2024-05


def _vintaged(
    frequency: ObservationFrequency,
    index: tuple[dt.date, ...],
    first: list[float],
    revised: list[float],
    published: list[dt.date],
    **changes: Any,  # noqa: ANN401 - series metadata
) -> Series:
    """Each period's first release, and its revision from REVISION on."""
    days, values, realtime = [], [], []
    for day, value, later, out in zip(index, first, revised, published, strict=True):
        if out < REVISION:
            days.append(day)
            values.append(value)
            realtime.append(RealtimePeriod(out, REVISION - dt.timedelta(days=1)))
        days.append(day)
        values.append(later)
        realtime.append(RealtimePeriod(max(out, REVISION), None))
    return Series(
        tuple(days),
        tuple(values),
        meta(frequency, provider="fred", terms=LIBRARY_TERMS, **changes),
        tuple(realtime),
    )


def _fred() -> type[DataProvider]:
    count = len(MONTHS)
    after = [day + dt.timedelta(days=31) for day in MONTHS]
    prices = _vintaged(
        ObservationFrequency.MONTHLY,
        MONTHS,
        [100.0 * 1.0025**i for i in range(count)],
        [100.0 * 1.0027**i for i in range(count)],
        after,
        series_id="PCEPILFE",
        unit=INDEX,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
    )
    unemployment = _vintaged(
        ObservationFrequency.MONTHLY,
        MONTHS,
        [0.036 + 0.0002 * i for i in range(count)],
        [0.037 + 0.0002 * i for i in range(count)],
        [day + dt.timedelta(days=7) for day in MONTHS],
        series_id="UNRATE",
        unit=RATE,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
    )
    quarters = period_ends(ObservationFrequency.QUARTERLY, (2022, 3), 20)  # to 2026Q4
    natural = _vintaged(
        ObservationFrequency.QUARTERLY,
        quarters,
        [0.0445] * 20,
        [0.0440] * 20,
        [dt.date(2024, 2, 1)] * 20,
        series_id="NROU",
        unit=RATE,
    )
    days = tuple(dt.date(2024, 6, 3) + dt.timedelta(days=i) for i in range(12))
    business = tuple(day for day in days if day.weekday() < 5)
    funds = Series(
        business,
        tuple(0.0533 for _ in business),
        meta(
            ObservationFrequency.BUSINESS_DAILY,
            provider="fred",
            series_id="EFFR",
            unit=RATE,
            terms=LIBRARY_TERMS,
        ),
        tuple(RealtimePeriod(day + dt.timedelta(days=1), None) for day in business),
    )
    return scripted(
        "fred",
        {"PCEPILFE": prices, "UNRATE": unemployment, "NROU": natural, "EFFR": funds},
        licence=LicenceClass.LIBRARY_ONLY,
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )


def _table(
    provider: str,
    table_id: str,
    frequency: ObservationFrequency,
    index: tuple[dt.date, ...],
    columns: Mapping[str, tuple[float | None, ...]],
) -> Table:
    from catalog_support import HOSTED_TERMS  # noqa: PLC0415

    return Table(
        index,
        tuple(
            ColumnMeta(
                name=name,
                unit=RATE,
                seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            )
            for name in columns
        ),
        tuple(columns.values()),
        TableMeta(
            provider=provider,
            table_id=table_id,
            title=f"Scripted {table_id}",
            frequency=frequency,
            source_dating=DateConvention.PERIOD_END,
            terms=HOSTED_TERMS,
        ),
    )


def _nyfed() -> type[DataProvider]:
    quarters = period_ends(ObservationFrequency.QUARTERLY, (2023, 3), 5)  # to 2024Q1
    return scripted(
        "nyfed",
        {
            "hlw": _table(
                "nyfed",
                "hlw",
                ObservationFrequency.QUARTERLY,
                quarters,
                {"rstar_US": (0.0072, 0.0075, 0.0078, 0.0080, 0.0083)},
            ),
            "effr": _table(
                "nyfed",
                "effr",
                ObservationFrequency.BUSINESS_DAILY,
                (dt.date(2024, 6, 13), dt.date(2024, 6, 14)),
                {"percentRate": (0.0533, 0.0533)},
            ),
        },
    )


def _fed_board() -> type[DataProvider]:
    meeting = dt.date(2024, 6, 12)
    columns = {
        "core_pce_inflation_median_2024": (0.028,),
        "unemployment_rate_median_2024": (0.040,),
        "unemployment_rate_median_Longer_run": (0.042,),
        "federal_funds_rate_median_Longer_run": (0.028,),
    }
    return scripted(
        "fed_board",
        {
            "sep:2024-06-12": _table(
                "fed_board",
                "sep:2024-06-12",
                ObservationFrequency.IRREGULAR,
                (meeting,),
                columns,
            )
        },
    )


@pytest.fixture
def world() -> ProviderRegistry:
    """FRED with vintages, the New York Fed without, the Board's SEP."""
    return registry_of(_fred(), _nyfed(), _fed_board())


def bind(world: ProviderRegistry, **arguments: Any) -> Bound:  # noqa: ANN401
    calculation = arguments.pop("calculation", "taylor_1993")
    overrides = {"calculation": calculation, **arguments.pop("overrides", {})}
    return bind_model(policy_rule, registry=world, overrides=overrides, **arguments)


def _covers(record: DataSource, day: dt.date) -> bool:
    return record.realtime is not None and record.realtime.covers(day)


# --- real time by default --------------------------------------------------------


def test_the_default_profile_reads_each_vintage_as_published_on_the_date(
    world: ProviderRegistry,
) -> None:
    bound = bind(world, as_of=PAST)
    by_field = {record.field or "": record for record in bound.sources}
    assert sorted(by_field) == [
        "inflation",
        "natural_unemployment",
        "neutral_real_rate",
        "previous_rate",
        "unemployment",
    ]
    for field in ("inflation", "natural_unemployment", "unemployment"):
        record = by_field[field]
        assert record.provider == "fred"
        assert record.vintage == f"as_of:{PAST.isoformat()}"
        assert _covers(record, PAST), field
        assert REVISED_DATA not in record.warnings
    # The New York Fed keeps no vintages of r* or of the funds rate, and ALFRED
    # none of FRED's daily EFFR: both are read as they stand, and labelled so.
    for field in ("neutral_real_rate", "previous_rate"):
        record = by_field[field]
        assert record.provider == "nyfed"
        assert record.realtime is None
        assert REVISED_DATA in record.warnings
    assert bound.revised == ("neutral_real_rate", "previous_rate")
    # By mid-June 2024 May's unemployment rate was out, but prices only to April.
    assert by_field["unemployment"].observation_end == month_end(2024, 5)
    assert by_field["inflation"].observation_end == month_end(2024, 4)
    assert bound.values["unemployment"] == pytest.approx(0.036 + 0.0002 * 28)
    assert bound.values["inflation"] == pytest.approx(1.0025**12 - 1)


def test_a_bound_run_records_the_vintages_in_its_manifest(
    world: ProviderRegistry,
) -> None:
    bound = bind(world, as_of=PAST)
    result = run_model(policy_rule, bound)
    assert result.manifest.data_sources == bound.sources
    assert [w.code for w in result.warnings] == [REVISED_DATA]
    assert "neutral_real_rate, previous_rate" in result.warnings[0].message
    records = result.manifest.to_dict()["data_sources"]
    assert isinstance(records, list)
    assert {r["vintage"] for r in records if r["provider"] == "fred"} == {
        f"as_of:{PAST.isoformat()}"
    }


def test_a_latest_bind_reads_revised_data_and_says_so(world: ProviderRegistry) -> None:
    real_time = bind(world, as_of=PAST)
    latest = bind(world, as_of=PAST, vintage=VintagePolicy.LATEST)
    assert all(REVISED_DATA in record.warnings for record in latest.sources)
    assert set(latest.revised) == set(latest.values) - {"calculation"}
    assert latest.values["unemployment"] != real_time.values["unemployment"]
    assert latest.values["inflation"] != real_time.values["inflation"]
    first = run_model(policy_rule, real_time).outputs.prescribed_rate
    revised = run_model(policy_rule, latest)
    assert revised.outputs.prescribed_rate != first
    assert [w.code for w in revised.warnings] == [REVISED_DATA]


def test_the_first_difference_rule_reads_the_gap_a_year_earlier(
    world: ProviderRegistry,
) -> None:
    bound = bind(world, as_of=PAST, calculation="first_difference")
    assert "neutral_real_rate" not in bound.values
    assert bound.values["unemployment_lagged"] == pytest.approx(0.036 + 0.0002 * 16)
    lagged = {r.field: r for r in bound.sources}["unemployment_lagged"]
    assert lagged.transforms[-2:] == ("lag(periods=12)", "asof(date=2024-06-15)")
    assert _covers(lagged, PAST)
    assert bound.values["natural_unemployment_lagged"] == pytest.approx(0.0445)
    outputs = run_model(policy_rule, bound).outputs
    assert outputs.calculation == "first_difference"


def test_a_calculation_binds_only_its_own_fields(world: ProviderRegistry) -> None:
    nyfed = next(world.provider_class(p) for p in world.ids() if p == "nyfed")
    bind(world, as_of=PAST, calculation="first_difference")
    # The rule reads no neutral rate, so no r* is fetched (the funds rate is).
    assert [query.series for query in calls_of(nyfed)] == [("effr",)]
    with pytest.raises(InputError, match="has several calculations"):
        bind_model(policy_rule, as_of=PAST, registry=world)
    with pytest.raises(InputError, match="no calculation 'taylor_2000'"):
        bind(world, as_of=PAST, calculation="taylor_2000")
    with pytest.raises(InputError, match="no input field 'cumulative_shortfall'"):
        bind(world, as_of=PAST, overrides={"cumulative_shortfall": 0.01})


def test_a_period_rule_passes_over_a_source_without_the_period() -> None:
    # CBO keeps vintages, but its quarterly file starts in 2025: as of mid-2024
    # it holds no second quarter of 2024, so the bind reads FRED's NROU instead
    # of picking CBO and failing the period.
    quarters = period_ends(ObservationFrequency.QUARTERLY, (2025, 3), 4)
    late = Series(
        quarters,
        (0.043, 0.043, 0.043, 0.043),
        meta(
            ObservationFrequency.QUARTERLY,
            provider="cbo",
            series_id="quarterly:noncyclical_rate_of_unemployment",
            unit=RATE,
        ),
        tuple(RealtimePeriod(dt.date(2024, 2, 1)) for _ in quarters),
    )
    cbo = scripted(
        "cbo",
        {"quarterly:noncyclical_rate_of_unemployment": late},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )
    bound = bind(registry_of(_fred(), _nyfed(), cbo), as_of=PAST)
    natural = {r.field: r for r in bound.sources}["natural_unemployment"]
    assert natural.provider == "fred"
    assert natural.fallback_chain == ("cbo", "fred")
    assert "skipped_cbo_no_observations" in natural.warnings
    assert bound.values["natural_unemployment"] == pytest.approx(0.0445)


def test_a_date_with_nothing_published_raises(world: ProviderRegistry) -> None:
    with pytest.raises(DataError):
        bind(world, as_of=dt.date(2022, 1, 15))


# --- the forecast profiles ----------------------------------------------------------


def test_the_sep_profile_reads_a_meeting_and_a_year(world: ProviderRegistry) -> None:
    bound = bind(
        world,
        profile="us_sep",
        as_of=PAST,
        parameters={"meeting": "2024-06-12", "year": "2024"},
    )
    assert bound.values["inflation"] == 0.028
    assert bound.values["unemployment"] == 0.040
    assert bound.values["natural_unemployment"] == 0.042
    assert bound.values["neutral_nominal_rate"] == 0.028
    series = {r.field: r.series_id for r in bound.sources}
    assert series["inflation"] == "sep:2024-06-12:core_pce_inflation_median_2024"
    outputs = run_model(policy_rule, bound).outputs
    # 0.028 - 0.02 + 0.028 + 0.5(0.008) + 0.5 x 2 x (0.042 - 0.040)
    assert outputs.prescribed_rate == pytest.approx(0.042)
    assert outputs.nominal_neutral_rate == 0.028


def test_the_sep_profile_needs_its_meeting_and_year(world: ProviderRegistry) -> None:
    with pytest.raises(InputError, match="needs the parameter 'year'"):
        bind(world, profile="us_sep", parameters={"meeting": "2024-06-12"})


def test_the_neutral_rate_binds_the_hlw_estimate(world: ProviderRegistry) -> None:
    bound = bind_model(
        neutral_rate,
        as_of=PAST,
        registry=world,
        overrides={"calculation": "holston_laubach_williams"},
    )
    assert bound.values["estimate"] == 0.0083
    result = run_model(neutral_rate, bound)
    assert result.outputs.real_policy_gap == pytest.approx(
        0.0533 - (1.0025**12 - 1) - 0.0083
    )
    assert {r.field for r in result.manifest.data_sources} == {
        "estimate",
        "inflation",
        "policy_rate",
    }
