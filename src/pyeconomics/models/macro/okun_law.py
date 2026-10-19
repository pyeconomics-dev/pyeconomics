# src/pyeconomics/models/macro/okun_law.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Okun's law: ``macro.okun_law``.

Okun (1962) related output to unemployment in two forms, estimated here by least
squares as two calculations discriminated on ``calculation``:

- ``gap``: the output gap on the unemployment gap,
  :math:`y_t = a + b\,(u_t - u^*_t) + e_t`, where :math:`-b`, about 2, is Okun's
  coefficient;
- ``difference``: Okun's first-difference form, the change in unemployment on
  output growth over the same span, :math:`\Delta u_t = a + b\,g_t + e_t`; the
  growth that holds unemployment constant is :math:`-a / b` (the economy's trend
  growth, in Okun's reading).

Growth is :math:`Y_t / Y_{t-k} - 1` and the change :math:`u_t - u_{t-k}` over a
span of :math:`k` periods (1 by default; 4 with quarterly data gives the
year-over-year form); with ``periods_per_year`` :math:`m`, growth is annualized
by compounding, :math:`(Y_t / Y_{t-k})^{m/k} - 1`, the form that reproduces
Knotek's (2007) estimates.
Standard errors are Newey-West by default.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    Money,
    Rate,
    Ratio,
    Reference,
    model,
    warn,
)
from pyeconomics.models.macro._estimates import (
    ESTIMATE_MAX,
    OBSERVATIONS_MAX,
    Estimates,
    Inference,
    check_lags,
    estimate,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["okun_law"]

_GAP_MAX: Final = 0.3
_UNEMPLOYMENT_MAX: Final = 0.3
_LEVEL_MAX: Final = 1e15
_SPAN_MAX: Final = 12
_PERIODS_PER_YEAR_MAX: Final = 12

_Gap = Annotated[Rate, Field(ge=-_GAP_MAX, le=_GAP_MAX)]
_Unemployment = Annotated[Rate, Field(ge=0.0, le=_UNEMPLOYMENT_MAX)]
_Level = Annotated[Money, Field(gt=0.0, le=_LEVEL_MAX)]


class GapInputs(Inference):
    """The gap form: the output gap on the unemployment gap."""

    calculation: Literal["gap"] = Field(
        "gap", description="The output gap on the unemployment gap"
    )
    output_gap: Annotated[tuple[_Gap, ...], ARRAY_INPUT] = Field(
        min_length=3,
        max_length=OBSERVATIONS_MAX,
        description="The output gap each period (real GDP over potential, less one)",
    )
    unemployment: Annotated[tuple[_Unemployment, ...], ARRAY_INPUT] = Field(
        min_length=3,
        max_length=OBSERVATIONS_MAX,
        description="The unemployment rate each period",
    )
    natural_unemployment: Annotated[tuple[_Unemployment, ...], ARRAY_INPUT] = Field(
        min_length=3,
        max_length=OBSERVATIONS_MAX,
        description="The natural rate of unemployment each period",
    )

    @model_validator(mode="after")
    def _one_sample(self) -> Self:
        periods = len(self.output_gap)
        for name in ("unemployment", "natural_unemployment"):
            if len(getattr(self, name)) != periods:
                msg = (
                    f"{name} has {len(getattr(self, name))} periods; output_gap "
                    f"has {periods}"
                )
                raise ValueError(msg)
        check_lags(self.lags, periods)
        return self


class DifferenceInputs(Inference):
    """The difference form: the change in unemployment on output growth."""

    calculation: Literal["difference"] = Field(
        "difference", description="The change in unemployment on output growth"
    )
    output: Annotated[tuple[_Level, ...], ARRAY_INPUT] = Field(
        min_length=4,
        max_length=OBSERVATIONS_MAX,
        description="Real output each period, positive",
    )
    unemployment: Annotated[tuple[_Unemployment, ...], ARRAY_INPUT] = Field(
        min_length=4,
        max_length=OBSERVATIONS_MAX,
        description="The unemployment rate each period",
    )
    span: Count = Field(
        1,
        ge=1,
        le=_SPAN_MAX,
        description="Periods each growth rate and change spans (4 for over a year)",
    )
    periods_per_year: Count | None = Field(
        None,
        ge=1,
        le=_PERIODS_PER_YEAR_MAX,
        description=(
            "Periods in a year, to annualize growth by compounding (4 for quarterly "
            "data); left out, growth is over the span"
        ),
    )

    @model_validator(mode="after")
    def _one_sample(self) -> Self:
        periods = len(self.output)
        if len(self.unemployment) != periods:
            msg = (
                f"unemployment has {len(self.unemployment)} periods; output has "
                f"{periods}"
            )
            raise ValueError(msg)
        observations = periods - self.span
        if observations < 3:  # noqa: PLR2004 - two coefficients need three points
            msg = (
                f"a span of {self.span} leaves {observations} changes; the "
                "regression needs at least 3"
            )
            raise ValueError(msg)
        check_lags(self.lags, observations)
        return self


OkunLawInputs = Annotated[
    GapInputs | DifferenceInputs, Field(discriminator="calculation")
]


class GapOutputs(Estimates):
    calculation: Literal["gap"] = Field(
        "gap", description="The output gap on the unemployment gap"
    )


class DifferenceOutputs(Estimates):
    calculation: Literal["difference"] = Field(
        "difference", description="The change in unemployment on output growth"
    )
    constant_unemployment_growth: Ratio | None = Field(
        ge=-ESTIMATE_MAX,
        le=ESTIMATE_MAX,
        description=(
            "The growth that holds unemployment constant, -intercept / slope, "
            "annualized as growth is; None when the slope is zero"
        ),
    )


OkunLawOutputs = Annotated[
    GapOutputs | DifferenceOutputs, Field(discriminator="calculation")
]


def _gap(inputs: GapInputs) -> GapOutputs:
    unemployment_gap = [
        u - natural
        for u, natural in zip(
            inputs.unemployment, inputs.natural_unemployment, strict=True
        )
    ]
    estimates, _ = estimate(inputs.output_gap, [unemployment_gap], inputs)
    return GapOutputs(**estimates)


def _difference(inputs: DifferenceInputs) -> DifferenceOutputs:
    k = inputs.span
    output, unemployment = inputs.output, inputs.unemployment
    power = 1.0 if inputs.periods_per_year is None else inputs.periods_per_year / k
    with np.errstate(over="ignore", divide="ignore"):
        ratios = np.asarray(output[k:]) / np.asarray(output[:-k])
        growth = np.expm1(power * np.log(ratios))
    if not np.all(np.isfinite(growth)):
        msg = "output grows by a factor beyond representation between two periods"
        raise DomainError(msg)
    change = [unemployment[t] - unemployment[t - k] for t in range(k, len(output))]
    estimates, _ = estimate(change, [growth.tolist()], inputs)
    slope, intercept = estimates["slope"], estimates["intercept"]
    steady = -intercept / slope if slope != 0 else math.inf
    if not abs(steady) <= ESTIMATE_MAX:
        warn(
            "no_constant_unemployment_growth",
            "the slope is zero (or nearly), so no growth rate holds unemployment "
            "constant",
        )
        steady = None
    return DifferenceOutputs(**estimates, constant_unemployment_growth=steady)


_OKUN = Reference(
    key="okun1962",
    citation=(
        "Okun, A. M. (1962). Potential GNP: Its Measurement and Significance. "
        "Proceedings of the Business and Economic Statistics Section of the "
        "American Statistical Association, 98-104."
    ),
    url="https://milescorak.com/wp-content/uploads/2016/01/okun-potential-gnp-its-measurement-and-significance-p0190.pdf",
    locator="The first-differences and gap relations between output and unemployment",
)
_KNOTEK = Reference(
    key="knotek2007",
    citation=(
        "Knotek, E. S. II (2007). How Useful Is Okun's Law? Federal Reserve Bank "
        "of Kansas City Economic Review, 92(4), 73-103."
    ),
    url=(
        "https://www.kansascityfed.org/Economic%20Review/documents/955/"
        "2007-How%20Useful%20is%20Okun%27s%20Law%3F.pdf"
    ),
    locator="The difference and gap versions estimated on US data",
)
_BALL = Reference(
    key="ball2017",
    citation=(
        "Ball, L., Leigh, D. and Loungani, P. (2017). Okun's Law: Fit at 50? "
        "Journal of Money, Credit and Banking, 49(7), 1413-1441."
    ),
    doi="10.1111/jmcb.12420",
    locator="The gap version across countries and its stability",
)

#: Quarterly: the quarter's last month, which a month the source left out of
#: another month of the quarter (October 2025's household survey) leaves whole.
_QUARTERLY: Final = "convert(to=quarterly,method=last)"
_WINDOW: Final = 120


@model(
    id="macro.okun_law",
    version=1,
    title="Okun's law",
    summary=(
        "Okun's law estimated in its gap form (the output gap on the unemployment "
        "gap) and its first-difference form (the change in unemployment on output "
        "growth, with the growth that holds unemployment constant)."
    ),
    formula=(
        r"y_t = a + b\,(u_t - u^*_t) + e_t \quad \text{(gap; Okun's coefficient } -b)",
        (
            r"u_t - u_{t-k} = a + b\,g_t + e_t, \quad g_t = "
            r"\left(\frac{Y_t}{Y_{t-k}}\right)^{m/k} - 1 \quad "
            r"\text{(difference; constant-unemployment growth } -a/b)"
        ),
    ),
    assumptions=(
        (
            "Least squares on the given series; Newey-West errors by default, with "
            "Bartlett weights, no small-sample correction and Newey and West's lag "
            "rule when no lag is given."
        ),
        (
            "The output gap is a ratio (real GDP over potential, less one); growth "
            "is a rate over the span, annualized by compounding when "
            "periods_per_year is given; unemployment rates are decimals."
        ),
        (
            "Profile: default binds 120 quarters of real GDP over CBO's potential, "
            "the unemployment rate (the quarter's last month) and CBO's noncyclical "
            "rate for the gap form, and real GDP with the unemployment rate for the "
            "difference form."
        ),
    ),
    limitations=(
        (
            "Okun's law is an empirical regularity, not a structural relation: the "
            "coefficient varies over time and across countries and shifts in "
            "recessions."
        ),
        (
            "The difference form's constant-unemployment growth is undefined when "
            "the slope is zero: None, with a warning."
        ),
        (
            "A gap or a change that barely varies leaves the slope unidentified, "
            "and output that changes by a factor beyond representation has no "
            "growth rate: both raise DomainError."
        ),
        (
            "Monthly unemployment is read at each quarter's last month: a quarter's "
            "average is missing when the source left a month out (BLS published no "
            "October 2025 household survey), and a window never takes a gap."
        ),
        (
            "In hosted mode, where FRED is refused, the originators serve too "
            "short a history for the default windows (BLS about three years, "
            "CBO's potential and natural rate from 2021), so the bind raises: "
            "supply the series instead."
        ),
    ),
    references=(_OKUN, _KNOTEK, _BALL),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.INSTANT,
    tags=("okun law", "output gap", "unemployment", "potential output", "regression"),
    invariants=(
        Invariant(
            id="exact_linear_data_recovers_coefficient",
            statement=(
                "When the dependent series is an exact line in the regressor, the "
                "estimate is that line's slope and intercept, in either form."
            ),
        ),
    ),
    examples=(
        Example(
            name="gap_form",
            inputs={
                "calculation": "gap",
                "output_gap": [
                    0.004,
                    0.009,
                    0.012,
                    0.01,
                    0.002,
                    -0.006,
                    -0.008,
                    -0.005,
                ],
                "unemployment": [0.042, 0.04, 0.038, 0.039, 0.043, 0.047, 0.048, 0.046],
                "natural_unemployment": [0.044] * 8,
            },
        ),
        Example(
            name="difference_form",
            inputs={
                "calculation": "difference",
                "output": [100.0, 100.8, 101.5, 101.4, 100.9, 101.6, 102.4, 103.1],
                "unemployment": [0.04, 0.039, 0.039, 0.041, 0.045, 0.044, 0.042, 0.041],
                "periods_per_year": 4,
            },
            note="Quarterly data, growth annualized as Knotek (2007) states it.",
        ),
    ),
    bindings=(
        Binding(
            "output_gap",
            "us.output_gap.real_potential",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
        ),
        Binding(
            "unemployment",
            "us.unemployment.rate",
            transform=_QUARTERLY,
            as_of=AsOf.WINDOW,
            window=_WINDOW,
        ),
        Binding(
            "natural_unemployment",
            "us.unemployment.noncyclical_rate",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
        ),
        Binding("output", "us.output.real_gdp", as_of=AsOf.WINDOW, window=_WINDOW),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def okun_law(inputs: OkunLawInputs) -> OkunLawOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], OkunLawOutputs]]] = {
    GapInputs: _gap,
    DifferenceInputs: _difference,
}
