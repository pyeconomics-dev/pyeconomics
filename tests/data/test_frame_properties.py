# tests/data/test_frame_properties.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Property tests: lossless round trips, periods, and vintage selection.

The vintage oracle is the definition itself: on a date, the value published
then is the one whose real-time period covers the date; the first release is
each date's earliest period, and the latest its most recent.
"""

from __future__ import annotations

import calendar
import datetime as dt
from typing import Any

from frame_builders import quarterly_meta, series_meta
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.data import (
    ObservationFrequency,
    RealtimePeriod,
    Series,
    Vintage,
    Weekday,
)

#: (frequency, anchors) pairs covering every kind of calendar.
CALENDARS: list[tuple[ObservationFrequency, dict[str, Any]]] = [
    (ObservationFrequency.DAILY, {}),
    (ObservationFrequency.BUSINESS_DAILY, {}),
    (ObservationFrequency.WEEKLY, {"week_ends_on": Weekday.FRIDAY}),
    (ObservationFrequency.WEEKLY, {"week_ends_on": Weekday.SUNDAY}),
    (ObservationFrequency.BIWEEKLY, {"week_ends_on": Weekday.WEDNESDAY}),
    (ObservationFrequency.MONTHLY, {}),
    (ObservationFrequency.QUARTERLY, {}),
    (ObservationFrequency.QUARTERLY, {"year_ends_in": 8}),
    (ObservationFrequency.SEMIANNUAL, {}),
    (ObservationFrequency.SEMIANNUAL, {"year_ends_in": 9}),
    (ObservationFrequency.ANNUAL, {}),
    (ObservationFrequency.ANNUAL, {"year_ends_in": 3}),
    (ObservationFrequency.IRREGULAR, {}),
]
_STEP = {
    ObservationFrequency.MONTHLY: 1,
    ObservationFrequency.QUARTERLY: 3,
    ObservationFrequency.SEMIANNUAL: 6,
    ObservationFrequency.ANNUAL: 12,
}

values = st.one_of(
    st.none(), st.floats(allow_nan=False, allow_infinity=False, width=64)
)


def _candidates(
    start: dt.date, frequency: ObservationFrequency, anchors: dict[str, Any]
) -> list[dt.date]:
    """Period ends after ``start``, enumerated from the definition, not the code."""
    if frequency in _STEP:
        year_end = anchors.get("year_ends_in", 12)
        ends = []
        for offset in range(150):
            year, month = divmod(start.year * 12 + start.month - 1 + offset, 12)
            if (month + 1 - year_end) % _STEP[frequency] == 0:
                ends.append(
                    dt.date(year, month + 1, calendar.monthrange(year, month + 1)[1])
                )
        return ends
    days = [start + dt.timedelta(days=offset) for offset in range(120)]
    if frequency is ObservationFrequency.BUSINESS_DAILY:
        return [day for day in days if day.weekday() < 5]
    if "week_ends_on" in anchors:
        return [day for day in days if day.weekday() == anchors["week_ends_on"].number]
    return days


@st.composite
def series(draw: st.DrawFn) -> Series:
    frequency, anchors = draw(st.sampled_from(CALENDARS))
    start = draw(st.dates(dt.date(1700, 1, 1), dt.date(2180, 12, 31)))
    candidates = _candidates(start, frequency, anchors)
    chosen = sorted(draw(st.sets(st.sampled_from(range(len(candidates))), max_size=24)))
    index = tuple(candidates[i] for i in chosen)
    data = tuple(draw(values) for _ in index)
    return Series(index, data, series_meta(frequency=frequency, **anchors))


@given(series())
def test_canonical_json_round_trips_losslessly(frame: Series) -> None:
    text = frame.canonical_json()
    back = Series.from_json(text)
    assert back == frame
    assert back.canonical_json() == text
    assert [v is None for v in back.values] == [v is None for v in frame.values]


@given(series())
def test_pandas_round_trips_losslessly(frame: Series) -> None:
    pandas = frame.to_pandas()
    assert int(pandas.isna().sum()) == frame.missing
    assert Series.from_pandas(pandas) == frame


@given(series())
def test_every_period_ends_on_its_index_date(frame: Series) -> None:
    if frame.meta.frequency is ObservationFrequency.IRREGULAR:
        return
    assert [p.end_time.date() for p in frame.periods()] == list(frame.index)


# --- vintages -----------------------------------------------------------------


@st.composite
def histories(
    draw: st.DrawFn,
) -> list[tuple[dt.date, dt.date, dt.date | None, float]]:
    """ALFRED-style rows: each quarter's releases follow one another without gaps."""
    quarters = sorted(draw(st.sets(st.integers(0, 40), min_size=1, max_size=6)))
    rows = []
    for quarter in quarters:
        year, index = divmod(quarter, 4)
        month = 3 * index + 3
        date = dt.date(2000 + year, month, calendar.monthrange(2000 + year, month)[1])
        first = date + dt.timedelta(days=draw(st.integers(1, 60)))
        gaps = draw(st.lists(st.integers(1, 120), min_size=0, max_size=4))
        starts = [first]
        for gap in gaps:
            starts.append(starts[-1] + dt.timedelta(days=gap))
        closed = draw(st.booleans())
        for position, start in enumerate(starts):
            if position + 1 < len(starts):
                end: dt.date | None = starts[position + 1] - dt.timedelta(days=1)
            else:
                end = (
                    start + dt.timedelta(days=draw(st.integers(0, 90)))
                    if closed
                    else None
                )
            rows.append((date, start, end, draw(st.floats(-0.2, 0.2))))
    return rows


def _series(rows: list[tuple[dt.date, dt.date, dt.date | None, float]]) -> Series:
    return Series(
        tuple(row[0] for row in rows),
        tuple(row[3] for row in rows),
        quarterly_meta(),
        tuple(RealtimePeriod(row[1], row[2]) for row in rows),
    )


@given(histories(), st.dates(dt.date(2000, 1, 1), dt.date(2012, 12, 31)))
def test_as_of_agrees_with_the_definition(
    rows: list[tuple[dt.date, dt.date, dt.date | None, float]], on: dt.date
) -> None:
    expected = [
        (date, value)
        for date, start, end, value in rows
        if start <= on and (end is None or on <= end)
    ]
    chosen = Vintage.as_of(on).select(_series(rows))
    assert list(zip(chosen.index, chosen.values, strict=True)) == expected


@given(histories())
def test_first_release_and_latest_agree_with_the_definition(
    rows: list[tuple[dt.date, dt.date, dt.date | None, float]],
) -> None:
    by_date: dict[dt.date, list[tuple[dt.date, float]]] = {}
    for date, start, _, value in rows:
        by_date.setdefault(date, []).append((start, value))
    first = [(date, min(found)[1]) for date, found in by_date.items()]
    last = [(date, max(found)[1]) for date, found in by_date.items()]
    frame = _series(rows)
    for vintage, expected in (
        (Vintage.first_release(), first),
        (Vintage.latest(), last),
    ):
        chosen = vintage.select(frame)
        assert list(zip(chosen.index, chosen.values, strict=True)) == expected
