# tests/data/bindings/test_bind_edges.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The edges of binding: windowed sources, derived concepts, units, bad models."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import bound_support as bs
import pytest
import toy_models as tm
from catalog_support import LIBRARY_TERMS, meta
from scripted import calls_of, registry_of, scripted

from pyeconomics.core import AsOf, Binding, InputError, LicenceClass, UnitKind
from pyeconomics.core.binding import FieldShape
from pyeconomics.data import (
    Capability,
    DataError,
    Mode,
    ObservationFrequency,
    RealtimePeriod,
    SeasonalAdjustment,
    Series,
    bind_model,
    candidate_notes,
    catalog,
)
from pyeconomics.data import bindings as bnd

if TYPE_CHECKING:
    from pyeconomics.data import DataProvider

DAYS = tuple(dt.date(2024, 3, day) for day in (4, 5, 6, 7, 8, 11, 12, 13, 14, 15))
TEN_YEAR = bs.bound_to("us.treasury.nominal_10y")


def dgs10() -> type[DataProvider]:
    series = Series(
        DAYS,
        tuple(0.040 + 0.0005 * i for i in range(len(DAYS))),
        meta(
            ObservationFrequency.BUSINESS_DAILY,
            provider="fred",
            series_id="DGS10",
            unit=bs.RATE,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            terms=LIBRARY_TERMS,
        ),
        tuple(RealtimePeriod(dt.date(2024, 1, 1)) for _ in DAYS),
    )
    return scripted(
        "fred",
        {"DGS10": series},
        licence=LicenceClass.LIBRARY_ONLY,
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )


# --- a source that answers for a window of dates ------------------------------


def test_a_windowed_concept_is_asked_for_the_days_around_the_date() -> None:
    fred = dgs10()
    bound = bind_model(TEN_YEAR, as_of=dt.date(2024, 3, 16), registry=registry_of(fred))
    assert bound.values["unemployment"] == pytest.approx(0.040 + 0.0005 * 9)
    (query,) = calls_of(fred)
    assert query.end == dt.date(2024, 3, 16)
    assert query.start == dt.date(2024, 3, 16) - dt.timedelta(
        days=bnd.lookback_days(ObservationFrequency.BUSINESS_DAILY)
    )


def test_a_windowed_concept_without_a_date_is_refused() -> None:
    with pytest.raises(InputError, match="needs an as_of date"):
        bind_model(TEN_YEAR, registry=registry_of(dgs10()))


def test_the_lookback_grows_with_the_count_and_the_frequency() -> None:
    daily = bnd.lookback_days(ObservationFrequency.BUSINESS_DAILY, 1)
    assert bnd.lookback_days(ObservationFrequency.BUSINESS_DAILY, 10) > daily
    assert bnd.lookback_days(ObservationFrequency.QUARTERLY) > daily
    assert bnd.lookback_days(ObservationFrequency.DAILY) == daily


# --- declarations the catalog or the model contradict -------------------------


def test_a_table_concept_cannot_be_bound() -> None:
    model = bs.bound_to("us.treasury.par_curve")
    with pytest.raises(InputError, match="is a table; a binding reads a series"):
        bind_model(model, as_of=dt.date(2024, 3, 15), registry=bs.world())


def test_a_binding_of_a_field_the_model_does_not_have_is_refused() -> None:
    broken = tm.variant(tm.zero_coupon, bindings=(Binding("nope", "a.b.c"),))
    with pytest.raises(InputError, match="binds 'nope', which is not one of its"):
        bind_model(broken, registry=bs.world())


def test_a_series_of_the_wrong_unit_kind_is_refused_naming_both() -> None:
    wrong = tm.variant(
        tm.zero_coupon, bindings=(Binding("years", "us.unemployment.rate"),)
    )
    with pytest.raises(InputError, match="the series is rate, but the field is years"):
        bind_model(wrong, as_of=dt.date(2024, 3, 20), registry=bs.world())


def test_a_transform_that_cannot_be_applied_names_the_concept_and_field() -> None:
    # A year-over-year change needs a month-based frequency to step back on.
    model = tm.variant(
        tm.zero_coupon,
        bindings=(Binding("rate", "us.treasury.nominal_10y", transform="yoy"),),
    )
    with pytest.raises(
        DataError, match=r"us\.treasury\.nominal_10y for the field 'rate'"
    ):
        bind_model(model, as_of=dt.date(2024, 3, 16), registry=registry_of(dgs10()))


# --- vintages of a derived concept --------------------------------------------


def test_a_derived_concept_serves_vintages_when_all_its_operands_do() -> None:
    concept = catalog.get("us.output_gap.real_potential")
    vintaged = registry_of(
        scripted("fred", {}, capabilities=(Capability.FETCH, Capability.VINTAGES)),
        scripted("cbo", {}, capabilities=(Capability.FETCH, Capability.VINTAGES)),
        scripted("bea", {}),
    )
    assert bnd._serves_vintages(concept, Mode.LIBRARY, vintaged)  # noqa: SLF001
    plain = registry_of(scripted("bea", {}), scripted("cbo", {}))
    assert not bnd._serves_vintages(concept, Mode.LIBRARY, plain)  # noqa: SLF001


def test_a_provider_that_is_not_registered_serves_no_vintages() -> None:
    concept = catalog.get("us.unemployment.rate")
    assert not bnd._serves_vintages(concept, Mode.LIBRARY, registry_of())  # noqa: SLF001


# --- units and the as-of rule -------------------------------------------------


def test_a_whole_number_field_gets_an_int_when_the_value_is_whole() -> None:
    count = FieldShape(kind=UnitKind.COUNT, array=False)
    rate = FieldShape(kind=UnitKind.RATE, array=False)
    assert bnd._number(3.0, 1.0, count) == 3  # noqa: SLF001
    assert isinstance(bnd._number(3.0, 1.0, count), int)  # noqa: SLF001
    assert bnd._number(3.5, 1.0, count) == 3.5  # noqa: SLF001
    assert isinstance(bnd._number(3.0, 1.0, rate), float)  # noqa: SLF001
    assert bnd._number(2.0, 1e3, count) == 2000  # noqa: SLF001


def test_a_missing_observation_cannot_be_delivered() -> None:
    with pytest.raises(DataError, match="missing"):
        bnd._number(None, 1.0, FieldShape(kind=UnitKind.RATE, array=False))  # noqa: SLF001


def test_the_rule_without_a_date_needs_an_observation() -> None:
    empty = Series((), (), meta(ObservationFrequency.MONTHLY))
    binding = Binding("rate", "us.unemployment.rate")
    with pytest.raises(DataError, match="holds no observation"):
        bnd._rule(binding, empty, None)  # noqa: SLF001
    full = Series(DAYS, (0.0,) * len(DAYS), meta(ObservationFrequency.DAILY))
    assert bnd._rule(binding, full, None) == "asof(date=2024-03-15)"  # noqa: SLF001
    window = Binding("rate", "x.y.z", as_of=AsOf.WINDOW, window=3)
    assert bnd._rule(window, full, dt.date(2024, 3, 10)) == (  # noqa: SLF001
        "window(count=3,date=2024-03-10)"
    )


def test_a_dimensionless_decimal_may_fill_a_ratio_field() -> None:
    shape = FieldShape(kind=UnitKind.RATIO, array=False)
    series = Series(
        DAYS, (0.1,) * len(DAYS), meta(ObservationFrequency.DAILY, unit=bs.RATE)
    )
    bnd._check_unit(series, shape, "x")  # noqa: SLF001


def test_a_source_that_labels_no_unit_kind_may_fill_an_index_but_not_a_rate() -> None:
    from pyeconomics.data import UnitRecord  # noqa: PLC0415

    unlabelled = Series(
        DAYS,
        (1.0,) * len(DAYS),
        meta(ObservationFrequency.DAILY, unit=UnitRecord(text="Index")),
    )
    bnd._check_unit(unlabelled, FieldShape(kind=UnitKind.INDEX_LEVEL, array=False), "x")  # noqa: SLF001
    with pytest.raises(InputError, match="the series is None, but the field is rate"):
        bnd._check_unit(unlabelled, FieldShape(kind=UnitKind.RATE, array=False), "x")  # noqa: SLF001


# --- the card's sources --------------------------------------------------------------


def test_a_concept_whose_provider_is_not_installed_still_lists_a_note() -> None:
    notes = candidate_notes(bs.unemployment, registry_of(bs.bls()))
    rate = notes["us.unemployment.rate"]
    assert [(n.provider, n.licence) for n in rate] == [
        ("bls", LicenceClass.HOSTED_SAFE),
        ("fred", None),
    ]


def test_a_derived_candidate_is_noted_as_derived() -> None:
    notes = candidate_notes(bs.bound_to("us.output_gap.real_potential"), bs.world())
    (derived,) = notes["us.output_gap.real_potential"]
    assert (derived.provider, derived.licence) == ("derived", None)
