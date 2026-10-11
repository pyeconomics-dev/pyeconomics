# tests/models/performance/test_return_measurement.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``performance.return_measurement``: invariants, parity, errors and an oracle.

The oracle is NumPy Financial's ``irr``, an independent IRR of periodic flows;
the money-weighted rate of flows at whole periods must agree. Dated flows must
equal ``foundations.time_value``'s XIRR exactly, as they share core's numerics.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import numpy_financial as npf
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.foundations import time_value
from pyeconomics.models.performance import return_measurement


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(return_measurement, inputs)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return result(**inputs).outputs


VALUE = st.floats(1.0, 1e6)


@pytest.mark.invariant(
    "performance.return_measurement", "time_and_money_weighted_agree_without_flows"
)
# The first run imports SciPy's root finder: no deadline.
@settings(deadline=None)
@given(values=st.lists(st.floats(1.0, 50.0), min_size=2, max_size=12))
def test_without_flows_time_and_money_weighting_agree(values: list[float]) -> None:
    periods = len(values) - 1
    total = values[-1] / values[0] - 1
    # The money-weighted rate per period must lie in the IRR's bracket.
    assume(-0.9 < (1 + total) ** (1 / periods) - 1 < 9)
    twr = run(calculation="time_weighted", values=values)
    mwr = run(
        calculation="money_weighted",
        beginning_value=values[0],
        ending_value=values[-1],
        periods=periods,
    )
    assert math.isclose(twr.time_weighted_return, total, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(mwr.money_weighted_return, total, rel_tol=1e-9, abs_tol=1e-9)


@pytest.mark.invariant(
    "performance.return_measurement",
    "modified_dietz_equals_simple_return_without_flows",
)
@given(start=VALUE, end=st.floats(0.0, 1e6), days=st.integers(1, 3_650))
def test_without_flows_dietz_is_the_simple_return(
    start: float, end: float, days: int
) -> None:
    assume(end / start - 1 <= 100)
    first = dt.date(2020, 1, 1)
    found = run(
        calculation="modified_dietz",
        beginning_value=start,
        ending_value=end,
        start_date=first,
        end_date=first + dt.timedelta(days=days),
    )
    assert math.isclose(
        found.modified_dietz_return, end / start - 1, rel_tol=1e-12, abs_tol=1e-15
    )


@pytest.mark.invariant(
    "performance.return_measurement", "time_weighted_ignores_flow_size"
)
@given(
    values=st.lists(VALUE, min_size=3, max_size=8),
    data=st.data(),
    scale=st.floats(1e-3, 1e3),
)
def test_scaling_values_and_flows_keeps_the_time_weighted_return(
    values: list[float], data: st.DataObject, scale: float
) -> None:
    flows = data.draw(
        st.lists(
            st.floats(0.0, 1e5), min_size=len(values) - 1, max_size=len(values) - 1
        )
    )
    try:
        base = run(calculation="time_weighted", values=values, flows=flows)
    except DomainError:
        return
    scaled = run(
        calculation="time_weighted",
        values=[v * scale for v in values],
        flows=[f * scale for f in flows],
    )
    assert math.isclose(
        scaled.time_weighted_return,
        base.time_weighted_return,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )


@pytest.mark.oracle("performance.return_measurement")
@given(
    start=st.floats(100.0, 1e4),
    flows=st.lists(st.floats(-50.0, 50.0), min_size=0, max_size=5),
    growth=st.floats(0.5, 2.0),
)
def test_periodic_money_weighting_matches_numpy_financial(
    start: float, flows: list[float], growth: float
) -> None:
    span = len(flows) + 1
    end = start * growth + sum(flows)
    assume(end > 1.0)
    found = run(
        calculation="money_weighted",
        beginning_value=start,
        ending_value=end,
        flows=flows,
        flow_times=list(range(1, span)),
        periods=span,
    )
    expected = float(npf.irr([-start, *(-f for f in flows), end]))
    assume(math.isfinite(expected) and -0.9 < expected < 5)
    assert found.rate is not None
    assert math.isclose(found.rate, expected, rel_tol=1e-8, abs_tol=1e-10)


def test_dated_money_weighting_is_xirr() -> None:
    dates = [dt.date(2024, 1, 1), dt.date(2024, 5, 10), dt.date(2025, 2, 1)]
    mwr = run(
        calculation="money_weighted",
        beginning_value=1000,
        ending_value=1300,
        flows=[150],
        start_date=dates[0],
        end_date=dates[-1],
        flow_dates=[dates[1]],
    )
    xirr = run_model(
        time_value,
        {"calculation": "xirr", "cash_flows": [-1000, -150, 1300], "dates": dates},
    ).outputs.xirr
    assert mwr.rate == xirr
    assert mwr.annualized_return == xirr


# --- warnings, undefined outputs and errors -------------------------------------


def test_an_unannualized_return_says_why() -> None:
    found = result(calculation="time_weighted", values=[100, 110])
    assert found.outputs.annualized_return is None
    assert [w.code for w in found.warnings] == ["not_annualized"]


def test_periodic_money_weighting_annualizes_by_periods_per_year() -> None:
    found = run(
        calculation="money_weighted",
        beginning_value=100,
        ending_value=110.25,
        periods=2,
        periods_per_year=2,
    )
    assert math.isclose(found.rate, 0.05, abs_tol=1e-11)
    assert math.isclose(found.annualized_return, 0.1025, abs_tol=1e-11)


def test_money_weighting_with_no_sign_change_is_undefined() -> None:
    found = result(
        calculation="money_weighted", beginning_value=100, ending_value=0, periods=1
    )
    assert found.outputs.rate is None
    assert found.outputs.money_weighted_return is None
    assert [w.code for w in found.warnings] == ["no_sign_change"]


def test_a_dietz_return_below_minus_one_is_not_annualized() -> None:
    first = dt.date(2026, 1, 1)
    found = result(
        calculation="modified_dietz",
        beginning_value=100,
        ending_value=0,
        flows=[100],
        flow_dates=[dt.date(2026, 1, 31)],
        start_date=first,
        end_date=dt.date(2026, 2, 1),
        periods_per_year=12,
    )
    assert found.outputs.modified_dietz_return < -1
    assert found.outputs.annualized_return is None
    assert [w.code for w in found.warnings] == ["not_annualized"]


def test_an_annualized_return_past_its_bound_is_null() -> None:
    found = result(
        calculation="time_weighted", values=[1, 100], periods=1, periods_per_year=365
    )
    assert found.outputs.annualized_return is None
    assert [w.code for w in found.warnings] == ["unrepresentable_result"]


def test_a_sub_period_with_nothing_invested_has_no_return() -> None:
    with pytest.raises(DomainError, match="sub-period 2 starts with"):
        run(calculation="time_weighted", values=[100, 50, 80], flows=[0, -50])


def test_a_sub_period_return_past_its_bound_is_a_domain_error() -> None:
    with pytest.raises(DomainError, match="outside its bounds"):
        run(calculation="time_weighted", values=[1, 1000])


def test_dietz_with_no_average_capital_is_a_domain_error() -> None:
    with pytest.raises(DomainError, match="day-weighted capital"):
        run(
            calculation="modified_dietz",
            beginning_value=0,
            ending_value=10,
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 2, 1),
        )


DATED = {
    "calculation": "money_weighted",
    "beginning_value": 100,
    "ending_value": 110,
    "start_date": dt.date(2026, 1, 1),
    "end_date": dt.date(2026, 12, 31),
}


@pytest.mark.parametrize(
    ("inputs", "match"),
    [
        (
            {"calculation": "time_weighted", "values": [1, 2, 3], "flows": [1]},
            "one flow per",
        ),
        ({**DATED, "end_date": None}, "both start_date and end_date"),
        ({**DATED, "periods": 1}, "give an annual rate"),
        ({**DATED, "periods_per_year": 12}, "give an annual rate"),
        ({**DATED, "end_date": dt.date(2025, 1, 1)}, "after start_date"),
        ({**DATED, "flows": [5]}, "one date per flow"),
        ({**DATED, "flows": [5], "flow_dates": [dt.date(2027, 1, 1)]}, "between"),
        (
            {"calculation": "money_weighted", "beginning_value": 1, "ending_value": 2},
            "give periods",
        ),
        (
            {
                "calculation": "money_weighted",
                "beginning_value": 1,
                "ending_value": 2,
                "periods": 1,
                "flow_dates": [dt.date(2026, 1, 1)],
            },
            "need start_date",
        ),
        (
            {
                "calculation": "money_weighted",
                "beginning_value": 1,
                "ending_value": 2,
                "periods": 1,
                "flows": [1],
            },
            "one time per flow",
        ),
        (
            {
                "calculation": "money_weighted",
                "beginning_value": 1,
                "ending_value": 2,
                "periods": 1,
                "flows": [1],
                "flow_times": [2],
            },
            "within the span",
        ),
        (
            {
                "calculation": "modified_dietz",
                "beginning_value": 1,
                "ending_value": 2,
                "start_date": dt.date(2026, 1, 1),
                "end_date": dt.date(2026, 1, 1),
            },
            "after start_date",
        ),
    ],
)
def test_flows_must_fit_their_span(inputs: dict[str, Any], match: str) -> None:
    with pytest.raises(InputError, match=match):
        run(**inputs)


def test_a_long_run_of_losses_annualizes_from_its_logs() -> None:
    # Review regression: halving sixty times compounds to a value that rounds
    # to -1, which used to annualize to -1 rather than -0.5.
    out = run(
        calculation="time_weighted",
        values=[1e12] + [5e11] * 60,
        flows=[0.0] + [5e11] * 59,
        periods=60,
        periods_per_year=1,
    )
    assert math.isclose(out.annualized_return, -0.5, rel_tol=1e-12)
