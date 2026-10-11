# src/pyeconomics/models/portfolio/mean_variance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Mean-variance portfolio mathematics: ``portfolio.mean_variance``.

Four calculations, discriminated on ``calculation``, all from expected returns
and either a covariance matrix or volatilities and correlations:

- ``portfolio``: the expected return, variance and volatility of given weights
  (Markowitz, 1952);
- ``frontier``: the minimum-variance frontier with short sales allowed, in
  Merton's (1972) closed form, at a bounded number of target returns;
- ``minimum_variance``: the global minimum-variance portfolio;
- ``tangency``: the portfolio of risky assets with the highest Sharpe ratio for
  a risk-free rate, and the slope of the capital market line through it.

With :math:`\mathbf{1}` a vector of ones, :math:`A = \mathbf{1}'\Sigma^{-1}
\mathbf{1}` and :math:`\mu_g = \mathbf{1}'\Sigma^{-1}\mu / A`, the
minimum-variance portfolio is :math:`w_g = \Sigma^{-1}\mathbf{1} / A`, with
variance :math:`1 / A`. Writing :math:`d = \mu - \mu_g \mathbf{1}`,
:math:`y = \Sigma^{-1} d` and :math:`q = d'y` (Merton's :math:`D / A`), the
frontier portfolio with expected return :math:`m` is :math:`w_g + (m - \mu_g)
y / q`, with variance :math:`1/A + (m - \mu_g)^2 / q`: a parabola in :math:`m`.
Formed this way, nothing subtracts two large, nearly equal numbers, as
:math:`AC - B^2` does.

For a risk-free rate :math:`r_f < \mu_g` the tangency portfolio is
:math:`w_g + y / (A(\mu_g - r_f))`, and the capital market line's slope is
:math:`\sqrt{q + A(\mu_g - r_f)^2}`.

No solver runs: each answer is one factorization of a matrix of at most 100
assets. Long-only and other constrained optimization are Phase 7's.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

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
    Rate,
    Ratio,
    Reference,
    Return,
    ReturnArray,
    Volatility,
    VolatilityArray,
    has_spread,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.portfolio._common import (
    ASSETS_MAX,
    COVARIANCE_MAX,
    CorrelationMatrix,
    CovarianceMatrix,
    bounded,
    covariance,
    matrix_field,
    square,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["mean_variance"]

#: The largest weight an input portfolio may hold on one asset, long or short.
_WEIGHT_IN: Final = 100.0
#: Weights of the given portfolio are at most 100 in size on at most 100 assets,
#: and returns at most 100, so its expected return is at most 1e6 in size; with
#: volatilities at most 10, its volatility is at most 100 * 100 * 10 = 1e5 and
#: its variance 1e10. The bounds of the portfolio outputs are sized to that.
_RETURN_OUT: Final = 1e6
_VOLATILITY_OUT: Final = 1e5
_VARIANCE_OUT: Final = 1e10
_WEIGHT_SUM_OUT: Final = _WEIGHT_IN * ASSETS_MAX
#: An optimized weight has no bound the inputs can size: a covariance matrix
#: close to singular gives weights of any size. Beyond this, DomainError.
_WEIGHT_OUT: Final = 1e6
#: The most target returns a frontier holds.
_POINTS_MAX: Final = 200
#: A slope of the capital market line, a Sharpe ratio, beyond this is unbounded.
_SLOPE_OUT: Final = 1e6

_Weights = Annotated[
    tuple[Annotated[Ratio, Field(ge=-_WEIGHT_IN, le=_WEIGHT_IN)], ...], ARRAY_INPUT
]
_OptimalWeights = Annotated[
    tuple[Annotated[Ratio, Field(ge=-_WEIGHT_OUT, le=_WEIGHT_OUT)], ...], ARRAY_INPUT
]
_WeightRow = Annotated[
    tuple[Annotated[Ratio, Field(ge=-_WEIGHT_OUT, le=_WEIGHT_OUT)], ...],
    Field(max_length=ASSETS_MAX),
    ARRAY_INPUT,
]
_Targets = Annotated[
    tuple[Annotated[Return, Field(ge=-_RETURN_OUT, le=_RETURN_OUT)], ...], ARRAY_INPUT
]
_Volatilities = Annotated[
    tuple[Annotated[Volatility, Field(ge=0.0, le=_VOLATILITY_OUT)], ...], ARRAY_INPUT
]
_Variances = Annotated[
    tuple[Annotated[Ratio, Field(ge=0.0, le=_VARIANCE_OUT)], ...], ARRAY_INPUT
]


# --- inputs ------------------------------------------------------------------


class _Assets(ModelInputs):
    """Expected returns and the covariance of the assets' returns."""

    expected_returns: ReturnArray = Field(
        min_length=1,
        max_length=ASSETS_MAX,
        description="Expected return of each asset per period",
    )
    covariance: CovarianceMatrix | None = matrix_field(
        "Covariance matrix of the asset returns per period, as rows; or give "
        "volatilities and correlations"
    )
    volatilities: VolatilityArray | None = Field(
        None,
        min_length=1,
        max_length=ASSETS_MAX,
        description="Volatility of each asset per period, with correlations",
    )
    correlations: CorrelationMatrix | None = matrix_field(
        "Correlation matrix of the asset returns, as rows, with volatilities"
    )

    @model_validator(mode="after")
    def _one_covariance(self) -> Self:
        size = len(self.expected_returns)
        if self.covariance is not None:
            if self.volatilities is not None or self.correlations is not None:
                msg = (
                    "give a covariance matrix or volatilities and correlations, "
                    "not both"
                )
                raise ValueError(msg)
            problem = square(self.covariance, size, "covariance matrix")
        elif self.volatilities is None or self.correlations is None:
            msg = "give a covariance matrix, or volatilities and correlations"
            raise ValueError(msg)
        elif len(self.volatilities) != size:
            problem = f"give one volatility per asset: {size} assets"
        else:
            problem = square(self.correlations, size, "correlation matrix")
        if problem is not None:
            raise ValueError(problem)
        return self

    def matrix(self) -> NDArray[np.float64]:
        """Return the checked covariance matrix."""
        return covariance(self.covariance, self.volatilities, self.correlations)


class PortfolioInputs(_Assets):
    """Weights of a portfolio of the assets."""

    calculation: Literal["portfolio"] = Field(
        "portfolio", description="Expected return and risk of given weights"
    )
    weights: _Weights = Field(
        min_length=1,
        max_length=ASSETS_MAX,
        description="Weight of each asset; negative is short. They need not sum to 1",
    )

    @model_validator(mode="after")
    def _one_weight_per_asset(self) -> Self:
        if len(self.weights) != len(self.expected_returns):
            msg = (
                f"give one weight per asset: {len(self.expected_returns)} assets, "
                f"{len(self.weights)} weights"
            )
            raise ValueError(msg)
        return self


class FrontierInputs(_Assets):
    """How many points of the frontier to trace, and over which returns."""

    calculation: Literal["frontier"] = Field(
        "frontier", description="Minimum-variance frontier, short sales allowed"
    )
    points: Count = Field(
        21, ge=2, le=_POINTS_MAX, description="Number of target returns to trace"
    )
    min_return: Return | None = Field(
        None,
        ge=-1.0,
        le=100.0,
        description="Lowest target return; by default the minimum-variance return",
    )
    max_return: Return | None = Field(
        None,
        ge=-1.0,
        le=100.0,
        description=(
            "Highest target return; by default the highest expected return of an asset"
        ),
    )

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if (
            self.min_return is not None
            and self.max_return is not None
            and self.min_return >= self.max_return
        ):
            msg = "min_return must be below max_return"
            raise ValueError(msg)
        return self


class MinimumVarianceInputs(_Assets):
    """The assets alone."""

    calculation: Literal["minimum_variance"] = Field(
        "minimum_variance", description="Global minimum-variance portfolio"
    )


class TangencyInputs(_Assets):
    """The assets and a risk-free rate per period."""

    calculation: Literal["tangency"] = Field(
        "tangency", description="Tangency portfolio and the capital market line"
    )
    risk_free_rate: Rate = Field(
        ge=-0.99, le=10.0, description="Risk-free rate per period"
    )


MeanVarianceInputs = Annotated[
    PortfolioInputs | FrontierInputs | MinimumVarianceInputs | TangencyInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _optimal_weights() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        max_length=ASSETS_MAX, description="Weight of each asset; they sum to 1"
    )


def _return_out(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_RETURN_OUT, le=_RETURN_OUT, description=description)


class PortfolioOutputs(ModelOutputs):
    calculation: Literal["portfolio"] = Field(
        "portfolio", description="Expected return and risk of given weights"
    )
    expected_return: Return = _return_out("Expected return per period, w'mu")
    variance: Ratio = Field(
        ge=0.0, le=_VARIANCE_OUT, description="Variance of the return, w' Sigma w"
    )
    volatility: Volatility = Field(
        ge=0.0, le=_VOLATILITY_OUT, description="Standard deviation of the return"
    )
    weight_sum: Ratio = Field(
        ge=-_WEIGHT_SUM_OUT, le=_WEIGHT_SUM_OUT, description="Sum of the weights"
    )


class FrontierOutputs(ModelOutputs):
    calculation: Literal["frontier"] = Field(
        "frontier", description="Minimum-variance frontier, short sales allowed"
    )
    minimum_variance_return: Return = _return_out(
        "Expected return of the minimum-variance portfolio"
    )
    minimum_variance_volatility: Volatility = Field(
        ge=0.0, le=10.0, description="Volatility of the minimum-variance portfolio"
    )
    target_returns: _Targets = Field(
        max_length=_POINTS_MAX, description="Target expected returns, ascending"
    )
    variances: _Variances = Field(
        max_length=_POINTS_MAX, description="Lowest variance at each target return"
    )
    volatilities: _Volatilities = Field(
        max_length=_POINTS_MAX, description="Lowest volatility at each target return"
    )
    weights: tuple[_WeightRow, ...] = Field(
        max_length=_POINTS_MAX,
        description="Weights of the frontier portfolio at each target, as rows",
    )


class MinimumVarianceOutputs(ModelOutputs):
    calculation: Literal["minimum_variance"] = Field(
        "minimum_variance", description="Global minimum-variance portfolio"
    )
    weights: _OptimalWeights = _optimal_weights()
    expected_return: Return = _return_out("Expected return per period")
    variance: Ratio = Field(
        ge=0.0,
        le=COVARIANCE_MAX,
        description="Variance, 1 / A; never above the least risky asset's",
    )
    volatility: Volatility = Field(
        ge=0.0, le=10.0, description="Standard deviation of the return"
    )


class TangencyOutputs(ModelOutputs):
    calculation: Literal["tangency"] = Field(
        "tangency", description="Tangency portfolio and the capital market line"
    )
    weights: _OptimalWeights = _optimal_weights()
    expected_return: Return = _return_out("Expected return per period")
    variance: Ratio = Field(
        ge=0.0, le=_VARIANCE_OUT, description="Variance of the return"
    )
    volatility: Volatility = Field(
        ge=0.0, le=_VOLATILITY_OUT, description="Standard deviation of the return"
    )
    capital_market_line_slope: Ratio = Field(
        ge=0.0,
        le=_SLOPE_OUT,
        description=(
            "Slope of the capital market line: the tangency portfolio's Sharpe "
            "ratio per period, the highest of any portfolio of the assets"
        ),
    )


MeanVarianceOutputs = Annotated[
    PortfolioOutputs | FrontierOutputs | MinimumVarianceOutputs | TangencyOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


class _Frontier:
    """The minimum-variance portfolio and the frontier's direction, solved once."""

    def __init__(self, inputs: _Assets) -> None:
        sigma = inputs.matrix()
        mu = np.asarray(inputs.expected_returns, dtype=np.float64)
        self.mu = mu
        # The weights do not depend on the matrix's scale: solve with its
        # largest entry scaled to one, so tiny or huge entries neither overflow
        # nor underflow, and carry the scale s into the variances.
        self.scale = scale = float(np.max(np.abs(sigma)))
        scaled = sigma / scale
        ones = np.linalg.solve(scaled, np.ones_like(mu))
        self.a = a = math.fsum(ones.tolist())
        self.weights = ones / a
        self.mean = math.fsum((self.weights * mu).tolist())
        # 1 / A, never above the least risky asset's variance.
        self.variance = min(scale / a, float(np.min(np.diag(sigma))))
        # d = mu - mean is orthogonal to 1 under Sigma^-1, so y sums to zero
        # and the frontier's weights keep summing to one. d is scaled to a
        # largest entry of one, for the same reason as the matrix.
        deviation = mu - self.mean
        self.unit = unit = float(np.max(np.abs(deviation)))
        if unit > 0:
            deviation = deviation / unit
        self.direction = np.linalg.solve(scaled, deviation)
        self.q = max(math.fsum((deviation * self.direction).tolist()), 0.0)
        self.spread = has_spread(inputs.expected_returns)

    def checked_weights(self, weights: NDArray[np.float64]) -> tuple[float, ...]:
        return tuple(bounded(float(w), _WEIGHT_OUT, "weight") for w in weights)


def _quadratic(weights: NDArray[np.float64], sigma: NDArray[np.float64]) -> float:
    return max(float(weights @ sigma @ weights), 0.0)


def _portfolio(inputs: PortfolioInputs) -> PortfolioOutputs:
    sigma = inputs.matrix()
    weights = np.asarray(inputs.weights, dtype=np.float64)
    mu = np.asarray(inputs.expected_returns, dtype=np.float64)
    variance = _quadratic(weights, sigma)
    return PortfolioOutputs(
        expected_return=math.fsum((weights * mu).tolist()),
        variance=variance,
        volatility=math.sqrt(variance),
        weight_sum=math.fsum(inputs.weights),
    )


def _minimum_variance(inputs: MinimumVarianceInputs) -> MinimumVarianceOutputs:
    found = _Frontier(inputs)
    return MinimumVarianceOutputs(
        weights=found.checked_weights(found.weights),
        expected_return=bounded(found.mean, _RETURN_OUT, "expected return"),
        variance=found.variance,
        volatility=math.sqrt(found.variance),
    )


def _range(inputs: FrontierInputs, found: _Frontier) -> tuple[float, float]:
    highest = float(np.max(found.mu))
    if highest <= found.mean:
        # The minimum-variance portfolio already earns at least any one asset:
        # trace one asset-return range above it.
        highest = found.mean + (highest - float(np.min(found.mu)))
    low = found.mean if inputs.min_return is None else inputs.min_return
    high = highest if inputs.max_return is None else inputs.max_return
    if not low < high:
        msg = (
            f"the range of target returns [{low!r}, {high!r}] is empty; give "
            "min_return and max_return"
        )
        raise DomainError(msg)
    return low, high


def _frontier(inputs: FrontierInputs) -> FrontierOutputs:
    found = _Frontier(inputs)
    if not found.spread or found.q <= 0:
        msg = (
            "the expected returns are equal, or differ by no more than rounding, "
            "so every portfolio earns the same: the frontier is the single "
            "minimum-variance portfolio"
        )
        raise DomainError(msg)
    low, high = _range(inputs, found)
    targets = np.linspace(low, high, inputs.points)
    # With z = (m - mean) / unit, the frontier's variance is 1/A + s z^2 / q
    # and its weights w_g + z y / q, in the scaled quantities.
    z = (targets - found.mean) / found.unit
    variances = found.variance + found.scale * (z * z) / found.q
    rows = tuple(
        found.checked_weights(found.weights + (step / found.q) * found.direction)
        for step in z
    )
    checked = [bounded(float(v), _VARIANCE_OUT, "variance") for v in variances]
    return FrontierOutputs(
        minimum_variance_return=bounded(found.mean, _RETURN_OUT, "expected return"),
        minimum_variance_volatility=math.sqrt(found.variance),
        target_returns=tuple(
            bounded(float(t), _RETURN_OUT, "target return") for t in targets
        ),
        variances=tuple(checked),
        volatilities=tuple(math.sqrt(v) for v in checked),
        weights=rows,
    )


def _tangency(inputs: TangencyInputs) -> TangencyOutputs:
    found = _Frontier(inputs)
    premium = found.mean - inputs.risk_free_rate
    if premium <= 0:
        msg = (
            f"the risk-free rate {inputs.risk_free_rate!r} is not below the "
            f"minimum-variance portfolio's expected return {found.mean!r}, so no "
            "portfolio of the assets is tangent to a line from it"
        )
        raise DomainError(msg)
    # In the scaled quantities: w_T = w_g + u y / (A prem), with return
    # mean + u^2 q / (A prem), variance 1/A + s q (u / (A prem))^2 and slope
    # sqrt((u^2 q + A prem^2) / s), for u the unit of d and s the matrix's scale.
    step = found.unit / (found.a * premium)
    weights = found.weights + step * found.direction
    variance = bounded(
        found.variance + found.scale * found.q * step * step, _VARIANCE_OUT, "variance"
    )
    slope = math.sqrt(
        (found.unit * found.unit * found.q + found.a * premium * premium) / found.scale
    )
    return TangencyOutputs(
        weights=found.checked_weights(weights),
        expected_return=bounded(
            found.mean + found.unit * found.q * step, _RETURN_OUT, "return"
        ),
        variance=variance,
        volatility=math.sqrt(variance),
        capital_market_line_slope=bounded(slope, _SLOPE_OUT, "slope"),
    )


# --- the model ---------------------------------------------------------------

_MARKOWITZ = Reference(
    key="markowitz",
    citation=(
        "Markowitz, H. (1952). Portfolio selection. The Journal of Finance, 7(1), "
        "77-91."
    ),
    doi="10.1111/j.1540-6261.1952.tb01525.x",
    locator="p. 81, the expected return E and variance V of a portfolio",
)
_MERTON = Reference(
    key="merton1972",
    citation=(
        "Merton, R. C. (1972). An analytic derivation of the efficient portfolio "
        "frontier. Journal of Financial and Quantitative Analysis, 7(4), "
        "1851-1872."
    ),
    doi="10.2307/2329621",
    locator=(
        "Eqs. (12)-(14), the frontier and its minimum-variance portfolio; "
        "Section IV, eq. (44), the tangency portfolio (numbered as in MIT "
        "Sloan working paper 493-70)"
    ),
)

_EXAMPLE_ASSETS: Final = {
    "expected_returns": [0.08, 0.12, 0.15],
    "volatilities": [0.15, 0.2, 0.25],
    "correlations": [[1.0, 0.3, 0.2], [0.3, 1.0, 0.5], [0.2, 0.5, 1.0]],
}


@model(
    id="portfolio.mean_variance",
    version=1,
    title="Mean-variance portfolios",
    summary=(
        "Portfolio expected return and risk, the minimum-variance frontier with "
        "short sales, and the minimum-variance and tangency portfolios."
    ),
    formula=(
        r"E[R_p] = w'\mu, \quad \sigma_p^2 = w'\Sigma w",
        (
            r"w_g = \frac{\Sigma^{-1}\mathbf{1}}{A}, \quad A = "
            r"\mathbf{1}'\Sigma^{-1}\mathbf{1}, \quad \sigma_g^2 = \frac{1}{A}"
        ),
        (
            r"\sigma^2(m) = \frac{1}{A} + \frac{(m - \mu_g)^2}{q}, \quad q = d'"
            r"\Sigma^{-1} d, \quad d = \mu - \mu_g \mathbf{1}"
        ),
        (
            r"w_T = \frac{\Sigma^{-1}(\mu - r_f \mathbf{1})}{\mathbf{1}'\Sigma^{-1}"
            r"(\mu - r_f\mathbf{1})}, \quad \text{slope} = \sqrt{(\mu - r_f "
            r"\mathbf{1})'\Sigma^{-1}(\mu - r_f \mathbf{1})}"
        ),
    ),
    assumptions=(
        (
            "Expected returns, volatilities and covariances are per period and "
            "given, not estimated here; the outputs are in the same period."
        ),
        (
            "Short sales are allowed and unlimited, there are no transaction costs "
            "or taxes, and the weights of an optimized portfolio sum to one."
        ),
        (
            "The outputs follow from the inputs the user supplies, the same for "
            "every user: they are formula results, not investment advice, and no "
            "portfolio here is advice to hold it."
        ),
    ),
    limitations=(
        (
            "A covariance (or correlation) matrix that is not symmetric and "
            "positive definite to working precision, or a correlation matrix "
            "without ones on its diagonal, raises DomainError."
        ),
        (
            "A frontier when every expected return is equal, or over an empty "
            "range of returns, raises DomainError; so does a tangency portfolio "
            "for a risk-free rate not below the minimum-variance return."
        ),
        (
            "A matrix so close to singular that a weight exceeds 1e6 in size, or "
            "another output its bounds, raises DomainError."
        ),
        (
            "Mean-variance weights are very sensitive to the expected returns; "
            "estimation error is not modelled. Long-only and other constraints are "
            "not supported."
        ),
    ),
    references=(_MARKOWITZ, _MERTON),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("portfolio", "markowitz", "efficient frontier", "tangency", "sharpe"),
    invariants=(
        Invariant(
            id="weights_sum_to_one",
            statement=(
                "The weights of the minimum-variance, tangency and every frontier "
                "portfolio sum to one."
            ),
        ),
        Invariant(
            id="minimum_variance_has_lowest_variance",
            statement=(
                "No fully invested portfolio of the assets has a lower variance "
                "than the minimum-variance portfolio."
            ),
        ),
        Invariant(
            id="frontier_variance_quadratic_in_return",
            statement=(
                "Along the frontier, the variance is a quadratic in the target "
                "return with its minimum at the minimum-variance portfolio."
            ),
        ),
        Invariant(
            id="tangency_maximizes_sharpe",
            statement=(
                "No fully invested portfolio of the assets has a higher Sharpe "
                "ratio than the tangency portfolio, whose Sharpe ratio is the "
                "capital market line's slope."
            ),
        ),
    ),
    examples=(
        Example(
            name="sixty_forty",
            inputs={
                "calculation": "portfolio",
                "weights": [0.6, 0.4],
                "expected_returns": [0.1, 0.06],
                "volatilities": [0.2, 0.1],
                "correlations": [[1.0, 0.3], [0.3, 1.0]],
            },
        ),
        Example(
            name="three_asset_frontier",
            inputs={"calculation": "frontier", "points": 5, **_EXAMPLE_ASSETS},
        ),
        Example(
            name="three_asset_minimum_variance",
            inputs={"calculation": "minimum_variance", **_EXAMPLE_ASSETS},
        ),
        Example(
            name="three_asset_tangency",
            inputs={
                "calculation": "tangency",
                "risk_free_rate": 0.03,
                **_EXAMPLE_ASSETS,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def mean_variance(inputs: MeanVarianceInputs) -> MeanVarianceOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], MeanVarianceOutputs]]] = {
    PortfolioInputs: _portfolio,
    FrontierInputs: _frontier,
    MinimumVarianceInputs: _minimum_variance,
    TangencyInputs: _tangency,
}
