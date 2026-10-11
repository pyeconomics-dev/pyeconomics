# src/pyeconomics/models/accounting/financial_ratios.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Financial-statement ratios and three-/five-step DuPont, one currency.

Activity and return ratios use supplied averages; liquidity and debt ratios
use period-end balances. Credit purchases, rather than COGS, drive payables
turnover. Ratios are period values and are not automatically annualized.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

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
    Ratio,
    Reference,
    model,
    warn,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["financial_ratios"]

RATIO_LIMIT = 1e6


def _bounded(value: float, name: str) -> float | None:
    if not math.isfinite(value) or abs(value) > RATIO_LIMIT:
        warn("unrepresentable_ratio", f"{name} is outside +/-1e6")
        return None
    return value


def _ratio(numerator: float, denominator: float, name: str) -> float | None:
    if denominator == 0:
        warn("zero_denominator", f"{name} has a zero denominator")
        return None
    return _bounded(numerator / denominator, name)


def _product(values: Sequence[float | None], name: str) -> float | None:
    if any(value is None for value in values):
        warn("undefined_component", f"{name} has an undefined component")
        return None
    return _bounded(math.prod(value for value in values if value is not None), name)


class Inputs(ModelInputs):
    current_assets: Money = Field(
        ge=0, le=1e12, description="Period-end current assets"
    )
    inventory: Money = Field(ge=0, le=1e12, description="Period-end inventory")
    prepayments: Money = Field(
        ge=0,
        le=1e12,
        description="Period-end prepaid expenses excluded from quick assets",
    )
    cash: Money = Field(
        ge=0, le=1e12, description="Period-end cash and cash equivalents"
    )
    marketable_securities: Money = Field(
        ge=0, le=1e12, description="Period-end short-term marketable securities"
    )
    current_liabilities: Money = Field(
        ge=0, le=1e12, description="Period-end current liabilities"
    )
    revenue: Money = Field(
        ge=0,
        le=1e12,
        description=(
            "Revenue for the period; all sales assumed on credit for "
            "receivables turnover"
        ),
    )
    cost_of_goods_sold: Money = Field(
        ge=0, le=1e12, description="Cost of goods sold, positive expense"
    )
    purchases: Money = Field(
        ge=0, le=1e12, description="Credit purchases for the period, positive outlay"
    )
    average_receivables: Money = Field(
        ge=0, le=1e12, description="Average trade receivables over the period"
    )
    average_inventory: Money = Field(
        ge=0, le=1e12, description="Average inventory over the period"
    )
    average_payables: Money = Field(
        ge=0, le=1e12, description="Average trade payables over the period"
    )
    average_assets: Money = Field(
        ge=0, le=1e12, description="Average total assets over the period"
    )
    average_equity: Money = Field(
        ge=-1e12,
        le=1e12,
        description="Average common equity over the period; may be negative",
    )
    total_assets: Money = Field(ge=0, le=1e12, description="Period-end total assets")
    total_debt: Money = Field(
        ge=0,
        le=1e12,
        description=("Period-end interest-bearing debt; excludes non-debt liabilities"),
    )
    equity: Money = Field(
        ge=-1e12, le=1e12, description="Period-end book common equity; may be negative"
    )
    ebit: Money = Field(
        ge=-1e12, le=1e12, description="Operating income before interest and taxes"
    )
    interest_expense: Money = Field(
        ge=0, le=1e12, description="Interest expense for the period"
    )
    pretax_income: Money = Field(
        ge=-1e12, le=1e12, description="Income before taxes for the period"
    )
    net_income: Money = Field(
        ge=-1e12,
        le=1e12,
        description="After-tax income attributable to common shareholders",
    )
    days: Count = Field(
        365, ge=1, le=366, description="Calendar days in the reporting period"
    )


class Outputs(ModelOutputs):
    current_ratio: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Current assets / current liabilities"
    )
    quick_ratio: Ratio | None = Field(
        ge=-1e6,
        le=1e6,
        description=(
            "(Current assets - inventory - prepayments) / current liabilities"
        ),
    )
    cash_ratio: Ratio | None = Field(
        ge=-1e6,
        le=1e6,
        description="(Cash + marketable securities) / current liabilities",
    )
    receivables_turnover: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Revenue / average receivables"
    )
    inventory_turnover: Ratio | None = Field(
        ge=-1e6, le=1e6, description="COGS / average inventory"
    )
    payables_turnover: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Credit purchases / average payables"
    )
    receivables_days: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Days in period * average receivables / revenue"
    )
    inventory_days: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Days in period * average inventory / COGS"
    )
    payables_days: Ratio | None = Field(
        ge=-1e6,
        le=1e6,
        description="Days in period * average payables / credit purchases",
    )
    asset_turnover: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Revenue / average total assets"
    )
    debt_to_equity: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Period-end interest-bearing debt / book equity"
    )
    debt_to_assets: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Period-end interest-bearing debt / total assets"
    )
    interest_coverage: Ratio | None = Field(
        ge=-1e6, le=1e6, description="EBIT / interest expense"
    )
    financial_leverage: Ratio | None = Field(
        ge=-1e6,
        le=1e6,
        description="Average assets / average equity; DuPont equity multiplier",
    )
    gross_margin: Ratio | None = Field(
        ge=-1e6, le=1e6, description="(Revenue - COGS) / revenue"
    )
    operating_margin: Ratio | None = Field(
        ge=-1e6, le=1e6, description="EBIT / revenue"
    )
    net_margin: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Net income / revenue"
    )
    roa: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Net income / average assets"
    )
    roe: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Net income / average common equity"
    )
    tax_burden: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Net income / pretax income"
    )
    interest_burden: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Pretax income / EBIT"
    )
    dupont_three_step: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Net margin * asset turnover * financial leverage"
    )
    dupont_five_step: Ratio | None = Field(
        ge=-1e6,
        le=1e6,
        description=(
            "Tax burden * interest burden * operating margin * asset "
            "turnover * financial leverage"
        ),
    )


@model(
    id="accounting.financial_ratios",
    version=1,
    title="Financial ratios and DuPont",
    summary=(
        "Liquidity, activity, solvency, profitability and three- and "
        "five-step DuPont ratios."
    ),
    formula=(
        r"ROE=NI/E_{avg}",
        r"ROE=(NI/S)(S/A_{avg})(A_{avg}/E_{avg})",
        r"ROE=(NI/EBT)(EBT/EBIT)(EBIT/S)(S/A_{avg})(A_{avg}/E_{avg})",
    ),
    assumptions=(
        (
            "All statement items share one currency and reporting period; "
            "averages are supplied, not inferred."
        ),
        (
            "Receivables turnover assumes all revenue is credit sales; "
            "payables turnover uses credit purchases. Days uses the "
            "supplied period length."
        ),
        (
            "Debt means interest-bearing debt, not total liabilities. "
            "Quick assets exclude inventory and prepayments; cash ratio "
            "includes short-term securities. These definitions vary "
            "across sources."
        ),
        (
            "The schema describes the numerator and denominator of every "
            "output. Five-step DuPont returns each tax, interest, "
            "operating and turnover component."
        ),
    ),
    limitations=(
        (
            "Zero denominators yield null with a warning; any ratio or "
            "DuPont product outside +/-1e6 also yields null. Other "
            "defined measures remain available."
        ),
        (
            "Inconsistent statement inputs are not reconciled; negative "
            "equity is allowed. DuPont identities require defined "
            "components, including nonzero revenue/assets and EBIT/pretax "
            "income for five-step."
        ),
    ),
    references=(
        Reference(
            key="damodaran",
            citation="Damodaran, A. (2012). Investment Valuation, 3rd ed. Wiley.",
            isbn="9781118011522",
            url="https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/finstat.pdf",
            locator=(
                "Financial statement analysis: profitability, leverage and efficiency"
            ),
        ),
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(
            id="dupont_three_step_equals_roe",
            statement=(
                "Defined three-step DuPont equals NI / average equity, within "
                "floating precision."
            ),
        ),
        Invariant(
            id="dupont_five_step_equals_roe",
            statement=(
                "Defined five-step DuPont equals NI / average equity, within "
                "floating precision."
            ),
        ),
    ),
    examples=(
        Example(
            name="consistent_statements",
            inputs={
                "current_assets": 200,
                "inventory": 50,
                "prepayments": 10,
                "cash": 40,
                "marketable_securities": 10,
                "current_liabilities": 100,
                "revenue": 1000,
                "cost_of_goods_sold": 600,
                "purchases": 500,
                "average_receivables": 100,
                "average_inventory": 150,
                "average_payables": 100,
                "average_assets": 800,
                "average_equity": 400,
                "total_assets": 900,
                "total_debt": 300,
                "equity": 450,
                "ebit": 200,
                "interest_expense": 40,
                "pretax_income": 160,
                "net_income": 120,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def financial_ratios(inputs: Inputs) -> Outputs:
    """Compute every defined ratio with warnings for undefined components."""
    i = inputs
    values = {
        "current_ratio": _ratio(
            i.current_assets, i.current_liabilities, "current_ratio"
        ),
        "quick_ratio": _ratio(
            i.current_assets - i.inventory - i.prepayments,
            i.current_liabilities,
            "quick_ratio",
        ),
        "cash_ratio": _ratio(
            i.cash + i.marketable_securities, i.current_liabilities, "cash_ratio"
        ),
        "receivables_turnover": _ratio(
            i.revenue, i.average_receivables, "receivables_turnover"
        ),
        "inventory_turnover": _ratio(
            i.cost_of_goods_sold, i.average_inventory, "inventory_turnover"
        ),
        "payables_turnover": _ratio(
            i.purchases, i.average_payables, "payables_turnover"
        ),
        "receivables_days": _ratio(
            i.days * i.average_receivables, i.revenue, "receivables_days"
        ),
        "inventory_days": _ratio(
            i.days * i.average_inventory, i.cost_of_goods_sold, "inventory_days"
        ),
        "payables_days": _ratio(
            i.days * i.average_payables, i.purchases, "payables_days"
        ),
        "asset_turnover": _ratio(i.revenue, i.average_assets, "asset_turnover"),
        "debt_to_equity": _ratio(i.total_debt, i.equity, "debt_to_equity"),
        "debt_to_assets": _ratio(i.total_debt, i.total_assets, "debt_to_assets"),
        "interest_coverage": _ratio(i.ebit, i.interest_expense, "interest_coverage"),
        "financial_leverage": _ratio(
            i.average_assets, i.average_equity, "financial_leverage"
        ),
        "gross_margin": _ratio(
            i.revenue - i.cost_of_goods_sold, i.revenue, "gross_margin"
        ),
        "operating_margin": _ratio(i.ebit, i.revenue, "operating_margin"),
        "net_margin": _ratio(i.net_income, i.revenue, "net_margin"),
        "roa": _ratio(i.net_income, i.average_assets, "roa"),
        "roe": _ratio(i.net_income, i.average_equity, "roe"),
        "tax_burden": _ratio(i.net_income, i.pretax_income, "tax_burden"),
        "interest_burden": _ratio(i.pretax_income, i.ebit, "interest_burden"),
    }
    values["dupont_three_step"] = _product(
        [values[n] for n in ("net_margin", "asset_turnover", "financial_leverage")],
        "three-step DuPont",
    )
    values["dupont_five_step"] = _product(
        [
            values[n]
            for n in (
                "tax_burden",
                "interest_burden",
                "operating_margin",
                "asset_turnover",
                "financial_leverage",
            )
        ],
        "five-step DuPont",
    )
    return Outputs(**values)
