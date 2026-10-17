# tests/data/catalog/test_conversion_properties.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Properties of frequency conversion: it never invents a value or a date.

Converting monthly data to quarterly by mean and back by period end must leave a
value only where a quarter has one, on that quarter's last day, and every other
month missing. Round trips by ``period_end`` return the original values on the
dates they share, and a conversion's dates are always the period ends of the
frequency it converts to.
"""

from __future__ import annotations

import math

from catalog_support import monthly
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.data import ObservationFrequency
from pyeconomics.data.catalog.transforms import apply

_VALUES = st.lists(
    st.one_of(st.none(), st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False)),
    min_size=5,  # five consecutive months always hold a whole quarter
    max_size=60,
)
_START = st.tuples(st.integers(1950, 2100), st.integers(1, 12))


@given(_VALUES, _START)
def test_mean_to_quarterly_and_back_by_period_end_never_invents_a_value(
    values: list[float | None], first: tuple[int, int]
) -> None:
    data = monthly(values, first=first)
    quarters = apply("convert(to=quarterly,method=mean)", data)
    back = apply("convert(to=monthly,method=period_end)", quarters)
    quarter_values = dict(zip(quarters.index, quarters.values, strict=True))
    for day, value in zip(back.index, back.values, strict=True):
        if day in quarter_values:
            assert value == quarter_values[day]
        else:
            assert value is None  # between quarter ends nothing is invented
    # Every month between the first and last quarter end is present.
    assert back.index[0] == quarters.index[0]
    assert back.index[-1] == quarters.index[-1]
    assert back.meta.frequency is ObservationFrequency.MONTHLY


@given(_VALUES, _START)
def test_a_quarterly_mean_is_the_mean_of_exactly_its_three_months(
    values: list[float | None], first: tuple[int, int]
) -> None:
    data = monthly(values, first=first)
    quarters = apply("convert(to=quarterly,method=mean)", data)
    by_month = dict(zip(data.index, data.values, strict=True))
    for day, value in zip(quarters.index, quarters.values, strict=True):
        months = [
            d
            for d in by_month
            if d.year == day.year and (day.month - 3) < d.month <= day.month
        ]
        parts = [by_month[d] for d in months]
        if len(parts) == 3 and None not in parts:
            assert value is not None
            assert math.isclose(value, sum(p for p in parts if p is not None) / 3)
        else:
            assert value is None


@given(_VALUES, _START)
def test_period_end_up_then_down_returns_the_original_values_at_quarter_ends(
    values: list[float | None], first: tuple[int, int]
) -> None:
    data = monthly(values, first=first)
    quarters = apply("convert(to=quarterly,method=period_end)", data)
    original = dict(zip(data.index, data.values, strict=True))
    for day, value in zip(quarters.index, quarters.values, strict=True):
        assert value == original.get(day)
