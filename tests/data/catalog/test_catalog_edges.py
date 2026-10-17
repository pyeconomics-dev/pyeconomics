# tests/data/catalog/test_catalog_edges.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The edges of the resolver, the public API, the catalog checks and the transforms.

Each test pins a refusal or a fallback that the main suites reach only in passing:
a skip reason that must be real, a derived concept whose operands disagree, a
provider that is not registered, a vintage that cannot be read, a gap that must
stay a gap.
"""

from __future__ import annotations

import datetime as dt

import pytest
from catalog_support import HOSTED_TERMS, days, monthly, quarterly, series
from scripted import calls_of, registry_of, scripted

from pyeconomics import data
from pyeconomics.core import InputError, UnitKind
from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.core.provenance import LicenceClass, RealtimePeriod
from pyeconomics.data import (
    Capability,
    ColumnMeta,
    DataError,
    DateConvention,
    Mode,
    ObservationFrequency,
    SeasonalAdjustment,
    Table,
    TableMeta,
    UnitRecord,
    catalog,
    resolve,
)
from pyeconomics.data.catalog import checks
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Derived,
    Operand,
    Parameter,
    Shape,
    Tier,
)
from pyeconomics.data.catalog.transforms import apply
from pyeconomics.data.resolver import Skip

DATA = [100.0 + i for i in range(30)]
QUARTERLY = ObservationFrequency.QUARTERLY


def toy(
    *candidates: Candidate | Derived,
    concept_id: str = "us.toy.value",
    kind: UnitKind | None = UnitKind.INDEX_LEVEL,
    frequency: ObservationFrequency = ObservationFrequency.MONTHLY,
    **fields: object,
) -> Concept:
    return Concept(
        id=concept_id,
        title="A toy",
        definition="A toy concept written to test the catalog's edges.",
        unit_kind=kind,
        frequency=frequency,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=candidates,
        **fields,  # type: ignore[arg-type]
    )


# --- resolver -----------------------------------------------------------------


def test_a_skip_names_a_real_reason_and_a_code_for_the_record() -> None:
    skip = Skip(provider="alpha", series="A", reason="key_missing", detail="set A")
    assert skip.code == "skipped_alpha_key_missing"
    with pytest.raises(InputError, match="not a skip reason"):
        Skip(provider="alpha", series="A", reason="whatever", detail="x")


def test_a_percent_change_over_several_periods_asks_for_enough_history() -> None:
    alpha = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    resolve(
        toy(
            Candidate(
                provider="alpha", series="A", transforms=("pct_change(periods=12)",)
            ),
            kind=UnitKind.RETURN,
        ),
        start=dt.date(2025, 1, 1),
        registry=registry_of(alpha),
    )
    (query,) = calls_of(alpha)
    assert query.start is not None
    assert query.start < dt.date(2020, 1, 1)  # periods + 1 years of 400 days


def test_a_query_the_provider_rejects_is_passed_over_not_raised() -> None:
    alpha = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    with pytest.raises(DataError, match="data_error"):
        resolve(
            toy(Candidate(provider="alpha", series="A", options=(("bogus", "x"),))),
            registry=registry_of(alpha),
        )


def _curve(unit_kind: UnitKind | None) -> Table:
    unit = UnitRecord(text="Percent", kind=unit_kind)
    column = ColumnMeta(
        name="c", unit=unit, seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE
    )
    meta = TableMeta(
        provider="alpha",
        table_id="t",
        title="A table",
        frequency=ObservationFrequency.MONTHLY,
        source_dating=DateConvention.PERIOD_END,
        terms=HOSTED_TERMS,
    )
    return Table((dt.date(2025, 1, 31),), (column,), ((1.0,),), meta)


def test_a_table_whose_columns_have_the_wrong_kind_is_passed_over() -> None:
    alpha = scripted("alpha", {"T": _curve(None)})
    with pytest.raises(DataError, match="column 'c' has unit kind None"):
        resolve(
            toy(
                Candidate(provider="alpha", series="T"),
                kind=UnitKind.RATE,
                shape=Shape.TABLE,
            ),
            registry=registry_of(alpha),
        )
    fine = scripted("alpha", {"T2": _curve(UnitKind.RATE)})
    resolve(
        toy(
            Candidate(provider="alpha", series="T2"),
            kind=UnitKind.RATE,
            shape=Shape.TABLE,
        ),
        registry=registry_of(fine),
    )


def test_transforms_are_refused_on_a_table_concept_at_import() -> None:
    with pytest.raises(InputError, match="transforms read a series"):
        toy(
            Candidate(provider="alpha", series="T", transforms=("yoy",)),
            kind=UnitKind.RATE,
            shape=Shape.TABLE,
        )


def _worlds(monkeypatch: pytest.MonkeyPatch, **concepts: Concept) -> None:
    monkeypatch.setattr(catalog, "CONCEPTS", dict(concepts))


def test_a_derived_concept_whose_operands_disagree_is_passed_over(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a = scripted("alpha", {"A": monthly(DATA, provider="alpha")})
    b = scripted("beta", {"B": quarterly([1.0, 2.0, 3.0], provider="beta")})
    left = toy(Candidate(provider="alpha", series="A"), concept_id="us.toy.left")
    right = toy(
        Candidate(provider="beta", series="B"),
        concept_id="us.toy.right",
        frequency=QUARTERLY,
    )
    _worlds(monkeypatch, **{"us.toy.left": left, "us.toy.right": right})
    mismatched = toy(
        Derived(
            operands=(Operand("us.toy.left"), Operand("us.toy.right")),
            transform="ratio",
        ),
        concept_id="us.toy.gap",
        kind=UnitKind.RATIO,
    )
    with pytest.raises(DataError, match="transform_failed"):
        resolve(mismatched, registry=registry_of(a, b))


def test_a_derived_concept_with_no_shared_dates_or_a_wrong_result_is_passed_over(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    early = scripted("alpha", {"A": quarterly([1.0, 2.0], provider="alpha")})
    late = scripted(
        "beta", {"B": quarterly([1.0, 2.0], provider="beta", first=(2030, 3))}
    )
    left = toy(
        Candidate(provider="alpha", series="A"),
        concept_id="us.toy.left",
        frequency=QUARTERLY,
    )
    right = toy(
        Candidate(provider="beta", series="B"),
        concept_id="us.toy.right",
        frequency=QUARTERLY,
    )
    right_again = toy(
        Candidate(provider="beta", series="B2"),
        concept_id="us.toy.right",
        frequency=QUARTERLY,
    )
    _worlds(monkeypatch, **{"us.toy.left": left, "us.toy.right": right})
    operands = (Operand("us.toy.left"), Operand("us.toy.right"))
    disjoint = toy(
        Derived(operands=operands, transform="ratio"),
        concept_id="us.toy.gap",
        kind=UnitKind.RATIO,
        frequency=QUARTERLY,
    )
    with pytest.raises(DataError, match="transform_failed"):
        resolve(disjoint, registry=registry_of(early, late))
    _worlds(monkeypatch, **{"us.toy.left": left, "us.toy.right": right_again})
    same = scripted("beta", {"B2": quarterly([4.0, 8.0], provider="beta")})
    wrong_frequency = toy(
        Derived(operands=operands, transform="ratio"),
        concept_id="us.toy.gap",
        kind=UnitKind.RATIO,
        frequency=ObservationFrequency.ANNUAL,
    )
    with pytest.raises(DataError, match="definition_mismatch"):
        resolve(wrong_frequency, registry=registry_of(early, same))
    nothing_in_window = toy(
        Derived(operands=operands, transform="ratio"),
        concept_id="us.toy.gap",
        kind=UnitKind.RATIO,
        frequency=QUARTERLY,
    )
    with pytest.raises(DataError, match="no_observations"):
        resolve(
            nothing_in_window,
            start=dt.date(2000, 1, 1),
            end=dt.date(2000, 12, 31),
            registry=registry_of(early, same),
        )


def test_a_derived_concept_over_a_table_operand_is_passed_over(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = scripted("alpha", {"T": _curve(UnitKind.RATE)})
    plain = scripted("beta", {"B": monthly(DATA, provider="beta")})
    tabular = toy(
        Candidate(provider="alpha", series="T"),
        concept_id="us.toy.table",
        kind=UnitKind.RATE,
        shape=Shape.TABLE,
    )
    plain_concept = toy(
        Candidate(provider="beta", series="B"), concept_id="us.toy.plain"
    )
    _worlds(monkeypatch, **{"us.toy.table": tabular, "us.toy.plain": plain_concept})
    derived = toy(
        Derived(
            operands=(Operand("us.toy.table"), Operand("us.toy.plain")),
            transform="ratio",
        ),
        concept_id="us.toy.gap",
        kind=UnitKind.RATIO,
    )
    with pytest.raises(DataError, match="is not a series"):
        resolve(derived, registry=registry_of(table, plain))


# --- public API ---------------------------------------------------------------


def test_a_concept_whose_provider_is_not_registered_is_described_not_crashed() -> None:
    by_mode = data.candidates_by_mode("us.unemployment.rate", registry_of())
    assert [c.licence for c in by_mode[Mode.LIBRARY]] == [None, None]
    assert by_mode[Mode.HOSTED] == ()


def test_a_provider_series_reads_a_vintage_label_and_a_size_bound() -> None:
    periods = [RealtimePeriod(dt.date(2015, 1, 1)) for _ in range(30)]
    vintaged = scripted(
        "alpha",
        {"A": monthly(DATA, provider="alpha", realtime=periods)},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )
    result = data.get(
        "alpha:A",
        vintage="first_release",
        max_observations=5,
        registry=registry_of(vintaged),
    )
    assert result.source.vintage == "first_release"
    assert len(result.frame.index) == 5
    assert calls_of(vintaged)[0].max_observations == 5


def test_a_provider_series_with_no_rows_keeps_its_record() -> None:
    empty = scripted(
        "alpha",
        {"A": series(ObservationFrequency.MONTHLY, [], [], provider="alpha")},
    )
    result = data.get("alpha:A", registry=registry_of(empty))
    assert result.frame.index == ()
    assert result.source.observation_start is None


def test_the_vintage_provider_skips_what_it_cannot_ask(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = (dt.date(2024, 2, 7),)
    parameterised = Candidate(provider="alpha", series="S{meeting}")
    meeting = Parameter(name="meeting", pattern=r"\d", summary="s", example="1")
    closed = scripted(
        "closed",
        {"C": monthly(DATA, provider="closed")},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        licence=LicenceClass.LIBRARY_ONLY,
    )
    keyed = scripted(
        "keyed",
        {"K": monthly(DATA, provider="keyed")},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        keyed=True,
    )
    good = scripted(
        "good",
        {"G": monthly(DATA, provider="good")},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        changed=dates,
    )
    one = toy(
        parameterised,
        Candidate(provider="ghost", series="X"),
        Candidate(provider="closed", series="C"),
        Candidate(provider="keyed", series="K"),
        Candidate(provider="good", series="G"),
        parameters=(meeting,),
    )
    _worlds(monkeypatch, **{one.id: one})
    registry = registry_of(closed, keyed, good)
    assert data.vintages(one.id, mode=Mode.HOSTED, registry=registry) == dates
    # Library mode asks the library-only candidate first; it lists no dates here.
    assert data.vintages(one.id, registry=registry) == ()


# --- catalog checks -----------------------------------------------------------


def test_the_catalog_checks_see_a_provider_that_cannot_fetch_or_cannot_be_judged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mute = scripted("mute", {}, capabilities=(Capability.SEARCH,))
    missing_extra = scripted("sdmxlike", {"S": monthly(DATA, provider="sdmxlike")})

    def refuse(self: object, query: object) -> object:
        msg = "the sdmx extra is not installed"
        raise MissingOptionalDependencyError(msg)

    missing_extra.build_requests = refuse  # type: ignore[method-assign,assignment]
    table = toy(
        Candidate(provider="mute", series="X"),
        concept_id="us.toy.mute",
    )
    unjudged = toy(
        Candidate(provider="sdmxlike", series="S"),
        concept_id="us.toy.unjudged",
    )
    tabular = toy(
        Candidate(provider="sdmxlike", series="S"),
        concept_id="us.toy.table",
        kind=UnitKind.RATE,
        shape=Shape.TABLE,
    )
    leaf = toy(Candidate(provider="sdmxlike", series="S"), concept_id="us.toy.leaf")
    operands = (Operand("us.toy.table"), Operand("us.toy.leaf"))
    over_table = toy(
        Derived(operands=operands, transform="ratio"), concept_id="us.toy.overtable"
    )
    a = toy(
        Derived(
            operands=(Operand("us.toy.b"), Operand("us.toy.leaf")), transform="ratio"
        ),
        concept_id="us.toy.a",
    )
    b = toy(
        Derived(
            operands=(Operand("us.toy.a"), Operand("us.toy.leaf")), transform="ratio"
        ),
        concept_id="us.toy.b",
    )
    c = toy(
        Derived(
            operands=(Operand("us.toy.leaf"), Operand("us.toy.leaf")),
            transform="ratio",
        ),
        concept_id="us.toy.c",
    )
    monkeypatch.setattr(
        checks,
        "CONCEPTS",
        {x.id: x for x in (table, unjudged, tabular, leaf, over_table, a, b, c)},
    )
    found = {
        (p.provider, p.rule)
        for p in checks.problems(registry_of(mute, missing_extra), deep=True)
    }
    assert ("us.toy.mute", "concept-provider") in found
    assert ("us.toy.unjudged", "concept-series") not in found  # the extra is absent
    assert ("us.toy.overtable", "concept-operand") in found
    assert ("us.toy.a", "concept-cycle") in found
    assert ("us.toy.b", "concept-cycle") in found
    assert ("us.toy.c", "concept-cycle") not in found


# --- transforms ---------------------------------------------------------------


def test_a_weekly_series_counts_periods_by_week() -> None:
    fridays = (
        dt.date(2025, 1, 3),
        dt.date(2025, 1, 10),
        dt.date(2025, 1, 24),  # 17 January is missing
    )
    weekly = series(ObservationFrequency.WEEKLY, fridays, [100.0, 110.0, 99.0])
    first, second, third = apply("pct_change", weekly).values
    assert (first, third) == (None, None)
    assert second == pytest.approx(0.10)


def test_ratio_and_add_take_the_real_time_period_of_whichever_has_one() -> None:
    period = RealtimePeriod(dt.date(2025, 1, 1))
    with_period = quarterly([1.0, 2.0], realtime=[period, period])
    without = quarterly([2.0, 4.0])
    assert apply("ratio", with_period, without).realtime == (period, period)
    assert apply("ratio", without, with_period).realtime == (period, period)
    assert apply("add", without, without).realtime is None


def test_converting_a_vintage_series_up_a_frequency_keeps_a_period_per_row() -> None:
    first = RealtimePeriod(dt.date(2025, 1, 1))
    second = RealtimePeriod(dt.date(2025, 4, 1))
    data_ = quarterly([1.0, 2.0], realtime=[first, second])
    months = apply("convert(to=monthly,method=period_end)", data_)
    assert months.realtime == (first, first, first, second)
    assert months.values == (1.0, None, None, 2.0)


def test_a_period_of_missing_values_and_a_gap_stay_missing() -> None:
    all_missing = series(
        ObservationFrequency.DAILY,
        days(dt.date(2024, 12, 1), 120),
        [None] * 31 + [1.0] * 89,
    )
    january = apply("convert(to=monthly,method=mean)", all_missing)
    assert january.values[0] is None  # December had no value at all
    gap = monthly([1.0, 2.0, None, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    # Drop March: the quarter has no last month to read.
    without_march = series(
        ObservationFrequency.MONTHLY,
        [d for d in gap.index if d != dt.date(2024, 3, 31)],
        [
            v
            for d, v in zip(gap.index, gap.values, strict=True)
            if d != dt.date(2024, 3, 31)
        ],
    )
    assert apply("convert(to=quarterly,method=last)", without_march).values[0] is None
    assert apply("convert(to=quarterly,method=first)", without_march).values[0] == 1.0
    assert Tier.ORIGINATOR.value == "originator"
