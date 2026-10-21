# src/pyeconomics/models/econometrics/garch.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""GARCH, GJR-GARCH and EGARCH volatility models: ``econometrics.garch``.

An adapter over arch (ROADMAP section 4 7.3, "wrap, don't rewrite"), behind the
``econometrics`` extra: arch is imported inside ``compute``, and without it the
model raises :class:`~pyeconomics.core.MissingOptionalDependencyError` naming
``pyeconomics[econometrics]``. arch publishes no wheel for CPython 3.15 yet, so
the extra leaves it out there and the error says so (issue #154).

Returns :math:`r_t = \mu + \varepsilon_t` (or :math:`\mu = 0`), with
:math:`\varepsilon_t = \sigma_t z_t` and :math:`z_t` standard normal or a
standardized Student's t. The ``calculation`` names the variance process:

- ``garch`` (Bollerslev 1986):
  :math:`\sigma^2_t = \omega + \sum_i \alpha_i \varepsilon^2_{t-i}
  + \sum_k \beta_k \sigma^2_{t-k}`;
- ``gjr`` (Glosten, Jagannathan and Runkle 1993) adds
  :math:`\sum_j \gamma_j \varepsilon^2_{t-j} 1[\varepsilon_{t-j} < 0]`;
- ``egarch`` (Nelson 1991):
  :math:`\ln\sigma^2_t = \omega + \sum_i \alpha_i (|z_{t-i}| - \sqrt{2/\pi})
  + \sum_j \gamma_j z_{t-j} + \sum_k \beta_k \ln\sigma^2_{t-k}`.

The returns are decimals. The model fits them in percent (times 100, and by a
further power of ten when the percent returns' variance lies outside
[0.1, 10,000), as arch advises) and reports every estimate back in decimals:
:math:`\mu` as a return per period, :math:`\omega` as a variance per period
(GARCH and GJR) or as the intercept of the log variance of decimal returns
(EGARCH), the log-likelihood of the decimal returns, and variances and
volatilities per period, annualized by an explicit number of periods a year.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    SEED_MAX,
    AsOf,
    Binding,
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    MissingOptionalDependencyError,
    ModelInputs,
    ModelOutputs,
    Probability,
    Ratio,
    Reference,
    Return,
    Volatility,
    generator,
    has_spread,
    library_warnings,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

__all__ = ["garch"]

#: The extra that installs arch.
EXTRA: Final = "econometrics"
#: What the error says where the extra cannot install arch (the Wheel rule).
GAP_NOTE: Final = (
    "On Python 3.15 and later the extra cannot install it yet: arch publishes no "
    "wheel for CPython 3.15 (pyeconomics issue #154)"
)
#: The fewest and most returns a fit takes. A 10,000-period GJR(2, 2, 2) fit
#: with Student's t errors takes about a second.
OBSERVATIONS_MIN: Final = 100
OBSERVATIONS_MAX: Final = 10_000
#: The largest p, o and q: each lag adds parameters a sample rarely identifies.
ORDER_MAX: Final = 2
#: The longest forecast, in periods: two years of trading days.
HORIZON_MAX: Final = 500
#: EGARCH forecasts beyond one period are simulated, with this many paths.
SIMULATIONS_MIN: Final = 100
SIMULATIONS_MAX: Final = 10_000
#: A return per period is a decimal of at most this size.
RETURN_MAX: Final = 10.0
#: Returns that vary less than this (their standard deviation) cannot be
#: rescaled into a range the optimizer handles.
SPREAD_MIN: Final = 1e-8
#: A year has at most this many periods: calendar days.
PERIODS_PER_YEAR_MAX: Final = 366
#: Student's t degrees of freedom: above 2 the variance exists; arch bounds the
#: estimate at 500.
NU_MIN: Final = 2.05
NU_MAX: Final = 500.0
#: A fixed parameter's size, and an estimate's (outputs beyond: DomainError).
PARAMETER_MAX: Final = 1e3
ESTIMATE_MAX: Final = 1e6
#: A variance per period of returns of at most RETURN_MAX, forecast over at most
#: HORIZON_MAX periods by an integrated process, stays far below this.
VARIANCE_MAX: Final = 1e8
_VOLATILITY_MAX: Final = math.sqrt(VARIANCE_MAX * PERIODS_PER_YEAR_MAX)
_STATISTIC_MAX: Final = 1e300
_LIKELIHOOD_MAX: Final = 1e15
#: arch's own scale rule: a variance in [0.1, 10,000) suits its optimizer.
_SCALE_LOW: Final = 0.1
_SCALE_HIGH: Final = 1e4
_PERCENT: Final = 100.0
#: A persistence this close to one counts as one (an integrated variance).
_PERSISTENCE_SLACK: Final = 1e-12
_NAME_MAX: Final = 16
_PARAMETERS_MAX: Final = 2 + 3 * ORDER_MAX + 1
#: The default demonstration window: four years of trading days, the most a
#: binding reads.
_WINDOW: Final = 1000

_Return = Annotated[Return, Field(ge=-RETURN_MAX, le=RETURN_MAX)]
_Parameter = Annotated[Ratio, Field(ge=-PARAMETER_MAX, le=PARAMETER_MAX)]
_Estimate = Annotated[Ratio, Field(ge=-ESTIMATE_MAX, le=ESTIMATE_MAX)]
_Error = Annotated[Ratio, Field(ge=0, le=_STATISTIC_MAX)]
_Statistic = Annotated[Ratio, Field(ge=-_STATISTIC_MAX, le=_STATISTIC_MAX)]
_PValue = Annotated[Probability, Field(ge=0, le=1)]
_Variance = Annotated[Ratio, Field(ge=0, le=VARIANCE_MAX)]
_Volatility = Annotated[Volatility, Field(ge=0, le=_VOLATILITY_MAX)]
_Horizon = Annotated[Count, Field(ge=1, le=HORIZON_MAX)]
_Name = Annotated[str, Field(min_length=1, max_length=_NAME_MAX)]


# --- inputs ------------------------------------------------------------------


class _Garch(ModelInputs):
    """What every variance process shares: the returns, the mean, the errors."""

    returns: Annotated[tuple[_Return, ...], ARRAY_INPUT] = Field(
        min_length=OBSERVATIONS_MIN,
        max_length=OBSERVATIONS_MAX,
        description="Returns per period, as decimals (0.01 is 1%), oldest first",
    )
    periods_per_year: Count = Field(
        ge=1,
        le=PERIODS_PER_YEAR_MAX,
        description=(
            "Periods in a year, to annualize volatilities: 252 for trading days, "
            "52 for weeks, 12 for months"
        ),
    )
    mean: Literal["constant", "zero"] = Field(
        "constant", description="The mean of the returns: a constant mu, or zero"
    )
    distribution: Literal["normal", "student_t"] = Field(
        "normal",
        description="The standardized errors: normal, or Student's t with nu estimated",
    )
    p: Count = Field(
        1, ge=1, le=ORDER_MAX, description="Lags of the shock terms (alpha), p"
    )
    q: Count = Field(
        1, ge=0, le=ORDER_MAX, description="Lags of the variance terms (beta), q"
    )
    horizon: _Horizon = Field(10, description="Periods to forecast the variance over")
    covariance: Literal["robust", "classic"] = Field(
        "robust",
        description=(
            "Standard errors: 'robust' (Bollerslev-Wooldridge quasi-maximum "
            "likelihood) or 'classic' (the inverse information matrix)"
        ),
    )
    fixed_parameters: Annotated[tuple[_Parameter, ...], ARRAY_INPUT] | None = Field(
        None,
        max_length=_PARAMETERS_MAX,
        description=(
            "Parameters to evaluate instead of estimating, in the order of "
            "parameter_names and in decimal units; null estimates them"
        ),
    )

    @property
    def o(self) -> int:
        """The asymmetric lags; none for GARCH."""
        return 0

    def names(self) -> tuple[str, ...]:
        """Return the parameter names, in arch's order."""
        return (
            *(("mu",) if self.mean == "constant" else ()),
            "omega",
            *(f"alpha[{i}]" for i in range(1, self.p + 1)),
            *(f"gamma[{i}]" for i in range(1, self.o + 1)),
            *(f"beta[{i}]" for i in range(1, self.q + 1)),
            *(("nu",) if self.distribution == "student_t" else ()),
        )

    @model_validator(mode="after")
    def _fixed(self) -> Self:
        if self.fixed_parameters is None:
            return self
        names = self.names()
        if len(self.fixed_parameters) != len(names):
            msg = (
                f"fixed_parameters must give {len(names)} values, one for each of "
                f"{', '.join(names)}"
            )
            raise ValueError(msg)
        values = dict(zip(names, self.fixed_parameters, strict=True))
        if "nu" in values and not NU_MIN <= values["nu"] <= NU_MAX:
            msg = f"nu must lie in [{NU_MIN}, {NU_MAX}] for the variance to exist"
            raise ValueError(msg)
        if abs(values.get("mu", 0.0)) > RETURN_MAX:
            msg = f"mu must lie in [-{RETURN_MAX:g}, {RETURN_MAX:g}]"
            raise ValueError(msg)
        self._check_process(values)
        return self

    def _check_process(self, values: dict[str, float]) -> None:
        """Refuse a variance process that is negative or explosive."""
        if values["omega"] <= 0:
            msg = "omega must be positive"
            raise ValueError(msg)
        terms = _terms(values)
        alphas, gammas, betas = terms["alpha"], terms["gamma"], terms["beta"]
        if min(alphas + betas, default=0.0) < 0:
            msg = "alpha and beta must not be negative"
            raise ValueError(msg)
        if any(
            (alphas[i] if i < len(alphas) else 0.0) + gamma < 0
            for i, gamma in enumerate(gammas)
        ):
            msg = "alpha + gamma must not be negative at any lag"
            raise ValueError(msg)
        if sum(alphas) + sum(gammas) / 2 + sum(betas) > 1:
            msg = (
                "the persistence alpha + gamma / 2 + beta must not exceed one: an "
                "explosive process has no forecast this model can represent"
            )
            raise ValueError(msg)


class GarchInputs(_Garch):
    """GARCH(p, q): the variance responds to squared shocks of either sign."""

    calculation: Literal["garch"] = Field(
        "garch", description="GARCH (Bollerslev 1986)"
    )


class GjrInputs(_Garch):
    """GJR-GARCH(p, o, q): negative shocks add gamma to the response."""

    calculation: Literal["gjr"] = Field(
        "gjr", description="GJR-GARCH (Glosten, Jagannathan and Runkle 1993)"
    )
    asymmetric_lags: Count = Field(
        1,
        ge=1,
        le=ORDER_MAX,
        description="Lags of the negative-shock terms (gamma), o",
    )

    @property
    def o(self) -> int:
        """The asymmetric lags."""
        return self.asymmetric_lags


class EgarchInputs(_Garch):
    """EGARCH(p, o, q): the log variance responds to standardized shocks."""

    calculation: Literal["egarch"] = Field("egarch", description="EGARCH (Nelson 1991)")
    asymmetric_lags: Count = Field(
        1,
        ge=0,
        le=ORDER_MAX,
        description="Lags of the signed standardized-shock terms (gamma), o",
    )
    simulations: Count = Field(
        1000,
        ge=SIMULATIONS_MIN,
        le=SIMULATIONS_MAX,
        description="Simulated paths for forecasts beyond one period",
    )
    seed: Count = Field(
        0,
        ge=0,
        le=SEED_MAX,
        description="Seed of the simulated forecasts: the same seed, the same draws",
    )

    @property
    def o(self) -> int:
        """The asymmetric lags."""
        return self.asymmetric_lags

    def _check_process(self, values: dict[str, float]) -> None:
        """Refuse a log variance that does not revert: |sum of beta| < 1."""
        if not abs(sum(_terms(values)["beta"])) < 1:
            msg = "the sum of beta must lie strictly between -1 and 1"
            raise ValueError(msg)


GarchFamilyInputs = Annotated[
    GarchInputs | GjrInputs | EgarchInputs, Field(discriminator="calculation")
]


# --- outputs -----------------------------------------------------------------


def _parameters(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(max_length=_PARAMETERS_MAX, description=description)


def _optional(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(None, max_length=_PARAMETERS_MAX, description=description)


def _forecasts(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(max_length=HORIZON_MAX, description=description)


class _Fit(ModelOutputs):
    """A fitted (or evaluated) volatility model and its forecasts."""

    parameter_names: Annotated[tuple[_Name, ...], ARRAY_INPUT] = _parameters(
        "Parameter names, in arch's order: mu, omega, alpha, gamma, beta, nu"
    )
    parameters: Annotated[tuple[_Estimate, ...], ARRAY_INPUT] = _parameters(
        "Estimates in decimal units: mu a return per period, omega a variance per "
        "period (the log-variance intercept for EGARCH), the rest pure numbers"
    )
    standard_errors: Annotated[tuple[_Error, ...], ARRAY_INPUT] | None = _optional(
        "Standard errors of the parameters; null for fixed parameters"
    )
    t_statistics: Annotated[tuple[_Statistic, ...], ARRAY_INPUT] | None = _optional(
        "Parameter over standard error; null without standard errors"
    )
    p_values: Annotated[tuple[_PValue, ...], ARRAY_INPUT] | None = _optional(
        "Two-sided p-values from the normal distribution"
    )
    log_likelihood: Ratio = Field(
        ge=-_LIKELIHOOD_MAX,
        le=_LIKELIHOOD_MAX,
        description="Log-likelihood of the decimal returns",
    )
    aic: Ratio = Field(
        ge=-_LIKELIHOOD_MAX, le=_LIKELIHOOD_MAX, description="Akaike criterion"
    )
    bic: Ratio = Field(
        ge=-_LIKELIHOOD_MAX, le=_LIKELIHOOD_MAX, description="Bayesian criterion"
    )
    observations: Count = Field(
        ge=OBSERVATIONS_MIN, le=OBSERVATIONS_MAX, description="Returns fitted"
    )
    persistence: Ratio = Field(
        ge=-ESTIMATE_MAX,
        le=ESTIMATE_MAX,
        description=(
            "alpha + beta (GARCH), alpha + gamma / 2 + beta (GJR) or beta "
            "(EGARCH), each summed over its lags"
        ),
    )
    unconditional_volatility: _Volatility | None = Field(
        description=(
            "Long-run volatility per period, sqrt(omega / (1 - persistence)); null "
            "when persistence is at least one, and for EGARCH"
        ),
    )
    unconditional_volatility_annualized: _Volatility | None = Field(
        description="The unconditional volatility times sqrt(periods_per_year)"
    )
    last_volatility: _Volatility = Field(
        description="The conditional volatility of the last period"
    )
    last_volatility_annualized: _Volatility = Field(
        description="The last conditional volatility times sqrt(periods_per_year)"
    )
    horizons: Annotated[tuple[_Horizon, ...], ARRAY_INPUT] = _forecasts(
        "Forecast horizons, 1 to horizon periods ahead"
    )
    variance_forecasts: Annotated[tuple[_Variance, ...], ARRAY_INPUT] = _forecasts(
        "Forecast variance of the decimal return each period ahead"
    )
    volatility_forecasts_annualized: Annotated[tuple[_Volatility, ...], ARRAY_INPUT] = (
        _forecasts("sqrt(periods_per_year x the variance forecast) each period ahead")
    )
    term_volatility_annualized: Annotated[tuple[_Volatility, ...], ARRAY_INPUT] = (
        _forecasts(
            "Annualized volatility of the cumulative return to each horizon: "
            "sqrt(periods_per_year / h x the sum of the first h variance forecasts)"
        )
    )


class GarchOutputs(_Fit):
    calculation: Literal["garch"] = Field("garch", description="GARCH")


class GjrOutputs(_Fit):
    calculation: Literal["gjr"] = Field("gjr", description="GJR-GARCH")


class EgarchOutputs(_Fit):
    calculation: Literal["egarch"] = Field("egarch", description="EGARCH")


GarchFamilyOutputs = Annotated[
    GarchOutputs | GjrOutputs | EgarchOutputs, Field(discriminator="calculation")
]
_OUTPUTS: Final[dict[type[_Garch], type[GarchOutputs | GjrOutputs | EgarchOutputs]]] = {
    GarchInputs: GarchOutputs,
    GjrInputs: GjrOutputs,
    EgarchInputs: EgarchOutputs,
}


# --- the computation ---------------------------------------------------------


def _terms(values: dict[str, float]) -> dict[str, list[float]]:
    """Group the alpha, gamma and beta values by family, in lag order."""
    grouped: dict[str, list[float]] = {"alpha": [], "gamma": [], "beta": []}
    for name, value in values.items():
        family = name.partition("[")[0]
        if family in grouped:
            grouped[family].append(value)
    return grouped


def _persistence(inputs: _Garch, values: dict[str, float]) -> float:
    terms = _terms(values)
    if isinstance(inputs, EgarchInputs):
        return sum(terms["beta"])
    return sum(terms["alpha"]) + sum(terms["gamma"]) / 2 + sum(terms["beta"])


def _scale(returns: NDArray[np.float64]) -> float:
    """Percent, then the power of ten arch advises for its optimizer."""
    variance = float(np.var(returns))
    scale = _PERCENT
    while not _SCALE_LOW <= variance * scale * scale < _SCALE_HIGH:
        scale = scale * 10 if variance * scale * scale < 1 else scale / 10
    return scale


def _bounded(value: float, limit: float, what: str) -> float:
    if not (math.isfinite(value) and abs(value) <= limit):
        msg = (
            f"the {what} is {value!r}, beyond {limit:g} in size: the fit has no "
            "answer this model can represent"
        )
        raise DomainError(msg)
    return value


def _to_scaled(inputs: _Garch, values: Sequence[float], scale: float) -> list[float]:
    """Convert fixed decimal parameters to the fitted units."""
    named = dict(zip(inputs.names(), values, strict=True))
    log_scale = 2 * math.log(scale)
    beta = sum(_terms(named)["beta"])
    converted = []
    for name, value in named.items():
        if name == "mu":
            converted.append(value * scale)
        elif name == "omega" and isinstance(inputs, EgarchInputs):
            converted.append(value + log_scale * (1 - beta))
        elif name == "omega":
            converted.append(value * scale * scale)
        else:
            converted.append(value)
    return converted


def _jacobian(
    inputs: _Garch, names: Sequence[str], scale: float
) -> NDArray[np.float64]:
    """Return the derivatives of the decimal parameters by the fitted ones.

    Every map is linear: mu / s, omega / s^2 (GARCH, GJR), and for EGARCH
    omega - (1 - sum beta) ln s^2, which also moves with each beta.
    """
    jacobian = np.eye(len(names))
    log_scale = 2 * math.log(scale)
    for i, name in enumerate(names):
        if name == "mu":
            jacobian[i, i] = 1 / scale
        elif name == "omega" and not isinstance(inputs, EgarchInputs):
            jacobian[i, i] = 1 / (scale * scale)
        elif name == "omega":
            for j, other in enumerate(names):
                if other.startswith("beta["):
                    jacobian[i, j] = log_scale
    return jacobian


def _to_decimal(
    inputs: _Garch, names: Sequence[str], fitted: NDArray[np.float64], scale: float
) -> NDArray[np.float64]:
    """Fitted parameters in decimal units: the inverse of :func:`_to_scaled`."""
    jacobian = _jacobian(inputs, names, scale)
    decimal = jacobian @ fitted
    if isinstance(inputs, EgarchInputs):
        omega = list(names).index("omega")
        decimal[omega] -= 2 * math.log(scale)
    return np.asarray(decimal, dtype=np.float64)


def _covariance(result: Any) -> NDArray[np.float64]:  # noqa: ANN401 - arch's result
    """Return arch's parameter covariance, or NaN where its Hessian is singular."""
    try:
        return np.asarray(result.param_cov, dtype=np.float64)
    except np.linalg.LinAlgError:
        size = len(result.params)
        return np.full((size, size), np.nan)


def _inference(
    decimal: NDArray[np.float64],
    covariance: NDArray[np.float64],
    jacobian: NDArray[np.float64],
) -> dict[str, Any]:
    """Carry the standard errors by the delta method; t and normal p-values."""
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    none = {"standard_errors": None, "t_statistics": None, "p_values": None}
    with np.errstate(all="ignore"):
        variances = np.diag(jacobian @ covariance @ jacobian.T)
    if not (np.all(np.isfinite(variances)) and np.all(variances >= 0)):
        warn(
            "standard_errors_undefined",
            "the parameters' covariance is not positive semi-definite at the "
            "estimates (a flat or boundary likelihood): no standard errors",
        )
        return none
    errors = np.sqrt(variances)
    if np.any(errors == 0) or np.any(errors > _STATISTIC_MAX):
        warn(
            "standard_errors_undefined",
            "a standard error is zero or overflows: no t statistics",
        )
        return {**none, "standard_errors": tuple(float(e) for e in errors)}
    t = decimal / errors
    return {
        "standard_errors": tuple(float(e) for e in errors),
        "t_statistics": tuple(_bounded(float(v), _STATISTIC_MAX, "t") for v in t),
        "p_values": tuple(min(1.0, float(p)) for p in 2 * stats.norm.sf(np.abs(t))),
    }


#: The result-warning codes of arch's warning categories (others: arch_warning).
_CODES: Final = {"ConvergenceWarning": "optimizer_not_converged"}


def _volatilities(
    inputs: _Garch,
    variances: NDArray[np.float64],
    unconditional: float | None,
    last: float,
) -> dict[str, Any]:
    periods = inputs.periods_per_year
    root = math.sqrt(periods)
    cumulative = np.cumsum(variances) / np.arange(1, len(variances) + 1)
    vol = None if unconditional is None else math.sqrt(unconditional)
    return {
        "unconditional_volatility": vol,
        "unconditional_volatility_annualized": None if vol is None else vol * root,
        "last_volatility": last,
        "last_volatility_annualized": last * root,
        "horizons": tuple(range(1, len(variances) + 1)),
        "variance_forecasts": tuple(float(v) for v in variances),
        "volatility_forecasts_annualized": tuple(
            float(v) for v in np.sqrt(periods * variances)
        ),
        "term_volatility_annualized": tuple(
            float(v) for v in np.sqrt(periods * cumulative)
        ),
    }


def _unconditional(
    inputs: _Garch, values: dict[str, float], persistence: float
) -> float | None:
    if isinstance(inputs, EgarchInputs):
        warn(
            "no_unconditional_variance",
            "EGARCH's unconditional variance has no closed form: it is not reported",
        )
        return None
    gap = 1 - persistence
    if not gap > _PERSISTENCE_SLACK or values["omega"] / gap > VARIANCE_MAX:
        warn(
            "no_unconditional_variance",
            "the persistence is one, or so near it that the long-run variance is "
            "beyond any the model represents: no unconditional volatility",
        )
        return None
    return values["omega"] / gap


def _build(arch: Any, inputs: _Garch, y: NDArray[np.float64]) -> Any:  # noqa: ANN401
    """Build the arch model: its mean, its variance process and its errors."""
    seed = inputs.seed if isinstance(inputs, EgarchInputs) else 0
    errors = arch.Normal if inputs.distribution == "normal" else arch.StudentsT
    process = (
        arch.EGARCH(p=inputs.p, o=inputs.o, q=inputs.q)
        if isinstance(inputs, EgarchInputs)
        else arch.GARCH(p=inputs.p, o=inputs.o, q=inputs.q)
    )
    mean = arch.ConstantMean if inputs.mean == "constant" else arch.ZeroMean
    return mean(
        y, volatility=process, distribution=errors(seed=generator(seed)), rescale=False
    )


def _forecast(inputs: _Garch, result: Any) -> NDArray[np.float64]:  # noqa: ANN401
    """Variance forecasts in the fitted units: analytic, or simulated for EGARCH."""
    options: dict[str, Any] = {"horizon": inputs.horizon, "reindex": False}
    if isinstance(inputs, EgarchInputs) and inputs.horizon > 1:
        options |= {"method": "simulation", "simulations": inputs.simulations}
    return np.asarray(result.forecast(**options).variance.to_numpy()[-1], dtype=float)


def _estimate(inputs: _Garch, arch: Any) -> GarchFamilyOutputs:  # noqa: ANN401 - arch.univariate
    # Adding zero turns -0.0 into 0.0, which canonical JSON cannot tell apart.
    returns = np.asarray(inputs.returns, dtype=np.float64) + 0.0
    if not has_spread(returns.tolist()) or float(np.std(returns)) < SPREAD_MIN:
        msg = (
            f"the returns barely vary (standard deviation below {SPREAD_MIN:g}): "
            "there is no volatility to model"
        )
        raise DomainError(msg)
    scale = _scale(returns)
    names = inputs.names()
    built = _build(arch, inputs, returns * scale)
    fixed = inputs.fixed_parameters
    with library_warnings("arch", codes=_CODES):
        if fixed is not None:
            result = built.fix(_to_scaled(inputs, fixed, scale))
        else:
            result = built.fit(disp="off", cov_type=inputs.covariance)
        forecasts = _forecast(inputs, result)
        last_variance = float(np.asarray(result.conditional_volatility)[-1]) ** 2
        # arch computes the covariance lazily: read it while its warnings count.
        covariance = _covariance(result) if fixed is None else np.empty((0, 0))
    fitted = np.asarray(result.params, dtype=np.float64)
    decimal = _to_decimal(inputs, names, fitted, scale)
    values = {
        name: _bounded(float(v), ESTIMATE_MAX, name)
        for name, v in zip(names, decimal, strict=True)
    }
    if fixed is not None:
        warn(
            "fixed_parameters",
            "the parameters were given, not estimated: they have no standard errors",
        )
        inference: dict[str, Any] = {
            "standard_errors": None,
            "t_statistics": None,
            "p_values": None,
        }
    else:
        inference = _inference(decimal, covariance, _jacobian(inputs, names, scale))
    observations = int(result.nobs)
    log_likelihood = _bounded(
        float(result.loglikelihood) + observations * math.log(scale),
        _LIKELIHOOD_MAX,
        "log-likelihood",
    )
    k = len(names)
    persistence = _persistence(inputs, values)
    unconditional = _unconditional(inputs, values, persistence)
    variances = forecasts / (scale * scale)
    last = math.sqrt(last_variance) / scale
    if not (
        np.all(np.isfinite(variances) & (variances > 0) & (variances <= VARIANCE_MAX))
        and 0 < last <= math.sqrt(VARIANCE_MAX)
    ):
        msg = (
            "a variance forecast or the last variance is not a positive number below "
            f"{VARIANCE_MAX:g}: the estimates describe an explosive process"
        )
        raise DomainError(msg)
    return _OUTPUTS[type(inputs)](
        parameter_names=names,
        parameters=tuple(values.values()),
        **inference,
        log_likelihood=log_likelihood,
        aic=-2 * log_likelihood + 2 * k,
        bic=-2 * log_likelihood + k * math.log(observations),
        observations=observations,
        persistence=persistence,
        **_volatilities(inputs, variances, unconditional, last),
    )


# --- the model ---------------------------------------------------------------


def _example_returns(count: int, seed: int) -> tuple[float, ...]:
    """Simulate a GARCH(1, 1) path, about 0.7% a day, for the examples."""
    shocks = generator(seed).standard_normal(count)
    omega, alpha, beta = 1e-6, 0.08, 0.9
    variance = omega / (1 - alpha - beta)
    path = []
    for shock in shocks:
        value = math.sqrt(variance) * float(shock)
        path.append(round(value, 6))
        variance = omega + alpha * value * value + beta * variance
    return tuple(path)


_EXAMPLE: Final = _example_returns(250, 17)

_ENGLE = Reference(
    key="engle1982",
    citation=(
        "Engle, R. F. (1982). Autoregressive conditional heteroscedasticity with "
        "estimates of the variance of United Kingdom inflation. Econometrica, "
        "50(4), 987-1007."
    ),
    doi="10.2307/1912773",
    locator="Section 2, the ARCH(p) process",
)
_BOLLERSLEV = Reference(
    key="bollerslev1986",
    citation=(
        "Bollerslev, T. (1986). Generalized autoregressive conditional "
        "heteroskedasticity. Journal of Econometrics, 31(3), 307-327."
    ),
    doi="10.1016/0304-4076(86)90063-1",
    locator="Section 2, eqs. (1)-(2): the GARCH(p, q) process",
)
_BOLLERSLEV_T = Reference(
    key="bollerslev1987",
    citation=(
        "Bollerslev, T. (1987). A conditionally heteroskedastic time series model "
        "for speculative prices and rates of return. The Review of Economics and "
        "Statistics, 69(3), 542-547."
    ),
    doi="10.2307/1925546",
    locator="GARCH with standardized Student's t errors",
)
_GJR = Reference(
    key="glosten1993",
    citation=(
        "Glosten, L. R., Jagannathan, R. and Runkle, D. E. (1993). On the relation "
        "between the expected value and the volatility of the nominal excess "
        "return on stocks. The Journal of Finance, 48(5), 1779-1801."
    ),
    doi="10.1111/j.1540-6261.1993.tb05128.x",
    locator="The asymmetric (GJR) variance equation",
)
_NELSON = Reference(
    key="nelson1991",
    citation=(
        "Nelson, D. B. (1991). Conditional heteroskedasticity in asset returns: A "
        "new approach. Econometrica, 59(2), 347-370."
    ),
    doi="10.2307/2938260",
    locator="Section 2, the EGARCH log-variance equation",
)
_BOLLERSLEV_WOOLDRIDGE = Reference(
    key="bollerslev1992",
    citation=(
        "Bollerslev, T. and Wooldridge, J. M. (1992). Quasi-maximum likelihood "
        "estimation and inference in dynamic models with time-varying covariances. "
        "Econometric Reviews, 11(2), 143-172."
    ),
    doi="10.1080/07474939208800229",
    locator="The robust (sandwich) covariance of the QML estimates",
)
_ARCH = Reference(
    key="sheppard_arch",
    citation=(
        "Sheppard, K. et al. arch: ARCH models and other tools for financial "
        "econometrics in Python, version 8.0."
    ),
    url="https://arch.readthedocs.io/en/latest/univariate/univariate.html",
    locator="arch.univariate: ConstantMean, ZeroMean, GARCH, EGARCH, fit and fix",
)
_KEN_FRENCH = Reference(
    key="french_data_library",
    citation=(
        "French, K. R. Data Library: Fama/French 3 Factors [Daily]. Tuck School "
        "of Business, Dartmouth College."
    ),
    url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
    locator="Fama/French 3 Factors [Daily], column Mkt-RF",
)


@model(
    id="econometrics.garch",
    version=1,
    title="GARCH, GJR-GARCH and EGARCH volatility",
    summary=(
        "GARCH, GJR-GARCH and EGARCH over arch, with normal or Student's t "
        "errors and a zero or constant mean: each parameter with its standard "
        "error, the log-likelihood, AIC and BIC, persistence, the unconditional "
        "and last conditional volatility, and annualized variance forecasts."
    ),
    formula=(
        r"r_t = \mu + \varepsilon_t, \quad \varepsilon_t = \sigma_t z_t",
        (
            r"\sigma^2_t = \omega + \sum_{i=1}^{p} \alpha_i \varepsilon^2_{t-i}"
            r" + \sum_{j=1}^{o} \gamma_j \varepsilon^2_{t-j} 1[\varepsilon_{t-j} < 0]"
            r" + \sum_{k=1}^{q} \beta_k \sigma^2_{t-k}"
        ),
        (
            r"\ln\sigma^2_t = \omega + \sum_{i} \alpha_i (|z_{t-i}| - \sqrt{2/\pi})"
            r" + \sum_{j} \gamma_j z_{t-j} + \sum_{k} \beta_k \ln\sigma^2_{t-k}"
        ),
        (
            r"E_T[\sigma^2_{T+h}] - \bar\sigma^2 = \pi^{h-1}"
            r"(E_T[\sigma^2_{T+1}] - \bar\sigma^2), \quad "
            r"\bar\sigma^2 = \frac{\omega}{1 - \pi}, \quad "
            r"\pi = \alpha + \tfrac{\gamma}{2} + \beta \text{ (order one)}"
        ),
        (
            r"\sigma_{\text{annual},h} = \sqrt{P\,E_T[\sigma^2_{T+h}]}, \quad "
            r"\sigma_{\text{term},h} = \sqrt{\tfrac{P}{h}\sum_{i \le h}"
            r"E_T[\sigma^2_{T+i}]}"
        ),
    ),
    assumptions=(
        (
            "Estimation is by maximum likelihood in arch (SLSQP, arch's stationarity "
            "constraints), on the returns times 100 and, when their percent variance "
            "lies outside [0.1, 10,000), by a further power of ten; every estimate "
            "is reported back in decimal units (omega in the units of the variance, "
            "or for EGARCH as the log-variance intercept of the decimal returns)."
        ),
        (
            "The recursion starts from arch's backcast: the 0.94-weighted average of "
            "the first min(75, n) squared residuals, for every pre-sample shock and "
            "variance (half of it for GJR's negative-shock terms; EGARCH starts from "
            "its logarithm, with no pre-sample shock). As in arch, the fit's "
            "residuals are the demeaned returns and the forecasts' are the returns "
            "less the estimated mean; the two paths differ only while the start "
            "has not decayed."
        ),
        (
            "Student's t errors are standardized to unit variance, with nu "
            "estimated in [2.05, 500]. Persistence for GJR counts gamma / 2, the "
            "chance of a negative shock under a symmetric distribution."
        ),
        (
            "Standard errors are Bollerslev and Wooldridge's robust (QML) sandwich "
            "by default, or the classic inverse information; the delta method "
            "carries them to decimal units, and p-values are normal."
        ),
        (
            "Forecasts are arch's analytic ones, except EGARCH beyond one period, "
            "whose variances are averages over seeded simulated paths. Volatilities "
            "are annualized by sqrt(periods_per_year): no compounding."
        ),
        (
            "Profiles: default binds 1,000 trading days of the Ken French daily "
            "market excess return (factors.ff3_market.us.daily) to returns; supply "
            "periods_per_year=252. concepts= rebinds returns to any other daily "
            "return series in the catalog."
        ),
    ),
    limitations=(
        (
            "Returns that barely vary (standard deviation below 1e-8), or an "
            "estimate or forecast that is not finite or beyond its bound, raise "
            "DomainError."
        ),
        (
            "The optimizer may stop short of the maximum (a warning names arch's "
            "message); estimates near a constraint (persistence near one, alpha "
            "near zero) may lack standard errors, which are then null with a "
            "warning."
        ),
        (
            "The unconditional volatility is null for EGARCH (no closed form) and "
            "when persistence is at least one. Fixed parameters must describe a "
            "non-negative, non-explosive variance (persistence at most one; an "
            "EGARCH beta sum strictly inside (-1, 1)); they have no standard errors."
        ),
        (
            "EGARCH forecasts beyond one period carry simulation error, which "
            "shrinks with the number of simulations; the seed makes them repeat."
        ),
        (
            "Needs the econometrics extra: pip install 'pyeconomics[econometrics]'. "
            "On Python 3.15 and later the extra cannot install arch yet (no "
            "CPython 3.15 wheel; issue #154), and the model raises "
            "MissingOptionalDependencyError saying so."
        ),
    ),
    references=(
        _ENGLE,
        _BOLLERSLEV,
        _BOLLERSLEV_T,
        _GJR,
        _NELSON,
        _BOLLERSLEV_WOOLDRIDGE,
        _ARCH,
        _KEN_FRENCH,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.HEAVY,
    tags=("garch", "volatility", "gjr", "egarch", "arch", "forecast"),
    invariants=(
        Invariant(
            id="forecast_converges_to_unconditional_variance",
            statement=(
                "When the persistence is below one, the variance forecasts approach "
                "the unconditional variance: for a model of order one the gap "
                "shrinks by the persistence each period."
            ),
        ),
        Invariant(
            id="conditional_variance_is_positive",
            statement=(
                "The last conditional volatility and every variance forecast are "
                "positive."
            ),
        ),
        Invariant(
            id="rescaling_returns_rescales_the_variance",
            statement=(
                "Multiplying the returns by c multiplies mu by c and the variances "
                "by c squared, and leaves alpha, gamma, beta and nu unchanged."
            ),
        ),
    ),
    examples=(
        Example(
            name="garch_daily",
            inputs={
                "calculation": "garch",
                "returns": _EXAMPLE,
                "periods_per_year": 252,
            },
            note="A year of simulated daily returns at about 11% annual volatility.",
        ),
        Example(
            name="gjr_student_t",
            inputs={
                "calculation": "gjr",
                "returns": _EXAMPLE,
                "periods_per_year": 252,
                "distribution": "student_t",
                "horizon": 20,
            },
        ),
        Example(
            name="egarch_zero_mean",
            inputs={
                "calculation": "egarch",
                "returns": _EXAMPLE,
                "periods_per_year": 252,
                "mean": "zero",
                "horizon": 5,
                "simulations": 500,
            },
        ),
    ),
    charts=(
        ChartSpec(
            id="volatility_forecasts",
            title="Annualized volatility forecasts",
            kind=ChartKind.LINE,
            x="horizons",
            y=("volatility_forecasts_annualized", "term_volatility_annualized"),
            x_label="Periods ahead",
            y_label="Annualized volatility",
        ),
    ),
    bindings=(
        Binding(
            "returns",
            "factors.ff3_market.us.daily",
            as_of=AsOf.WINDOW,
            window=_WINDOW,
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
    # A literal: the import allowlist reads it with ast to admit arch.
    extra="econometrics",
)
def garch(inputs: GarchFamilyInputs) -> GarchFamilyOutputs:
    """Fit (or evaluate) the variance process with arch, imported here."""
    try:
        from arch import univariate  # noqa: PLC0415 - the extra, imported on use
    except ImportError as error:
        package = "arch"
        raise MissingOptionalDependencyError(
            package, extra=EXTRA, note=GAP_NOTE
        ) from error
    return _estimate(inputs, univariate)
