# tests/data/test_series.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics.data.Series: validation, bounds, periods and lossless round trips."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import numpy as np
import pandas as pd
import pytest
from frame_builders import (
    HISTORY,
    RATE,
    RETRIEVED,
    history,
    month_ends,
    monthly,
    series_meta,
)

from pyeconomics.core import InputError, UnitKind
from pyeconomics.data import (
    MAX_OBSERVATIONS,
    DataError,
    ObservationFrequency,
    RealtimePeriod,
    Series,
    SeriesMeta,
    UnitRecord,
    Weekday,
)

DAILY = series_meta(frequency=ObservationFrequency.DAILY)


# --- canonical JSON -----------------------------------------------------------


def test_a_series_round_trips_through_canonical_json() -> None:
    series = monthly((0.01, None, -0.0, 1e-7, 5.78e16))
    text = series.canonical_json()
    back = Series.from_json(text)
    assert back == series
    assert back.canonical_json() == text
    assert back.values[1] is None


def test_missing_values_are_json_null_never_nan() -> None:
    data = json.loads(monthly((None, 0.5)).canonical_json())
    assert data["values"] == [None, 0.5]
    assert b"NaN" not in monthly((None,)).canonical_json()


def test_the_index_is_written_as_period_end_iso_dates() -> None:
    data = json.loads(monthly((1.0, 2.0)).canonical_json())
    assert data["index"] == ["2020-01-31", "2020-02-29"]
    assert data["schema_version"] == 1
    assert data["type"] == "series"
    assert data["realtime"] is None


def test_a_real_time_series_round_trips_with_its_periods() -> None:
    series = history()
    back = Series.from_json(series.canonical_json())
    assert back == series
    assert back.realtime == series.realtime
    assert json.loads(series.canonical_json())["realtime"][2] == ["2008-06-26", None]


def test_an_empty_series_round_trips() -> None:
    empty = Series((), (), series_meta())
    assert len(empty) == 0
    assert Series.from_json(empty.canonical_json()) == empty
    assert Series.from_pandas(empty.to_pandas()) == empty
    assert list(empty.periods()) == []


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.update(type="table"), "not a series"),
        (lambda d: d.update(schema_version=2), "not a series"),
        (lambda d: d.update(schema_version=True), "not a series"),
        (lambda d: d.update(extra=1), "unknown keys"),
        (lambda d: d.pop("realtime"), "missing keys"),
        (lambda d: d.update(values=[1.0, "2"]), "numbers or None"),
        (lambda d: d.update(values=[1.0]), "1 values for 2 dates"),
        (lambda d: d.update(index="2020-01-31"), "list or tuple"),
        (lambda d: d.update(index=["2020-01-31", "2020-02-30"]), "not a calendar date"),
        (lambda d: d.update(realtime=[["2020-02-01"], ["2020-03-01", None]]), "pairs"),
        (lambda d: d.update(realtime="x"), "list or tuple"),
        (lambda d: d["meta"].update(frequency="hourly"), "must be one of"),
        (lambda d: d["meta"]["unit"].update(scale=True), "numbers or None"),
    ],
)
def test_reading_refuses_any_other_form(
    change: Any,  # noqa: ANN401 - a mutator
    message: str,
) -> None:
    data = json.loads(monthly((1.0, 2.0)).canonical_json())
    change(data)
    with pytest.raises(InputError, match=message):
        Series.from_dict(data)


def test_reading_refuses_nan_and_repeated_keys() -> None:
    text = monthly((1.0,)).canonical_json().decode()
    with pytest.raises(InputError, match="no NaN"):
        Series.from_json(text.replace("[1]", "[NaN]"))
    with pytest.raises(InputError, match="repeats the key"):
        Series.from_json(text.replace('{"index"', '{"type":"series","index"', 1))


# --- pandas -------------------------------------------------------------------


def test_pandas_holds_float64_na_and_a_microsecond_index() -> None:
    frame = monthly((0.01, None)).to_pandas()
    assert str(frame.dtype) == "Float64"
    assert frame.isna().tolist() == [False, True]
    assert frame.index.dtype == "datetime64[us]"
    assert frame.index.name == "date"
    assert frame.name == "EXAMPLE_RATE"
    assert frame.attrs["pyeconomics"]["type"] == "series"
    assert frame.index[0] == pd.Timestamp("2020-01-31")


def test_a_series_round_trips_through_pandas() -> None:
    series = monthly((0.01, None, 0.03))
    assert Series.from_pandas(series.to_pandas()) == series


def test_a_real_time_series_round_trips_through_a_multi_index() -> None:
    series = history()
    frame = series.to_pandas()
    assert list(frame.index.names) == ["date", "realtime_start", "realtime_end"]
    assert pd.isna(frame.index.get_level_values("realtime_end")[2])
    assert Series.from_pandas(frame) == series


def test_metadata_can_be_passed_when_attrs_are_gone() -> None:
    series = monthly((1.0, 2.0))
    frame = series.to_pandas()
    frame.attrs.clear()
    with pytest.raises(InputError, match="no series metadata"):
        Series.from_pandas(frame)
    assert Series.from_pandas(frame, meta=series.meta) == series


def test_numpy_nan_from_pandas_becomes_none() -> None:
    frame = pd.Series(
        [1.0, np.nan], index=pd.DatetimeIndex(["2020-01-31", "2020-02-29"])
    )
    series = Series.from_pandas(frame, meta=series_meta())
    assert series.values == (1.0, None)


@pytest.mark.parametrize(
    ("index", "message"),
    [
        (pd.DatetimeIndex(["2020-01-31 12:00", "2020-02-29"]), "time of day"),
        (pd.DatetimeIndex(["2020-01-31", "2020-02-29"], tz="UTC"), "timezone-naive"),
        (pd.Index(["2020-01-31", "2020-02-29"]), "DatetimeIndex"),
        (
            pd.MultiIndex.from_arrays(
                [pd.DatetimeIndex(["2020-01-31", "2020-02-29"])] * 2,
                names=["date", "vintage"],
            ),
            "real-time index",
        ),
        (pd.DatetimeIndex(["2020-01-31", None]), "must be a date"),
    ],
)
def test_pandas_indexes_must_be_plain_dates(index: pd.Index[Any], message: str) -> None:
    frame = pd.Series([1.0, 2.0], index=index)
    with pytest.raises(InputError, match=message):
        Series.from_pandas(frame, meta=series_meta())


# --- validation ---------------------------------------------------------------


def test_numbers_become_floats() -> None:
    series = monthly((1, np.float64(2.5), np.int64(3)))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    assert series.values == (1.0, 2.5, 3.0)
    assert all(type(value) is float for value in series.values)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (float("nan"), "never NaN"),
        (float("inf"), "never NaN"),
        (True, "numbers or None"),
        (np.bool_(True), "numbers or None"),  # noqa: FBT003 - a NumPy flag
        ("1.0", "numbers or None"),
        (10**400, "too large"),
    ],
)
def test_values_are_finite_numbers_or_none(value: object, message: str) -> None:
    with pytest.raises(InputError, match=message):
        monthly((1.0, value))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_the_index_must_increase_without_real_time_periods() -> None:
    with pytest.raises(InputError, match="must increase"):
        Series(month_ends(2)[::-1], (1.0, 2.0), series_meta())
    day = month_ends(1)[0]
    with pytest.raises(InputError, match="must increase"):
        Series((day, day), (1.0, 2.0), series_meta())


@pytest.mark.parametrize(
    "day",
    ["2020-01-31", dt.datetime(2020, 1, 31, tzinfo=dt.UTC), dt.date(1699, 12, 31)],
)
def test_index_dates_are_dates_in_bounds(day: object) -> None:
    with pytest.raises(InputError):
        Series((day,), (1.0,), DAILY)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_long_run_history_before_1900_is_accepted() -> None:
    annual = series_meta(frequency=ObservationFrequency.ANNUAL)
    assert Series((dt.date(1871, 12, 31),), (1.0,), annual).index[0].year == 1871


def test_values_and_dates_must_pair_up() -> None:
    with pytest.raises(InputError, match="2 values for 1 dates"):
        Series(month_ends(1), (1.0, 2.0), series_meta())


def test_meta_must_be_series_metadata() -> None:
    with pytest.raises(InputError, match="must be a SeriesMeta"):
        Series((), (), {"provider": "x"})  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_missing_counts_none() -> None:
    assert monthly((None, 1.0, None)).missing == 2
    assert not monthly((1.0,)).has_realtime
    assert history().has_realtime


# --- bounds -------------------------------------------------------------------


def _days(count: int) -> tuple[dt.date, ...]:
    start = dt.date(1800, 1, 1)
    return tuple(start + dt.timedelta(days=offset) for offset in range(count))


def test_a_series_holds_at_most_100000_observations() -> None:
    assert MAX_OBSERVATIONS == 100_000
    largest = Series(_days(MAX_OBSERVATIONS), (0.0,) * MAX_OBSERVATIONS, DAILY)
    assert len(largest) == MAX_OBSERVATIONS
    with pytest.raises(InputError, match="at most 100000"):
        Series(_days(MAX_OBSERVATIONS + 1), (0.0,) * (MAX_OBSERVATIONS + 1), DAILY)


def test_an_oversized_document_is_refused_before_it_is_built() -> None:
    data = json.loads(Series(_days(1), (0.0,), DAILY).canonical_json())
    data["values"] = [0.0] * (MAX_OBSERVATIONS + 1)
    data["index"] = ["1800-01-01"] * (MAX_OBSERVATIONS + 1)
    with pytest.raises(InputError, match="at most 100000"):
        Series.from_dict(data)


# --- real-time periods --------------------------------------------------------


def test_real_time_periods_must_pair_with_dates() -> None:
    series = history()
    with pytest.raises(InputError, match="4 periods for 5 dates"):
        Series(series.index, series.values, series.meta, series.realtime[:4])  # type: ignore[index]  # ty: ignore[not-subscriptable]
    with pytest.raises(InputError, match="must be a RealtimePeriod"):
        Series(series.index[:1], series.values[:1], series.meta, (("2008-04-30",),))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_one_dates_periods_must_not_overlap_or_stay_open() -> None:
    q1 = HISTORY[0][0]
    meta = history().meta
    overlapping = (
        RealtimePeriod(dt.date(2008, 4, 30), dt.date(2008, 5, 29)),
        RealtimePeriod(dt.date(2008, 5, 29)),
    )
    with pytest.raises(InputError, match="without overlapping"):
        Series((q1, q1), (0.1, 0.2), meta, overlapping)
    still_open = (
        RealtimePeriod(dt.date(2008, 4, 30)),
        RealtimePeriod(dt.date(2008, 5, 29)),
    )
    with pytest.raises(InputError, match="without overlapping"):
        Series((q1, q1), (0.1, 0.2), meta, still_open)


def test_real_time_rows_sort_by_date() -> None:
    series = history()
    rows = list(zip(series.index, series.values, series.realtime or (), strict=True))
    rows = rows[3:] + rows[:3]  # Q2's rows before Q1's
    with pytest.raises(InputError, match="must not decrease"):
        Series(
            tuple(row[0] for row in rows),
            tuple(row[1] for row in rows),
            series.meta,
            tuple(row[2] for row in rows),
        )


# --- frequencies and periods --------------------------------------------------


CASES = [
    (ObservationFrequency.DAILY, {}, dt.date(2026, 10, 11), "D", "2026-10-11"),
    (ObservationFrequency.BUSINESS_DAILY, {}, dt.date(2026, 10, 9), "B", "2026-10-09"),
    (
        ObservationFrequency.WEEKLY,
        {"week_ends_on": Weekday.FRIDAY},
        dt.date(2026, 10, 9),
        "W-FRI",
        "2026-10-03",
    ),
    (
        ObservationFrequency.BIWEEKLY,
        {"week_ends_on": "wednesday"},
        dt.date(2026, 10, 14),
        "2W-WED",
        "2026-10-01",
    ),
    (ObservationFrequency.MONTHLY, {}, dt.date(2024, 2, 29), "ME", "2024-02-01"),
    (ObservationFrequency.QUARTERLY, {}, dt.date(2026, 9, 30), "QE-DEC", "2026-07-01"),
    (
        ObservationFrequency.QUARTERLY,
        {"year_ends_in": 9},
        dt.date(2026, 12, 31),
        "QE-SEP",
        "2026-10-01",
    ),
    (ObservationFrequency.SEMIANNUAL, {}, dt.date(2026, 6, 30), "6ME", "2026-01-01"),
    (
        ObservationFrequency.SEMIANNUAL,
        {"year_ends_in": 9},
        dt.date(2026, 3, 31),
        "6ME",
        "2025-10-01",
    ),
    (ObservationFrequency.ANNUAL, {}, dt.date(2025, 12, 31), "YE-DEC", "2025-01-01"),
    (
        ObservationFrequency.ANNUAL,
        {"year_ends_in": 9},
        dt.date(2026, 9, 30),
        "YE-SEP",
        "2025-10-01",
    ),
]


@pytest.mark.parametrize(("frequency", "anchors", "day", "alias", "start"), CASES)
def test_each_period_ends_on_its_index_date(
    frequency: ObservationFrequency,
    anchors: dict[str, Any],
    day: dt.date,
    alias: str,
    start: str,
) -> None:
    meta = series_meta(frequency=frequency, **anchors)
    assert meta.pandas_alias == alias
    period = Series((day,), (1.0,), meta).periods()[0]
    assert period.end_time.date() == day
    assert period.start_time.date() == dt.date.fromisoformat(start)


@pytest.mark.parametrize(
    ("frequency", "anchors", "alias"),
    [(case[0], case[1], case[3]) for case in CASES],
)
def test_pandas_period_end_dates_are_accepted(
    frequency: ObservationFrequency, anchors: dict[str, Any], alias: str
) -> None:
    meta = series_meta(frequency=frequency, **anchors)
    # 6ME steps six months from wherever it starts, so start it on a half-year.
    start = "2025-09-01" if meta.year_ends_in == 9 else "2025-12-01"
    dates = pd.date_range(start, periods=6, freq=alias)
    series = Series(tuple(d.date() for d in dates), (1.0,) * len(dates), meta)
    assert [p.end_time.date() for p in series.periods()] == list(series.index)


@pytest.mark.parametrize(
    ("frequency", "anchors", "day"),
    [
        (ObservationFrequency.BUSINESS_DAILY, {}, dt.date(2026, 10, 10)),
        (ObservationFrequency.WEEKLY, {"week_ends_on": "friday"}, dt.date(2026, 10, 8)),
        (ObservationFrequency.MONTHLY, {}, dt.date(2026, 1, 1)),
        (ObservationFrequency.MONTHLY, {}, dt.date(2023, 2, 28) + dt.timedelta(days=1)),
        (ObservationFrequency.QUARTERLY, {}, dt.date(2026, 8, 31)),
        (ObservationFrequency.SEMIANNUAL, {}, dt.date(2026, 9, 30)),
        (ObservationFrequency.ANNUAL, {}, dt.date(2026, 6, 30)),
        (ObservationFrequency.ANNUAL, {"year_ends_in": 9}, dt.date(2026, 12, 31)),
    ],
)
def test_a_date_that_does_not_end_its_period_is_refused(
    frequency: ObservationFrequency, anchors: dict[str, Any], day: dt.date
) -> None:
    meta = series_meta(frequency=frequency, **anchors)
    with pytest.raises(InputError, match="is not the last day"):
        Series((day,), (1.0,), meta)


def test_periods_of_a_period_start_source_are_its_own_months() -> None:
    # FRED dates July 2026 as 2026-07-01; pyeconomics indexes it 2026-07-31.
    series = monthly((0.042,))
    assert series.meta.source_dating.value == "period_start"
    assert str(series.periods()[0]) == "2020-01"


def test_an_irregular_series_has_no_periods() -> None:
    meta = series_meta(frequency=ObservationFrequency.IRREGULAR)
    series = Series((dt.date(2008, 12, 16), dt.date(2009, 1, 28)), (0.0, 0.0), meta)
    assert meta.pandas_alias is None
    with pytest.raises(DataError, match="irregular"):
        series.periods()


# --- metadata -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"frequency": ObservationFrequency.WEEKLY}, "must name week_ends_on"),
        ({"week_ends_on": Weekday.FRIDAY}, "only weekly and biweekly"),
        ({"year_ends_in": 9}, "no fiscal year-end month"),
        ({"frequency": "annual", "year_ends_in": 13}, "from 1 to 12"),
        ({"frequency": "annual", "year_ends_in": 0}, "from 1 to 12"),
        ({"frequency": "annual", "year_ends_in": True}, "month number"),
        ({"frequency": "weekly", "week_ends_on": "fri"}, "must be one of"),
        ({"provider": "Example"}, "snake_case"),
        ({"title": "Rates from https://api.example.org/"}, "must not contain a URL"),
        ({"retrieved_at": dt.datetime(2026, 10, 14)}, "time zone"),  # noqa: DTZ001
        ({"unit": "Percent"}, "must be a UnitRecord"),
        ({"terms": None}, "must be a Terms"),
        ({"seasonal_adjustment": "sa"}, "must be one of"),
        ({"source_dating": "start"}, "must be one of"),
    ],
)
def test_series_metadata_is_checked(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InputError, match=message):
        series_meta(**changes)


def test_metadata_takes_enum_values_and_keeps_utc() -> None:
    meta = series_meta(
        frequency="weekly", week_ends_on="saturday", retrieved_at=RETRIEVED
    )
    assert meta.frequency is ObservationFrequency.WEEKLY
    assert meta.week_ends_on is Weekday.SATURDAY
    assert meta.retrieved_at == RETRIEVED
    assert SeriesMeta.from_dict(json.loads(json.dumps(meta.to_dict()))) == meta


def test_metadata_without_a_retrieval_time_round_trips() -> None:
    meta = series_meta(retrieved_at=None)
    assert SeriesMeta.from_dict(meta.to_dict()) == meta


def test_weekdays_number_and_anchor_as_pandas_does() -> None:
    assert [day.number for day in Weekday] == list(range(7))
    assert Weekday.SUNDAY.pandas == "SUN"
    assert dt.date(2026, 10, 9).weekday() == Weekday.FRIDAY.number


# --- units --------------------------------------------------------------------


def test_a_rate_is_a_decimal_with_scale_one() -> None:
    assert RATE.scale == 1.0
    with pytest.raises(InputError, match="decimals with scale 1"):
        UnitRecord(text="Percent", kind=UnitKind.RATE, scale=100)


@pytest.mark.parametrize("scale", [1e-15, 1e-3, 1, 1000, 1e9, 1e15])
def test_scales_are_powers_of_ten(scale: float) -> None:
    unit = UnitRecord(text="Dollars", kind="money", scale=scale, currency="USD")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    assert unit.scale == float(scale)
    assert UnitRecord.from_dict(json.loads(json.dumps(unit.to_dict()))) == unit


@pytest.mark.parametrize("scale", [0, -1e3, 2.5, 1e16, 1e-16, float("nan"), None])
def test_other_scales_are_refused(scale: object) -> None:
    with pytest.raises(InputError):
        UnitRecord(text="Dollars", scale=scale)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize("currency", ["usd", "US", "USDX", "U$D", "ÜSD", 840])
def test_currencies_are_iso_4217_codes(currency: object) -> None:
    with pytest.raises(InputError, match="ISO 4217"):
        UnitRecord(text="Dollars", kind=UnitKind.MONEY, currency=currency)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_dates_are_not_a_value_unit() -> None:
    with pytest.raises(InputError, match="not a value unit"):
        UnitRecord(text="Date", kind=UnitKind.DATE)
    with pytest.raises(InputError, match="must be one of"):
        UnitRecord(text="Percent", kind="percent")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
