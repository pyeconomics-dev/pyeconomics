# tests/models/derivatives/test_forwards.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``derivatives.forwards``: its invariants and refusals.

The forward price is a closed form no oracle library adds to; the golden file
holds it to Hull's worked examples and to identities, and
``tests/models/international/test_parity_conditions.py`` holds the currency
forward to ``international.parity_conditions``.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
from hypothesis import assume, given, reject
from hypothesis import strategies as st

from pyeconomics.core import DomainError, run_model
from pyeconomics.models.derivatives import forwards

CARRY = {
    "spot": st.floats(min_value=0.01, max_value=1e6),
    "years": st.floats(min_value=0.0, max_value=50.0),
    "risk_free_rate": st.floats(min_value=-0.1, max_value=0.3),
    "income_yield": st.floats(min_value=-0.1, max_value=0.3),
    "storage_cost_rate": st.floats(min_value=0.0, max_value=0.3),
    "convenience_yield": st.floats(min_value=0.0, max_value=0.3),
    "storage_cost_present_value": st.floats(min_value=0.0, max_value=1e3),
}
MONEY_MARKET = st.floats(min_value=-0.05, max_value=1.0)
DAY_COUNTS = st.sampled_from(["act_360", "act_365_fixed"])


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(forwards, inputs).outputs


@pytest.mark.invariant("derivatives.forwards", "forward_value_zero_at_inception")
@given(
    position=st.sampled_from(["long", "short"]),
    income_share=st.floats(min_value=0.0, max_value=1.0),
    **CARRY,
)
def test_a_forward_at_todays_forward_price_is_worth_zero(
    position: str, income_share: float, **carry: float
) -> None:
    carry["income_present_value"] = income_share * carry["spot"]
    try:
        forward = run(calculation="cost_of_carry", **carry).forward_price
    except DomainError:
        reject()  # a forward price past 1e15: refused, tested below
    assume(forward <= 1e9)
    value = run(
        calculation="forward_value",
        delivery_price=forward,
        position=position,
        **carry,
    )
    assert value.forward_price == forward
    assert value.value == 0.0


@pytest.mark.invariant("derivatives.forwards", "fx_forward_matches_parity")
@given(
    spot=st.floats(min_value=1e-6, max_value=1e6),
    days=st.integers(min_value=1, max_value=3653),
    quote_rate=MONEY_MARKET,
    base_rate=MONEY_MARKET,
    quote_day_count=DAY_COUNTS,
    base_day_count=DAY_COUNTS,
)
def test_the_currency_forward_is_covered_interest_parity(  # noqa: PLR0913
    *,
    spot: float,
    days: int,
    quote_rate: float,
    base_rate: float,
    quote_day_count: str,
    base_day_count: str,
) -> None:
    result = run(
        calculation="fx_forward",
        spot=spot,
        days=days,
        quote_rate=quote_rate,
        base_rate=base_rate,
        quote_day_count=quote_day_count,
        base_day_count=base_day_count,
    )
    basis = {"act_360": 360, "act_365_fixed": 365}
    quote_growth = 1 + quote_rate * days / basis[quote_day_count]
    base_growth = 1 + base_rate * days / basis[base_day_count]
    assert math.isclose(
        result.forward_rate * base_growth, spot * quote_growth, rel_tol=1e-14
    )
    assert math.isclose(
        result.forward_points, result.forward_rate - spot, abs_tol=1e-15 * spot
    )
    assert math.isclose(
        result.forward_premium, result.forward_rate / spot - 1, abs_tol=1e-14
    )


def test_the_short_side_is_worth_the_negative_of_the_long() -> None:
    common = {
        "calculation": "forward_value",
        "spot": 100.0,
        "years": 1.0,
        "risk_free_rate": 0.05,
        "income_yield": 0.02,
        "delivery_price": 95.0,
    }
    long_value = run(position="long", **common).value
    short_value = run(position="short", **common).value
    assert short_value == -long_value
    expected = (100 * math.exp(0.03) - 95) * math.exp(-0.05)
    assert math.isclose(long_value, expected, rel_tol=1e-14)


def test_income_worth_more_than_the_asset_is_refused() -> None:
    with pytest.raises(DomainError, match="income"):
        run(
            calculation="cost_of_carry",
            spot=10.0,
            years=1.0,
            risk_free_rate=0.05,
            income_present_value=11.0,
        )


def test_a_forward_price_past_its_bound_is_refused() -> None:
    with pytest.raises(DomainError, match="forward price"):
        run(calculation="cost_of_carry", spot=1e9, years=50.0, risk_free_rate=1.0)
