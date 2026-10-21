# src/pyeconomics/models/portfolio/black_litterman.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The Black-Litterman model: ``portfolio.black_litterman``.

Black and Litterman (1992) start from the expected returns that make the market
portfolio optimal, the equilibrium :math:`\Pi = \delta \Sigma w_{mkt}` for a
risk aversion :math:`\delta`, and blend in views: :math:`K` portfolios
:math:`P` (the pick matrix, one row per view) with expected returns :math:`Q`
and uncertainty :math:`\Omega`. With :math:`\tau` scaling the uncertainty of
the equilibrium, the posterior expected returns and the posterior covariance of
their mean are

.. math::

   \mu = \Pi + \tau\Sigma P' (P\tau\Sigma P' + \Omega)^{-1} (Q - P\Pi), \quad
   M = \tau\Sigma - \tau\Sigma P' (P\tau\Sigma P' + \Omega)^{-1} P\tau\Sigma,

and the posterior covariance of returns is :math:`\Sigma + M`. Written this way
a view held with certainty (:math:`\Omega = 0`) holds exactly.

Two conventions set :math:`\Omega`: He and Litterman's
:math:`\Omega = \mathrm{diag}(P\tau\Sigma P')`, and Idzorek's (2005) confidence
levels :math:`c_k \in (0, 1]`. Idzorek calibrates each view's variance
numerically, so that the view alone tilts the weights a share :math:`c_k` of
the way from the market's to those of a certain view; for one view the tilt is
linear in :math:`1/(1 + \omega_k / p_k\tau\Sigma p_k')`, so
:math:`\omega_k = \frac{1 - c_k}{c_k} p_k \tau\Sigma p_k'` solves it exactly.

The unconstrained optimal weights against the covariance of returns,
:math:`w = (\delta\Sigma)^{-1}\mu = w_{mkt} + \frac{\tau}{\delta} P'
(P\tau\Sigma P' + \Omega)^{-1}(Q - P\Pi)`, are the market's with no views (as
in Idzorek, formula 2), and need no inverse of :math:`\Sigma`. He and Litterman
(2002) optimize against the posterior covariance instead,
:math:`(\delta(\Sigma + M))^{-1}\mu = (w_{mkt} + P'\Lambda)/(1 + \tau)`, which
scales the market weights by :math:`1/(1 + \tau)` with no views; both are
reported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
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
    VolatilityArray,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.portfolio._common import (
    ASSETS_MAX,
    COVARIANCE_MAX,
    CorrelationMatrix,
    CovarianceMatrix,
    ReturnWindow,
    bounded,
    covariance,
    matrix_field,
    sample_covariance,
    square,
    window_field,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["black_litterman"]

#: A pick-matrix entry is within this of zero.
_PICK_MAX: Final = 10.0
#: The most views.
_VIEWS_MAX: Final = ASSETS_MAX
#: The smallest Idzorek confidence: below it a view's variance passes 1e15.
_CONFIDENCE_MIN: Final = 1e-6
#: Equilibrium returns: delta (at most 100) times a row of Sigma (at most 100
#: entries of 100) times weights of at most 1.
_EQUILIBRIUM_MAX: Final = 1e6
#: Posterior returns and optimal weights have no bound the inputs can size: views
#: on near-duplicate portfolios give any size. Beyond this, DomainError.
_ESTIMATE_MAX: Final = 1e9
#: A view's variance: (1 - c)/c (at most 1e6) times tau (at most 1) times
#: p Sigma p' (at most (100 * 10)^2 * 100).
_VIEW_VARIANCE_MAX: Final = 1e15
#: Sigma + M lies between Sigma and (1 + tau) Sigma.
_POSTERIOR_MAX: Final = 2 * COVARIANCE_MAX
#: A view matrix P tau Sigma P' + Omega past this condition number is singular.
_CONDITION_MAX: Final = 1e12
#: The months of returns a binding reads: ten years.
_WINDOW: Final = 120

type _Matrix = NDArray[np.float64]

_PickRow = Annotated[
    tuple[Annotated[Ratio, Field(ge=-_PICK_MAX, le=_PICK_MAX)], ...],
    Field(min_length=1, max_length=ASSETS_MAX),
    ARRAY_INPUT,
]


# --- inputs ------------------------------------------------------------------


class BlackLittermanInputs(ModelInputs):
    """The prior (covariance, market weights, risk aversion) and the views."""

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
    market_weights: Annotated[
        tuple[Annotated[Ratio, Field(ge=0.0, le=1.0)], ...], ARRAY_INPUT
    ] = Field(
        min_length=1,
        max_length=ASSETS_MAX,
        description="Each asset's weight in the market portfolio",
    )
    risk_aversion: Ratio = Field(
        2.5,
        ge=1e-3,
        le=100.0,
        description=(
            "The market's risk aversion delta, the excess return per unit of "
            "variance (He and Litterman use 2.5)"
        ),
    )
    tau: Ratio = Field(
        0.05,
        ge=1e-6,
        le=1.0,
        description="The uncertainty of the equilibrium, relative to Sigma",
    )
    picks: tuple[_PickRow, ...] | None = Field(
        None,
        min_length=1,
        max_length=_VIEWS_MAX,
        description=(
            "The pick matrix P: one row per view, one weight per asset (a relative "
            "view's row sums to zero, an absolute view's has a single 1)"
        ),
    )
    view_returns: (
        Annotated[tuple[Annotated[Return, Field(ge=-10.0, le=10.0)], ...], ARRAY_INPUT]
        | None
    ) = Field(
        None,
        min_length=1,
        max_length=_VIEWS_MAX,
        description="Q: each view portfolio's expected return per period",
    )
    confidence: Literal["he_litterman", "idzorek"] = Field(
        "he_litterman",
        description=(
            "How the views' uncertainty is set: 'he_litterman', Omega = "
            "diag(P tau Sigma P'), or 'idzorek', from confidence levels"
        ),
    )
    confidences: (
        Annotated[
            tuple[Annotated[Probability, Field(ge=_CONFIDENCE_MIN, le=1.0)], ...],
            ARRAY_INPUT,
        ]
        | None
    ) = Field(
        None,
        min_length=1,
        max_length=_VIEWS_MAX,
        description=(
            "Idzorek's confidence in each view, from near 0 to 1 (certain); only "
            "with confidence='idzorek'"
        ),
    )

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        size = len(self.market_weights)
        problem = self._risk_problem(size)
        if problem is None:
            problem = self._view_problem(size)
        if problem is not None:
            raise ValueError(problem)
        return self

    def _risk_problem(self, size: int) -> str | None:
        given = [
            self.covariance is not None,
            self.volatilities is not None or self.correlations is not None,
            self.returns is not None,
        ]
        if sum(given) != 1:
            return (
                "give one of: a covariance matrix, volatilities and correlations, "
                "or returns"
            )
        if self.covariance is not None:
            return square(self.covariance, size, "covariance matrix")
        if self.returns is not None:
            if all(len(row) == size for row in self.returns):
                return None
            return f"every row of returns holds one value per asset: {size} assets"
        return self._volatility_problem(size)

    def _volatility_problem(self, size: int) -> str | None:
        if self.volatilities is None or self.correlations is None:
            return "give volatilities and correlations together"
        if len(self.volatilities) != size:
            return f"give one volatility per asset: {size} assets"
        return square(self.correlations, size, "correlation matrix")

    def _view_problem(self, size: int) -> str | None:
        if not any(w > 0 for w in self.market_weights):
            return "the market portfolio needs some weight"
        if (self.picks is None) != (self.view_returns is None):
            return "give picks and view_returns together, or neither"
        if self.picks is not None and self.view_returns is not None:
            problem = _pick_problem(self.picks, self.view_returns, size)
            if problem is not None:
                return problem
        return self._confidence_problem(0 if self.picks is None else len(self.picks))

    def _confidence_problem(self, views: int) -> str | None:
        if self.confidence != "idzorek":
            if self.confidences is None:
                return None
            return "confidences go with confidence='idzorek'"
        if not views:
            return None if self.confidences is None else "confidences go with views"
        if self.confidences is None or len(self.confidences) != views:
            return f"give one confidence per view: {views} views"
        return None

    def matrix(self) -> _Matrix:
        """Return the checked, positive definite covariance matrix."""
        if self.returns is not None:
            return covariance(sample_covariance(self.returns).tolist(), None, None)
        return covariance(self.covariance, self.volatilities, self.correlations)


def _pick_problem(
    picks: tuple[tuple[float, ...], ...], view_returns: tuple[float, ...], size: int
) -> str | None:
    """Say why the pick matrix does not fit the views and the assets, or ``None``."""
    if len(view_returns) != len(picks):
        return f"give one view return per view: {len(picks)} views"
    if any(len(row) != size for row in picks):
        return f"each row of picks holds one weight per asset: {size} assets"
    if any(not any(p != 0 for p in row) for row in picks):
        return "a view's row of picks is all zero"
    return None


# --- outputs -----------------------------------------------------------------

_Estimates = Annotated[
    tuple[Annotated[Ratio, Field(ge=-_ESTIMATE_MAX, le=_ESTIMATE_MAX)], ...],
    ARRAY_INPUT,
]
_PosteriorRow = Annotated[
    tuple[Annotated[Ratio, Field(ge=-_POSTERIOR_MAX, le=_POSTERIOR_MAX)], ...],
    Field(max_length=ASSETS_MAX),
    ARRAY_INPUT,
]


class BlackLittermanOutputs(ModelOutputs):
    equilibrium_returns: Annotated[
        tuple[Annotated[Return, Field(ge=-_EQUILIBRIUM_MAX, le=_EQUILIBRIUM_MAX)], ...],
        ARRAY_INPUT,
    ] = Field(
        max_length=ASSETS_MAX,
        description="Pi = delta Sigma w_mkt: the returns that make the market optimal",
    )
    posterior_returns: Annotated[
        tuple[Annotated[Return, Field(ge=-_ESTIMATE_MAX, le=_ESTIMATE_MAX)], ...],
        ARRAY_INPUT,
    ] = Field(
        max_length=ASSETS_MAX,
        description="The Black-Litterman expected returns per period",
    )
    posterior_covariance: tuple[_PosteriorRow, ...] = Field(
        max_length=ASSETS_MAX,
        description="Sigma + M: the posterior covariance of returns, as rows",
    )
    weights: _Estimates = Field(
        max_length=ASSETS_MAX,
        description=(
            "The unconstrained optimal weights (delta Sigma)^-1 mu: the market's "
            "with no views"
        ),
    )
    posterior_weights: _Estimates = Field(
        max_length=ASSETS_MAX,
        description=(
            "He and Litterman's weights against the posterior covariance, "
            "(delta (Sigma + M))^-1 mu"
        ),
    )
    view_variances: Annotated[
        tuple[Annotated[Ratio, Field(ge=0.0, le=_VIEW_VARIANCE_MAX)], ...], ARRAY_INPUT
    ] = Field(
        max_length=_VIEWS_MAX,
        description="The diagonal of Omega, one variance per view; empty with no views",
    )


# --- the calculation ---------------------------------------------------------


def _view_variances(inputs: BlackLittermanInputs, scaled_views: _Matrix) -> _Matrix:
    """Return the diagonal of Omega from the convention the inputs name."""
    base = np.diag(scaled_views).copy()
    if inputs.confidence == "idzorek" and inputs.confidences is not None:
        confidence = np.asarray(inputs.confidences, dtype=np.float64)
        base *= (1.0 - confidence) / confidence
    return np.clip(base, 0.0, None)


def _solve(matrix: _Matrix, right: _Matrix, what: str) -> _Matrix:
    """Solve ``matrix x = right`` after scaling, refusing a singular matrix."""
    scales = np.sqrt(np.abs(np.diag(matrix)))
    if np.any(scales == 0):
        msg = f"the {what} is singular: a view portfolio has no variance"
        raise DomainError(msg)
    scaled = matrix / np.outer(scales, scales)
    if np.linalg.cond(scaled) > _CONDITION_MAX:
        msg = (
            f"the {what} is singular to working precision: the views are certain "
            "and some are combinations of the others"
        )
        raise DomainError(msg)
    solved = np.linalg.solve(
        scaled, right / (scales if right.ndim == 1 else scales[:, None])
    )
    return solved / (scales if solved.ndim == 1 else scales[:, None])


def _checked(values: _Matrix, limit: float, what: str) -> tuple[float, ...]:
    return tuple(bounded(float(v), limit, what) for v in values)


def _weights(direction: _Matrix, divisor: float, base: _Matrix) -> tuple[float, ...]:
    """Return ``base + direction / divisor``, refusing a weight beyond its bound.

    The check comes before the division, so a tiny divisor (a covariance matrix
    of tiny entries) raises DomainError instead of overflowing.
    """
    limit = _ESTIMATE_MAX * divisor
    if not np.all(np.isfinite(direction)) or float(np.max(np.abs(direction))) > limit:
        msg = (
            f"a weight passes {_ESTIMATE_MAX:g} in size: the views and the "
            "covariance have no representable optimal portfolio"
        )
        raise DomainError(msg)
    return _checked(base + direction / divisor, _ESTIMATE_MAX, "weight")


def _black_litterman(inputs: BlackLittermanInputs) -> BlackLittermanOutputs:
    sigma = inputs.matrix()
    market = np.asarray(inputs.market_weights, dtype=np.float64)
    delta, tau = inputs.risk_aversion, inputs.tau
    # Work with Sigma scaled to a largest entry of one: the posterior returns do
    # not depend on the scale, and nothing tiny is divided by.
    scale = float(np.max(np.abs(sigma)))
    unit = sigma / scale
    prior = delta * (sigma @ market)
    if inputs.picks is None or inputs.view_returns is None:
        mean = prior
        uncertainty = tau * unit
        tilt = np.zeros_like(market)
        variances: _Matrix = np.zeros(0)
    else:
        # A view is the same view at any scale (Omega scales with it), so each
        # row of P and its return are divided by the row's largest entry.
        raw = np.asarray(inputs.picks, dtype=np.float64)
        sizes = np.max(np.abs(raw), axis=1)
        picks = raw / sizes[:, None]
        given = np.asarray(inputs.view_returns, dtype=np.float64)
        if np.any(np.abs(given) > _ESTIMATE_MAX * sizes):
            msg = (
                f"a view's return passes {_ESTIMATE_MAX:g} per unit of its "
                "portfolio: its row of picks is too small for the return it states"
            )
            raise DomainError(msg)
        views = given / sizes
        spread = tau * (unit @ picks.T)  # tau Sigma P' / s, N x K
        scaled_views = picks @ spread  # P tau Sigma P' / s, K x K
        variances = _view_variances(inputs, scaled_views)
        system = scaled_views + np.diag(variances)
        gap = _solve(system, views - picks @ prior, "view matrix")  # times s
        mean = prior + spread @ gap
        uncertainty = tau * unit - spread @ _solve(system, spread.T, "view matrix")
        # (delta Sigma)^-1 mu = w_mkt + (tau / delta) P' (P tau Sigma P' + Omega)^-1
        # (Q - P Pi): no inverse of Sigma.
        tilt = tau * (picks.T @ gap)
        variances = variances * scale * sizes * sizes
    posterior = unit + (uncertainty + uncertainty.T) / 2  # (Sigma + M) / s
    weights = _weights(tilt, delta * scale, market)
    roots = np.sqrt(np.diag(posterior))
    solved = np.linalg.solve(posterior / np.outer(roots, roots), mean / roots) / roots
    posterior_weights = _weights(solved, delta * scale, np.zeros_like(market))
    return BlackLittermanOutputs(
        equilibrium_returns=_checked(prior, _EQUILIBRIUM_MAX, "equilibrium return"),
        posterior_returns=_checked(mean, _ESTIMATE_MAX, "posterior return"),
        posterior_covariance=tuple(
            _checked(row * scale, _POSTERIOR_MAX, "posterior covariance")
            for row in posterior
        ),
        weights=weights,
        posterior_weights=posterior_weights,
        view_variances=_checked(variances, _VIEW_VARIANCE_MAX, "view variance"),
    )


# --- the model ---------------------------------------------------------------

_BLACK_LITTERMAN = Reference(
    key="bl1992",
    citation=(
        "Black, F. and Litterman, R. (1992). Global Portfolio Optimization. "
        "Financial Analysts Journal, 48(5), 28-43."
    ),
    doi="10.2469/faj.v48.n5.28",
    locator="Equilibrium returns and the combination of views with them",
)
_HE_LITTERMAN = Reference(
    key="hl2002",
    citation=(
        "He, G. and Litterman, R. (2002). The Intuition Behind Black-Litterman "
        "Model Portfolios. SSRN working paper 334304; first issued by Goldman "
        "Sachs Investment Management Research, 1999."
    ),
    doi="10.2139/ssrn.334304",
    locator=(
        "Eqs. (8)-(13) and (17), pp. 4-7: the posterior, Sigma + M and the "
        "weights (w_eq + P' Lambda) / (1 + tau); omega = tau p Sigma p' in the "
        "1999 version's footnote 6"
    ),
)
_IDZOREK = Reference(
    key="idzorek2005",
    citation=(
        "Idzorek, T. M. (2005). A Step-by-Step Guide to the Black-Litterman "
        "Model: Incorporating User-Specified Confidence Levels. Ibbotson "
        "Associates working paper; in Forecasting Expected Returns in the "
        "Financial Markets (2007), ch. 2, Elsevier."
    ),
    doi="10.1016/B978-075068321-0.50003-0",
    locator=(
        "Formula (2), the weights against Sigma; eq. (9), the 100% confidence "
        "posterior; section 3, confidence levels from 0% to 100%, which the "
        "closed form here solves exactly"
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
    "volatilities": [0.16, 0.2, 0.24],
    "correlations": [[1.0, 0.5, 0.3], [0.5, 1.0, 0.4], [0.3, 0.4, 1.0]],
    "market_weights": [0.5, 0.3, 0.2],
}


@model(
    id="portfolio.black_litterman",
    version=1,
    title="Black-Litterman expected returns and weights",
    summary=(
        "Equilibrium returns from market weights, views blended in with "
        "He-Litterman or Idzorek uncertainty, the posterior returns and "
        "covariance, and the unconstrained optimal weights."
    ),
    formula=(
        r"\Pi = \delta \Sigma w_{mkt}",
        (
            r"\mu = \Pi + \tau\Sigma P'(P\tau\Sigma P' + \Omega)^{-1}(Q - P\Pi), "
            r"\quad M = \tau\Sigma - \tau\Sigma P'(P\tau\Sigma P' + \Omega)^{-1}"
            r"P\tau\Sigma"
        ),
        (
            r"\Omega_{HL} = \mathrm{diag}(P\tau\Sigma P'), \quad \omega_k = "
            r"\frac{1 - c_k}{c_k}\, p_k \tau\Sigma p_k'"
        ),
        (
            r"w = (\delta\Sigma)^{-1}\mu = w_{mkt} + \tfrac{\tau}{\delta} P'"
            r"(P\tau\Sigma P' + \Omega)^{-1}(Q - P\Pi), \quad w_{HL} = "
            r"(\delta(\Sigma + M))^{-1}\mu"
        ),
    ),
    assumptions=(
        (
            "The market portfolio is mean-variance optimal for the risk aversion "
            "given; returns are per period, as the covariance is."
        ),
        (
            "Views are portfolios of the assets with normally distributed "
            "expected returns; Idzorek's confidence c moves the returns a share c "
            "of the way to a certain view, each view taken alone."
        ),
        (
            "Profile: default binds 120 months of the Ken French 12 industry "
            "portfolios' returns for the covariance; the market weights and the "
            "views are the user's own."
        ),
        (
            "The outputs follow from the inputs the user supplies, the same for "
            "every user: they are formula results, not investment advice."
        ),
    ),
    limitations=(
        (
            "A covariance matrix that is not symmetric and positive definite to "
            "working precision raises DomainError; so do certain views that are "
            "combinations of each other, and an output beyond its bounds."
        ),
        (
            "tau, the risk aversion and the confidences are judgement calls the "
            "results depend on; the model does not estimate them."
        ),
        (
            "The weights are unconstrained (short sales allowed); long-only and "
            "other constraints are not supported."
        ),
        (
            "The Ken French portfolios are library-only: fetched at run time and "
            "never stored."
        ),
    ),
    references=(_BLACK_LITTERMAN, _HE_LITTERMAN, _IDZOREK, _KEN_FRENCH),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("black-litterman", "views", "equilibrium returns", "portfolio"),
    invariants=(
        Invariant(
            id="no_views_return_equilibrium",
            statement=(
                "With no views, the posterior returns are the equilibrium returns "
                "and the posterior covariance is (1 + tau) Sigma."
            ),
        ),
        Invariant(
            id="certain_view_holds_exactly",
            statement=(
                "Views held with certainty hold exactly: each view portfolio's "
                "posterior return is its view return."
            ),
        ),
        Invariant(
            id="no_views_weights_equal_market_weights",
            statement=(
                "With no views, the optimal weights are the market weights, and "
                "He and Litterman's are the market weights over 1 + tau."
            ),
        ),
    ),
    examples=(
        Example(
            name="three_assets_one_view",
            inputs={
                **_EXAMPLE,
                "picks": [[1.0, -1.0, 0.0]],
                "view_returns": [0.002],
            },
            note="The first asset outperforms the second by 0.2% a period.",
        ),
        Example(
            name="three_assets_idzorek",
            inputs={
                **_EXAMPLE,
                "picks": [[1.0, -1.0, 0.0], [0.0, 0.0, 1.0]],
                "view_returns": [0.002, 0.01],
                "confidence": "idzorek",
                "confidences": [0.5, 0.25],
            },
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
def black_litterman(inputs: BlackLittermanInputs) -> BlackLittermanOutputs:
    """Return the equilibrium, the posterior returns and covariance, and weights."""
    return _black_litterman(inputs)
