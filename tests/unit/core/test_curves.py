# tests/unit/core/test_curves.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Zero-curve interpolation, discount factors, forward and par rates."""

from __future__ import annotations

import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from pyeconomics.core import (
    Compounding,
    DomainError,
    Frequency,
    InputError,
    curve_discount_factors,
    discount_factor,
    forward_rate,
    interpolate_rate,
    interpolate_rates,
    par_rate,
)

TENORS = (0.5, 1.0, 2.0, 5.0)
RATES = (0.01, 0.02, 0.03, 0.035)


def test_interpolation_is_linear_between_nodes_and_flat_outside() -> None:
    assert interpolate_rate(TENORS, RATES, 0.1) == 0.01
    assert interpolate_rate(TENORS, RATES, 0.5) == 0.01
    assert interpolate_rate(TENORS, RATES, 1.5) == pytest.approx(0.025)
    assert interpolate_rate(TENORS, RATES, 3.5) == pytest.approx(0.0325)
    assert interpolate_rate(TENORS, RATES, 5.0) == 0.035
    assert interpolate_rate(TENORS, RATES, 50.0) == 0.035
    assert interpolate_rate((1.0,), (0.04,), 7.0) == 0.04


@given(time=st.floats(min_value=0.0, max_value=10.0))
def test_an_interpolated_rate_lies_between_its_neighbours(time: float) -> None:
    rate = interpolate_rate(TENORS, RATES, time)
    assert min(RATES) <= rate <= max(RATES)


@pytest.mark.parametrize(
    ("tenors", "rates", "time", "message"),
    [
        ((), (), 1.0, "at least one node"),
        ((1.0, 2.0), (0.01,), 1.0, "one rate per tenor"),
        ((0.0, 1.0), (0.01, 0.02), 1.0, "positive"),
        ((2.0, 1.0), (0.01, 0.02), 1.0, "strictly increasing"),
        ((1.0, 1.0), (0.01, 0.02), 1.0, "strictly increasing"),
        ((1.0,), (math.nan,), 1.0, "finite"),
        ((1.0,), (0.01,), math.inf, "time must be finite"),
    ],
)
def test_bad_nodes_are_refused(
    tenors: tuple[float, ...], rates: tuple[float, ...], time: float, message: str
) -> None:
    with pytest.raises(InputError, match=message):
        interpolate_rate(tenors, rates, time)


def test_discount_factors_come_off_the_interpolated_curve() -> None:
    factors = curve_discount_factors(
        TENORS, RATES, (0.0, 1.5, 10.0), Compounding.CONTINUOUS
    )
    assert factors[0] == 1.0
    assert factors[1] == pytest.approx(math.exp(-0.025 * 1.5))
    assert factors[2] == pytest.approx(math.exp(-0.035 * 10.0))
    periodic = curve_discount_factors(
        TENORS, RATES, (2.0,), Compounding.PERIODIC, Frequency.SEMIANNUAL
    )
    assert periodic[0] == pytest.approx(1.015**-4)


@given(
    near=st.floats(min_value=-0.05, max_value=0.2),
    far=st.floats(min_value=-0.05, max_value=0.2),
    t1=st.floats(min_value=0.0, max_value=30.0),
    gap=st.floats(min_value=0.01, max_value=30.0),
    compounding=st.sampled_from(list(Compounding)),
)
def test_forwards_link_the_two_discount_factors(
    near: float, far: float, t1: float, gap: float, compounding: Compounding
) -> None:
    frequency = Frequency.QUARTERLY if compounding is Compounding.PERIODIC else None
    t2 = t1 + gap
    try:
        forward = forward_rate(near, t1, far, t2, compounding, frequency=frequency)
        d1 = discount_factor(near, t1, compounding, frequency)
        d2 = discount_factor(far, t2, compounding, frequency)
        df = discount_factor(forward, gap, compounding, frequency)
    except DomainError:
        return  # a simple rate whose factor is not positive
    # A forward within a hair of -100% a period (1 + r/m near 0) cannot carry
    # its factor's digits: one ulp of r moves it by eps / (1 + r/m). Found when
    # CI drew a quarterly forward 9e-10 above -400% (Phase 2 Step 9).
    growth = 1 + forward / 4 if frequency is not None else 1 + forward * gap
    assume(compounding is Compounding.CONTINUOUS or growth > 1e-6)
    assert math.isclose(d1 * df, d2, rel_tol=1e-9)


def test_a_short_periodic_forward_keeps_its_digits_and_never_overflows() -> None:
    for span in (1e-6, 1e-14, 1e-17):
        rate = forward_rate(
            0.03, 0.0, 0.05, span, Compounding.PERIODIC, frequency=Frequency.ANNUAL
        )
        assert rate == pytest.approx(0.05, rel=1e-9)
    simple = forward_rate(0.03, 1.0, 0.04, 2.0, Compounding.SIMPLE)
    assert simple == pytest.approx((1.08 / 1.03 - 1) / 1.0)
    with pytest.raises(DomainError, match="overflows"):
        forward_rate(
            -0.99,
            50.0,
            10.0,
            50.0 + 1e-6,
            Compounding.PERIODIC,
            frequency=Frequency.ANNUAL,
        )


def test_interpolating_many_times_checks_the_nodes_once() -> None:
    assert interpolate_rates(TENORS, RATES, (0.1, 1.5, 50.0)) == [
        interpolate_rate(TENORS, RATES, t) for t in (0.1, 1.5, 50.0)
    ]
    with pytest.raises(InputError, match="strictly increasing"):
        interpolate_rates((2.0, 1.0), (0.01, 0.02), ())


def test_a_continuous_forward_is_exact_in_rates() -> None:
    assert forward_rate(0.03, 1.0, 0.04, 2.0, Compounding.CONTINUOUS) == 0.05
    assert forward_rate(0.0, 0.0, 0.04, 2.0, Compounding.CONTINUOUS) == 0.04


@pytest.mark.parametrize(
    ("t1", "t2"), [(1.0, 1.0), (2.0, 1.0), (-1.0, 1.0), (math.nan, 1.0)]
)
def test_a_forward_must_run_forward_from_now(t1: float, t2: float) -> None:
    with pytest.raises(InputError):
        forward_rate(0.03, t1, 0.04, t2, Compounding.CONTINUOUS)


def test_the_par_rate_prices_a_bond_at_par() -> None:
    factors = [1.02**-k for k in range(1, 11)]
    rate = par_rate(factors, [1.0] * 10)
    assert rate == pytest.approx(0.02)
    assert rate * sum(factors) + factors[-1] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("factors", "accruals", "message"),
    [
        ((), (), "at least one"),
        ((0.9,), (1.0, 1.0), "one accrual"),
        ((0.0,), (1.0,), "discount factors"),
        ((0.9,), (0.0,), "accrual fractions"),
        ((math.inf,), (1.0,), "discount factors"),
    ],
)
def test_bad_par_inputs_are_refused(
    factors: tuple[float, ...], accruals: tuple[float, ...], message: str
) -> None:
    with pytest.raises(InputError, match=message):
        par_rate(factors, accruals)
