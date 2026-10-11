# src/pyeconomics/models/foundations/returns.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The return toolkit: ``foundations.returns``.

Five calculations, discriminated on ``calculation``:

- ``holding_period``: the return from a beginning value, an ending value and
  the income received in between;
- ``means``: the arithmetic, geometric and harmonic means of a return series,
  the last two taken of the gross returns ``1 + r``;
- ``annualized``: a return over some periods, compounded to a year of an
  explicit number of periods (ADR-0008 decision 4);
- ``log``: continuously compounded returns from simple ones, and back;
- ``real``: the real rate from a nominal rate and inflation, by the exact Fisher
  relation.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

import numpy as np
from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Periods,
    Rate,
    Reference,
    Return,
    ReturnArray,
    annualized_return,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.foundations._common import MONEY_IN, bounded

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["returns"]

#: The most returns a series may hold: forty years of trading days.
_SERIES_MAX: Final = 10_080
#: The highest return ADR-0008 allows (10,000%), and the largest log return
#: that converts to a simple return within it.
_RETURN_MAX: Final = 100.0
_LOG_RETURN_MAX: Final = math.log1p(_RETURN_MAX)
#: A log return can be far below -1 (-2.3 is a 90% loss), so the log series
#: widens the return's lower bound to -40: the smallest gross return a float
#: above -1 can give, about 1.1e-16, has a log return of -36.7.
_LOG_RETURN_MIN: Final = -40.0
#: Relative rounding allowed past the upper bound before it counts as overflow.
_ROUNDING: Final = 1e-12

_LogOrSimple = Annotated[
    tuple[Annotated[Return, Field(ge=_LOG_RETURN_MIN, le=_RETURN_MAX)], ...],
    ARRAY_INPUT,
]


def _return(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-1.0, le=_RETURN_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class HoldingPeriodInputs(ModelInputs):
    """Values at the start and end of a holding period, and the income between."""

    calculation: Literal["holding_period"] = Field(
        "holding_period", description="Holding-period return"
    )
    beginning_value: Money = Field(
        gt=0, le=MONEY_IN, description="Value at the start of the period"
    )
    ending_value: Money = Field(
        ge=0, le=MONEY_IN, description="Value at the end of the period"
    )
    income: Money = Field(
        0.0, ge=0, le=MONEY_IN, description="Income received during the period"
    )


class MeansInputs(ModelInputs):
    """A series of periodic returns."""

    calculation: Literal["means"] = Field(
        "means", description="Arithmetic, geometric and harmonic means"
    )
    returns: ReturnArray = Field(
        min_length=1, max_length=_SERIES_MAX, description="Periodic returns"
    )


class AnnualizedInputs(ModelInputs):
    """A return over some periods, and how many periods make a year."""

    calculation: Literal["annualized"] = Field(
        "annualized", description="Annualized (compounded) return"
    )
    period_return: Return = _return("Return over the whole span")
    periods: Periods = Field(
        1.0, gt=0, le=100_000, description="Number of periods the return spans"
    )
    periods_per_year: Periods = Field(
        gt=0, le=100_000, description="Periods in a year, such as 12 or 252"
    )


class LogInputs(ModelInputs):
    """A series to convert between simple and log returns."""

    calculation: Literal["log"] = Field(
        "log", description="Convert between simple and log returns"
    )
    returns: _LogOrSimple = Field(
        min_length=1,
        max_length=_SERIES_MAX,
        description="Simple returns, or log returns when direction is log_to_simple",
    )
    direction: Literal["simple_to_log", "log_to_simple"] = Field(
        "simple_to_log", description="Which way to convert"
    )


class RealInputs(ModelInputs):
    """A nominal rate and the inflation over the same period."""

    calculation: Literal["real"] = Field(
        "real", description="Real rate by the exact Fisher relation"
    )
    nominal: Rate = Field(ge=-0.99, le=10.0, description="Nominal rate or return")
    inflation: Rate = Field(ge=-0.5, le=10.0, description="Inflation rate")


ReturnsInputs = Annotated[
    HoldingPeriodInputs | MeansInputs | AnnualizedInputs | LogInputs | RealInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class HoldingPeriodOutputs(ModelOutputs):
    calculation: Literal["holding_period"] = Field(
        "holding_period", description="Holding-period return"
    )
    holding_period_return: Return = _return("Return over the holding period")
    income_return: Return = _return("Part of the return from income")
    price_return: Return = _return("Part of the return from the change in value")


class MeansOutputs(ModelOutputs):
    calculation: Literal["means"] = Field(
        "means", description="Arithmetic, geometric and harmonic means"
    )
    arithmetic: Return = _return("Arithmetic mean return")
    geometric: Return = _return("Geometric mean return, of the gross returns")
    harmonic: Return = _return("Harmonic mean return, of the gross returns")
    observations: Count = Field(ge=1, le=_SERIES_MAX, description="Number of returns")


class AnnualizedOutputs(ModelOutputs):
    calculation: Literal["annualized"] = Field(
        "annualized", description="Annualized (compounded) return"
    )
    annualized_return: Return = _return("Return compounded to one year")


class LogOutputs(ModelOutputs):
    calculation: Literal["log"] = Field(
        "log", description="Convert between simple and log returns"
    )
    converted: _LogOrSimple = Field(
        max_length=_SERIES_MAX, description="The converted returns, in order"
    )


class RealOutputs(ModelOutputs):
    calculation: Literal["real"] = Field(
        "real", description="Real rate by the exact Fisher relation"
    )
    real: Return = _return("Real rate: (1 + nominal) / (1 + inflation) - 1")


ReturnsOutputs = Annotated[
    HoldingPeriodOutputs | MeansOutputs | AnnualizedOutputs | LogOutputs | RealOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _holding_period(inputs: HoldingPeriodInputs) -> HoldingPeriodOutputs:
    begin = inputs.beginning_value
    price = (inputs.ending_value - begin) / begin
    income = inputs.income / begin
    return HoldingPeriodOutputs(
        holding_period_return=bounded(
            price + income, -1.0, _RETURN_MAX, "holding-period return"
        ),
        income_return=bounded(income, -1.0, _RETURN_MAX, "income return"),
        price_return=bounded(price, -1.0, _RETURN_MAX, "price return"),
    )


def _means(inputs: MeansInputs) -> MeansOutputs:
    values = np.asarray(inputs.returns, dtype=np.float64)
    gross = 1.0 + values
    lowest, highest = float(values.min()), float(values.max())
    arithmetic = float(np.mean(values))
    if np.any(gross == 0):
        # A total loss makes the product of gross returns zero: both means are
        # a total loss, the limit of each as one gross return falls to zero.
        geometric = harmonic = -1.0
    else:
        geometric = math.expm1(float(np.mean(np.log(gross))))
        harmonic = 1.0 / float(np.mean(1.0 / gross)) - 1.0
    # Rounding must not put a mean outside the range of the series.
    return MeansOutputs(
        arithmetic=min(max(arithmetic, lowest), highest),
        geometric=min(max(geometric, lowest), highest),
        harmonic=min(max(harmonic, lowest), highest),
        observations=values.size,
    )


def _annualized(inputs: AnnualizedInputs) -> AnnualizedOutputs:
    annual = annualized_return(
        inputs.period_return, inputs.periods, inputs.periods_per_year
    )
    # expm1(log1p(100)) rounds to just above 100: a few ulps over the bound are
    # rounding, and are clamped; more is a return the bounds cannot hold.
    if annual > _RETURN_MAX * (1 + _ROUNDING):
        msg = (
            f"compounding a return of {inputs.period_return!r} to a year of "
            f"{inputs.periods_per_year!r} periods exceeds a return of 100 (10,000%)"
        )
        raise DomainError(msg)
    return AnnualizedOutputs(annualized_return=min(annual, _RETURN_MAX))


def _log(inputs: LogInputs) -> LogOutputs:
    values = inputs.returns
    if inputs.direction == "simple_to_log":
        if min(values) <= -1:
            msg = "a simple return of -100% or less has no log return"
            raise DomainError(msg)
        return LogOutputs(converted=tuple(math.log1p(r) for r in values))
    if max(values) > _LOG_RETURN_MAX:
        msg = (
            f"a log return above {_LOG_RETURN_MAX:.6f} is a simple return above "
            "100 (10,000%)"
        )
        raise DomainError(msg)
    # expm1(log1p(100)) rounds to just above 100: clamp to the bound.
    return LogOutputs(converted=tuple(min(math.expm1(r), _RETURN_MAX) for r in values))


def _real(inputs: RealInputs) -> RealOutputs:
    real = (inputs.nominal - inputs.inflation) / (1.0 + inputs.inflation)
    return RealOutputs(real=real)


# --- the model ---------------------------------------------------------------

_BACON = Reference(
    key="bacon2008",
    citation=(
        "Bacon, C. R. (2008). Practical Portfolio Performance Measurement and "
        "Attribution, 2nd ed. Wiley."
    ),
    url="https://openlibrary.org/isbn/9780470059289",
    isbn="9780470059289",
    locator="Chapter 2 (the mathematics of portfolio return)",
)
_FISHER = Reference(
    key="fisher1930",
    citation="Fisher, I. (1930). The Theory of Interest. Macmillan.",
    url="https://www.econlib.org/library/YPDBooks/Fisher/fshToI.html",
    locator="Chapter II, Money interest and real interest",
)
_HARDY = Reference(
    key="hardy1952",
    citation=(
        "Hardy, G. H., Littlewood, J. E. and Polya, G. (1952). Inequalities, "
        "2nd ed. Cambridge University Press."
    ),
    url="https://openlibrary.org/isbn/9780521358804",
    isbn="9780521358804",
    locator="Chapter II, elementary mean values (the inequality of means)",
)


@model(
    id="foundations.returns",
    version=1,
    title="Return toolkit",
    summary=(
        "Holding-period, arithmetic, geometric, harmonic, annualized, log and "
        "real returns."
    ),
    formula=(
        r"HPR = \frac{V_1 - V_0 + D}{V_0}",
        (
            r"\bar{r}_A = \frac{1}{n}\sum r_t, \quad "
            r"\bar{r}_G = \Big(\prod (1 + r_t)\Big)^{1/n} - 1, \quad "
            r"\bar{r}_H = \frac{n}{\sum (1 + r_t)^{-1}} - 1"
        ),
        r"r_{annual} = (1 + R)^{m / k} - 1",
        r"\ell = \ln(1 + r), \quad r = e^{\ell} - 1",
        r"1 + r_{real} = \frac{1 + i}{1 + \pi}",
    ),
    assumptions=(
        (
            "Returns are decimals over equal periods, with income reinvested at the "
            "end of its period."
        ),
        (
            "The geometric and harmonic means are of the gross returns 1 + r, "
            "less one, so they are compound and harmonic growth rates."
        ),
        (
            "An annualized return compounds: a return over k periods becomes "
            "(1 + R)^(m / k) - 1 for m periods in a year."
        ),
    ),
    limitations=(
        (
            "A result above 100 (10,000%), or a holding-period return below the "
            "series bounds, raises DomainError."
        ),
        "A simple return of -100% or below has no log return: DomainError.",
        (
            "A total loss in a series makes its geometric and harmonic means -1, "
            "the limit as a gross return falls to zero."
        ),
    ),
    references=(_BACON, _FISHER, _HARDY),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("returns", "means", "log returns", "fisher"),
    invariants=(
        Invariant(
            id="means_ordering",
            statement=(
                "For returns above -1, the harmonic mean is at most the geometric "
                "mean, which is at most the arithmetic mean."
            ),
        ),
        Invariant(
            id="log_returns_additive",
            statement=(
                "The log return over the whole span equals the sum of the period "
                "log returns."
            ),
        ),
        Invariant(
            id="fisher_identity",
            statement="(1 + real)(1 + inflation) equals 1 + nominal.",
        ),
    ),
    examples=(
        Example(
            name="stock_with_dividend",
            inputs={
                "calculation": "holding_period",
                "beginning_value": 100,
                "ending_value": 108,
                "income": 2,
            },
        ),
        Example(
            name="three_years",
            inputs={"calculation": "means", "returns": [0.1, -0.05, 0.2]},
        ),
        Example(
            name="monthly_to_annual",
            inputs={
                "calculation": "annualized",
                "period_return": 0.01,
                "periods_per_year": 12,
            },
        ),
        Example(
            name="to_log",
            inputs={"calculation": "log", "returns": [0.1, -0.05, 0.2]},
        ),
        Example(
            name="real_rate",
            inputs={"calculation": "real", "nominal": 0.05, "inflation": 0.03},
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def returns(inputs: ReturnsInputs) -> ReturnsOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], ReturnsOutputs]]] = {
    HoldingPeriodInputs: _holding_period,
    MeansInputs: _means,
    AnnualizedInputs: _annualized,
    LogInputs: _log,
    RealInputs: _real,
}
