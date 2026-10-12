# src/pyeconomics/models/risk/value_at_risk.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Value-at-risk and expected shortfall: ``risk.value_at_risk``.

Five calculations, discriminated on ``calculation``. Each reports VaR and
expected shortfall (ES) at a one-tailed confidence level ``c`` over a horizon of
``h`` periods, as positive losses: decimals of the position's value, and money
amounts for a position value. With tail probability ``a = 1 - c``:

- ``parametric``: normal returns, with mean ``mu h`` and volatility
  ``sigma sqrt(h)``, the square-root-of-time rule for i.i.d. returns;
- ``cornish_fisher``: Zangari's modified VaR from skewness and excess kurtosis,
  and the matching modified ES of Boudt, Peterson and Croux (2008), integrating
  the Edgeworth density up to the Cornish-Fisher quantile; over ``h`` periods
  the cumulants of i.i.d. returns add, so skewness scales by ``1 / sqrt(h)``
  and excess kurtosis by ``1 / h``;
- ``historical``: the empirical ``a``-quantile of a return series under a
  stated interpolation rule, with ES the mean loss at or beyond it, scaled to
  the horizon by ``sqrt(h)``;
- ``monte_carlo``: seeded normal or Student-t draws of the horizon return, with
  the standard errors of both estimates;
- ``ewma``: the RiskMetrics exponentially weighted volatility forecast, seeded
  with the first squared return, and the normal VaR and ES of a zero-mean
  return with that volatility.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, TypedDict

import numpy as np
from pydantic import Field

from pyeconomics.core import (
    SEED_MAX,
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Periods,
    Probability,
    Ratio,
    Reference,
    Return,
    ReturnArray,
    Volatility,
    generator,
    model,
    warn,
)
from pyeconomics.models.risk._common import (
    LOSS_MAX,
    POSITION_MAX,
    SERIES_MAX,
    bounded,
    confidence_field,
    horizon_field,
    position_field,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["value_at_risk"]

_NORMAL: Final = NormalDist()
#: The largest periodic volatility and the largest periodic mean return.
_VOLATILITY_MAX: Final = 2.0
_MEAN_MAX: Final = 1.0
#: Skewness and excess kurtosis within these bounds keep the Cornish-Fisher
#: quantile within about 23 standard deviations, and its loss below about
#: 1,250 at the widest inputs (a grid search over the whole input box).
_SKEW_MAX: Final = 3.0
_KURTOSIS_MIN: Final = -2.0
_KURTOSIS_MAX: Final = 20.0
_SIMULATIONS_MIN: Final = 10_000
_SIMULATIONS_MAX: Final = 1_000_000
_AMOUNT_MAX: Final = LOSS_MAX * POSITION_MAX
_Interpolation = Literal["linear", "lower", "higher", "midpoint", "nearest"]


def _seed() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        default=0,
        ge=0,
        le=SEED_MAX,
        description="Random seed (ADR-0008 decision 7): the same seed, the same draws",
    )


def _mean() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(0.0, ge=-_MEAN_MAX, le=_MEAN_MAX, description="Mean return per period")


def _volatility() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        gt=0, le=_VOLATILITY_MAX, description="Standard deviation of returns per period"
    )


def _series(minimum: int, description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(min_length=minimum, max_length=SERIES_MAX, description=description)


def _loss(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-LOSS_MAX, le=LOSS_MAX, description=description)


def _amount(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_AMOUNT_MAX, le=_AMOUNT_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class ParametricInputs(ModelInputs):
    """Normal returns with a mean and a volatility per period."""

    calculation: Literal["parametric"] = Field(
        "parametric", description="Normal VaR and ES"
    )
    mean: Return = _mean()
    volatility: Volatility = _volatility()
    confidence: Probability = confidence_field()
    horizon: Periods = horizon_field()
    position_value: Money = position_field()


class CornishFisherInputs(ModelInputs):
    """The first four moments of returns per period."""

    calculation: Literal["cornish_fisher"] = Field(
        "cornish_fisher", description="Modified VaR and ES from skewness and kurtosis"
    )
    mean: Return = _mean()
    volatility: Volatility = _volatility()
    skewness: Ratio = Field(
        0.0, ge=-_SKEW_MAX, le=_SKEW_MAX, description="Skewness of returns per period"
    )
    excess_kurtosis: Ratio = Field(
        0.0,
        ge=_KURTOSIS_MIN,
        le=_KURTOSIS_MAX,
        description="Excess kurtosis of returns per period",
    )
    confidence: Probability = confidence_field()
    horizon: Periods = horizon_field()
    position_value: Money = position_field()


class HistoricalInputs(ModelInputs):
    """A return series and the rule that picks its quantile."""

    calculation: Literal["historical"] = Field(
        "historical", description="Historical-simulation VaR and ES"
    )
    returns: ReturnArray = _series(2, "Returns per period, in time order")
    interpolation: _Interpolation = Field(
        "linear",
        description=(
            "How the quantile falls between two returns (NumPy's methods; linear "
            "is Hyndman and Fan's definition 7)"
        ),
    )
    confidence: Probability = confidence_field()
    horizon: Periods = horizon_field()
    position_value: Money = position_field()


class MonteCarloInputs(ModelInputs):
    """A return distribution and the size of the simulation."""

    calculation: Literal["monte_carlo"] = Field(
        "monte_carlo", description="Monte Carlo VaR and ES with standard errors"
    )
    mean: Return = _mean()
    volatility: Volatility = _volatility()
    distribution: Literal["normal", "student_t"] = Field(
        "normal", description="Distribution of the standardized horizon return"
    )
    degrees_of_freedom: Ratio = Field(
        5.0,
        gt=2.0,
        le=1_000.0,
        description="Student-t degrees of freedom; ignored for the normal",
    )
    simulations: Count = Field(
        100_000,
        ge=_SIMULATIONS_MIN,
        le=_SIMULATIONS_MAX,
        description="Number of simulated horizon returns",
    )
    seed: Count = _seed()
    confidence: Probability = confidence_field()
    horizon: Periods = horizon_field()
    position_value: Money = position_field()


class EwmaInputs(ModelInputs):
    """A return series and the RiskMetrics decay factor."""

    calculation: Literal["ewma"] = Field(
        "ewma", description="RiskMetrics EWMA volatility with normal VaR and ES"
    )
    returns: ReturnArray = _series(1, "Returns per period, oldest first")
    decay: Ratio = Field(
        0.94,
        ge=0.5,
        le=0.999,
        description="Decay factor lambda (RiskMetrics uses 0.94 for daily data)",
    )
    confidence: Probability = confidence_field()
    horizon: Periods = horizon_field()
    position_value: Money = position_field()


ValueAtRiskInputs = Annotated[
    ParametricInputs
    | CornishFisherInputs
    | HistoricalInputs
    | MonteCarloInputs
    | EwmaInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class _Losses(ModelOutputs):
    value_at_risk: Return = _loss("VaR as a decimal of the position (a loss > 0)")
    expected_shortfall: Return = _loss(
        "Expected shortfall as a decimal of the position (a loss > 0)"
    )
    value_at_risk_amount: Money = _amount(
        "VaR in money: the decimal times the position"
    )
    expected_shortfall_amount: Money = _amount(
        "Expected shortfall in money: the decimal times the position"
    )


class ParametricOutputs(_Losses):
    calculation: Literal["parametric"] = Field(
        "parametric", description="Normal VaR and ES"
    )
    quantile: Ratio = Field(
        ge=0, le=4.0, description="Standard normal quantile of the loss at confidence c"
    )


class CornishFisherOutputs(_Losses):
    calculation: Literal["cornish_fisher"] = Field(
        "cornish_fisher", description="Modified VaR and ES from skewness and kurtosis"
    )
    quantile: Ratio = Field(
        ge=-1e3,
        le=1e3,
        description=(
            "Cornish-Fisher quantile of the standardized loss at the confidence "
            "level (the normal quantile without skewness or excess kurtosis)"
        ),
    )


class HistoricalOutputs(_Losses):
    calculation: Literal["historical"] = Field(
        "historical", description="Historical-simulation VaR and ES"
    )
    observations: Count = Field(ge=2, le=SERIES_MAX, description="Returns used")
    tail_observations: Count = Field(
        ge=1, le=SERIES_MAX, description="Returns at or below the VaR quantile"
    )


class MonteCarloOutputs(_Losses):
    calculation: Literal["monte_carlo"] = Field(
        "monte_carlo", description="Monte Carlo VaR and ES with standard errors"
    )
    value_at_risk_standard_error: Return = Field(
        ge=0, le=LOSS_MAX, description="Standard error of the simulated VaR"
    )
    expected_shortfall_standard_error: Return = Field(
        ge=0, le=LOSS_MAX, description="Standard error of the simulated ES"
    )
    simulations: Count = Field(
        ge=_SIMULATIONS_MIN, le=_SIMULATIONS_MAX, description="Simulated returns"
    )


class EwmaOutputs(_Losses):
    calculation: Literal["ewma"] = Field(
        "ewma", description="RiskMetrics EWMA volatility with normal VaR and ES"
    )
    volatility_forecast: Volatility = Field(
        ge=0, le=100.0, description="Volatility forecast for the next period"
    )


ValueAtRiskOutputs = Annotated[
    ParametricOutputs
    | CornishFisherOutputs
    | HistoricalOutputs
    | MonteCarloOutputs
    | EwmaOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


class _LossValues(TypedDict):
    value_at_risk: float
    expected_shortfall: float
    value_at_risk_amount: float
    expected_shortfall_amount: float


def _losses(var: float, es: float, position: float) -> _LossValues:
    """Bound a VaR and an ES, with ES at least VaR, and price them."""
    var = bounded(var, -LOSS_MAX, LOSS_MAX, "value-at-risk")
    # An ES cannot fall below its VaR; rounding in a tail mean can put it an
    # ulp below.
    es = bounded(max(es, var), -LOSS_MAX, LOSS_MAX, "expected shortfall")
    return {
        "value_at_risk": var,
        "expected_shortfall": es,
        "value_at_risk_amount": var * position,
        "expected_shortfall_amount": es * position,
    }


def _normal_tail(confidence: float) -> tuple[float, float]:
    """Return ``z`` and the normal tail mean ``phi(z) / (1 - c)``."""
    z = _NORMAL.inv_cdf(confidence)
    return z, _NORMAL.pdf(z) / (1.0 - confidence)


def _parametric(inputs: ParametricInputs) -> ParametricOutputs:
    z, tail = _normal_tail(inputs.confidence)
    mean = inputs.mean * inputs.horizon
    scale = inputs.volatility * math.sqrt(inputs.horizon)
    return ParametricOutputs(
        quantile=z,
        **_losses(-mean + z * scale, -mean + tail * scale, inputs.position_value),
    )


def _truncated_moments(g: float) -> list[float]:
    """Return ``J_q = int_{-inf}^g x^q phi(x) dx`` for q = 0, ..., 7."""
    density = _NORMAL.pdf(g)
    moments = [_NORMAL.cdf(g), -density]
    for q in range(2, 8):
        moments.append(-(g ** (q - 1)) * density + (q - 1) * moments[q - 2])
    return moments


def _cornish_fisher(inputs: CornishFisherInputs) -> CornishFisherOutputs:
    alpha = 1.0 - inputs.confidence
    z = -_NORMAL.inv_cdf(inputs.confidence)
    skew = inputs.skewness / math.sqrt(inputs.horizon)
    kurt = inputs.excess_kurtosis / inputs.horizon
    g = (
        z
        + (z * z - 1) * skew / 6
        + (z**3 - 3 * z) * kurt / 24
        - (2 * z**3 - 5 * z) * skew * skew / 36
    )
    slope = (
        1 + z * skew / 3 + (3 * z * z - 3) * kurt / 24 - (6 * z * z - 5) * skew**2 / 36
    )
    if slope <= 0:
        warn(
            "outside_expansion_domain",
            "the Cornish-Fisher quantile falls as the confidence rises here; the "
            "skewness and kurtosis are outside the expansion's domain of validity",
        )
    j = _truncated_moments(g)
    partial = (
        j[1]
        + skew / 6 * (j[4] - 3 * j[2])
        + kurt / 24 * (j[5] - 6 * j[3] + 3 * j[1])
        + skew * skew / 72 * (j[7] - 15 * j[5] + 45 * j[3] - 15 * j[1])
    )
    tail = partial / alpha
    if tail > g:
        warn(
            "tail_mean_capped",
            "the Edgeworth tail mean lies above the Cornish-Fisher quantile; the "
            "expected shortfall is set to the VaR",
        )
        tail = g
    mean = inputs.mean * inputs.horizon
    scale = inputs.volatility * math.sqrt(inputs.horizon)
    return CornishFisherOutputs(
        quantile=bounded(-g, -1e3, 1e3, "Cornish-Fisher quantile"),
        **_losses(-(mean + scale * g), -(mean + scale * tail), inputs.position_value),
    )


def _tail(returns: NDArray[np.float64], quantile: float) -> NDArray[np.float64]:
    """Return the returns at or below ``quantile``, or the quantile alone."""
    tail = returns[returns <= quantile]
    return tail if tail.size else np.array([quantile])


def _historical(inputs: HistoricalInputs) -> HistoricalOutputs:
    returns = np.asarray(inputs.returns, dtype=np.float64)
    alpha = 1.0 - inputs.confidence
    quantile = float(np.quantile(returns, alpha, method=inputs.interpolation))
    tail = _tail(returns, quantile)
    root = math.sqrt(inputs.horizon)
    return HistoricalOutputs(
        observations=returns.size,
        tail_observations=tail.size,
        **_losses(
            -quantile * root, -float(np.mean(tail)) * root, inputs.position_value
        ),
    )


def _standardized_density(inputs: MonteCarloInputs, u: float) -> float:
    """Return the density of the unit-variance draw at ``u``."""
    if inputs.distribution == "normal":
        return _NORMAL.pdf(u)
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    nu = inputs.degrees_of_freedom
    k = math.sqrt((nu - 2) / nu)
    return float(stats.t.pdf(u / k, nu)) / k


def _monte_carlo(inputs: MonteCarloInputs) -> MonteCarloOutputs:
    draws = generator(inputs.seed)
    n = inputs.simulations
    if inputs.distribution == "normal":
        shocks = draws.standard_normal(n)
    else:
        nu = inputs.degrees_of_freedom
        shocks = draws.standard_t(nu, n) * math.sqrt((nu - 2) / nu)
    mean = inputs.mean * inputs.horizon
    scale = inputs.volatility * math.sqrt(inputs.horizon)
    returns = mean + scale * shocks
    alpha = 1.0 - inputs.confidence
    quantile = float(np.quantile(returns, alpha))
    tail = _tail(returns, quantile)
    var, es = -quantile, -float(np.mean(tail))
    density = _standardized_density(inputs, (quantile - mean) / scale) / scale
    var_error = (
        math.sqrt(alpha * (1 - alpha) / n) / density if density > 0 else math.inf
    )
    spread = float(np.var(tail)) + inputs.confidence * (max(es, var) - var) ** 2
    es_error = math.sqrt(spread / (n * alpha))
    return MonteCarloOutputs(
        value_at_risk_standard_error=bounded(
            var_error, 0.0, LOSS_MAX, "VaR standard error"
        ),
        expected_shortfall_standard_error=bounded(
            es_error, 0.0, LOSS_MAX, "ES standard error"
        ),
        simulations=n,
        **_losses(var, es, inputs.position_value),
    )


def _ewma(inputs: EwmaInputs) -> EwmaOutputs:
    lam = inputs.decay
    variance = inputs.returns[0] ** 2
    for r in inputs.returns[1:]:
        variance = lam * variance + (1 - lam) * r * r
    sigma = math.sqrt(variance)
    z, tail = _normal_tail(inputs.confidence)
    scale = sigma * math.sqrt(inputs.horizon)
    return EwmaOutputs(
        volatility_forecast=sigma,
        **_losses(z * scale, tail * scale, inputs.position_value),
    )


# --- the model ---------------------------------------------------------------

_BOUDT = Reference(
    key="boudt2008",
    citation=(
        "Boudt, K., Peterson, B. and Croux, C. (2008). Estimation and "
        "decomposition of downside risk for portfolios with non-normal returns. "
        "The Journal of Risk, 11(2), 79-103."
    ),
    doi="10.21314/JOR.2008.188",
    locator=(
        "Section 2: modified VaR (after Zangari, 1996, RiskMetrics Monitor) and "
        "modified ES from the Edgeworth expansion"
    ),
)
_CORNISH_FISHER = Reference(
    key="cornish1938",
    citation=(
        "Cornish, E. A. and Fisher, R. A. (1938). Moments and cumulants in the "
        "specification of distributions. Revue de l'Institut International de "
        "Statistique, 5(4), 307-320."
    ),
    doi="10.2307/1400905",
    locator="The expansion of a quantile in terms of cumulants",
)
_HYNDMAN_FAN = Reference(
    key="hyndman1996",
    citation=(
        "Hyndman, R. J. and Fan, Y. (1996). Sample quantiles in statistical "
        "packages. The American Statistician, 50(4), 361-365."
    ),
    doi="10.1080/00031305.1996.10473566",
    locator="Section 2, definitions 1 to 9 (definition 7 is linear interpolation)",
)
_RISKMETRICS = Reference(
    key="riskmetrics1996",
    citation=(
        "J.P. Morgan and Reuters (1996). RiskMetrics Technical Document, 4th ed. "
        "Morgan Guaranty Trust Company."
    ),
    url="https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a",
    locator=(
        "Section 5.2.1, Eq. [5.3] and Table 5.3 (the recursive EWMA variance, "
        "seeded with the first squared return; decay 0.94 for daily data); "
        "Eq. [5.21] (the square-root-of-time rule)"
    ),
)
_BASEL = Reference(
    key="bcbs2019",
    citation=(
        "Basel Committee on Banking Supervision (2019). Minimum capital "
        "requirements for market risk. Bank for International Settlements."
    ),
    url="https://www.bis.org/bcbs/publ/d457.htm",
    locator="MAR33.3 (ES at 97.5%) and MAR32.5 (VaR at 99% for backtesting)",
)
_GLASSERMAN = Reference(
    key="glasserman2003",
    citation=(
        "Glasserman, P. (2003). Monte Carlo Methods in Financial Engineering. Springer."
    ),
    url="https://openlibrary.org/isbn/9780387004518",
    isbn="9780387004518",
    locator="Section 9.1 (the standard error of an estimated quantile)",
)
_MANISTRE = Reference(
    key="manistre2005",
    citation=(
        "Manistre, B. J. and Hancock, G. H. (2005). Variance of the CTE "
        "estimator. North American Actuarial Journal, 9(2), 129-156."
    ),
    doi="10.1080/10920277.2005.10596207",
    locator="The asymptotic variance of the empirical CTE",
)


@model(
    id="risk.value_at_risk",
    version=1,
    title="Value-at-risk and expected shortfall",
    summary=(
        "VaR and expected shortfall as positive losses by the parametric normal, "
        "Cornish-Fisher, historical, Monte Carlo and RiskMetrics EWMA methods."
    ),
    formula=(
        (
            r"\mathrm{VaR} = -\mu h + z_c \sigma\sqrt{h}, \quad "
            r"\mathrm{ES} = -\mu h + \sigma\sqrt{h}\,\frac{\varphi(z_c)}{1 - c}"
        ),
        (
            r"g = z + \tfrac{(z^2 - 1)S}{6} + \tfrac{(z^3 - 3z)K}{24} - "
            r"\tfrac{(2z^3 - 5z)S^2}{36}, \quad z = \Phi^{-1}(1 - c)"
        ),
        (
            r"\mathrm{mES} = -\mu - \frac{\sigma}{1 - c}\int_{-\infty}^{g} "
            r"x\,\varphi(x)\left[1 + \tfrac{S}{6}He_3(x) + \tfrac{K}{24}He_4(x) + "
            r"\tfrac{S^2}{72}He_6(x)\right]dx"
        ),
        (
            r"\mathrm{VaR} = -\sqrt{h}\,\hat{q}_{1 - c}, \quad "
            r"\mathrm{ES} = -\sqrt{h}\,\overline{r_t \mid r_t \le \hat{q}_{1 - c}}"
        ),
        (
            r"\sigma_t^2 = \lambda\sigma_{t-1}^2 + (1 - \lambda) r_t^2, "
            r"\quad \sigma_1^2 = r_1^2"
        ),
        (
            r"\mathrm{SE}(\widehat{\mathrm{VaR}}) = \frac{\sqrt{c(1 - c)/N}}"
            r"{f(\hat{q})}, \quad \mathrm{SE}(\widehat{\mathrm{ES}}) = "
            r"\sqrt{\frac{s^2_{tail} + c(\mathrm{ES} - \mathrm{VaR})^2}{N(1 - c)}}"
        ),
    ),
    assumptions=(
        (
            "Losses are positive decimals of the position's value; a negative VaR "
            "is a gain at that confidence."
        ),
        (
            "Scaling to a horizon of h periods by the square root of h assumes "
            "i.i.d. returns; the historical method scales its one-period "
            "quantile and tail mean the same way."
        ),
        (
            "The historical and Monte Carlo ES is the mean loss at or beyond the "
            "VaR quantile; the quantile interpolates as the input names "
            "(Monte Carlo: linearly)."
        ),
        (
            "The Monte Carlo horizon return is drawn directly, normal or Student-t "
            "scaled to the volatility; the Student-t horizon return is not a sum "
            "of t draws."
        ),
        (
            "The EWMA forecast assumes a zero mean and starts its recursion from "
            "the first squared return, as RiskMetrics' Table 5.3 does."
        ),
    ),
    limitations=(
        (
            "The Cornish-Fisher expansion is valid only for moderate skewness and "
            "kurtosis: outside its domain the quantile is not monotone in the "
            "confidence level, and the model warns."
        ),
        (
            "When the Edgeworth tail mean lies above the Cornish-Fisher quantile, "
            "the modified ES is set to the VaR, with a warning."
        ),
        (
            "An output outside its bounds raises DomainError; the input bounds "
            "are sized so that none is known to occur."
        ),
        "No method models volatility clustering except the EWMA forecast.",
    ),
    references=(
        _BOUDT,
        _CORNISH_FISHER,
        _HYNDMAN_FAN,
        _RISKMETRICS,
        _BASEL,
        _GLASSERMAN,
        _MANISTRE,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.HEAVY,
    tags=("value at risk", "expected shortfall", "cornish-fisher", "ewma", "risk"),
    invariants=(
        Invariant(
            id="es_at_least_var",
            statement="Expected shortfall is never below VaR, for every method.",
        ),
        Invariant(
            id="var_increases_with_confidence",
            statement=(
                "VaR does not fall as the confidence level rises (Cornish-Fisher "
                "within the expansion's domain; Monte Carlo with the same seed)."
            ),
        ),
        Invariant(
            id="parametric_var_scales_with_sqrt_horizon",
            statement=(
                "With a zero mean, the parametric VaR over h periods is sqrt(h) "
                "times the one-period VaR."
            ),
        ),
        Invariant(
            id="cornish_fisher_reduces_to_normal",
            statement=(
                "With zero skewness and excess kurtosis, the Cornish-Fisher VaR "
                "and ES equal the parametric normal ones."
            ),
        ),
    ),
    examples=(
        Example(
            name="ten_day_normal",
            inputs={
                "calculation": "parametric",
                "volatility": 0.012,
                "confidence": 0.99,
                "horizon": 10,
                "position_value": 1_000_000,
            },
        ),
        Example(
            name="fat_left_tail",
            inputs={
                "calculation": "cornish_fisher",
                "mean": 0.0005,
                "volatility": 0.012,
                "skewness": -0.5,
                "excess_kurtosis": 2.0,
                "confidence": 0.99,
            },
        ),
        Example(
            name="ten_returns",
            inputs={
                "calculation": "historical",
                "returns": [
                    -0.031,
                    0.012,
                    -0.008,
                    0.004,
                    -0.019,
                    0.022,
                    0.001,
                    -0.012,
                    0.009,
                    -0.002,
                ],
                "confidence": 0.9,
            },
        ),
        Example(
            name="student_t_simulation",
            inputs={
                "calculation": "monte_carlo",
                "volatility": 0.012,
                "distribution": "student_t",
                "degrees_of_freedom": 4,
                "simulations": 20_000,
                "seed": 7,
            },
        ),
        Example(
            name="riskmetrics_forecast",
            inputs={
                "calculation": "ewma",
                "returns": [0.004, -0.011, 0.007, -0.002, 0.013, -0.009],
                "confidence": 0.95,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def value_at_risk(inputs: ValueAtRiskInputs) -> ValueAtRiskOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], ValueAtRiskOutputs]]] = {
    ParametricInputs: _parametric,
    CornishFisherInputs: _cornish_fisher,
    HistoricalInputs: _historical,
    MonteCarloInputs: _monte_carlo,
    EwmaInputs: _ewma,
}
