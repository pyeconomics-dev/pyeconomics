# tests/models/fixed_income/test_long_stub_regression.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Issue #89: keep whole 30/360 accruals and ICMA reference periods distinct."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813
from fixed_income_draws import DAY_COUNTS, FREQUENCIES, qdate, quantlib_bond

from pyeconomics.core import run_model
from pyeconomics.models.fixed_income import bond_pricing, convexity, duration


@pytest.mark.oracle("fixed_income.bond_pricing")
@pytest.mark.oracle("fixed_income.duration")
@pytest.mark.oracle("fixed_income.convexity")
@pytest.mark.parametrize("day_count", list(DAY_COUNTS))
@pytest.mark.parametrize("first_period", ["short", "long"])
@pytest.mark.parametrize(
    "settlement",
    [dt.date(1993, 6, 30), dt.date(1994, 4, 15), dt.date(1994, 5, 31)],
)
@pytest.mark.parametrize("coupon", [0.0, 0.06])
@pytest.mark.parametrize("yield_", [0.0, 0.05])
def test_stub_prices_and_risk_agree_with_quantlib(
    day_count: str,
    first_period: str,
    settlement: dt.date,
    coupon: float,
    yield_: float,
) -> None:
    """Exercise settlement before, on and after the notional coupon date."""
    terms: dict[str, Any] = {
        "settlement": settlement,
        "maturity": dt.date(1995, 4, 15),
        "issue_date": dt.date(1993, 5, 30),
        "first_period": first_period,
        "frequency": "annual",
        "day_count": day_count,
        "coupon_rate": coupon,
    }
    bond = quantlib_bond(terms)
    date = qdate(settlement)
    dc, frequency = DAY_COUNTS[day_count], FREQUENCIES["annual"]
    rate = ql.InterestRate(yield_, dc, ql.Compounded, frequency)
    clean = ql.BondFunctions.cleanPrice(bond, rate, date)
    accrued = ql.BondFunctions.accruedAmount(bond, date)
    inputs = {**terms, "yield_to_maturity": yield_}
    priced = run_model(
        bond_pricing, {**inputs, "calculation": "price_from_yield"}
    ).outputs
    assert priced.flat_price == pytest.approx(clean, rel=1e-12, abs=1e-12)
    assert priced.accrued_interest == pytest.approx(accrued, abs=1e-12)
    solved = run_model(
        bond_pricing,
        {**terms, "calculation": "yield_from_price", "price": clean},
    ).outputs
    assert solved.yield_to_maturity == pytest.approx(yield_, abs=1e-10)
    risk = run_model(duration, {**inputs, "calculation": "macaulay_modified"}).outputs
    assert risk.full_price == pytest.approx(clean + accrued, rel=1e-12)
    assert risk.macaulay_duration == pytest.approx(
        ql.BondFunctions.duration(bond, rate, ql.Duration.Macaulay, date), rel=1e-12
    )
    assert risk.modified_duration == pytest.approx(
        ql.BondFunctions.duration(bond, rate, ql.Duration.Modified, date), rel=1e-12
    )
    curvature = run_model(convexity, {**inputs, "calculation": "analytical"}).outputs
    assert curvature.full_price == pytest.approx(clean + accrued, rel=1e-12)
    assert curvature.convexity == pytest.approx(
        ql.BondFunctions.convexity(bond, rate, date), rel=1e-12
    )
