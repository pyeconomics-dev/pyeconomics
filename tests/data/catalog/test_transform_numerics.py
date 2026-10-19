# tests/data/catalog/test_transform_numerics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Transforms against hand computations: every value below is worked out by hand.

The rules every transform keeps are tested alongside: a gap is a missing value and
never an earlier value carried forward, a date is never invented, and what cannot
be computed is refused with a reason.
"""

from __future__ import annotations

import datetime as dt
import math

import pytest
from catalog_support import (
    HOSTED_TERMS,
    LIBRARY_TERMS,
    days,
    monthly,
    quarterly,
    series,
)

from pyeconomics.core import InputError, UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse, RealtimePeriod
from pyeconomics.data import (
    CachePolicy,
    DataError,
    ObservationFrequency,
    Series,
    UnitRecord,
)
from pyeconomics.data.catalog.transforms import apply, convert, merge_terms


def close(actual: tuple[float | None, ...], expected: list[float | None]) -> None:
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected, strict=True):
        if want is None:
            assert got is None
        else:
            assert got is not None
            assert math.isclose(got, want, rel_tol=1e-12, abs_tol=1e-15)


# --- pct_change, diff, yoy, log ----------------------------------------------------


def test_pct_change_is_the_fractional_change_from_the_previous_period() -> None:
    result = apply("pct_change", monthly([100.0, 110.0, 99.0, 99.0]))
    close(result.values, [None, 0.10, -0.10, 0.0])
    assert result.meta.unit.kind is UnitKind.RETURN
    assert result.index == monthly([0.0] * 4).index


def test_pct_change_over_several_periods_reaches_back_that_far() -> None:
    result = apply("pct_change(periods=2)", monthly([100.0, 105.0, 121.0, 126.0]))
    close(result.values, [None, None, 0.21, 126.0 / 105.0 - 1])


def test_a_gap_in_the_dates_gives_a_missing_value_and_not_a_wrong_comparison() -> None:
    # 2024-03 is absent: the "previous month" of April does not exist.
    index = (dt.date(2024, 1, 31), dt.date(2024, 2, 29), dt.date(2024, 4, 30))
    gappy = series(ObservationFrequency.MONTHLY, index, [100.0, 102.0, 110.0])
    close(apply("pct_change", gappy).values, [None, 0.02, None])
    close(apply("diff", gappy).values, [None, 2.0, None])


def test_lag_reads_the_value_periods_back_on_each_date() -> None:
    result = apply("lag(periods=2)", monthly([1.0, 2.0, 3.0, 4.0]))
    close(result.values, [None, None, 1.0, 2.0])
    assert result.index == monthly([0.0] * 4).index
    assert result.meta.unit == monthly([0.0]).meta.unit
    assert "transformed: lag(periods=2)" in result.meta.notes


def test_lag_counts_periods_by_date_so_a_gap_is_missing() -> None:
    index = (dt.date(2024, 3, 31), dt.date(2024, 6, 30), dt.date(2024, 12, 31))
    gappy = series(ObservationFrequency.QUARTERLY, index, [1.0, 2.0, 4.0])
    close(apply("lag", gappy).values, [None, 1.0, None])  # Q3 is absent


def test_lag_counts_observations_on_a_daily_series() -> None:
    daily = series(
        ObservationFrequency.DAILY, days(dt.date(2024, 1, 1), 3), [1.0, 2.0, 3.0]
    )
    close(apply("lag", daily).values, [None, 1.0, 2.0])


def test_lag_keeps_the_real_time_period_of_the_value_it_reads() -> None:
    periods = [RealtimePeriod(dt.date(2024, m, 1)) for m in (2, 3, 4)]
    selected = monthly([1.0, 2.0, 3.0], realtime=periods)
    result = apply("lag", selected)
    assert result.realtime == (periods[0], periods[0], periods[1])


def test_a_missing_value_or_a_non_positive_base_gives_a_missing_value() -> None:
    result = apply("pct_change", monthly([100.0, None, 120.0, 0.0, 5.0, -4.0, 3.0]))
    close(result.values, [None, None, None, -1.0, None, -4.0 / 5.0 - 1, None])
    assert result.values[4] is None  # the base is zero
    assert result.values[6] is None  # the base is negative


def test_daily_series_count_observations_back_not_calendar_days() -> None:
    friday, monday = dt.date(2025, 1, 3), dt.date(2025, 1, 6)
    business = series(
        ObservationFrequency.BUSINESS_DAILY, [friday, monday], [100.0, 101.0]
    )
    close(apply("pct_change", business).values, [None, 0.01])


def test_diff_keeps_the_unit_and_names_the_change() -> None:
    result = apply("diff(periods=2)", monthly([1.0, 4.0, 9.0, 16.0]))
    close(result.values, [None, None, 8.0, 12.0])
    assert result.meta.unit.kind is UnitKind.INDEX_LEVEL
    assert result.meta.unit.text == "Change in Index"
    assert "transformed: diff(periods=2)" in result.meta.notes


def test_yoy_compares_with_the_same_month_a_year_earlier() -> None:
    values = [float(100 + i) for i in range(14)]
    result = apply("yoy", monthly(values))
    expected: list[float | None] = [None] * 12
    expected += [112.0 / 100.0 - 1, 113.0 / 101.0 - 1]
    close(result.values, expected)
    assert result.meta.unit.kind is UnitKind.RATE
    assert result.meta.title.startswith("Year-over-year change in")


def test_yoy_of_a_quarterly_series_looks_four_periods_back() -> None:
    result = apply("yoy", quarterly([100.0, 101.0, 102.0, 103.0, 104.0, 106.0]))
    close(result.values, [None, None, None, None, 0.04, 106.0 / 101.0 - 1])


def test_yoy_across_a_leap_day_still_finds_the_year_earlier_month() -> None:
    # Feb 2024 ends on the 29th; Feb 2025 on the 28th.
    result = apply("yoy", monthly([float(i + 100) for i in range(14)], first=(2024, 1)))
    assert result.index[13] == dt.date(2025, 2, 28)
    assert result.values[13] == pytest.approx(113.0 / 101.0 - 1)


def test_yoy_refuses_a_daily_series() -> None:
    daily = series(
        ObservationFrequency.DAILY, days(dt.date(2025, 1, 1), 3), [1.0, 2.0, 3.0]
    )
    with pytest.raises(DataError, match="yoy needs a monthly"):
        apply("yoy", daily)


def test_log_is_the_natural_logarithm_and_refuses_a_non_positive_value() -> None:
    result = apply("log", monthly([1.0, math.e, None, 100.0]))
    close(result.values, [0.0, 1.0, None, math.log(100.0)])
    assert result.meta.unit.kind is None
    with pytest.raises(DataError, match="log is undefined for 0"):
        apply("log", monthly([1.0, 0.0]))
    with pytest.raises(DataError, match="log is undefined"):
        apply("log", monthly([-1.0]))


def test_changes_only_keeps_the_first_date_and_each_date_the_value_moved() -> None:
    steps = series(
        ObservationFrequency.DAILY,
        days(dt.date(2025, 1, 1), 7),
        [1.0, 1.0, None, 2.0, 2.0, 1.0, 1.0],
    )
    result = apply("changes_only", steps)
    assert result.index == (
        dt.date(2025, 1, 1),
        dt.date(2025, 1, 4),
        dt.date(2025, 1, 6),
    )
    assert result.values == (1.0, 2.0, 1.0)
    assert result.meta.frequency is ObservationFrequency.IRREGULAR


def test_several_vintages_per_date_are_refused() -> None:
    first = RealtimePeriod(dt.date(2025, 1, 1), dt.date(2025, 1, 31))
    second = RealtimePeriod(dt.date(2025, 2, 1))
    stacked = series(
        ObservationFrequency.MONTHLY,
        [dt.date(2024, 12, 31), dt.date(2024, 12, 31)],
        [1.0, 2.0],
        realtime=[first, second],
    )
    for text in ("pct_change", "yoy", "diff", "lag", "log", "changes_only"):
        with pytest.raises(DataError, match="several vintages"):
            apply(text, stacked)


def test_a_vintage_selected_series_keeps_each_dates_real_time_period() -> None:
    periods = [RealtimePeriod(dt.date(2025, 1, 15)) for _ in range(3)]
    selected = series(
        ObservationFrequency.MONTHLY,
        [dt.date(2024, 10, 31), dt.date(2024, 11, 30), dt.date(2024, 12, 31)],
        [100.0, 102.0, 101.0],
        realtime=periods,
    )
    result = apply("pct_change", selected)
    assert result.realtime == tuple(periods)


# --- ratio and add ------------------------------------------------------------------


def test_a_ratio_is_first_over_second_and_excess_subtracts_one() -> None:
    actual = quarterly([105.0, 99.0, None, 50.0])
    potential = quarterly([100.0, 100.0, 100.0, 0.0])
    close(apply("ratio", actual, potential).values, [1.05, 0.99, None, None])
    gap = apply("ratio(excess=true)", actual, potential)
    close(gap.values, [0.05, -0.01, None, None])
    assert gap.meta.unit.kind is UnitKind.RATE
    assert apply("ratio", actual, potential).meta.unit.kind is UnitKind.RATIO


def test_a_ratio_scales_by_each_units_power_of_ten() -> None:
    billions = UnitRecord(text="Billions", kind=UnitKind.MONEY, scale=1e9)
    millions = UnitRecord(text="Millions", kind=UnitKind.MONEY, scale=1e6)
    debt = quarterly([30_000.0], unit=billions)
    gdp = quarterly([20_000_000.0], unit=millions)
    close(apply("ratio", debt, gdp).values, [1.5])


def test_a_ratio_reads_only_the_dates_both_series_have() -> None:
    first = quarterly([1.0, 2.0, 3.0, 4.0])
    second = quarterly([2.0, 4.0], first=(2024, 6))
    result = apply("ratio", first, second)
    assert result.index == (dt.date(2024, 6, 30), dt.date(2024, 9, 30))
    close(result.values, [1.0, 0.75])


def test_a_ratio_refuses_different_frequencies_and_disjoint_dates() -> None:
    with pytest.raises(DataError, match="same frequency"):
        apply("ratio", monthly([1.0]), quarterly([1.0]))
    with pytest.raises(DataError, match="share no date"):
        apply("ratio", quarterly([1.0]), quarterly([1.0], first=(2030, 3)))


def test_a_derived_series_carries_the_stricter_terms_and_names_both_sources() -> None:
    library = quarterly([1.0], terms=LIBRARY_TERMS, series_id="B")
    result = apply("ratio", quarterly([2.0], series_id="A"), library)
    assert result.meta.terms.licence is LicenceClass.LIBRARY_ONLY
    assert result.meta.terms.cache is CachePolicy.FORBIDDEN
    assert result.meta.terms.llm_use is LlmUse.FORBIDDEN
    assert result.meta.series_id == "A/B"
    assert result.meta.dataset == "derived"
    assert any(note.startswith("derived: ") for note in result.meta.notes)


def test_merge_terms_keeps_the_oldest_check_and_both_attributions() -> None:
    merged = merge_terms(HOSTED_TERMS, LIBRARY_TERMS)
    assert merged.checked == LIBRARY_TERMS.checked
    assert HOSTED_TERMS.attribution in merged.attribution
    assert LIBRARY_TERMS.attribution in merged.attribution
    assert merged.notice == HOSTED_TERMS.notice
    assert (
        merge_terms(HOSTED_TERMS, HOSTED_TERMS).attribution == HOSTED_TERMS.attribution
    )


def test_add_sums_in_the_first_units_and_refuses_unlike_kinds() -> None:
    millions = UnitRecord(text="Millions", kind=UnitKind.MONEY, scale=1e6)
    billions = UnitRecord(text="Billions", kind=UnitKind.MONEY, scale=1e9)
    lending = quarterly([-1_800_000.0, None, 5.0], unit=millions)
    interest = quarterly([1_200.0, 1.0, 1.0], unit=billions)
    result = apply("add", lending, interest)
    close(result.values, [-1_800_000.0 + 1_200_000.0, None, 5.0 + 1_000.0])
    assert result.meta.unit == millions
    with pytest.raises(DataError, match="one unit kind"):
        apply("add", lending, quarterly([1.0, 2.0, 3.0]))


# --- conversion ---------------------------------------------------------------------


def test_monthly_to_quarterly_by_mean_sum_first_last_and_period_end() -> None:
    values = [float(v) for v in (1, 2, 3, 4, 5, 6, 7, 8, 9)]
    data = monthly(values, first=(2024, 1))
    close(apply("convert(to=quarterly,method=mean)", data).values, [2.0, 5.0, 8.0])
    close(apply("convert(to=quarterly,method=sum)", data).values, [6.0, 15.0, 24.0])
    close(apply("convert(to=quarterly,method=first)", data).values, [1.0, 4.0, 7.0])
    close(apply("convert(to=quarterly,method=last)", data).values, [3.0, 6.0, 9.0])
    ends = apply("convert(to=quarterly,method=period_end)", data)
    close(ends.values, [3.0, 6.0, 9.0])
    assert ends.index == (
        dt.date(2024, 3, 31),
        dt.date(2024, 6, 30),
        dt.date(2024, 9, 30),
    )
    assert ends.meta.frequency is ObservationFrequency.QUARTERLY


def test_a_period_entered_or_left_part_way_is_left_out_and_a_hole_is_missing() -> None:
    # Starts in February, ends in November: Q1 and Q4 are partial and dropped;
    # August is missing, so the Q3 mean and sum are missing, never a mean of two
    # months.
    data = monthly(
        [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, None, 9.0, 10.0, 11.0], first=(2024, 2)
    )
    for method in ("mean", "sum"):
        result = apply(f"convert(to=quarterly,method={method})", data)
        assert result.index == (dt.date(2024, 6, 30), dt.date(2024, 9, 30))
        assert result.values[1] is None
    close(apply("convert(to=quarterly,method=mean)", data).values[:1], [5.0])
    # `last` reads the quarter's last month: June and September are present.
    close(apply("convert(to=quarterly,method=last)", data).values, [6.0, 9.0])


def test_a_missing_first_or_last_month_is_not_replaced_by_a_neighbour() -> None:
    data = monthly([1.0, 2.0, None, 4.0, None, 6.0, 7.0, 8.0, 9.0], first=(2024, 1))
    close(apply("convert(to=quarterly,method=last)", data).values, [None, 6.0, 9.0])
    close(apply("convert(to=quarterly,method=first)", data).values, [1.0, 4.0, 7.0])


def test_quarterly_to_annual_and_the_fiscal_year_end_are_kept() -> None:
    data = quarterly([float(v) for v in range(1, 9)], first=(2024, 3))
    close(apply("convert(to=annual,method=mean)", data).values, [2.5, 6.5])
    fiscal = series(
        ObservationFrequency.QUARTERLY,
        [
            dt.date(2024, 12, 31),
            dt.date(2025, 3, 31),
            dt.date(2025, 6, 30),
            dt.date(2025, 9, 30),
        ],
        [1.0, 2.0, 3.0, 4.0],
        year_ends_in=9,
    )
    annual = convert(fiscal, "annual", "sum")
    assert annual.index == (dt.date(2025, 9, 30),)
    assert annual.values == (10.0,)
    assert annual.meta.year_ends_in == 9


def test_daily_to_monthly_aggregates_only_the_observations_of_a_whole_month() -> None:
    # 15 Jan to 14 Apr: January and April are entered and left part-way.
    index = days(dt.date(2025, 1, 15), 90)
    data = series(ObservationFrequency.DAILY, index, [float(i) for i in range(90)])
    result = apply("convert(to=monthly,method=mean)", data)
    assert result.index == (dt.date(2025, 2, 28), dt.date(2025, 3, 31))
    # February holds the offsets 17..44 and March 45..75.
    close(result.values, [(17 + 44) / 2, (45 + 75) / 2])
    last = apply("convert(to=monthly,method=last)", data)
    close(last.values, [44.0, 75.0])
    first = apply("convert(to=monthly,method=first)", data)
    close(first.values, [17.0, 45.0])
    total = apply("convert(to=monthly,method=sum)", data)
    close(total.values, [sum(range(17, 45)), sum(range(45, 76))])


def test_period_end_reads_only_the_observation_on_the_last_day() -> None:
    index = days(dt.date(2025, 1, 25), 40)
    data = series(ObservationFrequency.DAILY, index, [float(i) for i in range(40)])
    result = apply("convert(to=monthly,method=period_end)", data)
    assert result.index == (dt.date(2025, 2, 28),)
    close(result.values, [34.0])


def test_going_up_a_frequency_keeps_each_value_on_its_own_date() -> None:
    quarters = quarterly([10.0, 20.0, 30.0])
    months = apply("convert(to=monthly,method=period_end)", quarters)
    assert months.index[0] == dt.date(2024, 3, 31)
    assert months.index[-1] == dt.date(2024, 9, 30)
    assert len(months) == 7
    assert months.values == (10.0, None, None, 20.0, None, None, 30.0)
    assert months.meta.frequency is ObservationFrequency.MONTHLY


def test_going_up_a_frequency_by_any_other_method_would_invent_values() -> None:
    for method in ("mean", "sum", "first", "last"):
        with pytest.raises(DataError, match="would invent values"):
            apply(f"convert(to=monthly,method={method})", quarterly([1.0, 2.0]))


def test_converting_to_the_same_frequency_changes_nothing() -> None:
    data = quarterly([1.0, 2.0])
    assert apply("convert(to=quarterly,method=mean)", data) is data


def test_a_series_with_no_complete_period_is_refused() -> None:
    with pytest.raises(DataError, match="no complete"):
        apply("convert(to=quarterly,method=mean)", monthly([1.0, 2.0], first=(2024, 2)))


def test_conversion_keeps_the_unit_the_terms_and_names_the_method() -> None:
    result = apply("convert(to=quarterly,method=mean)", monthly([1.0] * 6))
    assert result.meta.unit.kind is UnitKind.INDEX_LEVEL
    assert result.meta.terms == HOSTED_TERMS
    assert "transformed: convert(to=quarterly,method=mean)" in result.meta.notes


def test_conversion_of_a_vintage_series_keeps_a_period_per_row() -> None:
    periods = [RealtimePeriod(dt.date(2025, 1, 1)) for _ in range(6)]
    data = monthly([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], realtime=periods)
    result = apply("convert(to=quarterly,method=mean)", data)
    assert result.realtime is not None
    assert len(result.realtime) == len(result.index) == 2


def test_apply_checks_the_operand_count_and_the_text() -> None:
    with pytest.raises(DataError, match="reads 2 series"):
        apply("ratio", monthly([1.0]))
    with pytest.raises(DataError, match="reads 1 series"):
        apply("yoy", monthly([1.0]), monthly([1.0]))
    with pytest.raises(InputError):
        apply("nonsense", monthly([1.0]))


def test_apply_returns_a_series() -> None:
    assert isinstance(apply("yoy", monthly([1.0] * 13)), Series)
