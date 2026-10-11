# src/pyeconomics/models/equity/dividend_discount.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Dividend valuation, annual decimal rates and currency-agnostic per-share money.

The two-stage input is next year's dividend. The H-model instead takes the
dividend just paid and approximates a linear decline in growth over 2H years.
PVGO uses next year's earnings and the observed price, not a dividend forecast.
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
    Rate,
    Reference,
    Years,
    growing_perpetuity_factor,
    model,
)
from pyeconomics.models.equity._valuation import bounded, dcf

__all__ = ["dividend_discount"]

RETURN_LIMIT = 10.0


class GordonInputs(ModelInputs):
    calculation: Literal["gordon"] = Field("gordon", description="Constant growth")
    next_dividend: Money = Field(ge=0, le=1e9, description="Dividend per share at t=1")
    required_return: Rate = Field(gt=0, le=1, description="Annual cost of equity")
    growth: Rate = Field(ge=-0.5, le=1, description="Perpetual annual dividend growth")


class TwoStageInputs(ModelInputs):
    calculation: Literal["two_stage"] = Field("two_stage", description="Two-stage DDM")
    next_dividend: Money = Field(ge=0, le=1e9, description="Dividend per share at t=1")
    required_return: Rate = Field(gt=0, le=1, description="Annual cost of equity")
    growth: Rate = Field(ge=-0.5, le=1, description="Growth within the first stage")
    years: Count = Field(ge=1, le=100, description="Number of first-stage dividends")
    terminal_growth: Rate = Field(
        ge=-0.5, le=1, description="Growth after the first stage"
    )


class HModelInputs(ModelInputs):
    calculation: Literal["h_model"] = Field(
        "h_model", description="Linear-growth approximation"
    )
    dividend: Money = Field(
        ge=0, le=1e9, description="Dividend per share just paid, D0"
    )
    required_return: Rate = Field(gt=0, le=1, description="Annual cost of equity")
    growth: Rate = Field(ge=-0.5, le=1, description="Initial annual dividend growth")
    terminal_growth: Rate = Field(
        ge=-0.5, le=1, description="Stable annual dividend growth"
    )
    half_life: Years = Field(
        ge=0, le=50, description="H, half the growth transition duration"
    )


class PvgoInputs(ModelInputs):
    calculation: Literal["pvgo"] = Field(
        "pvgo", description="Value of growth opportunities"
    )
    price: Money = Field(ge=0, le=1e9, description="Observed price per share")
    earnings: Money = Field(
        ge=-1e9, le=1e9, description="Next year's earnings per share"
    )
    required_return: Rate = Field(gt=0, le=1, description="Annual cost of equity")


class ImpliedInputs(ModelInputs):
    calculation: Literal["implied_return"] = Field(
        "implied_return", description="Gordon implied return"
    )
    price: Money = Field(ge=0.01, le=1e9, description="Observed price per share")
    next_dividend: Money = Field(ge=0, le=1e9, description="Dividend per share at t=1")
    growth: Rate = Field(ge=-0.5, le=1, description="Perpetual annual growth")


Inputs = Annotated[
    GordonInputs | TwoStageInputs | HModelInputs | PvgoInputs | ImpliedInputs,
    Field(discriminator="calculation"),
]


class GordonOutputs(ModelOutputs):
    calculation: Literal["gordon"] = Field("gordon", description="Constant growth")
    value: Money = Field(ge=0, le=1e15, description="Equity value per share")


class TwoStageOutputs(ModelOutputs):
    calculation: Literal["two_stage"] = Field("two_stage", description="Two-stage DDM")
    value: Money = Field(ge=0, le=1e15, description="Equity value per share")


class HModelOutputs(ModelOutputs):
    calculation: Literal["h_model"] = Field(
        "h_model", description="Linear-growth approximation"
    )
    value: Money = Field(
        ge=-1e15, le=1e15, description="Approximate equity value per share"
    )


class PvgoOutputs(ModelOutputs):
    calculation: Literal["pvgo"] = Field(
        "pvgo", description="Value of growth opportunities"
    )
    no_growth_value: Money = Field(
        ge=-1e15, le=1e15, description="Earnings capitalized at required return"
    )
    pvgo: Money = Field(
        ge=-1e15, le=1e15, description="Observed price less no-growth value"
    )


class ImpliedOutputs(ModelOutputs):
    calculation: Literal["implied_return"] = Field(
        "implied_return", description="Gordon implied return"
    )
    required_return: Rate = Field(
        ge=-0.5, le=10, description="Dividend yield plus growth; decimal"
    )


Outputs = Annotated[
    GordonOutputs | TwoStageOutputs | HModelOutputs | PvgoOutputs | ImpliedOutputs,
    Field(discriminator="calculation"),
]


@model(
    id="equity.dividend_discount",
    version=1,
    title="Dividend discount valuation",
    summary=(
        "Gordon, two-stage and H-model values, PVGO and the Gordon implied return."
    ),
    formula=(
        r"V = D_1/(r-g)",
        r"V_H = D_0[(1+g_L)+H(g_S-g_L)]/(r-g_L)",
        r"PVGO=P-E_1/r",
    ),
    assumptions=(
        (
            "Annual end-of-year dividends; rates are decimals; all "
            "per-share money shares one currency."
        ),
        (
            "Two-stage starts with D1; H-model starts with D0 and linear "
            "growth decay over 2H years."
        ),
    ),
    limitations=(
        (
            "A terminal growth at or above required return raises "
            "DomainError, including for a zero dividend."
        ),
        (
            "Values outside +/-1e15 or implied returns outside [-0.5, 10] "
            "raise DomainError."
        ),
        (
            "H-model is an approximation; a declining growth path can "
            "give a negative approximate value. Values are formula "
            "outputs, not recommendations."
        ),
    ),
    references=(
        Reference(
            key="gordon1959",
            citation=(
                "Gordon, M. J. (1959). Dividends, Earnings, and Stock Prices. "
                "Review of Economics and Statistics 41, 99-105."
            ),
            doi="10.2307/1927792",
            locator="Dividend capitalization",
        ),
        Reference(
            key="gordon1962",
            citation=(
                "Gordon, M. J. (1962). The Investment, Financing, and "
                "Valuation of the Corporation. Irwin."
            ),
            url="https://archive.org/details/investmentfinanc0000gord",
            locator="Constant-growth valuation",
        ),
        Reference(
            key="fuller1984",
            citation=(
                "Fuller, R. J. and Hsia, C.-C. (1984). A Simplified Common "
                "Stock Valuation Model. Financial Analysts Journal 40(5), "
                "49-56."
            ),
            doi="10.2469/faj.v40.n5.49",
            locator="H-model",
        ),
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(
            id="two_stage_reduces_to_gordon",
            statement="Equal stage growth rates give Gordon's value.",
        ),
        Invariant(
            id="h_model_reduces_to_gordon",
            statement="Zero H gives Gordon with D1 = D0(1+gL).",
        ),
        Invariant(
            id="value_decreases_with_required_return",
            statement=(
                "For nonnegative dividends, Gordon value does not increase "
                "with required return above growth."
            ),
        ),
    ),
    examples=(
        Example(
            name="formula_gordon",
            inputs={
                "calculation": "gordon",
                "next_dividend": 2,
                "required_return": 0.1,
                "growth": 0,
            },
        ),
        Example(
            name="formula_h_model",
            inputs={
                "calculation": "h_model",
                "dividend": 2,
                "required_return": 0.1,
                "growth": 0.12,
                "terminal_growth": 0.04,
                "half_life": 5,
            },
        ),
        Example(
            name="formula_two_stage",
            inputs={
                "calculation": "two_stage",
                "next_dividend": 2,
                "required_return": 0.1,
                "growth": 0.02,
                "terminal_growth": 0.02,
                "years": 10,
            },
        ),
        Example(
            name="formula_pvgo",
            inputs={
                "calculation": "pvgo",
                "price": 50,
                "earnings": 3,
                "required_return": 0.1,
            },
        ),
        Example(
            name="formula_implied_return",
            inputs={
                "calculation": "implied_return",
                "price": 50,
                "next_dividend": 2,
                "growth": 0.02,
            },
        ),
        Example(
            name="constant_growth",
            inputs={
                "calculation": "gordon",
                "next_dividend": 2,
                "required_return": 0.1,
                "growth": 0.02,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def dividend_discount(inputs: Inputs) -> Outputs:
    """Evaluate the selected dividend formula."""
    if isinstance(inputs, GordonInputs):
        return GordonOutputs(
            value=dcf(
                inputs.next_dividend,
                inputs.required_return,
                inputs.growth,
                0,
                inputs.growth,
            )
        )
    if isinstance(inputs, TwoStageInputs):
        return TwoStageOutputs(
            value=dcf(
                inputs.next_dividend,
                inputs.required_return,
                inputs.growth,
                inputs.years,
                inputs.terminal_growth,
            )
        )
    if isinstance(inputs, HModelInputs):
        numerator = inputs.dividend * (
            (1 + inputs.terminal_growth)
            + inputs.half_life * (inputs.growth - inputs.terminal_growth)
        )
        if inputs.required_return <= inputs.terminal_growth:
            growing_perpetuity_factor(inputs.required_return, inputs.terminal_growth)
        return HModelOutputs(
            value=bounded(numerator / (inputs.required_return - inputs.terminal_growth))
        )
    if isinstance(inputs, PvgoInputs):
        base = bounded(inputs.earnings / inputs.required_return)
        return PvgoOutputs(no_growth_value=base, pvgo=bounded(inputs.price - base))
    from pyeconomics.core import DomainError  # noqa: PLC0415 - branch-specific error

    rate = inputs.next_dividend / inputs.price + inputs.growth
    if rate > RETURN_LIMIT:
        msg = "implied return exceeds its upper bound of 10"
        raise DomainError(msg)
    return ImpliedOutputs(required_return=rate)
