# src/pyeconomics/models/foundations/risk_statistics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Risk statistics of a return or value series: ``foundations.risk_statistics``.

Four calculations, discriminated on ``calculation``:

- ``volatility``: the sample standard deviation of returns, with ``n - 1``
  degrees of freedom, and its annualization by the square root of an explicit
  number of periods per year;
- ``semideviation``: the downside spread below the sample mean (``n - 1``) and
  below a target (``n``);
- ``moments``: the adjusted skewness G1 and excess kurtosis G2;
- ``drawdown``: the maximum drawdown of a value series, with the positions of
  its peak and trough.

The estimators are those of :mod:`pyeconomics.core.descriptive`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    IndexLevel,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Periods,
    Ratio,
    Reference,
    Return,
    ReturnArray,
    Symbol,
    Volatility,
    max_drawdown,
    model,
    sample_mean,
    sample_moments,
    sample_variance,
    semideviation_below_mean,
    semideviation_below_target,
)
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["risk_statistics"]

#: The most observations a series may hold: forty years of trading days.
_SERIES_MAX: Final = 10_080
#: A periodic standard deviation of returns within [-1, 100] is at most
#: 101 / sqrt(2), about 71.4 (two returns at the extremes), so the periodic
#: outputs widen the volatility's upper bound from 10 to 100, and annualizing by
#: sqrt(100,000) periods a year widens it to 1e5. Zero is allowed: a constant
#: series has no spread.
_VOLATILITY_MAX: Final = 100.0
_ANNUAL_VOLATILITY_MAX: Final = 1e5
#: A semideviation below a target in [-1, 100] is at most 101; below the mean,
#: with n - 1, at most 101 * sqrt(2).
_SEMIDEVIATION_MAX: Final = 150.0

_Values = Annotated[tuple[Annotated[IndexLevel, Field(gt=0, le=1e9)], ...], ARRAY_INPUT]


def _series(minimum: int, description: str) -> Any:  # noqa: ANN401 - Field
    return Field(min_length=minimum, max_length=_SERIES_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class VolatilityInputs(ModelInputs):
    """A return series and how many of its periods make a year."""

    calculation: Literal["volatility"] = Field(
        "volatility", description="Sample volatility and its annualization"
    )
    returns: ReturnArray = _series(2, "Periodic returns")
    periods_per_year: Periods = Field(
        gt=0, le=100_000, description="Periods in a year, such as 12 or 252"
    )


class SemideviationInputs(ModelInputs):
    """A return series and a target return."""

    calculation: Literal["semideviation"] = Field(
        "semideviation", description="Downside deviation below the mean and a target"
    )
    returns: ReturnArray = _series(2, "Periodic returns")
    target: Return = Field(
        0.0, ge=-1.0, le=100.0, description="Target return per period"
    )


class MomentsInputs(ModelInputs):
    """A return series of at least four observations."""

    calculation: Literal["moments"] = Field(
        "moments", description="Adjusted skewness (G1) and excess kurtosis (G2)"
    )
    returns: ReturnArray = _series(4, "Periodic returns")


class DrawdownInputs(ModelInputs):
    """A series of positive values, such as prices or an index."""

    calculation: Literal["drawdown"] = Field(
        "drawdown", description="Maximum drawdown with its peak and trough"
    )
    values: _Values = _series(1, "Values in time order, each above zero")


RiskStatisticsInputs = Annotated[
    VolatilityInputs | SemideviationInputs | MomentsInputs | DrawdownInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class VolatilityOutputs(ModelOutputs):
    calculation: Literal["volatility"] = Field(
        "volatility", description="Sample volatility and its annualization"
    )
    mean: Return = Field(ge=-1.0, le=100.0, description="Mean periodic return")
    volatility: Volatility = Field(
        ge=0,
        le=_VOLATILITY_MAX,
        description="Sample standard deviation of the periodic returns (n - 1)",
    )
    annualized_volatility: Volatility = Field(
        ge=0,
        le=_ANNUAL_VOLATILITY_MAX,
        description="Volatility times the square root of periods_per_year",
    )
    degrees_of_freedom: Count = Field(
        ge=1, le=_SERIES_MAX, description="n - 1, the denominator of the variance"
    )


class SemideviationOutputs(ModelOutputs):
    calculation: Literal["semideviation"] = Field(
        "semideviation", description="Downside deviation below the mean and a target"
    )
    below_mean: Volatility = Field(
        ge=0,
        le=_SEMIDEVIATION_MAX,
        description="Semideviation below the sample mean, with n - 1",
    )
    below_target: Volatility = Field(
        ge=0,
        le=_SEMIDEVIATION_MAX,
        description="Downside deviation below the target, with n",
    )


class MomentsOutputs(ModelOutputs):
    calculation: Literal["moments"] = Field(
        "moments", description="Adjusted skewness (G1) and excess kurtosis (G2)"
    )
    skewness: Ratio = Field(
        ge=-1e3, le=1e3, description="Adjusted Fisher-Pearson skewness, G1"
    )
    excess_kurtosis: Ratio = Field(
        ge=-1e5, le=1e5, description="Adjusted excess kurtosis, G2"
    )
    observations: Count = Field(ge=4, le=_SERIES_MAX, description="Number of returns")


class DrawdownOutputs(ModelOutputs):
    calculation: Literal["drawdown"] = Field(
        "drawdown", description="Maximum drawdown with its peak and trough"
    )
    max_drawdown: Return = Field(
        ge=0, le=1, description="Largest decline from a peak, as a positive decimal"
    )
    peak_index: Count = Field(
        ge=0, le=_SERIES_MAX, description="Position of the peak, from 0"
    )
    trough_index: Count = Field(
        ge=0, le=_SERIES_MAX, description="Position of the trough, from 0"
    )


RiskStatisticsOutputs = Annotated[
    VolatilityOutputs | SemideviationOutputs | MomentsOutputs | DrawdownOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _volatility(inputs: VolatilityInputs) -> VolatilityOutputs:
    periodic = math.sqrt(sample_variance(inputs.returns))
    annual = periodic * math.sqrt(inputs.periods_per_year)
    return VolatilityOutputs(
        mean=sample_mean(inputs.returns),
        volatility=periodic,
        annualized_volatility=annual,
        degrees_of_freedom=len(inputs.returns) - 1,
    )


def _semideviation(inputs: SemideviationInputs) -> SemideviationOutputs:
    return SemideviationOutputs(
        below_mean=semideviation_below_mean(inputs.returns),
        below_target=semideviation_below_target(inputs.returns, inputs.target),
    )


def _moments(inputs: MomentsInputs) -> MomentsOutputs:
    shape = sample_moments(inputs.returns)
    return MomentsOutputs(
        skewness=shape.skewness,
        excess_kurtosis=shape.excess_kurtosis,
        observations=len(inputs.returns),
    )


def _drawdown(inputs: DrawdownInputs) -> DrawdownOutputs:
    found = max_drawdown(inputs.values)
    return DrawdownOutputs(
        max_drawdown=found.depth, peak_index=found.peak, trough_index=found.trough
    )


# --- the model ---------------------------------------------------------------

_JOANES_GILL = Reference(
    key="joanes1998",
    citation=(
        "Joanes, D. N. and Gill, C. A. (1998). Comparing measures of sample "
        "skewness and kurtosis. Journal of the Royal Statistical Society: "
        "Series D (The Statistician), 47(1), 183-189."
    ),
    doi="10.1111/1467-9884.00122",
    locator="Section 2 (the estimators b, g and G)",
)
_CHAN = Reference(
    key="chan1983",
    citation=(
        "Chan, T. F., Golub, G. H. and LeVeque, R. J. (1983). Algorithms for "
        "computing the sample variance: analysis and recommendations. The "
        "American Statistician, 37(3), 242-247."
    ),
    doi="10.1080/00031305.1983.10483115",
    locator="Section 2 (the corrected two-pass algorithm)",
)
_NIST_SKEW = Reference(
    key="nist_skewness",
    citation=(
        "NIST/SEMATECH (2012). e-Handbook of Statistical Methods, section "
        "1.3.5.11, Measures of Skewness and Kurtosis."
    ),
    url="https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm",
    locator="Section 1.3.5.11",
)
_SORTINO = Reference(
    key="sortino1994",
    citation=(
        "Sortino, F. A. and Price, L. N. (1994). Performance measurement in a "
        "downside risk framework. The Journal of Investing, 3(3), 59-64."
    ),
    doi="10.3905/joi.3.3.59",
    locator="The downside deviation below a minimum acceptable return",
)


@model(
    id="foundations.risk_statistics",
    version=1,
    title="Risk statistics",
    summary=(
        "Sample volatility and its annualization, semideviation, adjusted "
        "skewness and excess kurtosis, and maximum drawdown."
    ),
    formula=(
        (
            r"s = \sqrt{\frac{1}{n-1}\sum (r_t - \bar{r})^2}, \quad "
            r"\sigma_{\mathrm{annual}} = s \sqrt{m}"
        ),
        r"SD_{\bar{r}} = \sqrt{\frac{1}{n-1}\sum \min(r_t - \bar{r}, 0)^2}",
        r"DD_T = \sqrt{\frac{1}{n}\sum \min(r_t - T, 0)^2}",
        r"G_1 = \frac{\sqrt{n(n-1)}}{n-2}\,\frac{m_3}{m_2^{3/2}}",
        r"G_2 = \frac{n-1}{(n-2)(n-3)}\left[(n+1)\frac{m_4}{m_2^2} - 3(n-1)\right]",
        r"MDD = \max_j \left(1 - \frac{V_j}{\max_{i \le j} V_i}\right)",
    ),
    symbols=(
        Symbol("s", "Sample standard deviation of the returns", "volatility"),
        Symbol("r_t", "The return in period t", "returns"),
        Symbol(r"\bar{r}", "Mean return", "mean"),
        Symbol("n", "Number of returns", "observations"),
        Symbol(
            r"\sigma_{\mathrm{annual}}",
            "Volatility for a year",
            "annualized_volatility",
        ),
        Symbol("m", "Periods in a year", "periods_per_year"),
        Symbol(
            r"SD_{\bar{r}}",
            "Semideviation: the deviation of the returns below the mean",
            "below_mean",
        ),
        Symbol("DD_T", "Downside deviation below the target", "below_target"),
        Symbol("T", "Target return per period", "target"),
        Symbol("G_1", "Sample skewness", "skewness"),
        Symbol("G_2", "Sample excess kurtosis", "excess_kurtosis"),
        Symbol(
            "m_2",
            "The returns' second central moment; m_3 and m_4 are the third and fourth",
        ),
        Symbol("MDD", "Maximum drawdown", "max_drawdown"),
        Symbol("V_j", "The value at observation j", "values"),
    ),
    assumptions=(
        (
            "Returns are decimals over equal periods; annualizing by the square "
            "root of the periods in a year assumes they are independent and "
            "identically distributed."
        ),
        (
            "The variance divides by n - 1; the semideviation below the mean by "
            "n - 1 and below a given target by n."
        ),
        "A drawdown is measured on values above zero, in time order.",
    ),
    limitations=(
        (
            "Skewness and kurtosis are undefined for a series with no spread: "
            "DomainError."
        ),
        "No statistic here corrects for autocorrelation or fat tails.",
    ),
    references=(_JOANES_GILL, _CHAN, _NIST_SKEW, _SORTINO),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("volatility", "semideviation", "skewness", "kurtosis", "drawdown"),
    invariants=(
        Invariant(
            id="volatility_scale_equivariant",
            statement=(
                "Multiplying every return by c multiplies the volatility by |c|."
            ),
        ),
        Invariant(
            id="volatility_shift_invariant",
            statement=(
                "Adding a constant to every return leaves the volatility unchanged."
            ),
        ),
        Invariant(
            id="drawdown_between_zero_and_one",
            statement=(
                "The maximum drawdown lies in [0, 1], and its peak comes no later "
                "than its trough."
            ),
        ),
    ),
    examples=(
        Example(
            name="monthly_volatility",
            inputs={
                "calculation": "volatility",
                "returns": [0.02, -0.01, 0.03, 0.005, -0.02, 0.01],
                "periods_per_year": 12,
            },
        ),
        Example(
            name="downside",
            inputs={
                "calculation": "semideviation",
                "returns": [0.02, -0.01, 0.03, 0.005, -0.02, 0.01],
            },
        ),
        Example(
            name="shape",
            inputs={
                "calculation": "moments",
                "returns": [0.02, -0.01, 0.03, 0.005, -0.02, 0.01],
            },
        ),
        Example(
            name="index_drawdown",
            inputs={
                "calculation": "drawdown",
                "values": [100, 120, 90, 130, 117],
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def risk_statistics(inputs: RiskStatisticsInputs) -> RiskStatisticsOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], RiskStatisticsOutputs]]
] = {
    VolatilityInputs: _volatility,
    SemideviationInputs: _semideviation,
    MomentsInputs: _moments,
    DrawdownInputs: _drawdown,
}
