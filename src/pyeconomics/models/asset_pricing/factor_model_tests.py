# src/pyeconomics/models/asset_pricing/factor_model_tests.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Tests of factor models: ``asset_pricing.factor_model_tests``.

Two tests of whether a set of factors prices a set of test assets, named by
``calculation``. Both start from each asset's time-series regression of its
excess return on the factors, :math:`r_{it} = \alpha_i + \beta_i' f_t + e_{it}`.

- ``grs``: the Gibbons-Ross-Shanken (1989) test that every alpha is zero, for
  :math:`N` assets on :math:`L` traded factors over :math:`T > N + L` periods,

  .. math:: W = \frac{T - N - L}{N}\,
     \frac{\hat\alpha' \hat\Sigma^{-1} \hat\alpha}{1 + \bar f' \hat\Omega^{-1}
     \bar f} \sim F(N,\ T - N - L),

  with :math:`\hat\Sigma` the residual covariance and :math:`\hat\Omega` the
  factor covariance, both with divisor :math:`T` (maximum likelihood), under
  normal, independent errors.
- ``fama_macbeth``: the two-pass regressions of Fama and MacBeth (1973). The
  betas come from the time-series regressions; each period's cross-section of
  excess returns is then regressed on them, :math:`r_t = \gamma_{0t} +
  B\gamma_t + \eta_t`, and the premia are the averages of the
  :math:`\gamma_t`, with standard errors from their standard deviation over
  :math:`\sqrt{T}`. Shanken's (1992) correction for the betas being estimates
  scales the part of that variance the residuals bring by :math:`1 + c`,
  :math:`c = \hat\gamma' \hat\Sigma_f^{-1} \hat\gamma`:

  .. math:: \hat V_{S} = \tfrac{1}{T}\left[(1 + c)\, A \hat\Sigma A' +
     \hat\Sigma_f^*\right], \quad A = (X'X)^{-1} X',

  where :math:`\hat\Sigma_f^*` is the factor covariance bordered by zeros for
  the intercept. Over one sample the Fama-MacBeth variance is exactly
  :math:`\tfrac{1}{T}[A \hat\Sigma A' + \hat\Sigma_f^*]` (the residuals are
  orthogonal to the factors), so this is Shanken's own form,
  :math:`(1 + c)(\hat V_{FM} - \hat\Sigma_f^*/T) + \hat\Sigma_f^*/T`, and never
  narrows the errors. Every covariance here has divisor :math:`T`, as Cochrane
  (2005, p. 246) and Goyal (2012, eq. 32) write the Fama-MacBeth variance;
  Fama and MacBeth (1973) do not state theirs.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
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
    ModelOutputs,
    Probability,
    Ratio,
    Reference,
    Return,
    least_squares,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.core.regression import CONDITION_MAX
from pyeconomics.models.asset_pricing._common import (
    ASSETS_MAX,
    ESTIMATE_MAX,
    FACTORS_MAX,
    PERIODS_MAX,
    FactorMatrix,
    ReturnMatrix,
    ReturnSeries,
    bounded,
    excess,
    matrix,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["factor_model_tests"]

#: A GRS statistic beyond this comes from residuals with almost no variance.
_STATISTIC_MAX: Final = 1e12
#: A Sharpe ratio per period beyond this comes from a factor that barely varies.
_SHARPE_MAX: Final = 1e6
#: The months a binding reads: ten years.
_WINDOW: Final = 120

type _Matrix = NDArray[np.float64]


# --- inputs ------------------------------------------------------------------


class _Panel(ModelInputs):
    """The test assets' and the factors' returns over the same periods."""

    returns: ReturnMatrix = Field(
        min_length=3,
        max_length=PERIODS_MAX,
        description=(
            "The test assets' returns, as rows: one per period, one value per "
            "asset; excess returns when risk_free is left out"
        ),
    )
    factors: FactorMatrix = Field(
        min_length=3,
        max_length=PERIODS_MAX,
        description=(
            "The factors' returns, as rows: one per period, one value per factor. "
            "Each is the excess return of a traded portfolio"
        ),
    )
    risk_free: ReturnSeries | None = Field(
        None,
        min_length=3,
        max_length=PERIODS_MAX,
        description=(
            "The risk-free return each period, subtracted from every asset's "
            "return; leave it out when returns are already excess returns"
        ),
    )

    @model_validator(mode="after")
    def _one_panel(self) -> Self:
        periods = len(self.returns)
        matrix(self.returns, "returns")
        matrix(self.factors, "factors")
        if len(self.factors) != periods:
            msg = f"factors has {len(self.factors)} periods; returns has {periods}"
            raise ValueError(msg)
        if self.risk_free is not None and len(self.risk_free) != periods:
            msg = f"risk_free has {len(self.risk_free)} periods; returns has {periods}"
            raise ValueError(msg)
        if periods <= self.factor_count + 1:
            msg = (
                f"a time-series regression on {self.factor_count} factors needs "
                f"more than {self.factor_count + 1} periods"
            )
            raise ValueError(msg)
        return self

    @property
    def asset_count(self) -> int:
        return len(self.returns[0])

    @property
    def factor_count(self) -> int:
        return len(self.factors[0])


class GrsInputs(_Panel):
    """The test assets and traded factors, over more periods than both."""

    calculation: Literal["grs"] = Field(
        "grs", description="The Gibbons-Ross-Shanken test that every alpha is zero"
    )

    @model_validator(mode="after")
    def _enough_periods(self) -> Self:
        periods, assets, factors = (
            len(self.returns),
            self.asset_count,
            self.factor_count,
        )
        if periods <= assets + factors:
            msg = (
                f"the GRS test of {assets} assets on {factors} factors needs more "
                f"than {assets + factors} periods, not {periods}"
            )
            raise ValueError(msg)
        return self


class FamaMacBethInputs(_Panel):
    """The test assets and factors, and how to run the cross-sections."""

    calculation: Literal["fama_macbeth"] = Field(
        "fama_macbeth",
        description="Fama-MacBeth two-pass regressions of returns on betas",
    )
    intercept: bool = Field(
        default=True,
        description=(
            "Include a constant in each cross-sectional regression: the zero-beta "
            "excess return; without it the constant is held at zero"
        ),
    )

    @model_validator(mode="after")
    def _enough_assets(self) -> Self:
        needed = self.factor_count + int(self.intercept)
        if self.asset_count <= needed:
            msg = (
                f"a cross-section of {needed} coefficients needs more than {needed} "
                f"assets, not {self.asset_count}"
            )
            raise ValueError(msg)
        return self


FactorModelTestsInputs = Annotated[
    GrsInputs | FamaMacBethInputs, Field(discriminator="calculation")
]


# --- outputs -----------------------------------------------------------------

_Estimate = Annotated[Ratio, Field(ge=-ESTIMATE_MAX, le=ESTIMATE_MAX)]
_Error = Annotated[Ratio, Field(ge=0.0, le=ESTIMATE_MAX)]
_Premium = Annotated[Return, Field(ge=-ESTIMATE_MAX, le=ESTIMATE_MAX)]
_ReturnError = Annotated[Return, Field(ge=0.0, le=ESTIMATE_MAX)]
_PerFactor = Field(max_length=FACTORS_MAX)
_BetaRow = Annotated[
    tuple[_Estimate, ...], Field(min_length=1, max_length=FACTORS_MAX), ARRAY_INPUT
]


class GrsOutputs(ModelOutputs):
    calculation: Literal["grs"] = Field(
        "grs", description="The Gibbons-Ross-Shanken test that every alpha is zero"
    )
    statistic: Ratio = Field(
        ge=0.0, le=_STATISTIC_MAX, description="The GRS F statistic"
    )
    p_value: Probability = Field(
        ge=0.0,
        le=1.0,
        description=(
            "The chance of a statistic at least this large if every alpha is zero"
        ),
    )
    numerator_degrees_of_freedom: Count = Field(
        ge=1, le=ASSETS_MAX, description="N, the test assets"
    )
    denominator_degrees_of_freedom: Count = Field(
        ge=1, le=PERIODS_MAX, description="T - N - L"
    )
    alphas: Annotated[tuple[_Premium, ...], ARRAY_INPUT] = Field(
        max_length=ASSETS_MAX, description="Each asset's alpha per period"
    )
    mean_absolute_alpha: Return = Field(
        ge=0.0, le=ESTIMATE_MAX, description="The average absolute alpha per period"
    )
    factor_sharpe_ratio: Ratio = Field(
        ge=0.0,
        le=_SHARPE_MAX,
        description=(
            "The highest Sharpe ratio per period of a portfolio of the factors, "
            "sqrt(f' Omega^-1 f)"
        ),
    )
    observations: Count = Field(ge=3, le=PERIODS_MAX, description="T, the periods")


class FamaMacBethOutputs(ModelOutputs):
    calculation: Literal["fama_macbeth"] = Field(
        "fama_macbeth",
        description="Fama-MacBeth two-pass regressions of returns on betas",
    )
    premia: Annotated[tuple[_Premium, ...], ARRAY_INPUT] = Field(
        max_length=FACTORS_MAX,
        description="Each factor's average premium per period, in order",
    )
    premium_standard_errors: Annotated[tuple[_ReturnError, ...], ARRAY_INPUT] = Field(
        max_length=FACTORS_MAX,
        description="Fama-MacBeth standard errors of the premia",
    )
    premium_t_statistics: Annotated[tuple[_Estimate, ...], ARRAY_INPUT] = Field(
        max_length=FACTORS_MAX, description="The premia over their standard errors"
    )
    shanken_standard_errors: Annotated[tuple[_ReturnError, ...], ARRAY_INPUT] = Field(
        max_length=FACTORS_MAX,
        description=(
            "The standard errors with Shanken's errors-in-variables correction"
        ),
    )
    shanken_t_statistics: Annotated[tuple[_Estimate, ...], ARRAY_INPUT] = Field(
        max_length=FACTORS_MAX, description="The premia over the corrected errors"
    )
    intercept: _Premium | None = Field(
        description=(
            "The average cross-sectional constant per period: the zero-beta excess "
            "return; None without one"
        )
    )
    intercept_standard_error: _ReturnError | None = Field(
        description="Its Fama-MacBeth standard error; None without a constant"
    )
    intercept_t_statistic: _Estimate | None = Field(
        description=(
            "The constant over its error; None without one, or when the "
            "cross-sections fit exactly"
        )
    )
    shanken_intercept_standard_error: _ReturnError | None = Field(
        description="The constant's error with Shanken's correction; None without one"
    )
    betas: tuple[_BetaRow, ...] = Field(
        max_length=ASSETS_MAX,
        description="Each asset's time-series betas on the factors, as rows",
    )
    observations: Count = Field(ge=3, le=PERIODS_MAX, description="T, the periods")


FactorModelTestsOutputs = Annotated[
    GrsOutputs | FamaMacBethOutputs, Field(discriminator="calculation")
]


# --- the calculations --------------------------------------------------------


def _time_series(
    inputs: _Panel, *, spanned: bool = True
) -> tuple[_Matrix, _Matrix, _Matrix, _Matrix]:
    """Regress each asset's excess return on the factors.

    Returns the alphas (N), the betas (N x L), the residuals (T x N) and the
    factors (T x L). With ``spanned=False`` an asset the factors fit exactly
    (residuals that are rounding error) raises DomainError: its residual
    variance is zero, so the residual covariance has no inverse.
    """
    returns = excess(np.asarray(inputs.returns, dtype=np.float64), inputs.risk_free)
    factors = np.asarray(inputs.factors, dtype=np.float64)
    alphas, betas, residuals = [], [], []
    for asset, column in enumerate(returns.T, start=1):
        fit = least_squares(column, factors)
        if fit.exact and not spanned:
            msg = (
                f"test asset {asset} is an exact combination of the factors: its "
                "residual variance is zero, so the residual covariance matrix is "
                "singular and the GRS test has no statistic"
            )
            raise DomainError(msg)
        coefficients = bounded(fit.coefficients, "time-series coefficient")
        alphas.append(coefficients[0])
        betas.append(coefficients[1:])
        residuals.append(fit.residuals)
    return (
        np.asarray(alphas, dtype=np.float64),
        np.asarray(betas, dtype=np.float64),
        np.asarray(residuals, dtype=np.float64).T,
        factors,
    )


def _quadratic_inverse(vector: _Matrix, rows: _Matrix, what: str) -> float:
    r"""Return :math:`v' (R'R / n)^{-1} v` for the rows ``R``, by a QR decomposition.

    The columns are scaled to a largest magnitude of one first, so the
    decomposition is accurate; columns collinear to working precision have no
    inverse, and raise DomainError.
    """
    scales = np.max(np.abs(rows), axis=0)
    if np.any(scales == 0) or np.linalg.cond(rows / scales) > CONDITION_MAX:
        msg = (
            f"the {what} is singular to working precision (a column is, or is "
            "nearly, a combination of the others), so the test has no statistic"
        )
        raise DomainError(msg)
    _, r = np.linalg.qr(rows / scales)
    from scipy.linalg import solve_triangular  # noqa: PLC0415 - SciPy on first use

    solved = solve_triangular(r, vector / scales, trans="T")
    return len(rows) * math.fsum(float(v) * float(v) for v in solved)


def _p_value(statistic: float, numerator: int, denominator: int) -> float:
    """Return the upper tail of F(numerator, denominator) through the beta function.

    With ``y = n w / (d + n w)``, ``P(F <= w)`` is the regularized incomplete
    beta function ``I_y(n/2, d/2)``; its complement, computed as such, keeps its
    digits both for a tiny statistic (where ``1 - y`` rounds to one) and a large.
    """
    from scipy.special import betaincc  # noqa: PLC0415 - SciPy on first use

    scaled = numerator * statistic
    y = scaled / (denominator + scaled)
    tail = betaincc(
        np.float64(numerator / 2), np.float64(denominator / 2), np.float64(y)
    )
    return min(1.0, max(0.0, float(tail)))


def _grs(inputs: GrsInputs) -> GrsOutputs:
    alphas, _, residuals, factors = _time_series(inputs, spanned=False)
    periods, assets = residuals.shape
    count = factors.shape[1]
    # Divisor T for both covariances: the maximum-likelihood estimates the F
    # distribution is exact for.
    quadratic = _quadratic_inverse(alphas, residuals, "residual covariance matrix")
    means = factors.mean(axis=0)
    sharpe = _quadratic_inverse(means, factors - means, "factor covariance matrix")
    denominator = periods - assets - count
    statistic = denominator / assets * quadratic / (1.0 + sharpe)
    if not math.isfinite(statistic) or statistic > _STATISTIC_MAX:
        msg = (
            f"the GRS statistic is {statistic!r}, beyond {_STATISTIC_MAX:g}: the "
            "residuals have almost no variance, so the test is degenerate"
        )
        raise DomainError(msg)
    ratio = math.sqrt(sharpe)
    if ratio > _SHARPE_MAX:
        msg = f"the factors' Sharpe ratio is {ratio!r}: a factor barely varies"
        raise DomainError(msg)
    return GrsOutputs(
        statistic=statistic,
        p_value=_p_value(statistic, assets, denominator),
        numerator_degrees_of_freedom=assets,
        denominator_degrees_of_freedom=denominator,
        alphas=tuple(float(a) for a in alphas),
        mean_absolute_alpha=math.fsum(abs(float(a)) for a in alphas) / assets,
        factor_sharpe_ratio=ratio,
        observations=periods,
    )


def _cross_sections(design: _Matrix, returns: _Matrix) -> tuple[_Matrix, _Matrix]:
    """Regress each period's cross-section on the design, by one QR decomposition.

    Returns the coefficients of every period (T x k) and the projection
    ``(X'X)^-1 X'`` (k x N), each in the design's own units.
    """
    scales = np.max(np.abs(design), axis=0)
    if np.any(scales == 0) or np.linalg.cond(design / scales) > CONDITION_MAX:
        msg = (
            "the betas are collinear across the assets to working precision (a "
            "factor's betas barely vary, or are a combination of the others'), so "
            "the premia are not identified"
        )
        raise DomainError(msg)
    q, r = np.linalg.qr(design / scales)
    from scipy.linalg import solve_triangular  # noqa: PLC0415 - SciPy on first use

    projection = solve_triangular(r, q.T) / scales[:, None]
    return (projection @ returns.T).T, projection


def _t_statistics(values: _Matrix, errors: _Matrix) -> list[float | None]:
    found: list[float | None] = []
    for value, error in zip(values, errors, strict=True):
        t = float(value) / float(error) if error > 0 else math.inf
        found.append(t if abs(t) <= ESTIMATE_MAX else None)
    return found


def _fama_macbeth(inputs: FamaMacBethInputs) -> FamaMacBethOutputs:
    _, betas, residuals, factors = _time_series(inputs)
    returns = excess(np.asarray(inputs.returns, dtype=np.float64), inputs.risk_free)
    periods, assets = returns.shape
    constant = inputs.intercept
    design = np.column_stack([np.ones(assets), betas]) if constant else betas
    gammas, projection = _cross_sections(design, returns)
    estimates = gammas.mean(axis=0)
    # Fama and MacBeth's error: the standard deviation of each period's estimate
    # over the root of the periods, with divisor T (Cochrane; Goyal, eq. 32).
    fm_errors = _root_mean_squares(gammas - estimates) / math.sqrt(periods)
    t = _t_statistics(estimates, fm_errors)
    shanken_errors = _shanken(estimates, projection, residuals, factors, constant)
    first = 1 if constant else 0
    premia = bounded(estimates[first:].tolist(), "premium")
    premium_t = t[first:]
    if None in premium_t:
        msg = "a premium's t statistic is beyond 1e9: the cross-sections are degenerate"
        raise DomainError(msg)
    intercept_t = t[0] if constant else None
    if not constant:
        warn(
            "no_intercept",
            "the cross-sections have no constant: the zero-beta excess return is "
            "held at zero, so no intercept is estimated",
        )
    elif intercept_t is None:
        warn(
            "exact_fit",
            "the cross-sections fit exactly: the constant's error is zero and it has "
            "no t statistic",
        )
    corrected = bounded(shanken_errors[first:].tolist(), "standard error")
    return FamaMacBethOutputs(
        premia=premia,
        premium_standard_errors=bounded(fm_errors[first:].tolist(), "standard error"),
        premium_t_statistics=tuple(v for v in premium_t if v is not None),
        shanken_standard_errors=corrected,
        shanken_t_statistics=bounded(
            [p / e for p, e in zip(premia, corrected, strict=True)], "t statistic"
        ),
        intercept=float(estimates[0]) if constant else None,
        intercept_standard_error=float(fm_errors[0]) if constant else None,
        intercept_t_statistic=intercept_t,
        shanken_intercept_standard_error=(
            float(shanken_errors[0]) if constant else None
        ),
        betas=tuple(tuple(float(b) for b in row) for row in betas),
        observations=periods,
    )


def _root_sum_squares(values: _Matrix) -> float:
    """Return ``sqrt(sum(values^2))``, scaled first so tiny values keep their digits."""
    scale = float(np.max(np.abs(values))) if values.size else 0.0
    if scale == 0:
        return 0.0
    return scale * math.sqrt(math.fsum((values / scale) ** 2))


def _root_mean_squares(columns: _Matrix) -> _Matrix:
    """Return each column's root mean square, divisor T, scaled as above."""
    return np.array([_root_sum_squares(column) for column in columns.T]) / math.sqrt(
        len(columns)
    )


def _shanken(
    estimates: _Matrix,
    projection: _Matrix,
    residuals: _Matrix,
    factors: _Matrix,
    constant: bool,  # noqa: FBT001 - an internal flag
) -> _Matrix:
    """Return the standard errors with Shanken's (1992) correction."""
    periods = len(factors)
    first = 1 if constant else 0
    premia = estimates[first:]
    centred = factors - factors.mean(axis=0)
    # c = gamma' Sigma_f^-1 gamma, the squared Sharpe ratio of the premia, with
    # Sigma_f at divisor T, as the Fama-MacBeth variance has.
    c = max(_quadratic_inverse(premia, centred, "factor covariance matrix"), 0.0)
    # A Sigma A', built from the rows of A E': a sum of squares for each variance.
    # The diagonal of ((1 + c) A Sigma A' + Sigma_f*) is the mean square of the
    # scores, scaled by sqrt(1 + c), beside the factors' deviations.
    scores = (projection @ residuals.T).T * math.sqrt(1.0 + c)
    rows = [
        np.concatenate([scores[:, k], centred[:, k - first]])
        if k >= first
        else scores[:, k]
        for k in range(scores.shape[1])
    ]
    return np.array([_root_sum_squares(row) for row in rows]) / periods


# --- the model ---------------------------------------------------------------

_GRS = Reference(
    key="grs1989",
    citation=(
        "Gibbons, M. R., Ross, S. A. and Shanken, J. (1989). A Test of the "
        "Efficiency of a Given Portfolio. Econometrica, 57(5), 1121-1152."
    ),
    doi="10.2307/1913625",
    locator=(
        "Eq. (5), p. 1124, for one portfolio; the statistic for L portfolios "
        "and its F(N, T - N - L) distribution, p. 1146"
    ),
)
_FAMA_MACBETH = Reference(
    key="fm1973",
    citation=(
        "Fama, E. F. and MacBeth, J. D. (1973). Risk, Return, and Equilibrium: "
        "Empirical Tests. Journal of Political Economy, 81(3), 607-636."
    ),
    doi="10.1086/260061",
    locator=(
        "Eq. (10), p. 616, the monthly cross-sections; p. 619, the t statistic "
        "of their average"
    ),
)
_SHANKEN = Reference(
    key="shanken1992",
    citation=(
        "Shanken, J. (1992). On the Estimation of Beta-Pricing Models. The Review "
        "of Financial Studies, 5(1), 1-33."
    ),
    doi="10.1093/rfs/5.1.1",
    locator=(
        "Theorem 1 and the corrected Fama-MacBeth covariance, eq. (11), of "
        "the 1991 working paper (University of Rochester MR 91-06), pp. 15-18"
    ),
)
_COCHRANE = Reference(
    key="cochrane2005",
    citation=(
        "Cochrane, J. H. (2005). Asset Pricing, revised edition, ch. 12: "
        "Regression-Based Tests of Linear Factor Models. Princeton University "
        "Press."
    ),
    url="https://www.johnhcochrane.com/s/Cochrane_asset_pricing_CH12_229-250.pdf",
    locator=(
        "Eq. (12.6), p. 233, GRS with both covariances at divisor T; eq. "
        "(12.19), p. 240; the Fama-MacBeth variance, p. 246"
    ),
)
_GOYAL = Reference(
    key="goyal2012",
    citation=(
        "Goyal, A. (2012). Empirical cross-sectional asset pricing: a survey. "
        "Financial Markets and Portfolio Management, 26(1), 3-38."
    ),
    doi="10.1007/s11408-011-0177-7",
    locator=(
        "Eq. (32), p. 13, the Fama-MacBeth variance; eq. (33), p. 14, Shanken's "
        "corrected form"
    ),
)
_KEN_FRENCH = Reference(
    key="french_library",
    citation=(
        "French, K. R. Data Library: the Fama/French factors and the 25 portfolios "
        "formed on size and book-to-market, monthly. Tuck School of Business, "
        "Dartmouth College."
    ),
    url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
    locator=(
        "Fama/French 3 Factors, 5 Factors (2x3) and 25 Portfolios Formed on "
        "Size and Book-to-Market (5 x 5)"
    ),
)

_PANEL: Final = {
    "returns": [
        [0.021, 0.014, 0.009],
        [-0.013, -0.008, -0.017],
        [0.034, 0.027, 0.031],
        [0.008, 0.011, 0.002],
        [-0.022, -0.015, -0.026],
        [0.015, 0.012, 0.019],
        [0.027, 0.018, 0.024],
        [-0.004, 0.001, -0.009],
        [0.012, 0.009, 0.016],
        [0.019, 0.013, 0.011],
    ],
    "factors": [
        [0.018, 0.004],
        [-0.02, -0.006],
        [0.03, 0.011],
        [0.006, -0.002],
        [-0.025, 0.003],
        [0.012, 0.007],
        [0.022, -0.005],
        [-0.006, 0.001],
        [0.009, 0.002],
        [0.016, -0.004],
    ],
}


def _bindings(
    profile: str, factors: str, columns: tuple[str, ...]
) -> tuple[Binding, ...]:
    return (
        Binding(
            "returns",
            "portfolios.size_bm25.us.monthly",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
            profile=profile,
        ),
        Binding(
            "factors",
            factors,
            as_of=AsOf.WINDOW,
            window=_WINDOW,
            profile=profile,
            columns=columns,
        ),
        Binding(
            "risk_free",
            "factors.risk_free.us.monthly",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
            profile=profile,
        ),
    )


@model(
    id="asset_pricing.factor_model_tests",
    version=1,
    title="Tests of factor models: GRS and Fama-MacBeth",
    summary=(
        "Whether factors price a set of test assets: the Gibbons-Ross-Shanken F "
        "test that every alpha is zero, and Fama-MacBeth two-pass regressions "
        "with Fama-MacBeth and Shanken-corrected standard errors."
    ),
    formula=(
        r"r_{it} = \alpha_i + \beta_i' f_t + e_{it}",
        (
            r"W = \frac{T - N - L}{N} \frac{\hat\alpha' \hat\Sigma^{-1} \hat\alpha}"
            r"{1 + \bar f' \hat\Omega^{-1} \bar f} \sim F(N, T - N - L)"
        ),
        (
            r"r_t = \gamma_{0t} + \hat B \gamma_t + \eta_t, \quad \hat\gamma = "
            r"\frac{1}{T}\sum_t \hat\gamma_t, \quad s(\hat\gamma) = "
            r"\frac{\mathrm{sd}(\hat\gamma_t)}{\sqrt{T}}"
        ),
        (
            r"\hat V_S = \tfrac{1}{T}\left[(1 + \hat\gamma'\hat\Sigma_f^{-1}"
            r"\hat\gamma)\, A \hat\Sigma A' + \hat\Sigma_f^*\right], \quad A = "
            r"(X'X)^{-1}X'"
        ),
    ),
    assumptions=(
        (
            "The factors are excess returns of traded portfolios, for GRS; the "
            "time-series betas are constant over the sample and estimated over "
            "the same periods as the cross-sections."
        ),
        (
            "GRS is exact under normal errors independent over time, with the "
            "residual and factor covariances at divisor T; Fama-MacBeth errors "
            "treat the periods' estimates as independent draws."
        ),
        (
            "Profiles: default binds 120 months of the Ken French 25 portfolios "
            "on size and book-to-market as test assets, the three-factor file's "
            "Mkt-RF, SMB and HML, and the risk-free return; ff5 binds the "
            "five-factor file's Mkt-RF, SMB, HML, RMW and CMA instead."
        ),
    ),
    limitations=(
        (
            "Residuals or factors collinear to working precision (an asset that is "
            "a combination of the factors, a factor that barely varies), or "
            "betas that barely vary across the assets, leave the test or the "
            "premia undefined: DomainError, as for a statistic beyond 1e12 or an "
            "estimate beyond 1e9."
        ),
        (
            "GRS has power only against the alternatives its assets span, and with "
            "many assets and few periods its size depends on normality. "
            "Fama-MacBeth errors ignore autocorrelation in the premia."
        ),
        (
            "The Ken French portfolios and factors are library-only: fetched at "
            "run time and never stored. A bound window ends at the library's "
            "latest month on or before the date."
        ),
    ),
    references=(_GRS, _FAMA_MACBETH, _SHANKEN, _COCHRANE, _GOYAL, _KEN_FRENCH),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=("grs", "fama-macbeth", "shanken", "factor model", "risk premia", "alpha"),
    invariants=(
        Invariant(
            id="grs_zero_when_alphas_are_zero",
            statement=(
                "When every asset's estimated alpha is zero, the GRS statistic is "
                "zero and its p-value one."
            ),
        ),
        Invariant(
            id="fama_macbeth_recovers_premia_on_exact_data",
            statement=(
                "When every asset's excess return is exactly a common constant "
                "plus its betas times the factors, the premia are the factors' "
                "sample means and the intercept is the constant."
            ),
        ),
        Invariant(
            id="shanken_correction_never_narrows_errors",
            statement=(
                "Shanken's corrected standard error of each premium and of the "
                "intercept is at least its Fama-MacBeth standard error."
            ),
        ),
    ),
    examples=(
        Example(
            name="grs_three_assets",
            inputs={"calculation": "grs", **_PANEL},
            note="Ten periods of three test assets on two factors.",
        ),
        Example(
            name="fama_macbeth_three_assets",
            inputs={"calculation": "fama_macbeth", **_PANEL, "intercept": False},
        ),
    ),
    bindings=(
        *_bindings("default", "factors.ff3.us.monthly", ("Mkt-RF", "SMB", "HML")),
        *_bindings(
            "ff5", "factors.ff5.us.monthly", ("Mkt-RF", "SMB", "HML", "RMW", "CMA")
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def factor_model_tests(inputs: FactorModelTestsInputs) -> FactorModelTestsOutputs:
    """Run the test the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[_Panel], Callable[[Any], FactorModelTestsOutputs]]] = {
    GrsInputs: _grs,
    FamaMacBethInputs: _fama_macbeth,
}
