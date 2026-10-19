# src/pyeconomics/models/macro/phillips_curve.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The expectations-augmented Phillips curve: ``macro.phillips_curve``.

Inflation above what was expected goes with unemployment below its natural rate
(Phelps 1967; Friedman 1968). The estimator regresses the inflation surprise on
the unemployment gap by least squares,

.. math:: \pi_t - \pi^e_t = \alpha + \beta (u_t - u^*_t) + \gamma' z_t + e_t,

with optional supply-shock controls :math:`z_t` (Gordon 1982's import-price or
food-and-energy terms), and reports the slope :math:`\beta`, the intercept, their
standard errors (Newey-West by default, since the errors of overlapping
inflation rates are autocorrelated), R² and the sample size. A negative slope is
the curve; how stable and how steep it is remain disputed.
"""

from __future__ import annotations

from typing import Annotated, Final, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    Rate,
    Ratio,
    Reference,
    model,
)
from pyeconomics.models.macro._estimates import (
    ESTIMATE_MAX,
    OBSERVATIONS_MAX,
    Estimates,
    Inference,
    check_lags,
    estimate,
)

__all__ = ["phillips_curve"]

#: Supply-shock controls: at most four series, each a decimal in [-10, 10].
CONTROLS_MAX: Final = 4
_CONTROL_MAX: Final = 10.0
_INFLATION_MIN: Final = -0.2
_INFLATION_MAX: Final = 0.5
_UNEMPLOYMENT_MAX: Final = 0.3

_Inflation = Annotated[Rate, Field(ge=_INFLATION_MIN, le=_INFLATION_MAX)]
_Unemployment = Annotated[Rate, Field(ge=0.0, le=_UNEMPLOYMENT_MAX)]
_Control = Annotated[Ratio, Field(ge=-_CONTROL_MAX, le=_CONTROL_MAX)]


class PhillipsCurveInputs(Inference):
    inflation: Annotated[tuple[_Inflation, ...], ARRAY_INPUT] = Field(
        min_length=3,
        max_length=OBSERVATIONS_MAX,
        description="Inflation each period",
    )
    expected_inflation: Annotated[tuple[_Inflation, ...], ARRAY_INPUT] = Field(
        min_length=3,
        max_length=OBSERVATIONS_MAX,
        description="Inflation expected for each period",
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
    supply_shocks: (
        tuple[
            Annotated[
                tuple[_Control, ...],
                Field(min_length=3, max_length=OBSERVATIONS_MAX),
                ARRAY_INPUT,
            ],
            ...,
        ]
        | None
    ) = Field(
        None,
        min_length=1,
        max_length=CONTROLS_MAX,
        description=(
            "Up to four supply-shock controls, one series each (relative import "
            "price inflation, say), as extra regressors"
        ),
    )

    @model_validator(mode="after")
    def _one_sample(self) -> Self:
        periods = len(self.inflation)
        series = {
            "expected_inflation": self.expected_inflation,
            "unemployment": self.unemployment,
            "natural_unemployment": self.natural_unemployment,
        }
        for i, control in enumerate(self.supply_shocks or ()):
            series[f"supply_shocks[{i}]"] = control
        for name, values in series.items():
            if len(values) != periods:
                msg = f"{name} has {len(values)} periods; inflation has {periods}"
                raise ValueError(msg)
        coefficients = 2 + len(self.supply_shocks or ())
        if periods <= coefficients:
            msg = f"{coefficients} coefficients need more than {coefficients} periods"
            raise ValueError(msg)
        check_lags(self.lags, periods)
        return self


_Estimate = Annotated[Ratio, Field(ge=-ESTIMATE_MAX, le=ESTIMATE_MAX)]
_Error = Annotated[Ratio, Field(ge=0.0, le=ESTIMATE_MAX)]


class PhillipsCurveOutputs(Estimates):
    control_coefficients: Annotated[tuple[_Estimate, ...], ARRAY_INPUT] = Field(
        max_length=CONTROLS_MAX,
        description="The coefficient on each supply-shock control, in order",
    )
    control_standard_errors: Annotated[tuple[_Error, ...], ARRAY_INPUT] = Field(
        max_length=CONTROLS_MAX, description="Their standard errors"
    )


_PHELPS = Reference(
    key="phelps1967",
    citation=(
        "Phelps, E. S. (1967). Phillips Curves, Expectations of Inflation and "
        "Optimal Unemployment over Time. Economica, 34(135), 254-281."
    ),
    doi="10.2307/2552025",
    locator="The expectations-augmented curve",
)
_FRIEDMAN = Reference(
    key="friedman",
    citation=(
        "Friedman, M. (1968). The Role of Monetary Policy. American Economic "
        "Review, 58(1), 1-17."
    ),
    url="https://www.aeaweb.org/aer/top20/58.1.1-17.pdf",
    locator="The natural rate of unemployment and expected inflation",
)
_GORDON = Reference(
    key="gordon1982",
    citation=(
        "Gordon, R. J. (1982). Inflation, Flexible Exchange Rates, and the Natural "
        "Rate of Unemployment. In M. N. Baily (ed.), Workers, Jobs, and "
        "Inflation, pp. 89-158. Brookings Institution."
    ),
    url="https://www.nber.org/papers/w0708",
    locator="The triangle model's supply-shock terms",
)
_NEWEY_WEST = Reference(
    key="newey1987",
    citation=(
        "Newey, W. K. and West, K. D. (1987). A simple, positive semi-definite, "
        "heteroskedasticity and autocorrelation consistent covariance matrix. "
        "Econometrica, 55(3), 703-708."
    ),
    doi="10.2307/1913610",
    locator="Bartlett weights 1 - j / (L + 1)",
)

#: Quarterly: the quarter's last month, which a month the source left out of
#: another month of the quarter (October 2025's household survey) leaves whole.
_QUARTERLY: Final = "convert(to=quarterly,method=last)"


def _bindings(
    profile: str, prices: str, expected: str, window: int
) -> tuple[Binding, ...]:
    return (
        Binding(
            "inflation",
            prices,
            transform=_QUARTERLY,
            as_of=AsOf.WINDOW,
            window=window,
            profile=profile,
        ),
        Binding(
            "expected_inflation",
            expected,
            as_of=AsOf.WINDOW,
            window=window,
            profile=profile,
        ),
        Binding(
            "unemployment",
            "us.unemployment.rate",
            transform=_QUARTERLY,
            as_of=AsOf.WINDOW,
            window=window,
            profile=profile,
        ),
        Binding(
            "natural_unemployment",
            "us.unemployment.noncyclical_rate",
            as_of=AsOf.WINDOW,
            window=window,
            profile=profile,
        ),
    )


@model(
    id="macro.phillips_curve",
    version=1,
    title="Expectations-augmented Phillips curve",
    summary=(
        "Inflation less expected inflation regressed on the unemployment gap, "
        "with optional supply-shock controls and Newey-West errors: the slope, "
        "intercept, standard errors and R-squared."
    ),
    formula=(
        r"\pi_t - \pi^e_t = \alpha + \beta\,(u_t - u^*_t) + \gamma' z_t + e_t",
        (
            r"\hat\beta, \hat\alpha \text{ by least squares}; \quad "
            r"V_{NW} = (X'X)^{-1} \hat S (X'X)^{-1}"
        ),
    ),
    assumptions=(
        (
            "Expected inflation is given (a survey, or a forecast), not estimated; "
            "the natural rate is given each period."
        ),
        (
            "The coefficients are least squares; Newey-West errors use Bartlett "
            "weights with no small-sample correction and, with no lag given, "
            "floor(4 (n/100)^(2/9)) lags."
        ),
        (
            "Profiles: default binds 60 quarters of core PCE inflation over four "
            "quarters (the quarter's last month), the SPF's median 10-year PCE "
            "inflation expectation, the unemployment rate (the quarter's last month) "
            "and CBO's noncyclical rate; us_cpi binds 120 quarters of CPI "
            "inflation with the SPF's 10-year CPI expectation."
        ),
    ),
    limitations=(
        (
            "The curve's slope and stability are disputed: estimates flattened "
            "after the 1990s and differ by sample and measure. Read the slope as "
            "a summary of the sample, not a structural constant."
        ),
        (
            "Long-run expectations stand in for expected inflation in the "
            "profiles; with year-over-year inflation the errors overlap, which the "
            "Newey-West errors allow for."
        ),
        (
            "A monthly series is read at each quarter's last month: a quarter's "
            "average is missing when the source left a month out (BLS published no "
            "October 2025 household survey), and a window never takes a gap."
        ),
        (
            "An unemployment gap that barely varies leaves the slope unidentified: "
            "DomainError."
        ),
        (
            "In hosted mode, where FRED is refused, the originators serve too "
            "short a history for the default windows (BLS about three years, "
            "CBO's potential and natural rate from 2021), so the bind raises: "
            "supply the series instead."
        ),
    ),
    references=(_PHELPS, _FRIEDMAN, _GORDON, _NEWEY_WEST),
    evidence=Evidence.CONTESTED,
    cost=CostClass.INSTANT,
    tags=("phillips curve", "inflation", "unemployment", "natural rate", "regression"),
    invariants=(
        Invariant(
            id="exact_linear_data_recovers_slope",
            statement=(
                "When the inflation surprise is an exact line in the unemployment "
                "gap, the estimate is that line's slope and intercept."
            ),
        ),
    ),
    examples=(
        Example(
            name="eight_quarters",
            inputs={
                "inflation": [0.031, 0.034, 0.038, 0.035, 0.029, 0.026, 0.024, 0.023],
                "expected_inflation": [
                    0.021,
                    0.021,
                    0.022,
                    0.022,
                    0.022,
                    0.021,
                    0.021,
                    0.021,
                ],
                "unemployment": [
                    0.041,
                    0.038,
                    0.036,
                    0.037,
                    0.039,
                    0.041,
                    0.042,
                    0.043,
                ],
                "natural_unemployment": [
                    0.044,
                    0.044,
                    0.044,
                    0.044,
                    0.044,
                    0.044,
                    0.043,
                    0.043,
                ],
            },
        ),
    ),
    bindings=(
        *_bindings("default", "us.inflation.pce_core.yoy", "us.spf.pce.median_10y", 60),
        *_bindings("us_cpi", "us.inflation.cpi.yoy", "us.spf.cpi.median_10y", 120),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def phillips_curve(inputs: PhillipsCurveInputs) -> PhillipsCurveOutputs:
    """Regress the inflation surprise on the unemployment gap."""
    surprise = [
        pi - expected
        for pi, expected in zip(
            inputs.inflation, inputs.expected_inflation, strict=True
        )
    ]
    gap = [
        u - natural
        for u, natural in zip(
            inputs.unemployment, inputs.natural_unemployment, strict=True
        )
    ]
    controls = list(inputs.supply_shocks or ())
    estimates, fit = estimate(surprise, [gap, *controls], inputs)
    return PhillipsCurveOutputs(
        **estimates,
        control_coefficients=fit.coefficients[2:],
        control_standard_errors=fit.standard_errors[2:],
    )
