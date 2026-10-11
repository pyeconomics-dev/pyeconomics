# src/pyeconomics/models/equity/free_cash_flow.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""FCFF, FCFE and annual one- or two-stage DCF, in one currency.

FCFF = EBIT(1-t) + depreciation - capex - change in noncash working capital.
FCFE = net income + depreciation - capex - change in working capital + net
borrowing. Valuation discounts FCFF at WACC or FCFE at the cost of equity.
For a firm valuation, equity is firm value less net debt; a direct FCFE
valuation returns equity and the corresponding firm value plus net debt.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Probability,
    Rate,
    Reference,
    model,
)
from pyeconomics.models.equity._valuation import bounded, dcf

__all__ = ["free_cash_flow"]


class _Components(ModelInputs):
    depreciation: Money = Field(
        ge=0, le=1e12, description="Noncash depreciation and amortization"
    )
    capex: Money = Field(
        ge=0, le=1e12, description="Capital expenditure, positive outlay"
    )
    working_capital_change: Money = Field(
        ge=-1e12,
        le=1e12,
        description="Increase in noncash working capital, positive outlay",
    )


class FcffInputs(_Components):
    calculation: Literal["fcff"] = Field(
        "fcff", description="Free cash flow to the firm"
    )
    ebit: Money = Field(
        ge=-1e12, le=1e12, description="Operating earnings before interest and tax"
    )
    tax_rate: Probability = Field(
        ge=0, le=1, description="Marginal tax rate; full loss tax benefit assumed"
    )


class FcfeInputs(_Components):
    calculation: Literal["fcfe"] = Field("fcfe", description="Free cash flow to equity")
    net_income: Money = Field(
        ge=-1e12, le=1e12, description="After-interest after-tax net income"
    )
    net_borrowing: Money = Field(
        ge=-1e12, le=1e12, description="New debt less principal repaid"
    )


class ValuationInputs(ModelInputs):
    calculation: Literal["valuation"] = Field(
        "valuation", description="One- or two-stage DCF"
    )
    basis: Literal["firm", "equity"] = Field(
        "firm", description="FCFF/WACC or FCFE/cost of equity"
    )
    next_cash_flow: Money = Field(ge=-1e12, le=1e12, description="FCFF or FCFE at t=1")
    discount_rate: Rate = Field(
        gt=0, le=1, description="WACC for firm basis; cost of equity for equity basis"
    )
    growth: Rate = Field(0, ge=-0.5, le=1, description="Growth within the first stage")
    years: Count = Field(
        0,
        ge=0,
        le=100,
        description="First-stage years; zero selects a single-stage perpetuity",
    )
    terminal_growth: Rate = Field(
        0,
        ge=-0.5,
        le=1,
        description="Stable growth after the first stage, or after t=1 if years=0",
    )
    net_debt: Money = Field(
        0,
        ge=-1e12,
        le=1e12,
        description="Debt less cash; excludes nonoperating assets other than cash",
    )


Inputs = Annotated[
    FcffInputs | FcfeInputs | ValuationInputs, Field(discriminator="calculation")
]


class FcffOutputs(ModelOutputs):
    calculation: Literal["fcff"] = Field(
        "fcff", description="Free cash flow to the firm"
    )
    fcff: Money = Field(
        ge=-4e12, le=4e12, description="Cash flow before debt financing"
    )


class FcfeOutputs(ModelOutputs):
    calculation: Literal["fcfe"] = Field("fcfe", description="Free cash flow to equity")
    fcfe: Money = Field(ge=-5e12, le=5e12, description="Cash flow after debt financing")


class ValuationOutputs(ModelOutputs):
    calculation: Literal["valuation"] = Field(
        "valuation", description="One- or two-stage DCF"
    )
    firm_value: Money = Field(ge=-1e15, le=1e15, description="Operating firm value")
    equity_value: Money = Field(
        ge=-1e15, le=1e15, description="Firm value less net debt"
    )


Outputs = Annotated[
    FcffOutputs | FcfeOutputs | ValuationOutputs, Field(discriminator="calculation")
]


@model(
    id="equity.free_cash_flow",
    version=1,
    title="Free cash flow and DCF valuation",
    summary=(
        "FCFF from EBIT, FCFE from net income, and one- or two-stage "
        "firm or equity valuation."
    ),
    formula=(
        r"FCFF=EBIT(1-t)+D-CapEx-\Delta WC",
        r"FCFE=NI+D-CapEx-\Delta WC+NB",
        r"E=V-NetDebt",
    ),
    assumptions=(
        ("Annual end-of-year cash flows in one currency; next_cash_flow is at t=1."),
        (
            "Firm basis uses FCFF and WACC; equity basis uses FCFE and "
            "cost of equity. Discount rates are constant."
        ),
        (
            "EBIT loss receives a full tax benefit; no separate loss "
            "carry-forward schedule."
        ),
    ),
    limitations=(
        (
            "A discount rate at or below stable growth raises "
            "DomainError; valuations outside +/-1e15 do too."
        ),
        (
            "Growth and discount rates are user assumptions. Negative "
            "equity is a formula result; no solvency floor or "
            "recommendation is imposed."
        ),
    ),
    references=(
        Reference(
            key="damodaran",
            citation="Damodaran, A. (2012). Investment Valuation, 3rd ed. Wiley.",
            isbn="9781118011522",
            url="https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/dcfall2pg.pdf",
            locator="Free cash flow to equity; firm valuation",
        ),
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(
            id="fcfe_equals_fcff_less_after_tax_interest_plus_net_borrowing",
            statement=(
                "With NI=(EBIT-interest)(1-tax), "
                "FCFE=FCFF-interest(1-tax)+net borrowing."
            ),
        ),
        Invariant(
            id="single_stage_matches_gordon_form",
            statement=(
                "A single-stage cash flow is "
                "next_cash_flow/(discount_rate-terminal_growth)."
            ),
        ),
    ),
    examples=(
        Example(
            name="formula_fcff",
            inputs={
                "calculation": "fcff",
                "ebit": 200,
                "tax_rate": 0.25,
                "depreciation": 50,
                "capex": 70,
                "working_capital_change": 10,
            },
        ),
        Example(
            name="formula_fcfe",
            inputs={
                "calculation": "fcfe",
                "net_income": 120,
                "depreciation": 50,
                "capex": 70,
                "working_capital_change": 10,
                "net_borrowing": 20,
            },
        ),
        Example(
            name="formula_valuation",
            inputs={
                "calculation": "valuation",
                "next_cash_flow": 100,
                "discount_rate": 0.1,
                "net_debt": 200,
            },
        ),
        Example(
            name="firm_perpetuity",
            inputs={
                "calculation": "valuation",
                "next_cash_flow": 100,
                "discount_rate": 0.1,
                "terminal_growth": 0.02,
                "net_debt": 200,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def free_cash_flow(inputs: Inputs) -> Outputs:
    """Evaluate cash flow components or discount the selected stream."""
    if isinstance(inputs, FcffInputs):
        return FcffOutputs(
            fcff=inputs.ebit * (1 - inputs.tax_rate)
            + inputs.depreciation
            - inputs.capex
            - inputs.working_capital_change
        )
    if isinstance(inputs, FcfeInputs):
        return FcfeOutputs(
            fcfe=inputs.net_income
            + inputs.depreciation
            - inputs.capex
            - inputs.working_capital_change
            + inputs.net_borrowing
        )
    value = dcf(
        inputs.next_cash_flow,
        inputs.discount_rate,
        inputs.growth,
        inputs.years,
        inputs.terminal_growth,
    )
    if inputs.basis == "firm":
        return ValuationOutputs(
            firm_value=value, equity_value=bounded(value - inputs.net_debt)
        )
    return ValuationOutputs(
        firm_value=bounded(value + inputs.net_debt), equity_value=value
    )
