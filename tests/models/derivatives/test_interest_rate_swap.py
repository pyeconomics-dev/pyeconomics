# tests/models/derivatives/test_interest_rate_swap.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``derivatives.interest_rate_swap``: invariants, QuantLib as an oracle, refusals.

The oracle is QuantLib's ``VanillaSwap`` on a flat, continuously compounded
ACT/365 (Fixed) curve, with a ``DiscountingSwapEngine`` on that curve. Its
floating leg follows an Ibor index on the same curve, with no fixing lag,
business-day adjustment or spread, and the same dates as the fixed leg; QuantLib
prices such coupons at par over their accrual periods, so the leg is worth
``N (d_0 - d_n)`` and the two must agree.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813 - oracle docs use ql
from hypothesis import assume, given, reject, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.derivatives import interest_rate_swap

FACTORS = st.floats(min_value=0.05, max_value=1.5)
ACCRUALS = st.floats(min_value=0.01, max_value=1.0)
NOTIONALS = st.floats(min_value=1.0, max_value=1e9)
FIXED = st.floats(min_value=-0.1, max_value=1.0)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(interest_rate_swap, inputs).outputs


@st.composite
def schedules(draw: st.DrawFn) -> dict[str, Any]:
    """Accruals with a discount factor each, from a declining curve or not."""
    size = draw(st.integers(min_value=1, max_value=40))
    return {
        "calculation": "discount_factors",
        "accruals": draw(st.lists(ACCRUALS, min_size=size, max_size=size)),
        "discount_factors": draw(st.lists(FACTORS, min_size=size, max_size=size)),
        "start_discount_factor": draw(FACTORS),
    }


@pytest.mark.invariant("derivatives.interest_rate_swap", "value_zero_at_par_rate")
@given(schedule=schedules(), notional=NOTIONALS, fixed=FIXED)
def test_a_swap_at_its_par_rate_is_worth_zero(
    schedule: dict[str, Any], notional: float, fixed: float
) -> None:
    try:
        par = run(notional=notional, fixed_rate=fixed, **schedule).par_swap_rate
    except DomainError:
        reject()  # a par rate past [-0.99, 10]: refused, tested below
    assume(-0.1 <= par <= 1.0)
    at_par = run(notional=notional, fixed_rate=par, **schedule)
    scale = notional * (
        schedule["start_discount_factor"] + max(schedule["discount_factors"])
    )
    assert abs(at_par.payer_value) <= 1e-13 * scale
    assert math.isclose(
        at_par.fixed_leg_value, at_par.floating_leg_value, abs_tol=1e-13 * scale
    )


@pytest.mark.invariant(
    "derivatives.interest_rate_swap", "payer_and_receiver_values_offset"
)
@given(schedule=schedules(), notional=NOTIONALS, fixed=FIXED)
def test_the_payer_and_receiver_values_offset(
    schedule: dict[str, Any], notional: float, fixed: float
) -> None:
    try:
        result = run(notional=notional, fixed_rate=fixed, **schedule)
    except DomainError:
        reject()
    assert result.payer_value + result.receiver_value == 0.0
    assert result.payer_value == result.floating_leg_value - result.fixed_leg_value


@pytest.mark.invariant("derivatives.interest_rate_swap", "value_linear_in_notional")
@given(
    schedule=schedules(),
    notional=st.floats(min_value=1.0, max_value=1e6),
    scale=st.floats(min_value=0.001, max_value=1000.0),
    fixed=FIXED,
)
def test_values_scale_with_the_notional(
    schedule: dict[str, Any], notional: float, scale: float, fixed: float
) -> None:
    try:
        one = run(notional=notional, fixed_rate=fixed, **schedule)
    except DomainError:
        reject()
    many = run(notional=notional * scale, fixed_rate=fixed, **schedule)
    assert many.par_swap_rate == one.par_swap_rate
    assert many.annuity_factor == one.annuity_factor
    for name in ("fixed_leg_value", "floating_leg_value", "payer_value"):
        size = abs(one.fixed_leg_value) + abs(one.floating_leg_value)
        assert math.isclose(
            getattr(many, name),
            scale * getattr(one, name),
            rel_tol=1e-12,
            abs_tol=1e-12 * scale * size,
        ), name


def test_a_curve_and_its_discount_factors_give_one_swap() -> None:
    accruals = [0.5, 0.5, 0.5, 0.5]
    rates = [0.05, 0.058, 0.064, 0.068]
    tenors = [0.5, 1.0, 1.5, 2.0]
    common = {"notional": 1e6, "fixed_rate": 0.06, "accruals": accruals}
    curve = run(
        calculation="zero_curve", curve_tenors=tenors, curve_rates=rates, **common
    )
    factors = [math.exp(-r * t) for r, t in zip(rates, tenors, strict=True)]
    direct = run(calculation="discount_factors", discount_factors=factors, **common)
    assert math.isclose(curve.par_swap_rate, direct.par_swap_rate, rel_tol=1e-14)
    assert math.isclose(curve.payer_value, direct.payer_value, rel_tol=1e-12)


@pytest.mark.parametrize(
    ("inputs", "match"),
    [
        (
            {
                "calculation": "discount_factors",
                "accruals": [1.0],
                "discount_factors": [0.9, 0.8],
            },
            "one of each",
        ),
        (
            {
                "calculation": "zero_curve",
                "accruals": [1.0],
                "curve_tenors": [2.0, 1.0],
                "curve_rates": [0.03, 0.03],
            },
            "increasing",
        ),
        (
            {
                "calculation": "zero_curve",
                "accruals": [1.0],
                "curve_tenors": [1.0],
                "curve_rates": [0.03, 0.04],
            },
            "one rate per tenor",
        ),
        (
            {
                "calculation": "dated",
                "valuation_date": "2026-02-01",
                "start_date": "2026-01-15",
                "payment_dates": ["2027-01-15"],
                "curve_tenors": [1.0],
                "curve_rates": [0.03],
            },
            "before the valuation date",
        ),
        (
            {
                "calculation": "dated",
                "valuation_date": "2026-01-15",
                "start_date": "2026-01-15",
                "payment_dates": ["2027-01-15", "2026-07-15"],
                "curve_tenors": [1.0],
                "curve_rates": [0.03],
            },
            "increasing",
        ),
    ],
)
def test_inconsistent_schedules_are_refused(inputs: dict[str, Any], match: str) -> None:
    with pytest.raises(InputError, match=match):
        run(fixed_rate=0.03, **inputs)


def test_a_par_rate_past_its_bounds_is_refused() -> None:
    with pytest.raises(DomainError, match="par swap rate"):
        run(
            calculation="discount_factors",
            fixed_rate=0.03,
            accruals=[0.01],
            discount_factors=[0.01],
        )


def test_an_annuity_that_underflows_is_refused() -> None:
    with pytest.raises(DomainError, match="annuity is zero"):
        run(
            calculation="discount_factors",
            fixed_rate=0.03,
            accruals=[1e-300],
            discount_factors=[1e-300],
        )


# --- QuantLib as an oracle -------------------------------------------------------

DAY_COUNTS = {
    "thirty_360_us": ql.Thirty360(ql.Thirty360.USA),
    "act_360": ql.Actual360(),
    "act_365_fixed": ql.Actual365Fixed(),
}


def qdate(day: dt.date) -> Any:  # noqa: ANN401 - a QuantLib Date
    return ql.Date(day.day, day.month, day.year)


@st.composite
def dated_swaps(draw: st.DrawFn) -> dict[str, Any]:
    """A spot- or forward-starting swap of 1 to 40 periods of 1 to 12 months."""
    valuation = dt.date(2026, 1, draw(st.integers(min_value=1, max_value=28)))
    start = valuation + dt.timedelta(days=draw(st.integers(min_value=0, max_value=730)))
    months = draw(st.sampled_from([1, 3, 6, 12]))
    periods = draw(st.integers(min_value=1, max_value=40))
    payments = []
    for k in range(1, periods + 1):
        year, month = divmod(start.month - 1 + k * months, 12)
        payments.append(dt.date(start.year + year, month + 1, min(start.day, 28)))
    return {
        "calculation": "dated",
        "notional": draw(NOTIONALS),
        "fixed_rate": draw(st.floats(min_value=-0.02, max_value=0.15)),
        "valuation_date": valuation,
        "start_date": start,
        "payment_dates": payments,
        "day_count": draw(st.sampled_from(sorted(DAY_COUNTS))),
        "curve_tenors": [1.0],
        "curve_rates": [draw(st.floats(min_value=-0.02, max_value=0.15))],
        "compounding": "continuous",
    }


@pytest.mark.oracle("derivatives.interest_rate_swap")
@settings(deadline=None)
@given(swap=dated_swaps())
def test_the_dated_swap_agrees_with_quantlibs_vanilla_swap(
    swap: dict[str, Any],
) -> None:
    today = qdate(swap["valuation_date"])
    ql.Settings.instance().evaluationDate = today
    curve = ql.YieldTermStructureHandle(
        ql.FlatForward(
            today, swap["curve_rates"][0], ql.Actual365Fixed(), ql.Continuous
        )
    )
    dates = [qdate(swap["start_date"]), *(qdate(d) for d in swap["payment_dates"])]
    schedule = ql.Schedule(dates)
    index = ql.IborIndex(
        "oracle",
        ql.Period(6, ql.Months),
        0,
        ql.USDCurrency(),
        ql.NullCalendar(),
        ql.Unadjusted,
        False,  # noqa: FBT003 - QuantLib's end-of-month flag
        ql.Actual360(),
        curve,
    )
    theirs = ql.VanillaSwap(
        ql.Swap.Payer,
        swap["notional"],
        schedule,
        swap["fixed_rate"],
        DAY_COUNTS[swap["day_count"]],
        schedule,
        index,
        0.0,
        ql.Actual360(),
    )
    theirs.setPricingEngine(ql.DiscountingSwapEngine(curve))
    ours = run(**swap)
    scale = swap["notional"]
    assert math.isclose(
        ours.payer_value, theirs.NPV(), rel_tol=1e-9, abs_tol=1e-10 * scale
    )
    assert math.isclose(
        ours.par_swap_rate, theirs.fairRate(), rel_tol=1e-9, abs_tol=1e-12
    )
    assert math.isclose(
        ours.floating_leg_value,
        theirs.floatingLegNPV(),
        rel_tol=1e-9,
        abs_tol=1e-10 * scale,
    )
    # QuantLib's fixed-leg BPS is the leg's value per basis point, signed for the payer.
    assert math.isclose(
        ours.annuity_factor * swap["notional"] * 1e-4,
        -theirs.fixedLegBPS(),
        rel_tol=1e-9,
    )


def test_a_period_that_accrues_nothing_is_refused() -> None:
    # On US 30/360, the 30th to the 31st of January is zero days; found by the
    # Step 9 review.
    with pytest.raises(DomainError, match="accrues nothing"):
        run(
            calculation="dated",
            fixed_rate=0.05,
            valuation_date="2000-01-30",
            start_date="2000-01-30",
            payment_dates=["2000-01-31"],
            curve_tenors=[1.0],
            curve_rates=[0.05],
        )
