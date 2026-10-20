# src/pyeconomics/models/fixed_income/curve_fitting.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Nelson-Siegel and Svensson yield curves: ``fixed_income.curve_fitting``.

The Svensson (1994) curve extends Nelson and Siegel's (1987) with a second hump.
Its continuously compounded zero-coupon yield at maturity :math:`n` years is

.. math::

    y(n) = \beta_0 + \beta_1 L(n/\tau_1) + \beta_2 \bigl(L(n/\tau_1)
        - e^{-n/\tau_1}\bigr) + \beta_3 \bigl(L(n/\tau_2) - e^{-n/\tau_2}\bigr),
    \qquad L(x) = \frac{1 - e^{-x}}{x},

and its instantaneous forward rate is
:math:`f(n) = \beta_0 + \beta_1 e^{-n/\tau_1} + \beta_2 \frac{n}{\tau_1}
e^{-n/\tau_1} + \beta_3 \frac{n}{\tau_2} e^{-n/\tau_2}`. With :math:`\beta_3 = 0`
it is the Nelson-Siegel curve. This is the form the Federal Reserve Board's
Gürkaynak-Sack-Wright file and the ECB's euro-area curves publish; the betas are
decimals here, as every rate in the library is (the sources print percent).

Two calculations, discriminated on ``calculation``:

- ``evaluate``: the zero yields, instantaneous forwards, par yields and discount
  factors of given parameters at given maturities;
- ``fit``: bounded least squares of the curve to observed zero or par yields
  from several deterministic starting points, with a cap on evaluations; it
  returns the fitted parameters, the fitted yields and the root mean squared
  error.

A par yield is the coupon rate, paid ``coupon_frequency`` times a year, of a bond
issued today and maturing at :math:`n` that the curve prices at par:
:math:`c = (1 - d_n) / \sum_i \alpha_i d_i`, with coupon dates counted back from
maturity, a short first period where :math:`n` is not a whole number of periods,
and :math:`d_t = e^{-y(t) t}`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
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
    Rate,
    Reference,
    Years,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.core.units import Ratio
from pyeconomics.models.fixed_income._bonds import (  # noqa: TC001 - pydantic reads it
    FrequencyName,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["curve_fitting"]

#: The most maturities an evaluation takes (thirty years of months), and a fit.
_POINTS_MAX: Final = 360
_FIT_POINTS_MAX: Final = 60
#: The longest maturity, in years.
_MATURITY_MAX: Final = 100.0
#: A beta is a coefficient in decimal rate units, not a rate: on days when the
#: two humps nearly coincide the Board's fits offset betas of several hundred
#: percentage points (BETA2 -417.8 and BETA3 427.9 on 2025-01-03), and one row
#: reaches 3,407 as a decimal (2011-08-03). An evaluation takes up to 1e4; a fit
#: searches within +-1.
_BETA_LIMIT: Final = 1e4
_BETA_FIT_LIMIT: Final = 1.0
#: A decay parameter, in years, for an evaluation and for a fit's search.
_TAU_MIN: Final = 1e-3
_TAU_MAX: Final = 200.0
_TAU_FIT_MIN: Final = 0.05
_TAU_FIT_MAX: Final = 30.0
#: Observed yields a fit takes, and the rates an output may hold.
_YIELD_MIN: Final = -0.1
_YIELD_MAX: Final = 1.0
_RATE_OUT_MIN: Final = -0.99
_RATE_OUT_MAX: Final = 10.0
#: The largest discount factor an output holds: a rate of -0.99 for 100 years
#: discounts by e^99, about 1e43. The smallest is e^-700, about 1e-304, before
#: the factor would underflow.
_DISCOUNT_EXPONENT_MAX: Final = 700.0
_FACTOR_MAX: Final = 1e44
#: The evaluations of the residuals each start of a fit may use: the cap.
_EVALUATIONS_PER_START: Final = 200
#: The grid of decays a fit starts from: log-spaced, each about 1.13 times the
#: last, and a Svensson pair's second decay at least 1.5 times its first.
_TAU_GRID_LOW: Final = 0.1
_TAU_GRID_HIGH: Final = _TAU_FIT_MAX
_TAU_GRID_SIZE: Final = 48
_TAU_SEPARATION: Final = 1.5
#: How many times a par fit rescores the grid against the zero curve it implies.
_PAR_PASSES: Final = 2
#: How many starting points a fit refines jointly, the best of the grid's.
_STARTS: Final = 8
#: The decays the grid of starting points tries, in years.
_TAU_GRID: Final = tuple(
    float(t) for t in np.geomspace(_TAU_GRID_LOW, _TAU_GRID_HIGH, _TAU_GRID_SIZE)
)
#: How close a maturity must be to a whole number of coupon periods to be one.
_WHOLE: Final = 1e-9
#: The most evaluations a fit can count: the grid's, scored once and again for
#: each par pass, and the joint refinements' (each at most its cap and two more).
_EVALUATIONS_MAX: Final = (1 + _PAR_PASSES) * _TAU_GRID_SIZE**2 + _STARTS * (
    _EVALUATIONS_PER_START + 2
)
#: scipy refuses tolerances at or below machine epsilon.
_TOLERANCE: Final = 1e-14

_PERIODS: Final = {"annual": 1, "semiannual": 2, "quarterly": 4, "monthly": 12}

type Form = Literal["nelson_siegel", "svensson"]
type YieldType = Literal["zero", "par"]

_Maturities = Annotated[
    tuple[Annotated[Years, Field(gt=0.0, le=_MATURITY_MAX)], ...], ARRAY_INPUT
]
_Observed = Annotated[
    tuple[Annotated[Rate, Field(ge=_YIELD_MIN, le=_YIELD_MAX)], ...], ARRAY_INPUT
]
_RatesOut = Annotated[
    tuple[Annotated[Rate, Field(ge=_RATE_OUT_MIN, le=_RATE_OUT_MAX)], ...],
    ARRAY_INPUT,
]
_Factors = Annotated[
    tuple[Annotated[Ratio, Field(gt=0.0, le=_FACTOR_MAX)], ...], ARRAY_INPUT
]


def _beta(
    description: str,
    default: float | None = None,
    limit: float = _BETA_LIMIT,
) -> Any:  # noqa: ANN401 - pydantic's Field
    """Return a beta's field: required unless it has a default."""
    if default is None:
        return Field(ge=-limit, le=limit, description=description)
    return Field(default, ge=-limit, le=limit, description=description)


def _coupon_frequency() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        "semiannual",
        description="Coupons a year of the par bonds a par yield describes",
    )


# --- inputs ------------------------------------------------------------------


class EvaluateInputs(ModelInputs):
    """Nelson-Siegel or Svensson parameters and the maturities to evaluate."""

    calculation: Literal["evaluate"] = Field(
        "evaluate", description="Yields, forwards and par yields of given parameters"
    )
    beta0: Ratio = _beta("The long-run level: the yield as maturity grows")
    beta1: Ratio = _beta("The slope: beta0 + beta1 is the instantaneous short rate")
    beta2: Ratio = _beta("The first hump's size")
    beta3: Ratio = _beta("The second hump's size (Svensson); 0 for Nelson-Siegel", 0.0)
    tau1: Years = Field(
        ge=_TAU_MIN, le=_TAU_MAX, description="The first decay, in years (GSW's TAU1)"
    )
    tau2: Years | None = Field(
        None,
        ge=_TAU_MIN,
        le=_TAU_MAX,
        description="The second decay, in years (Svensson); omitted for Nelson-Siegel",
    )
    maturities: _Maturities = Field(
        (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0),
        min_length=1,
        max_length=_POINTS_MAX,
        description="Maturities to evaluate, in years",
    )
    coupon_frequency: FrequencyName = _coupon_frequency()

    @model_validator(mode="after")
    def _second_hump(self) -> Self:
        if self.tau2 is None and self.beta3 != 0:
            msg = "a Svensson curve (beta3 not zero) needs its second decay, tau2"
            raise ValueError(msg)
        return self


class FitInputs(ModelInputs):
    """Observed yields to fit a Nelson-Siegel or Svensson curve to."""

    calculation: Literal["fit"] = Field(
        "fit", description="Fit a curve to observed yields by least squares"
    )
    maturities: _Maturities = Field(
        min_length=4,
        max_length=_FIT_POINTS_MAX,
        description="Maturity of each observed yield, in years, increasing",
    )
    yields: _Observed = Field(
        min_length=4,
        max_length=_FIT_POINTS_MAX,
        description="The observed yield at each maturity",
    )
    yield_type: YieldType = Field(
        "par",
        description=(
            "What the observed yields are: 'par' (coupon rates of bonds priced at "
            "par, as Treasury's par curve gives them) or 'zero' (continuously "
            "compounded zero-coupon yields)"
        ),
    )
    coupon_frequency: FrequencyName = _coupon_frequency()
    form: Form = Field(
        "svensson",
        description=(
            "The curve to fit: 'nelson_siegel' (4 parameters) or 'svensson' (6)"
        ),
    )

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if len(self.yields) != len(self.maturities):
            msg = (
                f"give one yield per maturity: {len(self.yields)} yields for "
                f"{len(self.maturities)} maturities"
            )
            raise ValueError(msg)
        if any(
            b <= a for a, b in zip(self.maturities, self.maturities[1:], strict=False)
        ):
            msg = "the maturities must be strictly increasing"
            raise ValueError(msg)
        needed = 4 if self.form == "nelson_siegel" else 6
        if len(self.yields) < needed:
            msg = f"a {self.form} fit has {needed} parameters and needs {needed} yields"
            raise ValueError(msg)
        return self


CurveFittingInputs = Annotated[
    EvaluateInputs | FitInputs, Field(discriminator="calculation")
]


# --- outputs -----------------------------------------------------------------


def _out(description: str, size: int = _POINTS_MAX) -> Any:  # noqa: ANN401 - Field
    return Field(max_length=size, description=description)


class EvaluateOutputs(ModelOutputs):
    calculation: Literal["evaluate"] = Field(
        "evaluate", description="Yields, forwards and par yields of given parameters"
    )
    maturities: _Maturities = _out("The maturities evaluated, in years")
    zero_yields: _RatesOut = _out(
        "The zero-coupon yield at each maturity, continuously compounded"
    )
    forward_rates: _RatesOut = _out(
        "The instantaneous forward rate at each maturity, continuously compounded"
    )
    par_yields: _RatesOut = _out(
        "The par yield at each maturity, with coupon_frequency coupons a year"
    )
    discount_factors: _Factors = _out("The discount factor to each maturity")


class FitOutputs(ModelOutputs):
    calculation: Literal["fit"] = Field(
        "fit", description="Fit a curve to observed yields by least squares"
    )
    beta0: Ratio = _beta("The fitted long-run level", limit=_BETA_FIT_LIMIT)
    beta1: Ratio = _beta("The fitted slope", limit=_BETA_FIT_LIMIT)
    beta2: Ratio = _beta("The fitted first hump", limit=_BETA_FIT_LIMIT)
    beta3: Ratio = _beta(
        "The fitted second hump; 0 for a Nelson-Siegel fit", limit=_BETA_FIT_LIMIT
    )
    tau1: Years = Field(
        ge=_TAU_FIT_MIN, le=_TAU_FIT_MAX, description="The fitted first decay, in years"
    )
    tau2: Years = Field(
        ge=_TAU_FIT_MIN,
        le=_TAU_FIT_MAX,
        description=(
            "The fitted second decay, in years; a Nelson-Siegel fit repeats tau1, "
            "so the parameters evaluate as a Svensson curve with beta3 = 0"
        ),
    )
    fitted_yields: _RatesOut = _out(
        "The fitted curve's yield at each observed maturity, of the observed type",
        _FIT_POINTS_MAX,
    )
    rmse: Rate = Field(
        ge=0.0,
        le=_RATE_OUT_MAX,
        description="Root mean squared difference of the fitted and observed yields",
    )
    evaluations: Count = Field(
        ge=0,
        le=_EVALUATIONS_MAX,
        description="Evaluations of the residuals across every start",
    )


CurveFittingOutputs = Annotated[
    EvaluateOutputs | FitOutputs, Field(discriminator="calculation")
]


# --- the curve ---------------------------------------------------------------

type _Vector = NDArray[np.float64]


def _loadings(times: _Vector, tau: float) -> tuple[_Vector, _Vector]:
    """Return ``L(t / tau)`` and ``e^(-t / tau)``, without cancellation near zero."""
    x = times / tau
    decay = np.exp(-x)
    return -np.expm1(-x) / x, decay


def _zero(params: _Vector, times: _Vector) -> _Vector:
    """Return the continuously compounded zero yields of Svensson parameters."""
    b0, b1, b2, b3, tau1, tau2 = params
    level1, decay1 = _loadings(times, tau1)
    level2, decay2 = _loadings(times, tau2)
    return np.asarray(
        b0 + b1 * level1 + b2 * (level1 - decay1) + b3 * (level2 - decay2),
        dtype=np.float64,
    )


def _zero_jacobian(params: _Vector, times: _Vector) -> _Vector:
    """Return the zero yields' derivatives in each of the six parameters."""
    _, b1, b2, b3, tau1, tau2 = params
    columns = [np.ones_like(times)]
    level1, decay1 = _loadings(times, tau1)
    level2, decay2 = _loadings(times, tau2)
    columns += [level1, level1 - decay1, level2 - decay2]
    for tau, weight_level, weight_hump, (level, decay) in (
        (tau1, b1, b2, (level1, decay1)),
        (tau2, 0.0, b3, (level2, decay2)),
    ):
        x = times / tau
        # L'(x) = (e^-x - L(x)) / x and dx/dtau = -x / tau, so the product needs
        # no division by a small x.
        slope = (decay - level) / x
        columns.append(
            (weight_level * slope + weight_hump * (slope + decay)) * (-x / tau)
        )
    return np.column_stack(columns)


def _forward(params: _Vector, times: _Vector) -> _Vector:
    b0, b1, b2, b3, tau1, tau2 = params
    x1, x2 = times / tau1, times / tau2
    return np.asarray(
        b0 + b1 * np.exp(-x1) + b2 * x1 * np.exp(-x1) + b3 * x2 * np.exp(-x2),
        dtype=np.float64,
    )


class _Schedule:
    """The coupon dates of par bonds at many maturities, on one set of times."""

    def __init__(self, maturities: _Vector, periods: int) -> None:
        times: list[float] = []
        self.rows: list[tuple[NDArray[np.intp], _Vector]] = []
        index: dict[float, int] = {}
        step = 1.0 / periods
        for n in maturities:
            whole = math.floor(n * periods + _WHOLE)
            stub = n - whole * step
            if stub > _WHOLE or whole == 0:
                when = [stub + j * step for j in range(whole + 1)]
                accruals = [stub] + [step] * whole
            else:
                when = [j * step for j in range(1, whole + 1)]
                accruals = [step] * whole
            when[-1] = float(n)
            positions = []
            for t in when:
                if t not in index:
                    index[t] = len(times)
                    times.append(t)
                positions.append(index[t])
            self.rows.append(
                (
                    np.asarray(positions, dtype=np.intp),
                    np.asarray(accruals, dtype=np.float64),
                )
            )
        self.times = np.asarray(times, dtype=np.float64)

    def par(self, zero: _Vector) -> _Vector:
        """Return each maturity's par yield from the zero yields at ``times``."""
        factors = np.exp(-zero * self.times)
        # 1 - d(n) as -expm1, so a short maturity keeps the yield's digits.
        lost = -np.expm1(-zero * self.times)
        return np.asarray(
            [lost[pos[-1]] / float(acc @ factors[pos]) for pos, acc in self.rows]
        )

    def par_jacobian(self, zero: _Vector, jacobian: _Vector) -> _Vector:
        """Return the par yields' derivatives from those of the zero yields."""
        factors = np.exp(-zero * self.times)
        lost = -np.expm1(-zero * self.times)
        factor_jacobian = -(self.times * factors)[:, None] * jacobian
        rows = []
        for positions, weights in self.rows:
            annuity = float(weights @ factors[positions])
            last = positions[-1]
            d_annuity = weights @ factor_jacobian[positions]
            rows.append(
                (-factor_jacobian[last] * annuity - lost[last] * d_annuity) / annuity**2
            )
        return np.vstack(rows)


def _params(inputs: EvaluateInputs) -> _Vector:
    tau2 = inputs.tau1 if inputs.tau2 is None else inputs.tau2
    return np.asarray(
        [inputs.beta0, inputs.beta1, inputs.beta2, inputs.beta3, inputs.tau1, tau2],
        dtype=np.float64,
    )


def _bounded(values: _Vector, what: str) -> tuple[float, ...]:
    if not np.all(np.isfinite(values)) or np.any(
        (values < _RATE_OUT_MIN) | (values > _RATE_OUT_MAX)
    ):
        msg = (
            f"the curve has {what} outside [{_RATE_OUT_MIN}, {_RATE_OUT_MAX}] at "
            "these maturities; it has no representable value there"
        )
        raise DomainError(msg)
    return tuple(float(v) for v in values)


def _evaluate(inputs: EvaluateInputs) -> EvaluateOutputs:
    params = _params(inputs)
    times = np.asarray(inputs.maturities, dtype=np.float64)
    zero = _bounded(_zero(params, times), "zero yields")
    forward = _bounded(_forward(params, times), "forward rates")
    schedule = _Schedule(times, _PERIODS[inputs.coupon_frequency])
    # A yield within [-0.99, 10] over at most 100 years grows by at most e^99, so
    # no factor overflows once the yields at the coupon dates are bounded; a high
    # one can still discount past the smallest float.
    coupon_zero = np.asarray(
        _bounded(_zero(params, schedule.times), "zero yields at coupon dates")
    )
    if np.any(coupon_zero * schedule.times > _DISCOUNT_EXPONENT_MAX):
        msg = (
            "the curve discounts past the smallest representable factor at these "
            "maturities (a yield times its maturity above 700)"
        )
        raise DomainError(msg)
    par = _bounded(schedule.par(coupon_zero), "par yields")
    factors = np.exp(-np.asarray(zero) * times)
    return EvaluateOutputs(
        maturities=inputs.maturities,
        zero_yields=zero,
        forward_rates=forward,
        par_yields=par,
        discount_factors=tuple(float(f) for f in factors),
    )


# --- the fit -----------------------------------------------------------------


class _Problem:
    """One fit: the observed yields and the map from parameters to residuals."""

    def __init__(self, inputs: FitInputs) -> None:
        self.svensson = inputs.form == "svensson"
        self.times = np.asarray(inputs.maturities, dtype=np.float64)
        self.observed = np.asarray(inputs.yields, dtype=np.float64)
        self.schedule = (
            _Schedule(self.times, _PERIODS[inputs.coupon_frequency])
            if inputs.yield_type == "par"
            else None
        )
        self.evaluations = 0

    def full(self, x: _Vector) -> _Vector:
        """Expand a Nelson-Siegel vector to six Svensson parameters."""
        if self.svensson:
            return x
        return np.asarray([x[0], x[1], x[2], 0.0, x[3], x[3]], dtype=np.float64)

    def fitted(self, x: _Vector) -> _Vector:
        params = self.full(x)
        if self.schedule is None:
            return _zero(params, self.times)
        return self.schedule.par(_zero(params, self.schedule.times))

    def residuals(self, x: _Vector) -> _Vector:
        self.evaluations += 1
        return self.fitted(x) - self.observed

    def jacobian(self, x: _Vector) -> _Vector:
        params = self.full(x)
        if self.schedule is None:
            full = _zero_jacobian(params, self.times)
        else:
            times = self.schedule.times
            full = self.schedule.par_jacobian(
                _zero(params, times), _zero_jacobian(params, times)
            )
        if self.svensson:
            return full
        # tau2 repeats tau1, but beta3 is zero, so tau2 moves nothing.
        return full[:, [0, 1, 2, 4]]

    def bounds(self) -> tuple[list[float], list[float]]:
        betas = 4 if self.svensson else 3
        taus = 2 if self.svensson else 1
        lower = [-_BETA_FIT_LIMIT] * betas + [_TAU_FIT_MIN] * taus
        upper = [_BETA_FIT_LIMIT] * betas + [_TAU_FIT_MAX] * taus
        return lower, upper

    def starts(self) -> list[_Vector]:
        """Return the best points of a dense grid of decays, betas by least squares.

        For given decays the zero yields are linear in the betas, so each point
        of the grid is scored by linear least squares against zero yields. A par
        yield is not a zero yield: the observed par yields stand in for zero
        yields at first, and then, twice, less the gap between the par and zero
        yields of the best start, so the grid is scored against the zero curve
        the par yields imply. Svensson pairs keep the second decay at least 1.5
        times the first: nearly equal decays make the two humps collinear, and
        huge offsetting betas would mimic a better fit. The grid and its order are
        fixed, so the starts, and the fit, are deterministic.
        """
        found = self.scored(self.observed)
        if self.schedule is not None:
            for _ in range(_PAR_PASSES):
                params = self.full(found[0])
                gap = self.fitted(found[0]) - _zero(params, self.times)
                found = self.scored(self.observed - gap)
        return found

    def scored(self, target: _Vector) -> list[_Vector]:
        """Return the grid's best starts against zero yields ``target``."""
        grid = _TAU_GRID
        if self.svensson:
            pairs = [(a, b) for a in grid for b in grid if b >= _TAU_SEPARATION * a]
        else:
            pairs = [(a, a) for a in grid]
        scored: list[tuple[float, int, _Vector]] = []
        for order, (tau1, tau2) in enumerate(pairs):
            level1, decay1 = _loadings(self.times, tau1)
            columns = [np.ones_like(self.times), level1, level1 - decay1]
            if self.svensson:
                level2, decay2 = _loadings(self.times, tau2)
                columns.append(level2 - decay2)
            design = np.column_stack(columns)
            betas = np.linalg.lstsq(design, target, rcond=None)[0]
            betas = np.clip(betas, -_BETA_FIT_LIMIT, _BETA_FIT_LIMIT)
            residuals = design @ betas - target
            taus = [tau1, tau2] if self.svensson else [tau1]
            scored.append(
                (float(residuals @ residuals), order, np.concatenate([betas, taus]))
            )
        self.evaluations += len(pairs)
        scored.sort(key=lambda item: (item[0], item[1]))
        return [x for _, _, x in scored[:_STARTS]]


def _fit(inputs: FitInputs) -> FitOutputs:
    from scipy.optimize import least_squares  # noqa: PLC0415 - SciPy on first use

    problem = _Problem(inputs)
    lower, upper = problem.bounds()
    best: tuple[float, _Vector] | None = None
    converged = False
    with np.errstate(over="ignore", invalid="ignore"):
        for start in problem.starts():
            result = least_squares(
                problem.residuals,
                start,
                jac=problem.jacobian,
                bounds=(lower, upper),
                method="trf",
                x_scale="jac",
                ftol=_TOLERANCE,
                xtol=_TOLERANCE,
                gtol=_TOLERANCE,
                max_nfev=_EVALUATIONS_PER_START,
            )
            if not np.all(np.isfinite(result.fun)):
                continue
            cost = float(np.sum(result.fun**2))
            if best is None or cost < best[0]:
                best = (cost, np.asarray(result.x, dtype=np.float64))
                converged = result.status > 0
    if best is None:
        msg = "no start of the fit reached finite yields: the data have no fit"
        raise DomainError(msg)
    if not converged:
        warn(
            "fit_not_converged",
            f"the best start used its {_EVALUATIONS_PER_START} evaluations before "
            "its tolerances were met; the parameters are the best found",
            stacklevel=2,
        )
    params = problem.full(best[1])
    fitted = _bounded(problem.fitted(best[1]), "fitted yields")
    residuals = np.asarray(fitted) - problem.observed
    return FitOutputs(
        beta0=float(params[0]),
        beta1=float(params[1]),
        beta2=float(params[2]),
        beta3=float(params[3]),
        tau1=float(params[4]),
        tau2=float(params[5]),
        fitted_yields=fitted,
        rmse=math.sqrt(math.fsum(r * r for r in residuals) / len(residuals)),
        evaluations=problem.evaluations,
    )


# --- the model ---------------------------------------------------------------

_NELSON_SIEGEL = Reference(
    key="nelson1987",
    citation=(
        "Nelson, C. R. and Siegel, A. F. (1987). Parsimonious Modeling of Yield "
        "Curves. Journal of Business, 60(4), 473-489."
    ),
    doi="10.1086/296409",
    locator="The three-component forward-rate curve and its yield curve",
)
_SVENSSON = Reference(
    key="svensson1994",
    citation=(
        "Svensson, L. E. O. (1994). Estimating and Interpreting Forward Interest "
        "Rates: Sweden 1992-1994. NBER Working Paper 4871."
    ),
    url="https://www.nber.org/papers/w4871",
    doi="10.3386/w4871",
    locator="The extended Nelson-Siegel forward curve with a second hump",
)
_GSW = Reference(
    key="gurkaynak2007",
    citation=(
        "Gürkaynak, R. S., Sack, B. and Wright, J. H. (2007). The U.S. Treasury "
        "Yield Curve: 1961 to the Present. Journal of Monetary Economics, 54(8), "
        "2291-2304."
    ),
    doi="10.1016/j.jmoneco.2007.06.029",
    locator="The Svensson zero, forward and par yields of the Board's daily file",
)
_ECB = Reference(
    key="ecb_yield_curves",
    citation=(
        "European Central Bank. Euro area yield curves: technical notes and the "
        "published Svensson parameters."
    ),
    url=(
        "https://www.ecb.europa.eu/stats/financial_markets_and_interest_rates/"
        "euro_area_yield_curves/html/index.en.html"
    ),
    locator="The Svensson model of the AAA and all-government curves",
)


@model(
    id="fixed_income.curve_fitting",
    version=1,
    title="Nelson-Siegel and Svensson yield curves",
    summary=(
        "Zero yields, forward rates and par yields of Nelson-Siegel and Svensson "
        "curves, and least-squares fits of either curve to observed yields."
    ),
    formula=(
        (
            r"y(n) = \beta_0 + \beta_1 L_1 + \beta_2 (L_1 - e^{-n/\tau_1}) + "
            r"\beta_3 (L_2 - e^{-n/\tau_2}), \quad L_k = \frac{1 - e^{-n/\tau_k}}"
            r"{n/\tau_k}"
        ),
        (
            r"f(n) = \beta_0 + \beta_1 e^{-n/\tau_1} + \beta_2 \frac{n}{\tau_1} "
            r"e^{-n/\tau_1} + \beta_3 \frac{n}{\tau_2} e^{-n/\tau_2}"
        ),
        r"d(n) = e^{-y(n)\,n}, \quad c(n) = \frac{1 - d(n)}{\sum_i \alpha_i d(t_i)}",
        r"\min_{\beta, \tau} \sum_k \left(\hat y_k(\beta, \tau) - y_k\right)^2",
    ),
    assumptions=(
        (
            "Zero yields and forward rates are continuously compounded; the betas "
            "are decimals, so the Board's and the ECB's percent parameters are "
            "divided by 100."
        ),
        (
            "Par yields pay coupon_frequency coupons a year, counted back from "
            "maturity, with a short first period when the maturity is not a whole "
            "number of periods; Treasury's par curve is semiannual."
        ),
        (
            "A fit weighs every observed yield equally. Its decays are searched in "
            "[0.05, 30] years and its betas in [-1, 1]; it scores a fixed grid "
            "of 48 decays (Svensson pairs at least 1.5 apart as a ratio) by linear "
            "least squares against the zero curve the observed yields imply, "
            "refines the eight best jointly and keeps the lowest sum of squares."
        ),
        (
            "Profile: default binds the evaluate calculation to the Board's GSW "
            "parameters on the date and the fit calculation to Treasury's par "
            "curve on the date (its last curve on or before it, the tenors it "
            "publishes)."
        ),
    ),
    limitations=(
        (
            "The parameters of a fit are not unique: different betas and decays "
            "can give nearly the same yields, so compare fitted yields, not "
            "parameters. A fit is local; the grid of starts makes it reproducible, "
            "not certainly global. A second hump the maturities cannot identify "
            "(beta3 near zero, or tau2 near the longest maturity, where the hump "
            "is nearly a straight line) can leave a Svensson fit a few tenths of "
            "a basis point from the best."
        ),
        (
            "A curve whose yields, forwards or par yields fall outside [-0.99, 10] "
            "at a maturity or a coupon date raises DomainError, as does one that "
            "discounts past the smallest float (a yield times its maturity above "
            "700) and a fit no start of which reaches finite yields."
        ),
        (
            "A fit stops after 200 evaluations a start; one that stopped before "
            "its tolerances were met warns fit_not_converged."
        ),
        (
            "The GSW file gives Nelson-Siegel parameters only before 1980 (no "
            "BETA3 or TAU2), so a bind of the evaluate calculation at such a date "
            "raises: supply beta0 to tau1 instead."
        ),
    ),
    references=(_NELSON_SIEGEL, _SVENSSON, _GSW, _ECB),
    evidence=Evidence.STANDARD,
    # An evaluation takes milliseconds; a fit is an optimisation, typically a
    # tenth of a second and a few seconds at worst (60 par yields to 100 years
    # with monthly coupons), so the model is budgeted as heavy.
    cost=CostClass.HEAVY,
    tags=(
        "yield curve",
        "nelson-siegel",
        "svensson",
        "curve fitting",
        "term structure",
    ),
    invariants=(
        Invariant(
            id="long_end_tends_to_beta0",
            statement=(
                "As maturity grows, the zero yield and the forward tend to beta0."
            ),
        ),
        Invariant(
            id="short_end_tends_to_beta0_plus_beta1",
            statement=(
                "As maturity shrinks to zero, the zero yield and the forward tend "
                "to beta0 + beta1."
            ),
        ),
        Invariant(
            id="svensson_with_zero_beta3_is_nelson_siegel",
            statement=(
                "A Svensson curve with beta3 = 0 gives the Nelson-Siegel curve of "
                "its other parameters, whatever tau2 is."
            ),
        ),
        Invariant(
            id="fit_recovers_noise_free_curve",
            statement=(
                "Fitting the yields of a curve of the same form recovers those "
                "yields (not necessarily the parameters, which are not unique)."
            ),
        ),
    ),
    examples=(
        Example(
            name="svensson_curve",
            inputs={
                "calculation": "evaluate",
                "beta0": 0.045,
                "beta1": -0.01,
                "beta2": -0.02,
                "beta3": 0.015,
                "tau1": 1.5,
                "tau2": 9.0,
            },
            note="A Svensson curve evaluated at ten maturities.",
        ),
        Example(
            name="fit_a_par_curve",
            inputs={
                "calculation": "fit",
                "maturities": [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30],
                "yields": [
                    0.0433,
                    0.0425,
                    0.0402,
                    0.0371,
                    0.0362,
                    0.0368,
                    0.0381,
                    0.0402,
                    0.0451,
                    0.0459,
                ],
                "form": "nelson_siegel",
            },
            note="A Nelson-Siegel fit to a par curve of the shape Treasury publishes.",
        ),
    ),
    bindings=(
        Binding("beta0", "us.treasury.gsw_beta0"),
        Binding("beta1", "us.treasury.gsw_beta1"),
        Binding("beta2", "us.treasury.gsw_beta2"),
        Binding("beta3", "us.treasury.gsw_beta3"),
        Binding("tau1", "us.treasury.gsw_tau1"),
        Binding("tau2", "us.treasury.gsw_tau2"),
        Binding("yields", "us.treasury.par_curve", tenors="maturities"),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def curve_fitting(inputs: CurveFittingInputs) -> CurveFittingOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], CurveFittingOutputs]]] = {
    EvaluateInputs: _evaluate,
    FitInputs: _fit,
}
