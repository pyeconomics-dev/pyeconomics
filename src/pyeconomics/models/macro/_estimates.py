# src/pyeconomics/models/macro/_estimates.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the macro estimators share: a slope on one gap, fitted by least squares.

``macro.phillips_curve`` and ``macro.okun_law`` each regress one series on
another (and, for the Phillips curve, on optional controls) with
:func:`pyeconomics.core.least_squares`, and report the same estimates.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import Field

from pyeconomics.core import (
    Count,
    DomainError,
    ModelInputs,
    ModelOutputs,
    Ratio,
    least_squares,
    warn,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.core import LeastSquares

#: The most observations an estimator takes: 250 years of quarters.
OBSERVATIONS_MAX: Final = 1_000
#: The most Newey-West lags.
LAGS_MAX: Final = 100
#: Estimates beyond these come from a regressor that barely varies; the model
#: raises DomainError rather than report them.
ESTIMATE_MAX: Final = 1e9

type CovarianceName = Literal["classical", "hc1", "newey_west"]

_Estimate = Annotated[Ratio, Field(ge=-ESTIMATE_MAX, le=ESTIMATE_MAX)]
_Error = Annotated[Ratio, Field(ge=0.0, le=ESTIMATE_MAX)]


class Inference(ModelInputs):
    """How the standard errors are computed."""

    covariance: CovarianceName = Field(
        "newey_west",
        description=(
            "Standard errors: 'newey_west' (heteroskedasticity and autocorrelation "
            "consistent), 'hc1' (heteroskedasticity consistent) or 'classical'"
        ),
    )
    lags: Count | None = Field(
        None,
        ge=0,
        le=LAGS_MAX,
        description=(
            "Newey-West lags; left out, Newey and West's rule floor(4 (n/100)^(2/9))"
        ),
    )


class Estimates(ModelOutputs):
    """The slope on the gap and the intercept, with their standard errors."""

    slope: _Estimate = Field(description="The coefficient on the gap")
    intercept: _Estimate = Field(description="The constant")
    slope_standard_error: _Error = Field(description="The slope's standard error")
    intercept_standard_error: _Error = Field(
        description="The intercept's standard error"
    )
    slope_t_statistic: _Estimate | None = Field(
        description=(
            "The slope over its standard error; None for a fit exact to rounding"
        )
    )
    r_squared: Ratio | None = Field(
        ge=0.0,
        le=1.0,
        description="R-squared; None when the dependent variable does not vary",
    )
    observations: Count = Field(
        ge=3, le=OBSERVATIONS_MAX, description="Observations in the regression"
    )
    hac_lags: Count = Field(
        ge=0, le=LAGS_MAX, description="Newey-West lags used; 0 for the others"
    )


def _bounded(values: Sequence[float], what: str) -> tuple[float, ...]:
    if not all(math.isfinite(v) and abs(v) <= ESTIMATE_MAX for v in values):
        msg = (
            f"a {what} passes {ESTIMATE_MAX:g}: the gap barely varies, so the "
            "slope is not identified to any useful precision"
        )
        raise DomainError(msg)
    return tuple(values)


def check_lags(lags: int | None, observations: int) -> None:
    """Refuse a lag the sample cannot carry (an input rule, so ``ValueError``)."""
    if lags is not None and lags >= observations:
        msg = f"lags must be below the {observations} observations"
        raise ValueError(msg)


def estimate(
    response: Sequence[float],
    regressors: Sequence[Sequence[float]],
    inference: Inference,
) -> tuple[dict[str, Any], LeastSquares]:
    """Regress ``response`` on a constant and ``regressors`` (the gap first)."""
    design = list(zip(*regressors, strict=True))
    fit = least_squares(
        response, design, covariance=inference.covariance, lags=inference.lags
    )
    coefficients = _bounded(fit.coefficients, "coefficient")
    errors = _bounded(fit.standard_errors, "standard error")
    t_statistic = None
    if fit.t_statistics is None:
        warn(
            "exact_fit",
            "the regression fits exactly: its standard errors are zero and it has "
            "no t statistic",
        )
    elif abs(fit.t_statistics[1]) <= ESTIMATE_MAX:
        t_statistic = fit.t_statistics[1]
    else:
        warn(
            "near_exact_fit",
            f"the slope's t statistic passes {ESTIMATE_MAX:g}: the fit is exact but "
            "for rounding, so no t statistic is reported",
        )
    if fit.r_squared is None:
        warn("no_variation", "the dependent variable does not vary: no R-squared")
    return {
        "slope": coefficients[1],
        "intercept": coefficients[0],
        "slope_standard_error": errors[1],
        "intercept_standard_error": errors[0],
        "slope_t_statistic": t_statistic,
        "r_squared": fit.r_squared,
        "observations": fit.observations,
        "hac_lags": fit.lags,
    }, fit
