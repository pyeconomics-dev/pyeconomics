# src/pyeconomics/models/corporate/cost_of_capital.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""CAPM, capital-weighted WACC, Hamada betas and country risk premium.

Weights are market values. Hamada assumes zero debt beta. Country risk uses
sovereign spread times equity/bond volatility, with matched periods and currency.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Probability,
    Rate,
    Ratio,
    Reference,
    Volatility,
    model,
)

__all__ = ["cost_of_capital"]


class CapmInputs(ModelInputs):
    calculation: Literal["capm"] = Field(
        "capm", description="Capital asset pricing model"
    )
    risk_free_rate: Rate = Field(ge=-0.05, le=0.5, description="Annual risk-free rate")
    equity_risk_premium: Rate = Field(
        ge=-0.5, le=0.5, description="Expected market return less risk-free rate"
    )
    beta: Ratio = Field(ge=-5, le=5, description="Equity beta to the market portfolio")


class WaccInputs(ModelInputs):
    calculation: Literal["wacc"] = Field(
        "wacc", description="Weighted average cost of capital"
    )
    equity: Money = Field(ge=0, le=1e12, description="Market value of common equity")
    debt: Money = Field(ge=0, le=1e12, description="Market value of debt")
    preferred: Money = Field(
        0, ge=0, le=1e12, description="Market value of preferred stock"
    )
    cost_of_equity: Rate = Field(ge=0, le=1, description="Annual cost of common equity")
    cost_of_debt: Rate = Field(ge=0, le=1, description="Annual pretax cost of debt")
    cost_of_preferred: Rate = Field(
        0, ge=0, le=1, description="Annual cost of preferred stock"
    )
    tax_rate: Probability = Field(
        ge=0, le=1, description="Marginal tax rate for debt shield"
    )


class _BetaInputs(ModelInputs):
    beta: Ratio = Field(
        ge=-5, le=5, description="Levered beta to unlever, or unlevered beta to relever"
    )
    debt_to_equity: Ratio = Field(ge=0, le=100, description="Market debt/equity ratio")
    tax_rate: Probability = Field(ge=0, le=1, description="Marginal tax rate")


class UnleverInputs(_BetaInputs):
    calculation: Literal["unlever_beta"] = Field(
        "unlever_beta", description="Remove financial leverage"
    )


class ReleverInputs(_BetaInputs):
    calculation: Literal["relever_beta"] = Field(
        "relever_beta", description="Add financial leverage"
    )


class CountryInputs(ModelInputs):
    calculation: Literal["country_risk_premium"] = Field(
        "country_risk_premium", description="Volatility-scaled sovereign spread"
    )
    sovereign_spread: Rate = Field(
        ge=0, le=1, description="Annual sovereign default spread"
    )
    equity_volatility: Volatility = Field(
        ge=1e-6, le=5, description="Equity volatility over the common period"
    )
    bond_volatility: Volatility = Field(
        ge=1e-6, le=5, description="Sovereign bond volatility over the common period"
    )


Inputs = Annotated[
    CapmInputs | WaccInputs | UnleverInputs | ReleverInputs | CountryInputs,
    Field(discriminator="calculation"),
]


class CapmOutputs(ModelOutputs):
    calculation: Literal["capm"] = Field(
        "capm", description="Capital asset pricing model"
    )
    cost_of_equity: Rate = Field(
        ge=-3, le=3, description="Risk-free rate plus beta times ERP"
    )  # beta can make the CAPM return below the default -0.99.


class WaccOutputs(ModelOutputs):
    calculation: Literal["wacc"] = Field(
        "wacc", description="Weighted average cost of capital"
    )
    wacc: Rate = Field(
        ge=0, le=1, description="Market-weighted after-tax cost of capital"
    )


class UnleverOutputs(ModelOutputs):
    calculation: Literal["unlever_beta"] = Field(
        "unlever_beta", description="Remove financial leverage"
    )
    beta: Ratio = Field(ge=-505, le=505, description="Unlevered beta")


class ReleverOutputs(ModelOutputs):
    calculation: Literal["relever_beta"] = Field(
        "relever_beta", description="Add financial leverage"
    )
    beta: Ratio = Field(ge=-505, le=505, description="Levered beta")


class CountryOutputs(ModelOutputs):
    calculation: Literal["country_risk_premium"] = Field(
        "country_risk_premium", description="Volatility-scaled sovereign spread"
    )
    premium: Rate = Field(
        ge=0, le=5e6, description="Country equity risk premium"
    )  # 1 * 5 / 1e-6 widens the rate bound.


Outputs = Annotated[
    CapmOutputs | WaccOutputs | UnleverOutputs | ReleverOutputs | CountryOutputs,
    Field(discriminator="calculation"),
]


@model(
    id="corporate.cost_of_capital",
    version=1,
    title="Cost of capital and beta",
    summary=(
        "CAPM, WACC with preferred equity, Hamada "
        "unlevering/relevering, and country risk premium."
    ),
    formula=(
        r"k_e=r_f+\beta ERP",
        r"WACC=(Ek_e+Dk_d(1-t)+Pk_p)/(E+D+P)",
        r"\beta_L=\beta_U[1+(1-t)D/E]",
        r"CRP=s\sigma_e/\sigma_b",
    ),
    assumptions=(
        ("Annual decimal rates; capital weights use market values in one currency."),
        ("Hamada assumes zero debt beta and a usable interest tax shield."),
        (
            "Country equity and sovereign bond volatilities use the same "
            "horizon and currency."
        ),
    ),
    limitations=(
        (
            "Zero total capital raises DomainError. Extremely small "
            "totals can underflow; normalized weights avoid this."
        ),
        (
            "CAPM and Hamada assumptions need not hold empirically; "
            "country spread scaling is a practitioner estimate, not a "
            "recommendation."
        ),
    ),
    references=(
        Reference(
            key="sharpe1964",
            citation=(
                "Sharpe, W. F. (1964). Capital Asset Prices. Journal of "
                "Finance 19, 425-442."
            ),
            doi="10.1111/j.1540-6261.1964.tb02865.x",
            locator="Equilibrium expected returns",
        ),
        Reference(
            key="lintner1965",
            citation=(
                "Lintner, J. (1965). The Valuation of Risk Assets and the "
                "Selection of Risky Investments. Review of Economics and "
                "Statistics 47, 13-37."
            ),
            doi="10.2307/1924119",
            locator="Risk and expected return",
        ),
        Reference(
            key="hamada1972",
            citation=(
                "Hamada, R. S. (1972). The Effect of the Firm's Capital "
                "Structure on the Systematic Risk of Common Stocks. Journal "
                "of Finance 27, 435-452."
            ),
            doi="10.1111/j.1540-6261.1972.tb00971.x",
            locator="Levered and unlevered beta",
        ),
        Reference(
            key="damodaran",
            citation=(
                "Damodaran, A. Measuring Company Exposure to Country Risk: "
                "Theory and Practice."
            ),
            url="https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/CountryRisk.htm",
            locator="Default spreads and relative volatility",
        ),
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(
            id="unlever_relever_round_trip",
            statement=(
                "Unlevering and relevering at the same debt/equity and tax "
                "rate recovers beta, when the intermediate beta is in bounds."
            ),
        ),
        Invariant(
            id="wacc_between_component_costs",
            statement=(
                "Nonnegative weights put WACC between equity, after-tax debt "
                "and preferred costs."
            ),
        ),
        Invariant(
            id="capm_linear_in_beta",
            statement=(
                "A beta increment changes the CAPM return by the increment times ERP."
            ),
        ),
    ),
    examples=(
        Example(
            name="formula_capm",
            inputs={
                "calculation": "capm",
                "risk_free_rate": 0.03,
                "equity_risk_premium": 0.05,
                "beta": 1.2,
            },
        ),
        Example(
            name="formula_wacc",
            inputs={
                "calculation": "wacc",
                "equity": 600,
                "debt": 400,
                "cost_of_equity": 0.12,
                "cost_of_debt": 0.06,
                "tax_rate": 0.25,
            },
        ),
        Example(
            name="formula_unlever_beta",
            inputs={
                "calculation": "unlever_beta",
                "beta": 1.2,
                "debt_to_equity": 0,
                "tax_rate": 0.25,
            },
        ),
        Example(
            name="formula_relever_beta",
            inputs={
                "calculation": "relever_beta",
                "beta": 1,
                "debt_to_equity": 0.5,
                "tax_rate": 0.2,
            },
        ),
        Example(
            name="formula_country_risk_premium",
            inputs={
                "calculation": "country_risk_premium",
                "sovereign_spread": 0.02,
                "equity_volatility": 0.3,
                "bond_volatility": 0.2,
            },
        ),
        Example(
            name="balanced_capital",
            inputs={
                "calculation": "wacc",
                "equity": 600,
                "debt": 400,
                "cost_of_equity": 0.12,
                "cost_of_debt": 0.06,
                "tax_rate": 0.25,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def cost_of_capital(inputs: Inputs) -> Outputs:
    """Evaluate the selected financing formula."""
    if isinstance(inputs, CapmInputs):
        return CapmOutputs(
            cost_of_equity=inputs.risk_free_rate
            + inputs.beta * inputs.equity_risk_premium
        )
    if isinstance(inputs, WaccInputs):
        scale = max(inputs.equity, inputs.debt, inputs.preferred)
        if scale == 0:
            msg = "WACC needs nonzero total capital"
            raise DomainError(msg)
        e, d, p = inputs.equity / scale, inputs.debt / scale, inputs.preferred / scale
        value = (
            e * inputs.cost_of_equity
            + d * inputs.cost_of_debt * (1 - inputs.tax_rate)
            + p * inputs.cost_of_preferred
        ) / (e + d + p)
        return WaccOutputs(wacc=min(1.0, value))
    if isinstance(inputs, UnleverInputs):
        return UnleverOutputs(
            beta=inputs.beta / (1 + (1 - inputs.tax_rate) * inputs.debt_to_equity)
        )
    if isinstance(inputs, ReleverInputs):
        return ReleverOutputs(
            beta=inputs.beta * (1 + (1 - inputs.tax_rate) * inputs.debt_to_equity)
        )
    return CountryOutputs(
        premium=inputs.sovereign_spread
        * (inputs.equity_volatility / inputs.bond_volatility)
    )
