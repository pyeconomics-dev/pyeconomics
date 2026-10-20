# src/pyeconomics/models/equity/implied_risk_premium.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The implied equity risk premium: ``equity.implied_risk_premium``.

Damodaran's implied premium is the expected return :math:`r` at which an index
level equals the present value of the cash its companies are expected to return
to shareholders, dividends and buybacks together. The cash of the last twelve
months, :math:`C_0`, grows at :math:`g` for :math:`N` years and at a terminal
rate :math:`g_T` (the risk-free rate by default) for ever after:

.. math::

    P = \sum_{t=1}^{N} \frac{C_0 (1 + g)^t}{(1 + r)^t}
        + \frac{C_0 (1 + g)^N (1 + g_T)}{(r - g_T)(1 + r)^N},

and the premium is :math:`r - r_f`. The present value falls as :math:`r` rises
above :math:`g_T`, from infinity towards zero, so there is one root; it is found
with :func:`~pyeconomics.core.numerics.find_root`.
"""

from __future__ import annotations

import math
from typing import Final

from pydantic import Field

from pyeconomics.core import (
    AsOf,
    Binding,
    ChangelogEntry,
    ConvergenceError,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    IndexLevel,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Ratio,
    Reference,
    RootPolicy,
    find_root,
    growing_annuity_factor,
    model,
)

__all__ = ["implied_risk_premium"]

#: The most years of growth before the terminal rate.
_YEARS_MAX: Final = 50
#: The highest implied return searched for: 500% a year.
_RETURN_MAX: Final = 5.0
#: How far above the terminal growth rate the search starts, at most: the present
#: value there is the cash over 1e-12, large but finite.
_ABOVE_TERMINAL: Final = 1e-12
_LEVEL_MAX: Final = 1e9
#: The return to full relative precision: the premium is a small difference of
#: two rates, which ADR-0008's absolute xtol of 2e-12 would blur for a tiny cash
#: yield. The iteration cap stays.
_POLICY: Final = RootPolicy(xtol=1e-300, maxiter=200)


class ImpliedRiskPremiumInputs(ModelInputs):
    index_level: IndexLevel = Field(
        gt=0.0, le=_LEVEL_MAX, description="The index level: the price paid today"
    )
    cash_flow: Money = Field(
        gt=0.0,
        le=_LEVEL_MAX,
        description=(
            "Dividends plus buybacks over the last twelve months, in the index's "
            "own units (index points)"
        ),
    )
    growth: Rate = Field(
        ge=-0.5,
        le=1.0,
        description="Expected annual growth of the cash for the growth years",
    )
    years: Count = Field(
        5,
        ge=0,
        le=_YEARS_MAX,
        description="Years of that growth before the terminal rate (Damodaran: 5)",
    )
    risk_free: Rate = Field(
        ge=-0.05, le=0.5, description="The risk-free rate, a 10-year government yield"
    )
    terminal_growth: Rate | None = Field(
        None,
        ge=-0.05,
        le=0.5,
        description=(
            "Growth for ever after the growth years; the risk-free rate if omitted"
        ),
    )


class ImpliedRiskPremiumOutputs(ModelOutputs):
    implied_return: Rate = Field(
        ge=-0.05,
        le=_RETURN_MAX,
        description="The expected return at which the cash is worth the index level",
    )
    equity_risk_premium: Rate = Field(
        ge=-0.55,
        le=_RETURN_MAX + 0.05,
        description="The implied return less the risk-free rate",
    )
    cash_yield: Ratio = Field(
        gt=0.0, le=1e9, description="The last twelve months' cash over the index level"
    )
    terminal_growth: Rate = Field(
        ge=-0.05, le=0.5, description="The terminal growth rate used"
    )


def present_value(
    rate: float,
    cash_flow: float,
    growth: float,
    years: int,
    terminal_growth: float,
) -> float:
    """Return the present value of the cash at ``rate``, above the terminal growth.

    Formed in logs, so the factors of a long growth stage never overflow.
    """
    log_rate = math.log1p(rate)
    stream = 0.0
    if years:
        stream = (
            cash_flow * (1.0 + growth) * growing_annuity_factor(rate, growth, years)
        )
    last = math.log(cash_flow) + years * (math.log1p(growth) - log_rate)
    tail = math.exp(last) * (1.0 + terminal_growth) / (rate - terminal_growth)
    return stream + tail


def _implied(inputs: ImpliedRiskPremiumInputs) -> ImpliedRiskPremiumOutputs:
    terminal = (
        inputs.risk_free if inputs.terminal_growth is None else inputs.terminal_growth
    )
    level = inputs.index_level

    def gap(rate: float) -> float:
        value = present_value(
            rate, inputs.cash_flow, inputs.growth, inputs.years, terminal
        )
        return value / level - 1.0

    cash_yield = inputs.cash_flow / level
    # The return lies about the cash yield above terminal growth: start the
    # search a thousandth of that above it, so a tiny yield still brackets it.
    low = terminal + min(_ABOVE_TERMINAL, cash_yield * 1e-3)
    if not low > terminal:
        msg = (
            f"the cash yield {cash_yield!r} puts the implied return within "
            f"rounding of the terminal growth rate {terminal!r}"
        )
        raise DomainError(msg)
    try:
        found = find_root(
            gap, low, low + 1.0, limits=(low, _RETURN_MAX), policy=_POLICY
        )
    except ConvergenceError as error:
        msg = (
            f"no return above the terminal growth rate and up to {_RETURN_MAX} "
            f"prices the cash at the index level {level!r}: {error}"
        )
        raise ConvergenceError(msg) from None
    rate = found.root
    return ImpliedRiskPremiumOutputs(
        implied_return=rate,
        equity_risk_premium=rate - inputs.risk_free,
        cash_yield=cash_yield,
        terminal_growth=terminal,
    )


_DAMODARAN = Reference(
    key="damodaran2026",
    citation=(
        "Damodaran, A. (2026). Equity Risk Premiums (ERP): Determinants, "
        "Estimation, and Implications - The 2026 Edition. SSRN working paper."
    ),
    url="https://pages.stern.nyu.edu/~adamodar/",
    locator="The implied equity risk premium from the index level and cash yield",
)
_DAMODARAN_FILE = Reference(
    key="damodaran_histimpl",
    citation=(
        "Damodaran, A. Historical Implied Equity Risk Premiums for the S&P 500, "
        "histimpl.xls, Damodaran Online."
    ),
    url="https://pages.stern.nyu.edu/~adamodar/pc/datasets/histimpl.xls",
    locator=(
        "Sheet 'Historical Impl Premiums': the yearly inputs and Implied ERP (FCFE)"
    ),
)


@model(
    id="equity.implied_risk_premium",
    version=1,
    title="Implied equity risk premium",
    summary=(
        "The expected return at which an index level equals the present value of "
        "its expected dividends and buybacks, and its premium over the risk-free "
        "rate."
    ),
    formula=(
        (
            r"P = \sum_{t=1}^{N} \frac{C_0 (1+g)^t}{(1+r)^t} + "
            r"\frac{C_0 (1+g)^N (1+g_T)}{(r - g_T)(1+r)^N}"
        ),
        r"\mathrm{ERP} = r - r_f, \quad g_T = r_f \text{ by default}",
    ),
    assumptions=(
        (
            "The cash returned to shareholders (dividends and buybacks) is the "
            "cash the index's owners receive; it arrives at the end of each year."
        ),
        (
            "Cash grows at the growth rate for the growth years and at the "
            "terminal rate after; with the terminal rate equal to the risk-free "
            "rate, the market grows no faster than the economy in the long run."
        ),
        (
            "Profile: default binds Damodaran's year-end S&P 500 level, its "
            "dividends and buybacks and the analysts' expected growth from his "
            "file, and Treasury's 10-year yield on the date; read as of a year "
            "end, they are the inputs of his published premium."
        ),
    ),
    limitations=(
        (
            "The premium is only as good as the expected cash and growth: it is a "
            "forward-looking estimate, not a forecast of returns."
        ),
        (
            "An implied return above 500% a year (cash far above the index level) "
            "raises ConvergenceError; a cash yield so small that the implied "
            "return is within rounding of the terminal growth rate raises "
            "DomainError."
        ),
        (
            "Damodaran's inputs are year-end values: bound as of a date within a "
            "year, the default profile pairs last year's index and cash with "
            "today's 10-year yield."
        ),
    ),
    references=(_DAMODARAN, _DAMODARAN_FILE),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.INSTANT,
    tags=(
        "equity risk premium",
        "implied premium",
        "expected return",
        "discounted cash flow",
        "buybacks",
    ),
    invariants=(
        Invariant(
            id="premium_rises_as_the_index_falls",
            statement=(
                "With the cash and rates fixed, a lower index level gives a higher "
                "implied premium."
            ),
        ),
        Invariant(
            id="implied_return_exceeds_terminal_growth",
            statement="The implied return is always above the terminal growth rate.",
        ),
    ),
    examples=(
        Example(
            name="damodaran_style_inputs",
            inputs={
                "index_level": 6000.0,
                "cash_flow": 190.0,
                "growth": 0.06,
                "risk_free": 0.045,
            },
            note="An index at 6000 returning 190 points of cash a year.",
        ),
        Example(
            name="no_growth_stage",
            inputs={
                "index_level": 100.0,
                "cash_flow": 4.0,
                "growth": 0.0,
                "years": 0,
                "risk_free": 0.03,
            },
            note="With no growth years, r = C0 (1 + g_T) / P + g_T.",
        ),
    ),
    bindings=(
        Binding("index_level", "us.equity.sp500_year_end"),
        Binding("cash_flow", "us.equity.sp500_dividends_buybacks"),
        Binding("growth", "us.equity.sp500_expected_growth"),
        Binding("risk_free", "us.treasury.nominal_10y", as_of=AsOf.LAST_ON_OR_BEFORE),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def implied_risk_premium(
    inputs: ImpliedRiskPremiumInputs,
) -> ImpliedRiskPremiumOutputs:
    """Return the implied return and the equity risk premium."""
    return _implied(inputs)
