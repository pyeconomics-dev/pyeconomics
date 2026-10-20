# tests/data/bindings/test_curve_rows.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A curve binding reads one row of a table of tenors (Phase 3 Step 15).

The observation of a curve on a date is its row: the binding fills an array of
values and, through ``tenors``, an array of each value's tenor in years, both
from the last row on or before the date that holds anything, leaving out the
tenors that row lacks. A scripted Treasury provider answers the par curve.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from catalog_support import HOSTED_TERMS
from pydantic import Field
from scripted import registry_of, scripted

from pyeconomics.core import (
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    InputError,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Rate,
    RateArray,
    Reference,
    Registry,
    RegistryError,
    UnitKind,
    Years,
    YearsArray,
    model,
    run_model,
)
from pyeconomics.data import (
    ColumnMeta,
    DataError,
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Table,
    TableMeta,
    UnitRecord,
)
from pyeconomics.data.bindings import bind_model, tenor_years, validate_bindings

#: Treasury's nominal tenors, as the provider names its columns.
COLUMNS = (
    "BC_1MONTH",
    "BC_2MONTH",
    "BC_3MONTH",
    "BC_4MONTH",
    "BC_6MONTH",
    "BC_1YEAR",
    "BC_2YEAR",
    "BC_3YEAR",
    "BC_5YEAR",
    "BC_7YEAR",
    "BC_10YEAR",
    "BC_20YEAR",
    "BC_30YEAR",
)
YEARS = (1 / 12, 2 / 12, 3 / 12, 4 / 12, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)
DAYS = tuple(dt.date(2026, 3, d) for d in (2, 3, 4, 5, 6, 9))


def _value(day: int, column: int) -> float | None:
    """A rate per day and tenor; the 2-month bill is missing on the 6th, and the
    9th (a stand-in for a day the curve was not published) holds nothing."""
    if day == len(DAYS) - 1 or (day == len(DAYS) - 2 and column == 1):
        return None
    return 0.04 + 0.001 * column + 0.0001 * day


def _treasury(*, published: bool = True) -> Any:  # noqa: ANN401 - a provider class
    """Treasury's par curve, or (``published=False``) rows that hold nothing."""
    meta = TableMeta(
        provider="treasury",
        table_id="par_nominal",
        title="Daily par yield curve rates",
        frequency=ObservationFrequency.IRREGULAR,
        source_dating=DateConvention.PERIOD_END,
        terms=HOSTED_TERMS,
    )
    columns = tuple(
        ColumnMeta(
            name=name,
            unit=UnitRecord(text="Decimal", kind=UnitKind.RATE),
            seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        )
        for name in COLUMNS
    )
    data = tuple(
        tuple(_value(day, column) if published else None for day in range(len(DAYS)))
        for column in range(len(COLUMNS))
    )
    return scripted("treasury", {"par_nominal": Table(DAYS, columns, data, meta)})


class CurveInputs(ModelInputs):
    maturities: YearsArray = Field(min_length=1, max_length=20, description="Tenors")
    yields: RateArray = Field(min_length=1, max_length=20, description="Yields")


class CurveOutputs(ModelOutputs):
    longest: Years = Field(ge=0, le=200, description="The longest tenor")
    level: Rate = Field(ge=-1, le=1, description="The longest tenor's yield")


_COMMON: dict[str, Any] = {
    "formula": (r"y = y(T)",),
    "assumptions": ("A toy: it reads a curve's longest point.",),
    "limitations": ("It models nothing.",),
    "references": (
        Reference(
            key="toy2026",
            citation="A toy source for the curve tests (2026).",
            url="https://www.example.org/toy",
            locator="Table 1",
        ),
    ),
    "evidence": Evidence.PRACTITIONER,
    "cost": CostClass.INSTANT,
    "changelog": (ChangelogEntry(version=1, note="First version."),),
    "invariants": (Invariant(id="reads_the_end", statement="It reads the end."),),
    "examples": (
        Example(name="two", inputs={"maturities": [1, 2], "yields": [0.1, 0.2]}),
    ),
}


def _curve_model(concept: str = "us.treasury.par_curve") -> Any:  # noqa: ANN401
    @model(
        id="fixed_income.toy_curve",
        version=1,
        title="Toy curve reader",
        summary="Reads the longest point of a curve bound to the catalog.",
        bindings=(Binding("yields", concept, tenors="maturities"),),
        **_COMMON,
    )
    def curve(inputs: CurveInputs) -> CurveOutputs:
        return CurveOutputs(longest=inputs.maturities[-1], level=inputs.yields[-1])

    return curve


def test_a_curve_reads_its_last_row_and_leaves_out_a_missing_tenor() -> None:
    bound = bind_model(
        _curve_model(),
        as_of=dt.date(2026, 3, 6),
        registry=registry_of(_treasury()),
    )
    tenors = bound.values["maturities"]
    assert tenors == tuple(y for k, y in enumerate(YEARS) if k != 1)
    assert bound.values["yields"] == tuple(
        _value(4, k) for k in range(len(COLUMNS)) if k != 1
    )
    records = {record.field: record for record in bound.sources}
    assert set(records) == {"yields", "maturities"}
    for record in records.values():
        assert record.concept == "us.treasury.par_curve"
        assert record.observation_start == record.observation_end == DAYS[4]
        assert record.transforms[-1] == "asof(date=2026-03-06)"
        assert "revised_data" in record.warnings  # Treasury keeps no vintages
    result = run_model(_curve_model(), bound)
    assert result.outputs.longest == 30.0


def test_an_empty_row_is_passed_over_for_the_last_curve_before_it() -> None:
    bound = bind_model(
        _curve_model(), as_of=dt.date(2026, 3, 9), registry=registry_of(_treasury())
    )
    (record, _) = bound.sources
    assert record.observation_end == DAYS[4]
    yields = bound.values["yields"]
    assert isinstance(yields, tuple)
    assert len(yields) == len(COLUMNS) - 1


def test_no_curve_on_or_before_the_date_raises() -> None:
    with pytest.raises(DataError, match="holds no curve on or before 2026-03-06"):
        bind_model(
            _curve_model(),
            as_of=dt.date(2026, 3, 6),
            registry=registry_of(_treasury(published=False)),
        )


def test_the_caller_gives_a_curve_whole_or_not_at_all() -> None:
    bound = bind_model(
        _curve_model(),
        as_of=dt.date(2026, 3, 6),
        overrides={"maturities": (1.0, 2.0), "yields": (0.03, 0.04)},
        registry=registry_of(_treasury()),
    )
    assert {r.field for r in bound.sources} == {"yields", "maturities"}
    assert all(r.provider == "user" for r in bound.sources)
    for part in ({"maturities": (1.0, 2.0)}, {"yields": (0.03, 0.04)}):
        with pytest.raises(InputError, match="supply both, or neither"):
            bind_model(
                _curve_model(),
                as_of=dt.date(2026, 3, 6),
                overrides=part,
                registry=registry_of(_treasury()),
            )


@pytest.mark.parametrize(
    ("concept", "problem"),
    [
        ("us.treasury.nominal_10y", "is a series; a curve's binding reads a table"),
        ("us.treasury.gsw_curve", "names no tenor columns"),
    ],
)
def test_a_curve_must_bind_a_table_of_tenors(concept: str, problem: str) -> None:
    registry = Registry.from_models(_curve_model(concept), distribution="toy-dist")
    with pytest.raises(RegistryError, match=problem):
        validate_bindings(registry)
    with pytest.raises(InputError, match=r"tenor|series"):
        bind_model(
            _curve_model(concept),
            as_of=dt.date(2026, 3, 6),
            registry=registry_of(_treasury(), _board()),
        )


def _board() -> Any:  # noqa: ANN401 - a provider class
    """The Board's GSW table: parameters, whose columns are no tenors."""
    meta = TableMeta(
        provider="fed_board",
        table_id="gsw",
        title="GSW parameters",
        frequency=ObservationFrequency.IRREGULAR,
        source_dating=DateConvention.PERIOD_END,
        terms=HOSTED_TERMS,
    )
    column = ColumnMeta(
        name="BETA0",
        unit=UnitRecord(text="Decimal", kind=UnitKind.RATE),
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
    )
    table = Table(DAYS, (column,), ((0.04,) * len(DAYS),), meta)
    return scripted("fed_board", {"gsw": table})


@pytest.mark.parametrize(
    ("label", "years"),
    [("1m", 1 / 12), ("6m", 0.5), ("10y", 10.0), ("0m", None), ("BETA0", None)],
)
def test_tenor_labels(label: str, years: float | None) -> None:
    assert tenor_years(label) == years
