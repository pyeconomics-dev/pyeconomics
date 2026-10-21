# src/pyeconomics/models/portfolio/risk_based_allocation.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Risk-based allocation: ``portfolio.risk_based_allocation``.

Three long-only, fully invested allocations that use the covariance of the
assets' returns and no expected returns, named by ``calculation``:

- ``inverse_volatility``: :math:`w_i \propto 1/\sigma_i`;
- ``equal_risk_contribution``: the portfolio in which every asset contributes
  the same share of the risk (Maillard, Roncalli and Teiletche 2010). Asset
  :math:`i` contributes :math:`RC_i = w_i (\Sigma w)_i / \sigma_p`, and the
  contributions sum to the volatility :math:`\sigma_p`. The weights are the
  normalized minimizer of the strictly convex :math:`\tfrac{1}{2} y'\Sigma y -
  \tfrac{1}{N}\sum_i \log y_i`, whose first-order conditions are exactly
  :math:`y_i (\Sigma y)_i = 1/N`. Newton's method with a backtracking line
  search solves it until every :math:`y_i(\Sigma y)_i` is within
  :data:`TOLERANCE` (relative) of :math:`1/N`, in at most
  :data:`ITERATIONS_MAX` steps;
- ``hierarchical_risk_parity`` (López de Prado 2016): the correlation distance
  :math:`d_{ij} = \sqrt{(1 - \rho_{ij})/2}`, the Euclidean distance between the
  columns of :math:`d`, single-linkage clustering of the assets on it (SciPy),
  the quasi-diagonal order of the tree's leaves, and recursive bisection of
  that order into halves, splitting each cluster's weight between its two
  halves in inverse proportion to their inverse-variance portfolios'
  variances.

Each reports the weights, every asset's risk contribution and the volatility.
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
    ConvergenceError,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Ratio,
    Reference,
    Volatility,
    VolatilityArray,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.portfolio._common import (
    ASSETS_MAX,
    CorrelationMatrix,
    CovarianceMatrix,
    ReturnWindow,
    covariance,
    matrix_field,
    sample_covariance,
    square,
    window_field,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["risk_based_allocation"]

#: Equal risk contribution: Newton's method stops when every y_i (Sigma y)_i is
#: within this, relatively, of 1/N (or within the rounding of computing it).
TOLERANCE: Final = 1e-12
#: Units in the last place a product y_i (Sigma y)_i may be off, per asset.
_ROUNDING: Final = 16 * float(np.finfo(np.float64).eps)
#: ... and gives up after this many steps (it takes a dozen or so).
ITERATIONS_MAX: Final = 200
#: Backtracking halves a step at most this many times.
_HALVINGS_MAX: Final = 60
#: A Newton iterate whose y_i sigma_i passes this has run away: some long
#: portfolio's variance is about 1e-16 of its assets'.
_DIVERGED: Final = 1e8
_RISKLESS_PORTFOLIO: Final = (
    "some long portfolio of the assets has no risk to working precision "
    "(perfectly negatively correlated assets), so no portfolio has equal risk "
    "contributions"
)
_ARMIJO: Final = 1e-4
#: A Newton decrement this small is below the objective's rounding (it is about 1).
_DECREMENT: Final = 1e-12
#: A risk contribution is at most the asset's weight (at most 1) times its
#: volatility (at most 10), by the Cauchy-Schwarz inequality.
_CONTRIBUTION_MAX: Final = 10.0
#: A portfolio volatility below this fraction of the least volatile asset's has
#: no risk to working precision.
_RISKLESS: Final = 1e-8
#: The months of returns a binding reads: ten years.
_WINDOW: Final = 120

type _Matrix = NDArray[np.float64]


# --- inputs ------------------------------------------------------------------


class _Risk(ModelInputs):
    """The covariance of the assets' returns, or the returns themselves."""

    covariance: CovarianceMatrix | None = matrix_field(
        "Covariance matrix of the asset returns per period, as rows; or give "
        "volatilities and correlations, or returns"
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
    returns: ReturnWindow | None = window_field(
        "The assets' returns, as rows: one per period, one value per asset; "
        "their sample covariance (divisor T - 1) is used"
    )

    @model_validator(mode="after")
    def _one_risk_matrix(self) -> Self:
        given = [
            self.covariance is not None,
            self.volatilities is not None or self.correlations is not None,
            self.returns is not None,
        ]
        if sum(given) != 1:
            msg = (
                "give one of: a covariance matrix, volatilities and correlations, "
                "or returns"
            )
            raise ValueError(msg)
        problem: str | None = None
        if self.covariance is not None:
            problem = square(self.covariance, len(self.covariance), "covariance matrix")
        elif self.returns is not None:
            if len({len(row) for row in self.returns}) != 1:
                problem = "every row of returns holds one value per asset"
        elif self.volatilities is None or self.correlations is None:
            problem = "give volatilities and correlations together"
        else:
            problem = square(
                self.correlations, len(self.volatilities), "correlation matrix"
            )
        if problem is not None:
            raise ValueError(problem)
        return self

    def matrix(self) -> _Matrix:
        """Return the checked covariance matrix; it may be singular."""
        if self.returns is not None:
            found = sample_covariance(self.returns)
            return covariance(found.tolist(), None, None, definite=False)
        return covariance(
            self.covariance, self.volatilities, self.correlations, definite=False
        )


class InverseVolatilityInputs(_Risk):
    """Weights inversely proportional to the volatilities."""

    calculation: Literal["inverse_volatility"] = Field(
        "inverse_volatility", description="Weights proportional to 1 / volatility"
    )


class EqualRiskContributionInputs(_Risk):
    """The portfolio in which every asset contributes the same risk."""

    calculation: Literal["equal_risk_contribution"] = Field(
        "equal_risk_contribution",
        description="Risk parity: every asset contributes the same risk",
    )


class HierarchicalRiskParityInputs(_Risk):
    """Hierarchical risk parity over the correlation tree."""

    calculation: Literal["hierarchical_risk_parity"] = Field(
        "hierarchical_risk_parity",
        description="Hierarchical risk parity: clustering and recursive bisection",
    )


RiskBasedAllocationInputs = Annotated[
    InverseVolatilityInputs
    | EqualRiskContributionInputs
    | HierarchicalRiskParityInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------

_Weights = Annotated[tuple[Annotated[Ratio, Field(ge=0.0, le=1.0)], ...], ARRAY_INPUT]
_Contributions = Annotated[
    tuple[
        Annotated[Volatility, Field(ge=-_CONTRIBUTION_MAX, le=_CONTRIBUTION_MAX)], ...
    ],
    ARRAY_INPUT,
]


class _Allocation(ModelOutputs):
    """The weights, each asset's risk contribution and the volatility."""

    weights: _Weights = Field(
        max_length=ASSETS_MAX,
        description="Weight of each asset: long only, summing to 1",
    )
    risk_contributions: _Contributions = Field(
        max_length=ASSETS_MAX,
        description=(
            "Each asset's contribution to the volatility, w_i (Sigma w)_i / "
            "sigma_p; they sum to the volatility"
        ),
    )
    volatility: Volatility = Field(
        ge=0.0, le=10.0, description="The portfolio's volatility per period"
    )


class InverseVolatilityOutputs(_Allocation):
    calculation: Literal["inverse_volatility"] = Field(
        "inverse_volatility", description="Weights proportional to 1 / volatility"
    )


class EqualRiskContributionOutputs(_Allocation):
    calculation: Literal["equal_risk_contribution"] = Field(
        "equal_risk_contribution",
        description="Risk parity: every asset contributes the same risk",
    )
    iterations: Count = Field(
        ge=0, le=ITERATIONS_MAX, description="Newton steps the solve took"
    )


class HierarchicalRiskParityOutputs(_Allocation):
    calculation: Literal["hierarchical_risk_parity"] = Field(
        "hierarchical_risk_parity",
        description="Hierarchical risk parity: clustering and recursive bisection",
    )
    order: Annotated[
        tuple[Annotated[Count, Field(ge=0, le=ASSETS_MAX - 1)], ...], ARRAY_INPUT
    ] = Field(
        max_length=ASSETS_MAX,
        description=(
            "The assets' quasi-diagonal order: their positions in the inputs, as "
            "the tree's leaves run, from 0"
        ),
    )


RiskBasedAllocationOutputs = Annotated[
    InverseVolatilityOutputs
    | EqualRiskContributionOutputs
    | HierarchicalRiskParityOutputs,
    Field(discriminator="calculation"),
]


# --- the calculations --------------------------------------------------------


def _report(weights: _Matrix, sigma: _Matrix) -> dict[str, Any]:
    """Return the weights, risk contributions and volatility of a portfolio.

    They are computed against Sigma scaled to a largest entry of one, then scaled
    back by the root of the scale, so tiny variances keep their digits.
    """
    weights = weights / math.fsum(weights.tolist())
    scale = float(np.max(np.abs(sigma)))
    unit = sigma / scale
    marginal = unit @ weights
    variance = max(math.fsum((weights * marginal).tolist()), 0.0)
    volatility = math.sqrt(variance)
    if volatility <= _RISKLESS * math.sqrt(float(np.min(np.diag(unit)))):
        msg = (
            "the portfolio has no risk to working precision: some long portfolio "
            "of the assets is riskless (perfectly negatively correlated assets), "
            "so risk contributions are undefined"
        )
        raise DomainError(msg)
    root = math.sqrt(scale)
    contributions = weights * marginal / volatility * root
    volatility *= root
    return {
        "weights": tuple(min(1.0, max(0.0, float(w))) for w in weights),
        "risk_contributions": tuple(
            min(_CONTRIBUTION_MAX, max(-_CONTRIBUTION_MAX, float(c)))
            for c in contributions
        ),
        "volatility": min(volatility, 10.0),
    }


def _inverse_volatility(inputs: InverseVolatilityInputs) -> InverseVolatilityOutputs:
    sigma = inputs.matrix()
    weights = 1.0 / np.sqrt(np.diag(sigma))
    return InverseVolatilityOutputs(**_report(weights, sigma))


def _objective(y: _Matrix, scaled: _Matrix, budget: float) -> float:
    return 0.5 * float(y @ scaled @ y) - budget * math.fsum(np.log(y).tolist())


def _solve_erc(sigma: _Matrix) -> tuple[_Matrix, int]:
    """Return the equal-risk-contribution weights and the Newton steps taken."""
    size = len(sigma)
    budget = 1.0 / size
    # Scaled to a largest entry of one: the weights do not depend on the scale.
    scaled = sigma / float(np.max(np.abs(sigma)))
    vols = np.sqrt(np.diag(scaled))
    start = 1.0 / vols
    variance = float(start @ scaled @ start)
    # Each term start_i^2 sigma_i^2 is 1: a start this far below N is riskless.
    if variance <= _RISKLESS * _RISKLESS * size:
        raise DomainError(_RISKLESS_PORTFOLIO)
    y = start / math.sqrt(variance)
    for step in range(ITERATIONS_MAX + 1):
        marginal = scaled @ y
        # Converged when each y_i (Sigma y)_i is within the tolerance of 1/N, or
        # within the rounding of computing it (Sigma y cancels when a long
        # portfolio is nearly riskless).
        rounding = _ROUNDING * size * y * (np.abs(scaled) @ y)
        allowed = np.maximum(TOLERANCE * budget, rounding)
        if np.all(np.abs(y * marginal - budget) <= allowed):
            return y / math.fsum(y.tolist()), step
        if step == ITERATIONS_MAX:
            break
        # At the solution y' Sigma y = 1, so y_i sigma_i passes _DIVERGED only when
        # a long portfolio's variance is rounding error next to its assets': the
        # objective then has no minimum, and Newton's method runs away.
        if float(np.max(y * vols)) > _DIVERGED:
            raise DomainError(_RISKLESS_PORTFOLIO)
        gradient = marginal - budget / y
        hessian = scaled + np.diag(budget / (y * y))
        try:
            direction = np.linalg.solve(hessian, -gradient)
        except np.linalg.LinAlgError:
            raise DomainError(_RISKLESS_PORTFOLIO) from None
        y = _line_search(y, direction, gradient, scaled, budget)
    msg = (
        f"the equal-risk-contribution solve did not reach a relative tolerance of "
        f"{TOLERANCE:g} in {ITERATIONS_MAX} Newton steps: some long portfolio of "
        "the assets is nearly riskless"
    )
    raise ConvergenceError(msg)


def _line_search(
    y: _Matrix, direction: _Matrix, gradient: _Matrix, scaled: _Matrix, budget: float
) -> _Matrix:
    """Take the longest step, halving from one, that keeps y positive and descends.

    Near the minimizer the objective's change is below its rounding, so the
    descent test cannot judge a step: once the Newton decrement is that small,
    the full step is taken, where Newton's method converges quadratically.
    """
    slope = float(gradient @ direction)
    full = y + direction
    if -slope <= _DECREMENT and np.all(full > 0):
        return full
    current = _objective(y, scaled, budget)
    t = 1.0
    for _ in range(_HALVINGS_MAX):
        trial = y + t * direction
        if np.all(trial > 0) and (
            _objective(trial, scaled, budget) <= current + _ARMIJO * t * slope
        ):
            return trial
        t /= 2
    # No descent left at working precision: the iterate is the minimizer.
    return y


def _equal_risk_contribution(
    inputs: EqualRiskContributionInputs,
) -> EqualRiskContributionOutputs:
    sigma = inputs.matrix()
    weights, steps = _solve_erc(sigma)
    return EqualRiskContributionOutputs(**_report(weights, sigma), iterations=steps)


def _quasi_diagonal(link: _Matrix, size: int) -> list[int]:
    """Return the leaves of a linkage tree, left to right (López de Prado's order)."""
    order = [int(link[-1, 0]), int(link[-1, 1])]
    while any(item >= size for item in order):
        expanded: list[int] = []
        for item in order:
            if item >= size:
                row = link[item - size]
                expanded += [int(row[0]), int(row[1])]
            else:
                expanded.append(item)
        order = expanded
    return order


def _cluster_variance(sigma: _Matrix, items: list[int]) -> float:
    """Return the variance of the inverse-variance portfolio of the items."""
    block = sigma[np.ix_(items, items)]
    inverse = 1.0 / np.diag(block)
    weights = inverse / math.fsum(inverse.tolist())
    return max(float(weights @ block @ weights), 0.0)


def _bisect(sigma: _Matrix, order: list[int]) -> _Matrix:
    """Split the weight down the quasi-diagonal order, half by half."""
    weights = np.ones(len(sigma))
    clusters = [order]
    while clusters:
        halves = [
            part
            for cluster in clusters
            if len(cluster) > 1
            for part in (cluster[: len(cluster) // 2], cluster[len(cluster) // 2 :])
        ]
        for left, right in zip(halves[::2], halves[1::2], strict=True):
            low, high = _cluster_variance(sigma, left), _cluster_variance(sigma, right)
            scale = min(float(sigma[i, i]) for i in left + right)
            if min(low, high) <= _RISKLESS * _RISKLESS * scale:
                msg = (
                    "a cluster's inverse-variance portfolio has no variance to "
                    "working precision (perfectly negatively correlated assets), "
                    "so hierarchical risk parity cannot split its weight"
                )
                raise DomainError(msg)
            # Each half's share, as its own ratio: 1 - low / (low + high) would
            # cancel to nothing for a half with a tiny variance.
            weights[left] *= high / (low + high)
            weights[right] *= low / (low + high)
        clusters = halves
    return weights


def _hierarchical_risk_parity(
    inputs: HierarchicalRiskParityInputs,
) -> HierarchicalRiskParityOutputs:
    sigma = inputs.matrix()
    size = len(sigma)
    if size == 1:
        return HierarchicalRiskParityOutputs(**_report(np.ones(1), sigma), order=(0,))
    from scipy.cluster.hierarchy import linkage  # noqa: PLC0415 - SciPy on first use
    from scipy.spatial.distance import pdist  # noqa: PLC0415

    # Scaled to a largest entry of one: the weights do not depend on the scale,
    # and 1 / variance cannot overflow.
    unit = sigma / float(np.max(np.abs(sigma)))
    vols = np.sqrt(np.diag(unit))
    correlation = np.clip(unit / np.outer(vols, vols), -1.0, 1.0)
    np.fill_diagonal(correlation, 1.0)
    distance = np.sqrt(np.clip((1.0 - correlation) / 2.0, 0.0, None))
    # The Euclidean distance between the columns of the correlation distance,
    # as the paper's code computes it, then single linkage.
    link = linkage(pdist(distance), method="single")
    order = _quasi_diagonal(link, size)
    weights = _bisect(unit, order)
    return HierarchicalRiskParityOutputs(**_report(weights, sigma), order=tuple(order))


# --- the model ---------------------------------------------------------------

_MAILLARD = Reference(
    key="maillard2010",
    citation=(
        "Maillard, S., Roncalli, T. and Teiletche, J. (2010). The Properties of "
        "Equally Weighted Risk Contribution Portfolios. The Journal of Portfolio "
        "Management, 36(4), 60-70."
    ),
    doi="10.3905/jpm.2010.36.4.060",
    locator=(
        "The ERC portfolio and its risk contributions, the log-barrier problem "
        "whose solution it is, and the example of section 4.1"
    ),
)
_LOPEZ_DE_PRADO = Reference(
    key="lopez2016",
    citation=(
        "López de Prado, M. (2016). Building Diversified Portfolios that Outperform "
        "Out of Sample. The Journal of Portfolio Management, 42(4), 59-69."
    ),
    doi="10.3905/jpm.2016.42.4.059",
    locator=(
        "Stages 1-3, pp. 5-8 of the SSRN preprint: the distance of distances, "
        "single linkage, quasi-diagonalization and bisection of the ordered list"
    ),
)
_KEN_FRENCH = Reference(
    key="french_library",
    citation=(
        "French, K. R. Data Library: 12 industry portfolios, monthly. Tuck School "
        "of Business, Dartmouth College."
    ),
    url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
    locator="12 Industry Portfolios, value-weighted monthly returns",
)

_EXAMPLE: Final = {
    "volatilities": [0.1, 0.2, 0.3, 0.4],
    "correlations": [
        [1.0, 0.8, 0.0, 0.0],
        [0.8, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, -0.5],
        [0.0, 0.0, -0.5, 1.0],
    ],
}


@model(
    id="portfolio.risk_based_allocation",
    version=1,
    title="Risk-based allocation: inverse volatility, risk parity and HRP",
    summary=(
        "Long-only weights from the covariance alone: inverse volatility, equal "
        "risk contribution (risk parity) and hierarchical risk parity, with each "
        "asset's risk contribution and the portfolio's volatility."
    ),
    formula=(
        r"w_i^{IV} = \frac{1/\sigma_i}{\sum_j 1/\sigma_j}",
        (
            r"RC_i = \frac{w_i (\Sigma w)_i}{\sigma_p}, \quad \sum_i RC_i = "
            r"\sigma_p = \sqrt{w'\Sigma w}"
        ),
        (
            r"w^{ERC} = \frac{y^*}{\mathbf{1}'y^*}, \quad y^* = \arg\min_{y > 0} "
            r"\tfrac{1}{2} y'\Sigma y - \tfrac{1}{N}\sum_i \log y_i"
        ),
        (
            r"d_{ij} = \sqrt{\tfrac{1}{2}(1 - \rho_{ij})}, \quad \alpha = 1 - "
            r"\frac{V_1}{V_1 + V_2}"
        ),
    ),
    assumptions=(
        (
            "The covariance is per period and given (or estimated from the "
            "returns given, divisor T - 1); no expected returns are used."
        ),
        (
            "The weights are long only and sum to one; there are no costs or "
            "constraints beyond that."
        ),
        (
            "Profile: default binds 120 months of the Ken French 12 industry "
            "portfolios' returns."
        ),
        (
            "The outputs follow from the inputs the user supplies, the same for "
            "every user: they are formula results, not investment advice."
        ),
    ),
    limitations=(
        (
            "A covariance matrix that is not symmetric and positive semidefinite, "
            "or an asset without variance, raises DomainError; so does a long "
            "portfolio with no risk (perfectly negatively correlated assets), "
            "whose risk contributions are undefined."
        ),
        (
            "The equal-risk-contribution solve raises ConvergenceError if it does "
            f"not reach a relative tolerance of {TOLERANCE:g} in "
            f"{ITERATIONS_MAX} Newton steps."
        ),
        (
            "Hierarchical risk parity depends on the clustering: single linkage "
            "chains, and a tie between distances is broken by SciPy's order. Its "
            "bisection halves the ordered list, not the tree."
        ),
        (
            "The Ken French portfolios are library-only: fetched at run time and "
            "never stored."
        ),
    ),
    references=(_MAILLARD, _LOPEZ_DE_PRADO, _KEN_FRENCH),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.LIGHT,
    tags=("risk parity", "equal risk contribution", "hrp", "inverse volatility"),
    invariants=(
        Invariant(
            id="weights_sum_to_one",
            statement="The weights of every allocation sum to one.",
        ),
        Invariant(
            id="erc_contributions_are_equal",
            statement=(
                "In the equal-risk-contribution portfolio every asset's risk "
                "contribution is the volatility over the number of assets."
            ),
        ),
        Invariant(
            id="inverse_volatility_equals_erc_for_uncorrelated_assets",
            statement=(
                "When the assets are uncorrelated, the equal-risk-contribution "
                "weights are the inverse-volatility weights."
            ),
        ),
        Invariant(
            id="hrp_weights_are_positive",
            statement="Every hierarchical-risk-parity weight is above zero.",
        ),
    ),
    examples=(
        Example(
            name="four_assets_inverse_volatility",
            inputs={"calculation": "inverse_volatility", **_EXAMPLE},
        ),
        Example(
            name="four_assets_risk_parity",
            inputs={"calculation": "equal_risk_contribution", **_EXAMPLE},
            note="Volatilities 10% to 40%, two correlated pairs.",
        ),
        Example(
            name="four_assets_hrp",
            inputs={"calculation": "hierarchical_risk_parity", **_EXAMPLE},
        ),
    ),
    bindings=(
        Binding(
            "returns",
            "portfolios.industry12.us.monthly",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def risk_based_allocation(
    inputs: RiskBasedAllocationInputs,
) -> RiskBasedAllocationOutputs:
    """Run the allocation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[_Risk], Callable[[Any], RiskBasedAllocationOutputs]]] = {
    InverseVolatilityInputs: _inverse_volatility,
    EqualRiskContributionInputs: _equal_risk_contribution,
    HierarchicalRiskParityInputs: _hierarchical_risk_parity,
}
