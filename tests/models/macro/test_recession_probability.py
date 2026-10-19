# tests/models/macro/test_recession_probability.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.recession_probability``: monotone in the spread, one half at -84 bp."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from scipy.stats import norm

from pyeconomics.core import run_model
from pyeconomics.models.macro import recession_probability
from pyeconomics.models.macro.recession_probability import INTERCEPT, SLOPE

YIELDS = st.floats(-0.05, 0.5)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return run_model(recession_probability, inputs).outputs


@pytest.mark.invariant(
    "macro.recession_probability", "probability_falls_as_spread_rises"
)
@given(
    long_a=YIELDS,
    long_b=YIELDS,
    bill=YIELDS,
    basis=st.sampled_from(["bond_equivalent", "discount"]),
)
def test_a_higher_long_yield_never_raises_the_probability(
    long_a: float, long_b: float, bill: float, basis: str
) -> None:
    low, high = sorted((long_a, long_b))
    flatter = run(ten_year_yield=low, three_month_yield=bill, bill_basis=basis)
    steeper = run(ten_year_yield=high, three_month_yield=bill, bill_basis=basis)
    assert steeper.probability <= flatter.probability


@pytest.mark.invariant(
    "macro.recession_probability", "probability_is_one_half_at_the_threshold"
)
@given(bill=st.floats(0.0, 0.2))
def test_the_probability_is_one_half_at_the_threshold(bill: float) -> None:
    spread = -INTERCEPT / SLOPE / 100
    outputs = run(ten_year_yield=bill + spread, three_month_yield=bill)
    assert outputs.probability == pytest.approx(0.5, abs=1e-12)


@pytest.mark.parametrize("spread_points", [-3.5, -1.71, 0.0, 0.955, 3.69])
def test_scipy_normal_cdf_agrees(spread_points: float) -> None:
    outputs = run(ten_year_yield=0.04 + spread_points / 100, three_month_yield=0.04)
    expected = norm.cdf(-0.5333 - 0.6330 * spread_points)
    assert outputs.probability == pytest.approx(expected, rel=1e-12, abs=1e-15)


def test_a_discount_rate_is_put_on_a_bond_equivalent_basis() -> None:
    outputs = run(
        ten_year_yield=0.0499, three_month_yield=0.0394, bill_basis="discount"
    )
    expected = 365 * 0.0394 / (360 - 91 * 0.0394)
    assert outputs.bill_bond_equivalent == pytest.approx(expected, rel=1e-15)
    assert outputs.spread == pytest.approx(0.0499 - expected, rel=1e-13)
