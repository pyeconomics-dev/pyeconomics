# tests/data/test_vintage.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics.data.Vintage on hand-built ALFRED-style real-time observations.

frame_builders.HISTORY holds two quarters: Q1 published on 2008-04-30 and
revised on 2008-05-29 and 2008-06-26; Q2 published on 2008-07-31 and revised
on 2008-08-28.
"""

from __future__ import annotations

import datetime as dt

import pytest
from frame_builders import HISTORY, Q1, Q2, column, history, monthly, table_meta

from pyeconomics.core import InputError
from pyeconomics.core.provenance import VINTAGE_LABEL_PATTERN
from pyeconomics.data import (
    DataError,
    ObservationFrequency,
    RealtimePeriod,
    Series,
    Table,
    Vintage,
    VintageKind,
)


def observed(series: Series) -> list[tuple[dt.date, float | None]]:
    return list(zip(series.index, series.values, strict=True))


@pytest.mark.parametrize(
    ("on", "expected"),
    [
        (dt.date(2008, 4, 29), []),
        (dt.date(2008, 4, 30), [(Q1, 0.006)]),
        (dt.date(2008, 5, 28), [(Q1, 0.006)]),
        (dt.date(2008, 5, 29), [(Q1, 0.009)]),
        (dt.date(2008, 6, 26), [(Q1, 0.010)]),
        (dt.date(2008, 7, 30), [(Q1, 0.010)]),
        (dt.date(2008, 7, 31), [(Q1, 0.010), (Q2, 0.019)]),
        (dt.date(2008, 8, 27), [(Q1, 0.010), (Q2, 0.019)]),
        (dt.date(2008, 8, 28), [(Q1, 0.010), (Q2, 0.033)]),
        (dt.date(2026, 10, 14), [(Q1, 0.010), (Q2, 0.033)]),
    ],
)
def test_as_of_picks_the_value_whose_real_time_period_covers_the_date(
    on: dt.date, expected: list[tuple[dt.date, float]]
) -> None:
    chosen = Vintage.as_of(on).select(history())
    assert observed(chosen) == expected
    assert chosen.realtime is not None
    assert all(period.covers(on) for period in chosen.realtime)


def test_first_release_is_each_dates_earliest_value() -> None:
    chosen = Vintage.first_release().select(history())
    assert observed(chosen) == [(Q1, 0.006), (Q2, 0.019)]
    assert chosen.realtime == (
        RealtimePeriod(dt.date(2008, 4, 30), dt.date(2008, 5, 28)),
        RealtimePeriod(dt.date(2008, 7, 31), dt.date(2008, 8, 27)),
    )


def test_latest_is_each_dates_most_recent_value() -> None:
    chosen = Vintage.latest().select(history())
    assert observed(chosen) == [(Q1, 0.010), (Q2, 0.033)]
    assert chosen.realtime is not None
    assert all(period.is_current for period in chosen.realtime)


def test_all_returns_every_row() -> None:
    series = history()
    assert Vintage.all().select(series) is series
    assert len(series) == len(HISTORY)


def test_a_selection_keeps_its_metadata_and_is_a_valid_series() -> None:
    series = history()
    chosen = Vintage.first_release().select(series)
    assert chosen.meta == series.meta
    assert Series.from_json(chosen.canonical_json()) == chosen


def test_a_table_is_selected_row_by_row() -> None:
    series = history()
    table = Table(
        series.index,
        (column("growth"), column("level")),
        (series.values, tuple(float(i) for i in range(len(series)))),
        table_meta(frequency=ObservationFrequency.QUARTERLY),
        series.realtime,
    )
    chosen = Vintage.as_of(dt.date(2008, 8, 1)).select(table)
    assert chosen.index == (Q1, Q2)
    assert chosen.data == ((0.010, 0.019), (2.0, 3.0))


def test_a_source_without_vintages_has_only_its_latest_data() -> None:
    series = monthly((0.01, 0.02))
    assert Vintage.latest().select(series) is series
    assert Vintage.all().select(series) is series
    for vintage in (Vintage.as_of(dt.date(2020, 3, 1)), Vintage.first_release()):
        with pytest.raises(DataError, match="keeps no vintages") as caught:
            vintage.select(series)
        assert caught.value.provider == "example"


# --- the selector itself ------------------------------------------------------


@pytest.mark.parametrize(
    "vintage",
    [
        Vintage.latest(),
        Vintage.first_release(),
        Vintage.all(),
        Vintage.as_of(dt.date(2008, 12, 16)),
    ],
)
def test_labels_round_trip_and_match_the_record_grammar(vintage: Vintage) -> None:
    assert VINTAGE_LABEL_PATTERN.fullmatch(vintage.label)
    assert Vintage.parse(vintage.label) == vintage


def test_the_kinds() -> None:
    assert [kind.value for kind in VintageKind] == [
        "latest",
        "as_of",
        "first_release",
        "all",
    ]
    assert Vintage("first_release") == Vintage.first_release()  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    "label", ["revised", "as_of:2008-12-32", "as_of:20081216", "", 3]
)
def test_parse_refuses_anything_else(label: object) -> None:
    with pytest.raises(InputError):
        Vintage.parse(label)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_only_as_of_names_a_date() -> None:
    with pytest.raises(InputError, match="only an as_of vintage"):
        Vintage(VintageKind.LATEST, dt.date(2008, 1, 1))
    with pytest.raises(InputError, match="must be a date"):
        Vintage(VintageKind.AS_OF)
    with pytest.raises(InputError, match="must lie between"):
        Vintage.as_of(dt.date(1600, 1, 1))


def test_an_empty_real_time_series_selects_to_empty() -> None:
    empty = Series((), (), history().meta, ())
    assert empty.has_realtime
    for vintage in (Vintage.latest(), Vintage.first_release()):
        assert len(vintage.select(empty)) == 0
