# tests/models/corporate/test_corporate_catalog.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Financing, appraisal and leverage identities and shared cash-flow parity."""

from __future__ import annotations

from typing import Any

import numpy_financial as npf
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, run_model
from pyeconomics.models.corporate import capital_budgeting, cost_of_capital, leverage
from pyeconomics.models.foundations import time_value

RATE = st.floats(0, 0.5)


def capital(**raw: Any) -> Any:  # noqa: ANN401 - discriminated outputs
    return run_model(cost_of_capital, raw).outputs


@pytest.mark.invariant("corporate.cost_of_capital", "unlever_relever_round_trip")
@given(beta=st.floats(-5, 5), debt=st.floats(0, 100), tax=st.floats(0, 1))
def test_beta_round_trip(beta: float, debt: float, tax: float) -> None:
    common = {"debt_to_equity": debt, "tax_rate": tax}
    unlevered = capital(calculation="unlever_beta", beta=beta, **common).beta
    assert capital(
        calculation="relever_beta", beta=unlevered, **common
    ).beta == pytest.approx(beta, abs=1e-12)


@pytest.mark.invariant("corporate.cost_of_capital", "wacc_between_component_costs")
@given(
    e=st.floats(1, 1e9),
    d=st.floats(0, 1e9),
    p=st.floats(0, 1e9),
    ke=RATE,
    kd=RATE,
    kp=RATE,
    tax=st.floats(0, 1),
)
def test_wacc_convex_combination(  # noqa: PLR0913 - independent weights and costs
    *, e: float, d: float, p: float, ke: float, kd: float, kp: float, tax: float
) -> None:
    out = capital(
        calculation="wacc",
        equity=e,
        debt=d,
        preferred=p,
        cost_of_equity=ke,
        cost_of_debt=kd,
        cost_of_preferred=kp,
        tax_rate=tax,
    )
    components = [ke, kd * (1 - tax), kp]
    assert min(components) - 1e-15 <= out.wacc <= max(components) + 1e-15


@pytest.mark.invariant("corporate.cost_of_capital", "capm_linear_in_beta")
@given(beta=st.floats(-4, 4), erp=st.floats(-0.5, 0.5))
def test_capm_linearity(beta: float, erp: float) -> None:
    low = capital(
        calculation="capm", risk_free_rate=0.03, equity_risk_premium=erp, beta=beta
    ).cost_of_equity
    high = capital(
        calculation="capm", risk_free_rate=0.03, equity_risk_premium=erp, beta=beta + 1
    ).cost_of_equity
    assert high - low == pytest.approx(erp, abs=1e-12)


@pytest.mark.invariant("corporate.capital_budgeting", "npv_positive_iff_pi_above_one")
@pytest.mark.invariant(
    "corporate.capital_budgeting", "mirr_between_reinvestment_rate_and_irr"
)
@pytest.mark.invariant(
    "corporate.capital_budgeting", "discounted_payback_not_shorter_than_payback"
)
@settings(deadline=None)
@given(
    outlay=st.floats(1, 1e6),
    inflows=st.lists(st.floats(1, 1e6), min_size=1, max_size=10),
    rate=RATE,
    reinvest=RATE,
)
def test_project_identities(
    outlay: float, inflows: list[float], rate: float, reinvest: float
) -> None:
    flows = [-outlay, *inflows]
    out = run_model(
        capital_budgeting,
        {"cash_flows": flows, "rate": rate, "reinvestment_rate": reinvest},
    ).outputs
    if out.profitability_index is not None and abs(out.npv) > 1e-8 * sum(
        abs(f) for f in flows
    ):
        assert (out.npv > 0) == (out.profitability_index > 1)
    if out.mirr is not None and out.irr is not None:
        assert (
            min(reinvest, out.irr) - 1e-9 <= out.mirr <= max(reinvest, out.irr) + 1e-9
        )
    if out.discounted_payback is not None:
        assert out.payback is not None
        assert out.discounted_payback >= out.payback - 1e-10


@settings(deadline=None)
@given(
    flows=st.lists(st.floats(-1e5, 1e5), min_size=2, max_size=12),
    rate=st.floats(-0.5, 0.5),
)
def test_npv_and_irr_match_foundations_exactly(flows: list[float], rate: float) -> None:
    project = run_model(capital_budgeting, {"cash_flows": flows, "rate": rate}).outputs
    npv = run_model(
        time_value, {"calculation": "npv", "cash_flows": flows, "rate": rate}
    ).outputs.npv
    irr = run_model(time_value, {"calculation": "irr", "cash_flows": flows}).outputs.irr
    assert project.npv == npv
    assert project.irr == irr


@pytest.mark.invariant("corporate.leverage", "dtl_equals_dol_times_dfl")
@pytest.mark.invariant("corporate.leverage", "dol_above_one_with_fixed_costs")
@given(
    fixed=st.floats(1, 1000),
    interest=st.floats(0, 100),
    quantity=st.integers(1101, 10000),
)
def test_leverage_factorization(fixed: float, interest: float, quantity: int) -> None:
    out = run_model(
        leverage,
        {
            "price": 2,
            "variable_cost": 1,
            "fixed_costs": fixed,
            "interest": interest,
            "quantity": quantity,
        },
    ).outputs
    assert out.dol >= 1
    assert out.dtl == pytest.approx(out.dol * out.dfl)


@pytest.mark.parametrize(
    "flows", [[-100, 0, 0], [0, 0, 0], [100, 0, 0], [-100, -50, 20], [-1, 1e12]]
)
def test_undefined_project_outputs_warn(flows: list[float]) -> None:
    result = run_model(capital_budgeting, {"cash_flows": flows, "rate": 0.1})
    assert result.warnings


def test_npv_overflow_raises_domain_error() -> None:
    with pytest.raises(DomainError):
        run_model(
            capital_budgeting, {"cash_flows": [-100, *([1e12] * 1200)], "rate": -0.99}
        )


def test_zero_capital_is_undefined() -> None:
    with pytest.raises(DomainError):
        capital(
            calculation="wacc",
            equity=0,
            debt=0,
            cost_of_equity=0.1,
            cost_of_debt=0.05,
            tax_rate=0.2,
        )


def test_subnormal_capital_weights() -> None:
    assert capital(
        calculation="wacc",
        equity=5e-324,
        debt=5e-324,
        cost_of_equity=0.1,
        cost_of_debt=0.05,
        tax_rate=0,
    ).wacc == pytest.approx(0.075)


@pytest.mark.parametrize(
    ("flows", "expected"), [([-100, 1], -0.99), ([-1e6, 11e6], 10.0)]
)
@pytest.mark.parametrize("scale", [1e-10, 1.0, 100.0])
def test_mirr_endpoints_survive_log_rounding(
    flows: list[float], expected: float, scale: float
) -> None:
    out = run_model(
        capital_budgeting, {"cash_flows": [c * scale for c in flows], "rate": 0}
    ).outputs
    assert out.mirr == pytest.approx(expected, abs=1e-12)


def test_country_premium() -> None:
    assert capital(
        calculation="country_risk_premium",
        sovereign_spread=0.02,
        equity_volatility=0.3,
        bond_volatility=0.2,
    ).premium == pytest.approx(0.03)


@pytest.mark.oracle("corporate.capital_budgeting")
@settings(deadline=None)
@given(
    outlay=st.floats(100, 1e6),
    inflows=st.lists(st.floats(100, 1e5), min_size=2, max_size=8),
    rate=RATE,
    reinvest=RATE,
)
def test_project_matches_numpy_financial(
    outlay: float, inflows: list[float], rate: float, reinvest: float
) -> None:
    flows = [-outlay, *inflows]
    out = run_model(
        capital_budgeting,
        {
            "cash_flows": flows,
            "rate": rate,
            "finance_rate": 0.1,
            "reinvestment_rate": reinvest,
        },
    ).outputs
    assert out.npv == pytest.approx(float(npf.npv(rate, flows)), abs=1e-8)
    if out.mirr is not None:
        assert out.mirr == pytest.approx(
            float(npf.mirr(flows, 0.1, reinvest)), abs=1e-10
        )
    if out.irr is not None:
        assert out.irr == pytest.approx(float(npf.irr(flows)), abs=1e-9)


@pytest.mark.parametrize(
    "raw",
    [
        {
            "price": 10,
            "variable_cost": 10,
            "fixed_costs": 100,
            "interest": 20,
            "quantity": 10,
        },
        {
            "price": 20,
            "variable_cost": 10,
            "fixed_costs": 100,
            "interest": 20,
            "quantity": 10,
        },
        {
            "price": 20,
            "variable_cost": 10,
            "fixed_costs": 100,
            "interest": 20,
            "quantity": 12,
        },
        {
            "price": 20,
            "variable_cost": 19.999999999999996,
            "fixed_costs": 1e12,
            "interest": 20,
            "quantity": 10,
        },
    ],
)
def test_leverage_undefined_components_preserve_other_outputs(
    raw: dict[str, float],
) -> None:
    result = run_model(leverage, raw)
    assert result.warnings
    assert result.outputs.operating_income is not None
