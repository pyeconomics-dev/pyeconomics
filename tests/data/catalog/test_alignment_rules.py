# tests/data/catalog/test_alignment_rules.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Alignment: the last observation on or before a date, one period's value, a window.

Each rule names what it needs and refuses, with a reason, when the data cannot
supply it. None of them fills silently: ``asof`` and ``align_to`` keep the true
date of the observation they read, and ``max_age_days`` bounds how stale it may be.
"""

from __future__ import annotations

import datetime as dt

import pytest
from catalog_support import days, monthly, quarterly, series

from pyeconomics.core.provenance import RealtimePeriod
from pyeconomics.data import DataError, ObservationFrequency
from pyeconomics.data.catalog.transforms import apply

# --- asof ---------------------------------------------------------------------------


def test_asof_reads_the_last_observation_on_or_before_the_date() -> None:
    data = quarterly([1.0, 2.0, 3.0])
    on_the_day = apply("asof(date=2024-06-30)", data)
    assert (on_the_day.index, on_the_day.values) == ((dt.date(2024, 6, 30),), (2.0,))
    between = apply("asof(date=2024-08-15)", data)
    assert (between.index, between.values) == ((dt.date(2024, 6, 30),), (2.0,))
    after = apply("asof(date=2030-01-01)", data)
    assert after.values == (3.0,)


def test_asof_keeps_the_observations_own_date_so_staleness_is_visible() -> None:
    result = apply("asof(date=2024-12-31)", quarterly([1.0, 2.0]))
    assert result.index == (dt.date(2024, 6, 30),)


def test_asof_skips_a_missing_value_and_never_reads_the_future() -> None:
    data = monthly([1.0, 2.0, None, None, 5.0])
    assert apply("asof(date=2024-04-30)", data).index == (dt.date(2024, 2, 29),)
    assert apply("asof(date=2024-05-31)", data).values == (5.0,)


def test_asof_refuses_when_nothing_precedes_the_date() -> None:
    with pytest.raises(DataError, match="no observation on or before 2023-12-31"):
        apply("asof(date=2023-12-31)", monthly([1.0, 2.0]))
    with pytest.raises(DataError, match="no observation on or before"):
        apply("asof(date=2024-12-31)", monthly([None, None]))


def test_asof_refuses_an_observation_older_than_the_limit() -> None:
    data = quarterly([1.0, 2.0])
    assert apply("asof(date=2024-08-01,max_age_days=32)", data).values == (2.0,)
    with pytest.raises(DataError, match="days old; the limit is 30"):
        apply("asof(date=2024-08-01,max_age_days=30)", data)


def test_asof_carries_the_real_time_period_of_the_row_it_reads() -> None:
    periods = [
        RealtimePeriod(dt.date(2025, 1, 10)),
        RealtimePeriod(dt.date(2025, 4, 10)),
    ]
    data = series(
        ObservationFrequency.QUARTERLY,
        [dt.date(2024, 9, 30), dt.date(2024, 12, 31)],
        [1.0, 2.0],
        realtime=periods,
    )
    assert apply("asof(date=2024-10-15)", data).realtime == (periods[0],)


# --- period -------------------------------------------------------------------------


def test_period_reads_the_observation_of_the_period_that_holds_the_date() -> None:
    q = quarterly([1.0, 2.0, 3.0])
    assert apply("period(date=2024-05-17)", q).values == (2.0,)
    assert apply("period(date=2024-06-30)", q).values == (2.0,)
    assert apply("period(date=2024-04-01)", q).values == (2.0,)
    m = monthly([1.0, 2.0, 3.0])
    assert apply("period(date=2024-02-10)", m).index == (dt.date(2024, 2, 29),)


def test_period_of_a_weekly_and_a_daily_series() -> None:
    fridays = (dt.date(2025, 1, 3), dt.date(2025, 1, 10), dt.date(2025, 1, 17))
    weekly = series(ObservationFrequency.WEEKLY, fridays, [1.0, 2.0, 3.0])
    assert apply("period(date=2025-01-08)", weekly).index == (dt.date(2025, 1, 10),)
    daily = series(
        ObservationFrequency.DAILY, days(dt.date(2025, 1, 1), 3), [1.0, 2.0, 3.0]
    )
    assert apply("period(date=2025-01-02)", daily).values == (2.0,)


def test_period_refuses_an_absent_or_missing_period_and_an_irregular_series() -> None:
    with pytest.raises(
        DataError, match="no observation for the period ending 2024-09-30"
    ):
        apply("period(date=2024-08-01)", quarterly([1.0]))
    with pytest.raises(DataError, match="is missing for the period"):
        apply("period(date=2024-02-10)", monthly([1.0, None]))
    irregular = series(ObservationFrequency.IRREGULAR, [dt.date(2024, 3, 14)], [1.0])
    with pytest.raises(DataError, match="irregular and has no periods"):
        apply("period(date=2024-03-14)", irregular)


def test_period_respects_a_fiscal_year_end() -> None:
    fiscal = series(
        ObservationFrequency.QUARTERLY,
        [dt.date(2024, 12, 31), dt.date(2025, 3, 31)],
        [1.0, 2.0],
        year_ends_in=9,
    )
    assert apply("period(date=2025-02-01)", fiscal).values == (2.0,)


# --- window -------------------------------------------------------------------------


def test_window_reads_the_last_n_observations_on_or_before_the_date() -> None:
    data = quarterly([1.0, 2.0, 3.0, 4.0, 5.0])
    result = apply("window(count=3,date=2025-03-31)", data)
    assert result.values == (3.0, 4.0, 5.0)
    earlier = apply("window(count=2,date=2024-12-31)", data)
    assert earlier.values == (3.0, 4.0)
    assert earlier.index[-1] == dt.date(2024, 12, 31)


def test_window_refuses_too_few_a_missing_value_or_a_hole() -> None:
    data = quarterly([1.0, 2.0, 3.0])
    with pytest.raises(DataError, match="fewer than the 4 asked for"):
        apply("window(count=4,date=2025-12-31)", data)
    with pytest.raises(DataError, match="missing a value in the last 2"):
        apply("window(count=2,date=2025-12-31)", quarterly([1.0, None, 3.0]))
    gappy = series(
        ObservationFrequency.QUARTERLY,
        [dt.date(2024, 3, 31), dt.date(2024, 9, 30), dt.date(2024, 12, 31)],
        [1.0, 2.0, 3.0],
    )
    with pytest.raises(DataError, match="not consecutive periods"):
        apply("window(count=3,date=2024-12-31)", gappy)


# --- align_to -----------------------------------------------------------------------


def test_align_to_reads_the_last_observation_on_or_before_each_target_date() -> None:
    nrou = quarterly([0.050, 0.049])  # Mar and Jun 2024
    months = monthly([0.0] * 5, first=(2024, 3))  # Mar .. Jul
    result = apply("align_to", nrou, months)
    assert result.index == months.index
    assert result.values == (0.050, 0.050, 0.050, 0.049, 0.049)
    assert result.meta.frequency is ObservationFrequency.MONTHLY
    assert "transformed: align_to" in result.meta.notes


def test_align_to_bounds_the_staleness_and_refuses_what_it_cannot_read() -> None:
    nrou = quarterly([0.050, 0.049])
    months = monthly([0.0] * 5, first=(2024, 3))
    with pytest.raises(DataError, match="limit is 40"):
        apply("align_to(max_age_days=40)", nrou, months)
    assert apply("align_to(max_age_days=92)", nrou, months).values[2] == 0.050
    early = monthly([0.0], first=(2024, 1))
    with pytest.raises(DataError, match="no observation on or before 2024-01-31"):
        apply("align_to", nrou, early)


def test_align_to_with_a_zero_limit_reads_only_exact_dates() -> None:
    data = monthly([1.0, 2.0, 3.0])
    assert apply("align_to(max_age_days=0)", data, data).values == (1.0, 2.0, 3.0)
    with pytest.raises(DataError, match="days old"):
        apply(
            "align_to(max_age_days=0)",
            quarterly([9.0]),
            monthly([0.0] * 2, first=(2024, 3)),
        )


def test_align_to_carries_each_matched_rows_real_time_period() -> None:
    period = RealtimePeriod(dt.date(2025, 1, 1))
    source = series(
        ObservationFrequency.QUARTERLY, [dt.date(2024, 3, 31)], [1.0], realtime=[period]
    )
    result = apply("align_to", source, monthly([0.0, 0.0], first=(2024, 3)))
    assert result.realtime == (period, period)
