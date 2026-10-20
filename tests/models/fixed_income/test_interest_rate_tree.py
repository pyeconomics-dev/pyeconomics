# tests/models/fixed_income/test_interest_rate_tree.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``fixed_income.interest_rate_tree``: its invariants, two oracles, refusals.

The model calibrates by forward induction over state prices. The first oracle
is Kalotay, Williams and Fabozzi's own method, written independently here: each
period's lowest rate found by bisection, so that the whole tree, valued by
backward induction, prices that maturity's par bond at par. The two must give
the same rates. The second is QuantLib: an option-free bond's value on the
calibrated tree, whatever the volatility, is its value off the curve the par
bonds bootstrap, and QuantLib's ``PiecewiseLogLinearDiscount`` bootstraps it
from ``FixedRateBondHelper`` par bonds.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813 - oracle docs use ql
from hypothesis import assume, given, reject, settings
from hypothesis import strategies as st

from pyeconomics.core import ConvergenceError, DomainError, InputError, run_model
from pyeconomics.models.fixed_income import interest_rate_tree

PERIODS = {"annual": 1, "semiannual": 2, "quarterly": 4}
KWF = {
    "curve_tenors": [1.0, 2.0, 3.0],
    "par_yields": [0.035, 0.04, 0.045],
    "volatility": 0.1,
    "frequency": "annual",
}
KWF_BOND = {"maturity_years": 3.0, "coupon_rate": 0.0525}


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(interest_rate_tree, inputs).outputs


@st.composite
def curves(draw: st.DrawFn, *, shortest: int = 1) -> dict[str, Any]:
    """Upward or gently humped par curves, yearly tenors, a volatility, a step."""
    years = draw(st.integers(min_value=shortest, max_value=12))
    start = draw(st.floats(min_value=0.005, max_value=0.08))
    steps = draw(
        st.lists(
            st.floats(min_value=-0.002, max_value=0.004),
            min_size=years - 1,
            max_size=years - 1,
        )
    )
    par = [start]
    for step in steps:
        par.append(max(par[-1] + step, 0.001))
    return {
        "curve_tenors": [float(k) for k in range(1, years + 1)],
        "par_yields": par,
        "volatility": draw(st.floats(min_value=0.0, max_value=0.3)),
        "frequency": draw(st.sampled_from(list(PERIODS))),
    }


@st.composite
def bonds(draw: st.DrawFn) -> dict[str, Any]:
    """A curve and a bond within it, with an exercise schedule after its first date."""
    curve = draw(curves(shortest=2))
    m = PERIODS[curve["frequency"]]
    last = len(curve["curve_tenors"])
    periods = draw(st.integers(min_value=2, max_value=last * m))
    first = draw(st.integers(min_value=1, max_value=periods - 1))
    dates = [k / m for k in range(first, periods)]
    return {
        **curve,
        "maturity_years": periods / m,
        "coupon_rate": draw(st.floats(min_value=0.0, max_value=0.1)),
        "exercise_years": dates,
        "exercise_prices": [
            draw(st.floats(min_value=95.0, max_value=105.0)) for _ in dates
        ],
    }


def _negative_forwards(curve: dict[str, Any]) -> bool:
    """Whether the curve's par bonds bootstrap a forward rate below zero."""
    m = PERIODS[curve["frequency"]]
    n = int(curve["curve_tenors"][-1] * m)
    par = np.interp(
        [(k + 1) / m for k in range(n)], curve["curve_tenors"], curve["par_yields"]
    )
    factors, annuity, previous = [], 0.0, 1.0
    for c in par / m:
        factor = (1 - c * annuity) / (1 + c)
        if factor > previous * (1 + 1e-12):
            return True
        factors.append(factor)
        annuity += factor
        previous = factor
    return False


# --- invariants ----------------------------------------------------------------


@pytest.mark.invariant(
    "fixed_income.interest_rate_tree", "calibrated_tree_prices_par_bonds_at_par"
)
@settings(deadline=None)
@given(curve=curves(), data=st.data())
def test_the_tree_prices_each_par_bond_at_par(
    curve: dict[str, Any], data: st.DataObject
) -> None:
    assume(not _negative_forwards(curve))
    m = PERIODS[curve["frequency"]]
    periods = data.draw(
        st.integers(min_value=1, max_value=len(curve["curve_tenors"]) * m)
    )
    maturity = periods / m
    coupon = float(np.interp(maturity, curve["curve_tenors"], curve["par_yields"]))
    out = run(calculation="value", maturity_years=maturity, coupon_rate=coupon, **curve)
    assert math.isclose(out.value, 100.0, rel_tol=1e-9)


@pytest.mark.invariant(
    "fixed_income.interest_rate_tree", "callable_below_straight_below_putable"
)
@settings(deadline=None)
@given(bond=bonds())
def test_callable_below_straight_below_putable(bond: dict[str, Any]) -> None:
    assume(not _negative_forwards(bond))
    called = run(calculation="value", option="call", **bond)
    put = run(calculation="value", option="put", **bond)
    straight = called.option_free_value
    assert called.value <= straight * (1 + 1e-12)
    assert straight <= put.value * (1 + 1e-12)
    assert math.isclose(put.option_free_value, straight, rel_tol=1e-15)


def _zero_volatility_price(
    curve: dict[str, Any], bond: dict[str, Any], s: float
) -> float:
    """Discount the bond's flows at the par curve's forward rates plus ``s``."""
    m = PERIODS[curve["frequency"]]
    n = round(bond["maturity_years"] * m)
    par = np.interp(
        [(k + 1) / m for k in range(n)], curve["curve_tenors"], curve["par_yields"]
    )
    factors, annuity = [], 0.0
    for c in par / m:
        factors.append((1 - c * annuity) / (1 + c))
        annuity += factors[-1]
    forwards = [(a / b - 1) * m for a, b in zip([1.0, *factors], factors, strict=False)]
    coupon = bond["coupon_rate"] / m * 100
    value, growth = 0.0, 1.0
    for k, forward in enumerate(forwards, start=1):
        growth *= 1 + (forward + s) / m
        value += (coupon + (100 if k == n else 0)) / growth
    return value


@pytest.mark.invariant(
    "fixed_income.interest_rate_tree",
    "zero_volatility_oas_equals_zero_volatility_spread",
)
@settings(deadline=None)
@given(bond=bonds(), spread=st.floats(min_value=-0.01, max_value=0.05))
def test_at_zero_volatility_the_oas_is_the_zero_volatility_spread(
    bond: dict[str, Any], spread: float
) -> None:
    curve = {**bond, "volatility": 0.0}
    assume(not _negative_forwards(curve))
    price = _zero_volatility_price(curve, bond, spread)
    plain = {
        k: v for k, v in curve.items() if k not in {"exercise_years", "exercise_prices"}
    }
    out = run(calculation="oas", price=price, **plain)
    assert math.isclose(out.oas, spread, abs_tol=1e-9)


@pytest.mark.invariant("fixed_income.interest_rate_tree", "oas_falls_as_price_rises")
@settings(deadline=None)
@given(
    bond=bonds(),
    low=st.floats(min_value=85.0, max_value=110.0),
    rise=st.floats(min_value=0.0, max_value=10.0),
    option=st.sampled_from(["call", "put"]),
)
def test_a_higher_price_never_raises_the_oas(
    bond: dict[str, Any], low: float, rise: float, option: str
) -> None:
    assume(not _negative_forwards(bond))
    try:
        cheap = run(calculation="oas", price=low, option=option, **bond).oas
        dear = run(calculation="oas", price=low + rise, option=option, **bond).oas
    except ConvergenceError:
        reject()  # a price no spread in [-0.5, 1] reaches
    assert dear <= cheap + 1e-12


# --- oracles -------------------------------------------------------------------


def _kwf_tree(par: list[float], sigma: float, m: int) -> list[list[float]]:
    """Calibrate as KWF do: bisect each lowest rate until the par bond is at par."""
    step = 1 / m
    ratio = math.exp(2 * sigma * math.sqrt(step))
    tree: list[list[float]] = []

    def value(rows: list[list[float]], coupon: float) -> float:
        n = len(rows)
        values = [100.0] * (n + 1)
        for t in range(n - 1, -1, -1):
            values = [
                0.5
                * (values[j] + values[j + 1] + 2 * coupon * step * 100)
                / (1 + rows[t][j] * step)
                for j in range(t + 1)
            ]
        return values[0]

    for t, coupon in enumerate(par):
        low, high = 0.0, 1.0
        for _ in range(200):
            mid = (low + high) / 2
            trial = [*tree, [mid * ratio**j for j in range(t + 1)]]
            if value(trial, coupon) > 100.0:
                low = mid
            else:
                high = mid
        tree.append([(low + high) / 2 * ratio**j for j in range(t + 1)])
    return tree


@pytest.mark.oracle("fixed_income.interest_rate_tree")
@settings(deadline=None, max_examples=40)
@given(curve=curves())
def test_calibration_agrees_with_kwf_backward_induction(curve: dict[str, Any]) -> None:
    assume(not _negative_forwards(curve))
    m = PERIODS[curve["frequency"]]
    years = curve["curve_tenors"][-1]
    assume(years * m <= 24)
    out = run(calculation="calibrate", years=years, **curve)
    par = list(out.par_yields)
    oracle = _kwf_tree(par, curve["volatility"], m)
    for ours, theirs in zip(out.node_rates, oracle, strict=True):
        for a, b in zip(ours, theirs, strict=True):
            assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-11)


def _quantlib_value(par: list[float], coupon: float, years: int) -> float:
    """Bootstrap annual par bonds in QuantLib and price an annual bond off them."""
    today = ql.Date(15, 6, 2026)
    ql.Settings.instance().evaluationDate = today
    counter = ql.Thirty360(ql.Thirty360.BondBasis)
    helpers = []
    for k, rate in enumerate(par, start=1):
        schedule = ql.Schedule(
            today,
            today + ql.Period(k, ql.Years),
            ql.Period(ql.Annual),
            ql.NullCalendar(),
            ql.Unadjusted,
            ql.Unadjusted,
            ql.DateGeneration.Backward,
            False,  # noqa: FBT003 - QuantLib's end-of-month flag is positional
        )
        helpers.append(
            ql.FixedRateBondHelper(
                ql.QuoteHandle(ql.SimpleQuote(100.0)),
                0,
                100.0,
                schedule,
                [rate],
                counter,
            )
        )
    curve = ql.PiecewiseLogLinearDiscount(today, helpers, counter)
    schedule = ql.Schedule(
        today,
        today + ql.Period(years, ql.Years),
        ql.Period(ql.Annual),
        ql.NullCalendar(),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False,  # noqa: FBT003 - QuantLib's end-of-month flag is positional
    )
    bond = ql.FixedRateBond(0, 100.0, schedule, [coupon], counter)
    bond.setPricingEngine(ql.DiscountingBondEngine(ql.YieldTermStructureHandle(curve)))
    return float(bond.NPV())


@pytest.mark.oracle("fixed_income.interest_rate_tree")
@settings(deadline=None, max_examples=40)
@given(
    curve=curves(),
    coupon=st.floats(min_value=0.0, max_value=0.1),
    data=st.data(),
)
def test_an_option_free_value_agrees_with_quantlib(
    curve: dict[str, Any], coupon: float, data: st.DataObject
) -> None:
    curve = {**curve, "frequency": "annual"}
    assume(not _negative_forwards(curve))
    years = data.draw(st.integers(min_value=1, max_value=len(curve["curve_tenors"])))
    out = run(
        calculation="value", maturity_years=float(years), coupon_rate=coupon, **curve
    )
    expected = _quantlib_value(list(curve["par_yields"]), coupon, years)
    assert math.isclose(out.value, expected, rel_tol=1e-9)


# --- details and refusals ------------------------------------------------------


def test_the_kwf_tree_and_bonds() -> None:
    tree = run(calculation="calibrate", years=3.0, **KWF)
    assert [round(r, 7) for r in tree.node_rates[2]] == [
        0.0452959,
        0.0553246,
        0.0675736,
    ]
    oas = run(
        calculation="oas",
        option="call",
        exercise_years=[1.0, 2.0],
        exercise_prices=[100.0, 100.0],
        price=101.0,
        **KWF,
        **KWF_BOND,
    )
    assert math.isclose(oas.oas, 0.0023146500901, abs_tol=1e-10)
    assert math.isclose(oas.model_value, 101.43066758719, abs_tol=1e-9)


def test_effective_duration_and_convexity_follow_kwf() -> None:
    # KWF (1993, p. 45) give the formulas, not numbers: these come from an
    # independent implementation of their tree (shifting the par curve and
    # recalibrating, a shift of one basis point), written for this step's research.
    out = run(calculation="effective", shift=0.0001, **KWF, **KWF_BOND)
    assert math.isclose(out.effective_duration, 2.748411, abs_tol=5e-6)
    assert math.isclose(out.effective_convexity, 10.4004, abs_tol=5e-3)
    assert out.value_down > out.value > out.value_up


@pytest.mark.parametrize(
    ("frequency", "volatility", "years"),
    [
        ("semiannual", 0.5, 30.0),
        ("quarterly", 0.5, 30.0),
        ("quarterly", 0.3, 30.0),
        ("monthly", 0.5, 10.0),
    ],
)
def test_a_long_volatile_tree_still_prices_its_par_bond_at_par(
    frequency: str, volatility: float, years: float
) -> None:
    # Its lowest rates fall below 1e-9: the calibration solves them to relative
    # precision, so the par bond stays at par (an absolute tolerance missed it by
    # 4e-5, and quarterly at 50% reported a negative forward rate it has not).
    coupon = float(np.interp(years, [1.0, 30.0], [0.03, 0.05]))
    out = run(
        calculation="value",
        curve_tenors=[1.0, 30.0],
        par_yields=[0.03, 0.05],
        volatility=volatility,
        frequency=frequency,
        maturity_years=years,
        coupon_rate=coupon,
    )
    assert math.isclose(out.value, 100.0, rel_tol=1e-12)


def test_a_down_shift_through_zero_names_the_shifted_curve() -> None:
    near_zero = {
        "curve_tenors": [1 / 12, 0.25, 0.5, 1.0, 2.0],
        "par_yields": [0.0009, 0.0009, 0.0009, 0.001, 0.0011],
        "volatility": 0.1,
        "maturity_years": 2.0,
        "coupon_rate": 0.002,
    }
    with pytest.raises(DomainError, match=r"shifted by -0.001"):
        run(calculation="effective", **near_zero)
    out = run(calculation="effective", shift=0.0002, **near_zero)
    assert out.effective_duration > 0


def test_zero_volatility_holds_the_forward_rates() -> None:
    out = run(calculation="calibrate", years=3.0, **{**KWF, "volatility": 0.0})
    assert out.rate_ratio == 1.0
    assert all(len(set(row)) == 1 for row in out.node_rates)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"par_yields": [0.03, 0.04]}, "one par yield per tenor"),
        ({"curve_tenors": [2.0, 1.0, 3.0]}, "strictly increasing"),
        ({"maturity_years": 4.0}, "beyond the par curve"),
        ({"maturity_years": 2.5}, "whole number"),
        ({"option": "call"}, "needs exercise dates"),
        (
            {"option": "call", "exercise_years": [3.0], "exercise_prices": [100.0]},
            "not before maturity",
        ),
        (
            {
                "option": "put",
                "exercise_years": [2.0, 1.0],
                "exercise_prices": [100.0, 100.0],
            },
            "strictly increasing",
        ),
        (
            {
                "option": "put",
                "exercise_years": [1.0],
                "exercise_prices": [100.0, 100.0],
            },
            "one exercise price",
        ),
    ],
    ids=[
        "lengths",
        "tenors",
        "beyond",
        "fraction",
        "no_dates",
        "at_maturity",
        "dates_order",
        "prices",
    ],
)
def test_inconsistent_bonds_are_refused(changes: dict[str, Any], message: str) -> None:
    inputs = {"calculation": "value", **KWF, **KWF_BOND, **changes}
    with pytest.raises(InputError, match=message):
        run_model(interest_rate_tree, inputs)


def test_a_tree_too_long_is_refused() -> None:
    with pytest.raises(InputError, match="at most 120"):
        run_model(
            interest_rate_tree,
            {
                "calculation": "calibrate",
                "curve_tenors": [30.0],
                "par_yields": [0.04],
                "volatility": 0.1,
                "frequency": "monthly",
                "years": 30.0,
            },
        )


def test_a_negative_forward_is_refused() -> None:
    with pytest.raises(DomainError, match="negative forward"):
        run(
            calculation="calibrate",
            curve_tenors=[1.0, 2.0],
            par_yields=[0.06, 0.0],
            volatility=0.1,
            frequency="annual",
            years=2.0,
        )


def test_node_rates_beyond_ten_are_refused_only_where_reported() -> None:
    curve = {
        "curve_tenors": [1.0, 30.0],
        "par_yields": [0.04, 0.06],
        "volatility": 0.5,
        "frequency": "annual",
    }
    out = run(calculation="value", maturity_years=30.0, coupon_rate=0.06, **curve)
    assert math.isclose(out.value, 100.0, rel_tol=1e-12)
    with pytest.raises(DomainError, match="exceed"):
        run(
            calculation="calibrate",
            curve_tenors=[1.0, 30.0],
            par_yields=[0.04, 0.06],
            volatility=0.5,
            frequency="annual",
            years=30.0,
        )


def test_a_price_no_spread_reaches_is_refused() -> None:
    with pytest.raises(ConvergenceError, match="no spread"):
        run(calculation="oas", price=1e6, **KWF, **KWF_BOND)
