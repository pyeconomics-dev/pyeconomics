# tests/models/equity/test_equity_catalog.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Valuation identities, timing conventions and domain edges."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import DomainError, run_model
from pyeconomics.models.equity import dividend_discount, free_cash_flow

MONEY = st.floats(min_value=0, max_value=1e6)
GROWTH = st.floats(min_value=-0.1, max_value=0.05)
RETURNS = st.floats(min_value=0.06, max_value=0.5)


def dd(**raw: Any) -> Any:  # noqa: ANN401 - discriminated outputs
    return run_model(dividend_discount, raw).outputs


def cf(**raw: Any) -> Any:  # noqa: ANN401 - discriminated outputs
    return run_model(free_cash_flow, raw).outputs


@pytest.mark.invariant("equity.dividend_discount", "two_stage_reduces_to_gordon")
@given(dividend=MONEY, growth=GROWTH, rate=RETURNS, years=st.integers(1, 100))
def test_equal_growth_stages(
    dividend: float, growth: float, rate: float, years: int
) -> None:
    common = {"next_dividend": dividend, "growth": growth, "required_return": rate}
    one = dd(calculation="gordon", **common).value
    two = dd(
        calculation="two_stage", years=years, terminal_growth=growth, **common
    ).value
    assert two == pytest.approx(one, rel=1e-9, abs=1e-9)


@pytest.mark.invariant("equity.dividend_discount", "h_model_reduces_to_gordon")
@given(dividend=MONEY, growth=GROWTH, rate=RETURNS)
def test_zero_half_life(dividend: float, growth: float, rate: float) -> None:
    h = dd(
        calculation="h_model",
        dividend=dividend,
        growth=0.5,
        terminal_growth=growth,
        half_life=0,
        required_return=rate,
    )
    g = dd(
        calculation="gordon",
        next_dividend=dividend * (1 + growth),
        growth=growth,
        required_return=rate,
    )
    assert h.value == pytest.approx(g.value)


@pytest.mark.invariant(
    "equity.dividend_discount", "value_decreases_with_required_return"
)
@given(dividend=MONEY, growth=GROWTH, low=RETURNS, high=RETURNS)
def test_higher_return_lowers_value(
    dividend: float, growth: float, low: float, high: float
) -> None:
    low, high = sorted((low, high))
    assert (
        dd(
            calculation="gordon",
            next_dividend=dividend,
            growth=growth,
            required_return=low,
        ).value
        >= dd(
            calculation="gordon",
            next_dividend=dividend,
            growth=growth,
            required_return=high,
        ).value
    )


@pytest.mark.invariant(
    "equity.free_cash_flow",
    "fcfe_equals_fcff_less_after_tax_interest_plus_net_borrowing",
)
@given(ebit=MONEY, interest=MONEY, borrowing=MONEY, tax=st.floats(0, 1))
def test_cash_flow_bridge(
    ebit: float, interest: float, borrowing: float, tax: float
) -> None:
    common = {"depreciation": 50, "capex": 70, "working_capital_change": 10}
    firm = cf(calculation="fcff", ebit=ebit, tax_rate=tax, **common).fcff
    equity = cf(
        calculation="fcfe",
        net_income=(ebit - interest) * (1 - tax),
        net_borrowing=borrowing,
        **common,
    ).fcfe
    assert equity == pytest.approx(firm - interest * (1 - tax) + borrowing, abs=1e-8)


@pytest.mark.invariant("equity.free_cash_flow", "single_stage_matches_gordon_form")
@given(flow=MONEY, growth=GROWTH, rate=RETURNS)
def test_single_stage_cash_flow(flow: float, growth: float, rate: float) -> None:
    out = cf(
        calculation="valuation",
        next_cash_flow=flow,
        discount_rate=rate,
        terminal_growth=growth,
        net_debt=200,
    )
    assert out.firm_value == pytest.approx(flow / (rate - growth))
    assert out.equity_value == pytest.approx(out.firm_value - 200)


@pytest.mark.parametrize(
    "raw",
    [
        {
            "calculation": "gordon",
            "next_dividend": 1,
            "required_return": 0.1,
            "growth": 0.1,
        },
        {
            "calculation": "gordon",
            "next_dividend": 1,
            "required_return": 0.1,
            "growth": 0.2,
        },
        {
            "calculation": "gordon",
            "next_dividend": 1e9,
            "required_return": 0.100000000000001,
            "growth": 0.1,
        },
        {
            "calculation": "implied_return",
            "price": 0.01,
            "next_dividend": 1,
            "growth": 0,
        },
        {"calculation": "pvgo", "price": 1, "earnings": 1e9, "required_return": 1e-20},
    ],
)
def test_unrepresentable_dividend_values(raw: dict[str, Any]) -> None:
    with pytest.raises(DomainError):
        run_model(dividend_discount, raw)


def test_two_stage_cash_flow_timing_and_equity_basis() -> None:
    firm = cf(
        calculation="valuation",
        next_cash_flow=100,
        discount_rate=0.1,
        growth=0.2,
        years=2,
        terminal_growth=0.02,
        net_debt=50,
    )
    expected = 100 / 1.1 + 120 / 1.1**2 + (120 * 1.02 / 0.08) / 1.1**2
    assert firm.firm_value == pytest.approx(expected)
    equity = cf(
        calculation="valuation",
        basis="equity",
        next_cash_flow=100,
        discount_rate=0.1,
        terminal_growth=0,
        net_debt=50,
    )
    assert equity.equity_value == 1000
    assert equity.firm_value == 1050


def test_h_model_is_not_an_exact_linear_growth_schedule() -> None:
    out = dd(
        calculation="h_model",
        dividend=2,
        required_return=0.1,
        growth=0.12,
        terminal_growth=0.04,
        half_life=5,
    )
    assert out.value == pytest.approx(48)


def test_pvgo_and_implied_return() -> None:
    out = dd(calculation="pvgo", price=50, earnings=3, required_return=0.1)
    assert (out.no_growth_value, out.pvgo) == (30, 20)
    assert dd(
        calculation="implied_return", price=50, next_dividend=2, growth=0.02
    ).required_return == pytest.approx(0.06)


@pytest.mark.parametrize("dividend", [0.0, 1e-300])
def test_tiny_cash_flow_has_a_finite_perpetuity(dividend: float) -> None:
    rate = 1e-310
    expected = dividend / rate
    assert dd(
        calculation="gordon", next_dividend=dividend, required_return=rate, growth=0
    ).value == pytest.approx(expected)
    assert dd(
        calculation="h_model",
        dividend=dividend,
        required_return=rate,
        growth=0,
        terminal_growth=0,
        half_life=0,
    ).value == pytest.approx(expected)
    assert cf(
        calculation="valuation", next_cash_flow=dividend, discount_rate=rate
    ).firm_value == pytest.approx(expected)
