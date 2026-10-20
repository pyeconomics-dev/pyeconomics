# tests/models/equity/test_implied_risk_premium.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``equity.implied_risk_premium``: its invariants, an oracle, refusals.

The oracle solves Damodaran's equation as his spreadsheets lay it out, year by
year: each year's cash flow written out, the terminal value at the last growth
year, and SciPy's ``brentq`` on the difference from the index, with none of the
model's present-value numerics.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from scipy.optimize import brentq

from pyeconomics.core import ConvergenceError, DomainError, run_model
from pyeconomics.models.equity import implied_risk_premium

INPUTS = st.fixed_dictionaries(
    {
        "index_level": st.floats(min_value=100.0, max_value=10_000.0),
        "cash_yield": st.floats(min_value=0.005, max_value=0.12),
        "growth": st.floats(min_value=-0.05, max_value=0.15),
        "years": st.integers(min_value=0, max_value=10),
        "risk_free": st.floats(min_value=0.0, max_value=0.08),
    }
)


def run(inputs: dict[str, Any]) -> Any:  # noqa: ANN401 - the outputs
    given_inputs = {k: v for k, v in inputs.items() if k != "cash_yield"}
    given_inputs["cash_flow"] = inputs["cash_yield"] * inputs["index_level"]
    return run_model(implied_risk_premium, given_inputs).outputs


@pytest.mark.invariant(
    "equity.implied_risk_premium", "premium_rises_as_the_index_falls"
)
@given(inputs=INPUTS, fall=st.floats(min_value=0.01, max_value=0.5))
def test_a_lower_index_raises_the_premium(inputs: dict[str, Any], fall: float) -> None:
    level = inputs["index_level"]
    cash = inputs["cash_yield"] * level
    high = run(inputs)
    low = run(
        {
            **inputs,
            "index_level": level * (1 - fall),
            "cash_yield": cash / (level * (1 - fall)),
        }
    )
    assert low.equity_risk_premium >= high.equity_risk_premium


@pytest.mark.invariant(
    "equity.implied_risk_premium", "implied_return_exceeds_terminal_growth"
)
@given(
    inputs=INPUTS,
    terminal=st.one_of(st.none(), st.floats(min_value=-0.02, max_value=0.06)),
)
def test_the_implied_return_exceeds_terminal_growth(
    inputs: dict[str, Any], terminal: float | None
) -> None:
    out = run({**inputs, "terminal_growth": terminal})
    floor = inputs["risk_free"] if terminal is None else terminal
    assert out.terminal_growth == floor
    assert out.implied_return > floor


def _spreadsheet(
    level: float, cash: float, growth: float, years: int, rf: float
) -> float:
    """Damodaran's layout: each year's cash, then the terminal value, discounted."""

    def value(r: float) -> float:
        flows = [cash * (1 + growth) ** t for t in range(1, years + 1)]
        last = flows[-1] if flows else cash
        terminal = last * (1 + rf) / (r - rf)
        present = sum(f / (1 + r) ** t for t, f in enumerate(flows, start=1))
        return present + terminal / (1 + r) ** years - level

    return float(brentq(value, rf + 1e-9, 5.0, xtol=1e-15, rtol=1e-15, maxiter=500))


@pytest.mark.oracle("equity.implied_risk_premium")
@given(inputs=INPUTS)
def test_the_return_agrees_with_a_spreadsheet_solve(inputs: dict[str, Any]) -> None:
    out = run(inputs)
    level = inputs["index_level"]
    expected = _spreadsheet(
        level,
        inputs["cash_yield"] * level,
        inputs["growth"],
        inputs["years"],
        inputs["risk_free"],
    )
    assert math.isclose(out.implied_return, expected, rel_tol=1e-9, abs_tol=1e-12)


def test_with_no_growth_years_the_return_is_the_gordon_rate() -> None:
    out = run_model(
        implied_risk_premium,
        {
            "index_level": 100.0,
            "cash_flow": 4.0,
            "growth": 0.5,
            "years": 0,
            "risk_free": 0.03,
        },
    ).outputs
    # The growth rate is ignored: the next cash is 4 x 1.03.
    assert math.isclose(out.implied_return, 0.03 + 4.12 / 100, rel_tol=1e-12)
    assert math.isclose(out.cash_yield, 0.04)


def test_cash_far_above_the_index_is_refused() -> None:
    with pytest.raises(ConvergenceError, match=r"and up to 5\.0 prices the cash"):
        run_model(
            implied_risk_premium,
            {"index_level": 1.0, "cash_flow": 100.0, "growth": 0.5, "risk_free": 0.03},
        )


@pytest.mark.parametrize("cash", [1e-6, 1e-10, 1e-13])
def test_a_tiny_cash_yield_keeps_the_premium_to_relative_precision(cash: float) -> None:
    # With no growth years r = gT + C0 (1 + gT) / P: the premium is the yield's
    # 1.03 times, which an absolute root tolerance of 2e-12 would blur.
    out = run_model(
        implied_risk_premium,
        {
            "index_level": 1.0,
            "cash_flow": cash,
            "growth": 0.0,
            "years": 0,
            "risk_free": 0.03,
        },
    ).outputs
    assert math.isclose(out.equity_risk_premium, 1.03 * cash, rel_tol=1e-4)


def test_a_cash_yield_within_rounding_of_terminal_growth_is_refused() -> None:
    with pytest.raises(DomainError, match="within rounding"):
        run_model(
            implied_risk_premium,
            {
                "index_level": 1.0,
                "cash_flow": 1e-20,
                "growth": 0.0,
                "years": 0,
                "risk_free": 0.03,
            },
        )
