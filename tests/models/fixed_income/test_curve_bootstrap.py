# tests/models/fixed_income/test_curve_bootstrap.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``fixed_income.curve_bootstrap``: its invariants, QuantLib as an oracle, refusals.

The oracle is a QuantLib discount curve bootstrapped (``PiecewiseLogLinearDiscount``)
from par bonds (``FixedRateBondHelper`` at a clean price of 100) with the same
coupons and maturities: each bond's flows fall on the curve's nodes, so the
interpolation never enters and the discount factors must agree.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813 - oracle docs use ql
from hypothesis import given, reject, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.fixed_income import curve_bootstrap

PAR = st.floats(min_value=0.0, max_value=0.12)
PERIODS = {"annual": 1, "semiannual": 2, "quarterly": 4, "monthly": 12}
QL_FREQUENCY = {
    "annual": ql.Annual,
    "semiannual": ql.Semiannual,
    "quarterly": ql.Quarterly,
    "monthly": ql.Monthly,
}


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(curve_bootstrap, inputs).outputs


def par_curves(max_size: int = 40) -> st.SearchStrategy[list[float]]:
    """Smooth par curves: a start and small steps, so every factor is positive."""
    return st.tuples(
        PAR, st.lists(st.floats(min_value=-0.004, max_value=0.004), max_size=max_size)
    ).map(
        lambda t: [
            min(max(t[0] + sum(t[1][:k]), 0.0), 0.2) for k in range(len(t[1]) + 1)
        ]
    )


@pytest.mark.invariant("fixed_income.curve_bootstrap", "flat_curve_is_invariant")
@given(
    level=st.floats(min_value=-0.05, max_value=0.5),
    size=st.integers(min_value=1, max_value=120),
    frequency=st.sampled_from(list(PERIODS)),
)
def test_a_flat_par_curve_bootstraps_to_itself(
    level: float, size: int, frequency: str
) -> None:
    result = run(calculation="from_par", par_yields=[level] * size, frequency=frequency)
    for spot, forward in zip(result.spot_rates, result.forward_rates, strict=True):
        assert math.isclose(spot, level, rel_tol=1e-9, abs_tol=1e-12)
        assert math.isclose(forward, level, rel_tol=1e-9, abs_tol=1e-12)


@pytest.mark.invariant(
    "fixed_income.curve_bootstrap", "bootstrapped_curve_reprices_par_bonds"
)
@given(par=par_curves(), frequency=st.sampled_from(list(PERIODS)))
def test_the_curve_reprices_every_par_bond(par: list[float], frequency: str) -> None:
    m = PERIODS[frequency]
    try:
        factors = run(
            calculation="from_par", par_yields=par, frequency=frequency
        ).discount_factors
    except DomainError:
        # A steep long end can bootstrap a factor below zero (6.25% for 36
        # years, then 6.64% and 7.03%): refused, as the limitations say.
        reject()
    for k, coupon in enumerate(par, start=1):
        value = coupon / m * math.fsum(factors[:k]) + factors[k - 1]
        assert math.isclose(value, 1.0, rel_tol=1e-12)


@pytest.mark.invariant("fixed_income.curve_bootstrap", "forwards_compose_to_spots")
@given(
    par=par_curves(),
    frequency=st.sampled_from(list(PERIODS)),
    compounding=st.sampled_from(["periodic", "continuous"]),
)
def test_the_forwards_compound_to_the_spot_rates(
    par: list[float], frequency: str, compounding: str
) -> None:
    m = PERIODS[frequency]
    result = run(
        calculation="from_par",
        par_yields=par,
        frequency=frequency,
        compounding=compounding,
    )
    log_growth = 0.0
    for k, (spot, forward) in enumerate(
        zip(result.spot_rates, result.forward_rates, strict=True), start=1
    ):
        if compounding == "periodic":
            log_growth += math.log1p(forward / m)
            assert math.isclose(
                log_growth, k * math.log1p(spot / m), rel_tol=1e-9, abs_tol=1e-12
            )
        else:
            log_growth += forward / m
            assert math.isclose(log_growth, k / m * spot, rel_tol=1e-9, abs_tol=1e-12)


@pytest.mark.invariant("fixed_income.curve_bootstrap", "discount_factors_positive")
@given(par=st.lists(st.floats(min_value=-0.1, max_value=1.0), min_size=1, max_size=30))
def test_every_discount_factor_returned_is_positive(par: list[float]) -> None:
    try:
        result = run(calculation="from_par", par_yields=par)
    except DomainError:
        return  # refused, as the limitations say, rather than a factor <= 0
    assert all(d > 0 for d in result.discount_factors)


# --- QuantLib as an oracle -------------------------------------------------------


@pytest.mark.oracle("fixed_income.curve_bootstrap")
@settings(deadline=None)
@given(
    par=par_curves(max_size=30),
    frequency=st.sampled_from(["annual", "semiannual", "quarterly"]),
)
def test_the_bootstrap_agrees_with_a_quantlib_curve(
    par: list[float], frequency: str
) -> None:
    today = ql.Date(15, 1, 2026)
    ql.Settings.instance().evaluationDate = today
    tenor = ql.Period(QL_FREQUENCY[frequency])
    day_count = ql.ActualActual(ql.ActualActual.ISMA)
    helpers = []
    for k, coupon in enumerate(par, start=1):
        maturity = today + ql.Period(12 // PERIODS[frequency] * k, ql.Months)
        schedule = ql.Schedule(
            today,
            maturity,
            tenor,
            ql.NullCalendar(),
            ql.Unadjusted,
            ql.Unadjusted,
            ql.DateGeneration.Backward,
            False,  # noqa: FBT003 - QuantLib's positional end-of-month flag
        )
        helpers.append(
            ql.FixedRateBondHelper(
                ql.QuoteHandle(ql.SimpleQuote(100.0)),
                0,
                100.0,
                schedule,
                [coupon],
                day_count,
            )
        )
    curve = ql.PiecewiseLogLinearDiscount(today, helpers, day_count)
    ours = run(calculation="from_par", par_yields=par, frequency=frequency)
    for k, factor in enumerate(ours.discount_factors, start=1):
        node = today + ql.Period(12 // PERIODS[frequency] * k, ql.Months)
        assert math.isclose(factor, curve.discount(node), rel_tol=1e-10)


# --- cases with exact answers and documented refusals ----------------------------


def test_the_par_yield_of_a_zero_curve() -> None:
    # Hull (2018), chapter 4: zero rates of 5.0, 5.8, 6.4 and 6.8% (continuous) at
    # half-year tenors give a two-year par yield of 6.87% (semiannual coupons).
    result = run(
        calculation="from_spot",
        spot_rates=[0.05, 0.058, 0.064, 0.068],
        compounding="continuous",
    )
    assert abs(result.par_yields[-1] - 0.0687) < 5e-5


def test_from_spot_inverts_from_par() -> None:
    par = [0.02, 0.025, 0.03, 0.032, 0.035]
    spots = run(calculation="from_par", par_yields=par).spot_rates
    back = run(calculation="from_spot", spot_rates=list(spots)).par_yields
    for a, b in zip(back, par, strict=True):
        assert math.isclose(a, b, rel_tol=1e-12)


@pytest.mark.parametrize(
    "inputs",
    [
        {
            "calculation": "from_par",
            "par_yields": [0.0, 0.999999],
            "frequency": "annual",
        },
        {"calculation": "from_par", "par_yields": [0.0, 1.0], "frequency": "annual"},
        {
            "calculation": "forward_rate",
            "near_rate": 1.0,
            "near_years": 99.0,
            "far_rate": -0.1,
            "far_years": 100.0,
        },
    ],
)
def test_curves_with_no_representable_rate_are_refused(inputs: dict[str, Any]) -> None:
    with pytest.raises(DomainError):
        run(**inputs)


@pytest.mark.parametrize(
    ("near", "near_years", "far", "far_years", "frequency"),
    [(0.0, 99.99, 0.7864, 100.0, "quarterly"), (-0.1, 50.0, 1.0, 50.01, "annual")],
)
def test_a_forward_over_a_short_span_is_refused_not_overflowed(
    near: float, near_years: float, far: float, far_years: float, frequency: str
) -> None:
    # Found by the Step 8 review: the ratio of factors overflowed math.pow.
    with pytest.raises(DomainError):
        run(
            calculation="forward_rate",
            near_rate=near,
            near_years=near_years,
            far_rate=far,
            far_years=far_years,
            frequency=frequency,
        )


def test_a_forward_must_run_forward() -> None:
    with pytest.raises(InputError, match="far maturity"):
        run(
            calculation="forward_rate",
            near_rate=0.03,
            near_years=2.0,
            far_rate=0.04,
            far_years=1.0,
        )
