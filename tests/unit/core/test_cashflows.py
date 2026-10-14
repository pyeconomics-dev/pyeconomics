# tests/unit/core/test_cashflows.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Cash-flow discounting: factors, present values and the IRR.

The functions never raise on overflow (a factor too large is infinity) and
refuse inputs outside their domain with ``InputError``.
"""

from __future__ import annotations

import math
import warnings

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from pyeconomics.core import (
    DomainError,
    InputError,
    ModelWarning,
    accumulated_annuity_factor,
    accumulated_growing_annuity_factor,
    annuity_factor,
    collect_warnings,
    growing_annuity_factor,
    growing_perpetuity_factor,
    growth_factor,
    internal_rate_of_return,
    present_value,
    present_value_factor,
    sign_changes,
)

RATES = st.floats(min_value=-0.9, max_value=1.0)
PERIODS = st.floats(min_value=0.0, max_value=300.0)


@pytest.mark.parametrize(
    ("rate", "periods"),
    [(-1.0, 1.0), (math.nan, 1.0), (0.1, -1.0), (0.1, math.inf)],
    ids=["rate_at_minus_one", "rate_nan", "negative_periods", "infinite_periods"],
)
def test_a_rate_or_period_outside_the_domain_is_refused(
    rate: float, periods: float
) -> None:
    for function in (
        growth_factor,
        annuity_factor,
        accumulated_annuity_factor,
        present_value_factor,
    ):
        with pytest.raises(InputError):
            function(rate, periods)


def test_factors_that_overflow_are_infinite() -> None:
    assert growth_factor(1.0, 2000) == math.inf
    assert present_value_factor(-0.99, 200) == math.inf
    assert annuity_factor(-0.99, 200) == math.inf
    assert accumulated_annuity_factor(1.0, 2000) == math.inf
    assert growing_annuity_factor(0.0, 1.0, 2000) == math.inf
    assert accumulated_growing_annuity_factor(1.0, 0.0, 2000) == math.inf


def test_zero_rate_and_zero_growth_limits() -> None:
    assert annuity_factor(0.0, 7.5) == 7.5
    assert accumulated_annuity_factor(0.0, 7.5, due=True) == 7.5
    assert growing_annuity_factor(0.1, 0.1, 4, due=True) == 4.0
    assert accumulated_growing_annuity_factor(0.0, 0.0, 3) == 3.0


def test_a_perpetuity_needs_a_rate_above_its_growth() -> None:
    assert growing_perpetuity_factor(0.1, due=True) == pytest.approx(11.0)
    with pytest.raises(DomainError, match="above its growth rate"):
        growing_perpetuity_factor(0.03, 0.03)


@given(rate=RATES, periods=PERIODS)
def test_accumulated_is_the_annuity_factor_compounded(
    rate: float, periods: float
) -> None:
    grown = growth_factor(rate, periods)
    later = accumulated_annuity_factor(rate, periods)
    now = annuity_factor(rate, periods)
    if math.isfinite(grown) and grown < 1e200 and now < 1e200:
        assert math.isclose(later, now * grown, rel_tol=1e-9, abs_tol=1e-12)


@given(rate=RATES, growth=RATES, periods=st.floats(min_value=0.0, max_value=60.0))
def test_the_growing_factors_are_symmetric_in_the_two_rates(
    rate: float, growth: float, periods: float
) -> None:
    one = accumulated_growing_annuity_factor(rate, growth, periods)
    other = accumulated_growing_annuity_factor(growth, rate, periods)
    assert math.isclose(one, other, rel_tol=1e-9, abs_tol=1e-12)


@pytest.mark.parametrize(
    ("flows", "times"),
    [([1.0, math.nan], None), ([[1.0], [2.0]], None), ([1.0, 2.0], [0.0])],
    ids=["nan_flow", "two_dimensional", "times_of_another_length"],
)
def test_bad_cash_flows_are_refused(
    flows: list[object], times: list[float] | None
) -> None:
    with pytest.raises(InputError):
        present_value(0.1, flows, times)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_present_values_of_nothing_are_zero() -> None:
    assert present_value(0.1, []) == 0.0
    assert present_value(0.1, [0.0, 0.0]) == 0.0
    assert present_value(-0.99, [0.0] * 500 + [0.0]) == 0.0


def test_a_present_value_beyond_a_float_is_infinite_with_its_sign() -> None:
    flows = [0.0] * 300 + [-1e12]
    assert present_value(-0.99, flows) == -math.inf


def test_a_finite_value_behind_an_infinite_factor_is_summed_in_log_space() -> None:
    # The discount factor 100^160 = 1e320 overflows a float; the value of a
    # flow of 1e-300 at that time, 1e20, does not.
    value = present_value(-0.99, [1e-300], [160.0])
    assert math.isclose(math.log10(value), 20.0, rel_tol=1e-12)


def test_the_irr_of_flows_that_never_change_sign_is_undefined() -> None:
    with collect_warnings() as recorded:
        assert internal_rate_of_return([0.0, 0.0]) is None
    assert [w.code for w in recorded] == ["no_sign_change"]


def test_the_irr_warns_outside_a_run() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert internal_rate_of_return([-1.0, 1000.0]) is None
    assert [w.message.code for w in caught if isinstance(w.message, ModelWarning)] == [
        "no_root_in_range"
    ]


def test_the_irr_of_dated_flows_uses_their_times() -> None:
    irr = internal_rate_of_return([-100.0, 121.0], [0.0, 2.0])
    assert irr is not None
    assert math.isclose(irr, 0.1, rel_tol=1e-12)


def test_the_irr_bracket_is_checked() -> None:
    with pytest.raises(InputError):
        internal_rate_of_return([-1.0, 2.0], lower=-1.5)


def test_sign_changes_ignore_zeros() -> None:
    assert sign_changes([]) == 0
    assert sign_changes([0.0, -1.0, 0.0, 0.0, 2.0, -3.0]) == 2


@pytest.mark.parametrize(
    ("flows", "expected"), [([-100, 1], -0.99), ([-1e6, 11e6], 10.0)]
)
@pytest.mark.parametrize("scale", [1e-100, 1e-10, 1.0, 100.0, 1e100])
def test_irr_endpoint_roots_survive_rescaling(
    flows: list[float], expected: float, scale: float
) -> None:
    with collect_warnings() as recorded:
        found = internal_rate_of_return([c * scale for c in flows])
    assert found == expected
    assert not recorded


@pytest.mark.parametrize("rate", [-0.99000001, 10.00000001, -0.999, 11.0])
def test_irr_does_not_invent_roots_outside_the_bracket(rate: float) -> None:
    with collect_warnings() as recorded:
        found = internal_rate_of_return([-100.0, 100.0 * (1 + rate)])
    assert found is None
    assert [w.code for w in recorded] == ["no_root_in_range"]


@settings(deadline=None)
@given(
    rate=st.floats(-0.99, 10.0), outlay=st.floats(1.0, 1e8), periods=st.integers(1, 5)
)
@example(rate=-0.99, outlay=100.0, periods=1)
@example(rate=10.0, outlay=1e6, periods=1)
@example(rate=-0.99, outlay=1e8, periods=5)
@example(rate=10.0, outlay=1.0, periods=5)
def test_irr_recovers_a_chosen_rate(rate: float, outlay: float, periods: int) -> None:
    # Single future receipt: -P + P(1+r)^n/(1+r)^n = 0.
    flows = [-outlay, *([0.0] * (periods - 1)), outlay * (1 + rate) ** periods]
    with collect_warnings() as recorded:
        found = internal_rate_of_return(flows)
    assert found is not None
    assert math.isclose(found, rate, abs_tol=3e-12, rel_tol=2e-15)
    assert not recorded
