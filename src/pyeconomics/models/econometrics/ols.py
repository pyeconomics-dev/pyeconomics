# src/pyeconomics/models/econometrics/ols.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Ordinary least squares with robust errors and diagnostics: ``econometrics.ols``.

An adapter over statsmodels (ROADMAP section 4 7.3, "wrap, don't rewrite"),
behind the ``econometrics`` extra: statsmodels is imported inside ``compute``,
and without it the model raises
:class:`~pyeconomics.core.MissingOptionalDependencyError` naming
``pyeconomics[econometrics]``.

statsmodels fits the regression by QR decomposition and supplies the
covariance estimators (classical, White's HC0 and MacKinnon and White's HC1 to
HC3, and Newey and West's HAC with Bartlett weights and no small-sample
correction) and the 0.2.x diagnostics: Durbin-Watson, Breusch-Pagan (Koenker's
studentized form, statsmodels' default), Jarque-Bera, the D'Agostino-Pearson
omnibus test, Ramsey's RESET (an F test on powers of the fitted values) and a
variance inflation factor per regressor. Inference uses Student's t with
``n - k`` degrees of freedom for every covariance type, and the F statistic is
the Wald test that every slope is zero under the chosen covariance.

Cases where a statistic divides by zero are found before statsmodels is asked
for it: a perfect fit has no t statistics, F statistic or residual diagnostics
(each ``None``, with a warning), and a perfectly collinear design has no fit at
all (:class:`~pyeconomics.core.DomainError`).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import BeforeValidator, Field, model_validator

from pyeconomics.core import (
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
    has_spread,
    model,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["ols"]

#: The extra that installs statsmodels.
EXTRA: Final = "econometrics"
#: The most observations and regressors a regression may hold, and the most
#: HAC lags. A 10,000 x 20 fit and its diagnostics take well under a second.
ROWS_MAX: Final = 10_000
COLUMNS_MAX: Final = 20
LAGS_MAX: Final = 100
#: Regression variables are in their own units, polynomial terms included
#: (NIST's Pontius squares values of 3e6), so their bound widens a ratio's from
#: 1e6 to 1e15.
VALUE_MAX: Final = 1e15
#: Outputs from such inputs: a coefficient of a near-collinear design, a t
#: statistic of a near-perfect fit. Beyond these, DomainError.
OUT_MAX: Final = 1e300
_NAME_MAX: Final = 64
_CONSTANT: Final = "const"
#: Below this many observations SciPy's kurtosis test, half the omnibus test,
#: is not valid.
_OMNIBUS_MIN: Final = 20
#: The largest condition number of the equilibrated design: beyond it the
#: design is collinear to working precision (NIST's hardest datasets here reach
#: about 4e4), and statsmodels' inverse of R'R loses every digit.
_CONDITION_MAX: Final = 1e7
#: An auxiliary regression whose residuals are this small, relative to its
#: target, fits exactly.
_EXACT_FIT: Final = 1e-10
#: Residuals this small, relative to the response's variation, are rounding
#: error: the fit is exact (NIST certifies Wampler1 and Wampler2 so).
_EXACT_RESIDUAL: Final = 1e-12
#: A leverage this close to one leaves HC2 and HC3 without a denominator.
_LEVERAGE_SLACK: Final = 1e-12

_Value = Annotated[Ratio, Field(ge=-VALUE_MAX, le=VALUE_MAX)]
_Name = Annotated[str, Field(min_length=1, max_length=_NAME_MAX)]
_Out = Annotated[Ratio, Field(ge=-OUT_MAX, le=OUT_MAX)]
_NonNegative = Annotated[Ratio, Field(ge=0, le=OUT_MAX)]
_Probability = Annotated[Probability, Field(ge=0, le=1)]


def _to_rows(value: object) -> object:
    """Turn a table, a 2-D array or a single column into rows of values."""
    to_numpy = getattr(value, "to_numpy", None)
    array = to_numpy() if callable(to_numpy) else value
    if (
        isinstance(array, list | tuple)
        and array
        and not any(isinstance(item, list | tuple | np.ndarray) for item in array)
    ):
        return [[item] for item in array]
    if isinstance(array, np.ndarray) and array.ndim in {1, 2}:
        if array.size > ROWS_MAX * COLUMNS_MAX:
            msg = f"a design may hold at most {ROWS_MAX} x {COLUMNS_MAX} values"
            raise ValueError(msg)
        return array.reshape(-1, 1).tolist() if array.ndim == 1 else array.tolist()
    return value


_Row = Annotated[
    tuple[_Value, ...],
    Field(min_length=1, max_length=COLUMNS_MAX),
    ARRAY_INPUT,
]
_Design = Annotated[tuple[_Row, ...], BeforeValidator(_to_rows)]


# --- inputs ------------------------------------------------------------------


class OlsInputs(ModelInputs):
    response: Annotated[tuple[_Value, ...], ARRAY_INPUT] = Field(
        min_length=2, max_length=ROWS_MAX, description="The dependent variable, y"
    )
    design: _Design = Field(
        min_length=2,
        max_length=ROWS_MAX,
        description="Regressors, one row per observation (a table or a 2-D array)",
    )
    names: tuple[_Name, ...] | None = Field(
        None,
        max_length=COLUMNS_MAX,
        description="Regressor names; a table's columns, or x1, x2, ... when null",
    )
    add_constant: bool = Field(
        default=True, description="Add an intercept named const as the first term"
    )
    covariance: Literal["nonrobust", "hc0", "hc1", "hc2", "hc3", "hac"] = Field(
        "nonrobust", description="Covariance of the coefficients"
    )
    hac_lags: Count | None = Field(
        None,
        ge=0,
        le=LAGS_MAX,
        description="HAC lags; null for Newey-West's floor(4 (n/100)^(2/9))",
    )
    alpha: Probability = Field(
        0.05, ge=0.001, le=0.5, description="Size of tests and 1 - interval coverage"
    )
    reset_power: Count = Field(
        2, ge=2, le=4, description="Highest power of the fitted values in RESET"
    )

    @model_validator(mode="before")
    @classmethod
    def _table_names(cls, data: object) -> object:
        """Name the regressors after a table's columns when no names are given."""
        if isinstance(data, dict) and data.get("names") is None:
            columns = getattr(data.get("design"), "columns", None)
            if columns is not None:
                return {**data, "names": tuple(str(c) for c in columns)}
        return data

    @model_validator(mode="after")
    def _shape(self) -> Self:
        width = len(self.design[0])
        if any(len(row) != width for row in self.design):
            msg = "every row of the design must have the same number of values"
            raise ValueError(msg)
        if len(self.response) != len(self.design):
            msg = "the response and the design must have the same number of rows"
            raise ValueError(msg)
        if self.names is not None:
            if len(self.names) != width:
                msg = f"names must name each of the design's {width} columns"
                raise ValueError(msg)
            if len(set(self.names)) != width:
                msg = "names must be unique"
                raise ValueError(msg)
            if self.add_constant and _CONSTANT in self.names:
                msg = f"{_CONSTANT!r} names the intercept; rename that regressor"
                raise ValueError(msg)
        terms = width + int(self.add_constant)
        if len(self.response) <= terms:
            msg = f"{terms} coefficients need more than {terms} observations"
            raise ValueError(msg)
        if self.hac_lags is not None and self.hac_lags >= len(self.response):
            msg = "hac_lags must be below the number of observations"
            raise ValueError(msg)
        return self


# --- outputs -----------------------------------------------------------------


_Outs = Annotated[tuple[_Out, ...], ARRAY_INPUT]
_NonNegatives = Annotated[tuple[_NonNegative, ...], ARRAY_INPUT]
_Probabilities = Annotated[tuple[_Probability, ...], ARRAY_INPUT]
_Vifs = Annotated[tuple[Annotated[Ratio, Field(ge=1, le=OUT_MAX)], ...], ARRAY_INPUT]


def _terms(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(max_length=COLUMNS_MAX + 1, description=description)


def _optional_terms(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(None, max_length=COLUMNS_MAX + 1, description=description)


def _statistic(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(None, ge=0, le=OUT_MAX, description=description)


def _p_value(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(None, ge=0, le=1, description=description)


class OlsOutputs(ModelOutputs):
    names: tuple[_Name, ...] = _terms("Term names, const first when added")
    coefficients: _Outs = _terms("Estimated coefficients")
    standard_errors: _NonNegatives = _terms("Standard errors, from the covariance")
    t_statistics: _Outs | None = _optional_terms("t statistics; null for a perfect fit")
    p_values: _Probabilities | None = _optional_terms(
        "Two-sided p-values from Student's t; null for a perfect fit"
    )
    conf_lower: _Outs = _terms("Lower ends of the 1 - alpha confidence intervals")
    conf_upper: _Outs = _terms("Upper ends of the 1 - alpha confidence intervals")
    vif: _Vifs = Field(
        max_length=COLUMNS_MAX, description="Variance inflation factor per regressor"
    )
    observations: Count = Field(ge=2, le=ROWS_MAX, description="Observations, n")
    degrees_of_freedom: Count = Field(
        ge=1, le=ROWS_MAX, description="Residual degrees of freedom, n - k"
    )
    hac_lags: Count = Field(
        ge=0, le=LAGS_MAX, description="Lags in the HAC covariance; 0 for the others"
    )
    r_squared: Ratio | None = Field(
        ge=0,
        le=1,
        description=(
            "R-squared, uncentered without a constant; null if y does not vary "
            "about its mean (or, without a constant, is all zero)"
        ),
    )
    adjusted_r_squared: Ratio | None = Field(
        ge=-ROWS_MAX, le=1, description="R-squared adjusted for degrees of freedom"
    )
    f_statistic: Ratio | None = _statistic(
        "Wald F statistic that every slope is zero, under the chosen covariance"
    )
    f_p_value: Probability | None = _p_value("P-value of the F statistic")
    residual_std_error: Ratio = Field(
        ge=0, le=OUT_MAX, description="sqrt(SSR / (n - k))"
    )
    durbin_watson: Ratio | None = Field(
        None, ge=0, le=4, description="Durbin-Watson statistic of the residuals"
    )
    breusch_pagan: Ratio | None = _statistic(
        "Breusch-Pagan LM statistic (Koenker's studentized form)"
    )
    breusch_pagan_p_value: Probability | None = _p_value("Breusch-Pagan p-value")
    jarque_bera: Ratio | None = _statistic("Jarque-Bera statistic of the residuals")
    jarque_bera_p_value: Probability | None = _p_value("Jarque-Bera p-value")
    omnibus: Ratio | None = _statistic(
        "D'Agostino-Pearson omnibus K-squared statistic of the residuals"
    )
    omnibus_p_value: Probability | None = _p_value("Omnibus p-value")
    reset_f: Ratio | None = _statistic("Ramsey RESET F statistic")
    reset_p_value: Probability | None = _p_value("Ramsey RESET p-value")
    fitted: _Outs = Field(max_length=ROWS_MAX, description="Fitted values")
    residuals: _Outs = Field(max_length=ROWS_MAX, description="Residuals, y - fitted")


# --- the computation ---------------------------------------------------------


def _bounded(value: float, low: float, high: float, what: str) -> float:
    if not (math.isfinite(value) and low <= value <= high):
        msg = (
            f"the {what} is {value!r}, outside its bounds [{low:g}, {high:g}]; "
            "the regression has no answer this model can represent"
        )
        raise DomainError(msg)
    return value


def _statistic_value(value: float, what: str) -> float:
    """Bound a test statistic, which rounding can leave a hair below zero."""
    return _bounded(max(0.0, value), 0.0, OUT_MAX, what)


def _values(array: NDArray[np.float64], what: str) -> tuple[float, ...]:
    return tuple(_bounded(float(v), -OUT_MAX, OUT_MAX, what) for v in array)


def _full_rank(matrix: NDArray[np.float64]) -> bool:
    """Return whether the columns are independent, by NumPy's rank tolerance.

    statsmodels applies the same test to the matrices it is given, so a matrix
    that passes here fits without its rank-deficiency warning.
    """
    return bool(np.linalg.matrix_rank(matrix) == matrix.shape[1])


def _well_conditioned(matrix: NDArray[np.float64]) -> bool:
    """Return whether a design of comparable columns is far from collinear."""
    return bool(np.linalg.cond(matrix) <= _CONDITION_MAX)


def _fits_exactly(design: NDArray[np.float64], target: NDArray[np.float64]) -> bool:
    """Return whether least squares fits ``target`` to within rounding error.

    statsmodels divides by an auxiliary regression's residual variance; a fit
    exact to 1e-10 of the target's scale may leave it exactly zero there.
    """
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    residual = float(np.max(np.abs(target - design @ coefficients)))
    return residual <= _EXACT_FIT * float(np.max(np.abs(target)))


def _exact(
    y: NDArray[np.float64], resid: NDArray[np.float64], *, constant: bool
) -> bool:
    """Return whether the residuals are rounding error: the fit is exact.

    They are when they are within 1e-12 of the response's variation (about its
    mean with a constant), or within 64 ulps per root observation of its level,
    the rounding a large level leaves in residuals of an exact fit.
    """
    level = float(np.max(np.abs(y)))
    spread = float(np.max(np.abs(y - np.mean(y)))) if constant else level
    rounding = 64 * float(np.finfo(np.float64).eps) * level * math.sqrt(len(y))
    return float(np.max(np.abs(resid))) <= max(_EXACT_RESIDUAL * spread, rounding)


def _column_scales(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return each column's largest magnitude, or raise for a zero column."""
    scales = np.max(np.abs(matrix), axis=0)
    if np.any(scales == 0):
        msg = "a regressor is zero in every observation, so it is not identified"
        raise DomainError(msg)
    return scales


def _newey_west_lags(n: int) -> int:
    """Newey and West's (1994) rule of thumb, floor(4 (n / 100)^(2/9))."""
    return min(math.floor(4 * math.pow(n / 100, 2 / 9)), n - 1, LAGS_MAX)


def _max_leverage(x: NDArray[np.float64]) -> float:
    q, _ = np.linalg.qr(x)
    return float(np.max(np.sum(q * q, axis=1)))


class _Fit:
    """The statsmodels objects one regression needs, imported by ``ols``."""

    def __init__(self, sm: Any, diagnostic: Any, stattools: Any) -> None:  # noqa: ANN401
        self.sm = sm
        self.diagnostic = diagnostic
        self.stattools = stattools


def _covariance_kwargs(inputs: OlsInputs, n: int) -> tuple[dict[str, Any], int]:
    if inputs.covariance == "nonrobust":
        return {}, 0
    if inputs.covariance == "hac":
        lags = inputs.hac_lags if inputs.hac_lags is not None else _newey_west_lags(n)
        kwds = {"maxlags": lags, "use_correction": False}
        return {"cov_type": "HAC", "cov_kwds": kwds}, lags
    return {"cov_type": inputs.covariance.upper()}, 0


def _inference(  # noqa: PLR0913 - the fit's parts
    params: NDArray[np.float64],
    cov: NDArray[np.float64],
    unit: float,
    df: int,
    alpha: float,
    *,
    perfect: bool,
) -> dict[str, Any]:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    errors = np.sqrt(np.clip(np.diag(cov), 0.0, None)) * unit
    margin = float(stats.t.ppf(1 - alpha / 2, df)) * errors
    result: dict[str, Any] = {
        "standard_errors": _values(errors, "standard error"),
        "conf_lower": _values(params - margin, "confidence bound"),
        "conf_upper": _values(params + margin, "confidence bound"),
        "t_statistics": None,
        "p_values": None,
    }
    if perfect:
        return result
    if np.any(errors == 0):
        warn(
            "zero_standard_error",
            "a standard error is zero to working precision: no t statistic",
        )
        return result
    t = params / errors
    result["t_statistics"] = _values(t, "t statistic")
    result["p_values"] = tuple(
        min(1.0, float(p)) for p in 2 * stats.t.sf(np.abs(t), df)
    )
    return result


def _f_test(res: Any, *, constant: bool, perfect: bool) -> dict[str, Any]:  # noqa: ANN401
    """Wald F that every slope is zero, on the equilibrated fit."""
    none = {"f_statistic": None, "f_p_value": None}
    if perfect:
        return none
    width = len(res.params)
    restriction = np.eye(width)[1:] if constant else np.eye(width)
    middle = restriction @ np.asarray(res.cov_params()) @ restriction.T
    if not _full_rank(middle):
        warn("f_undefined", "the covariance of the slopes is singular: no F test")
        return none
    test = res.f_test(restriction)
    return {
        "f_statistic": _statistic_value(float(np.squeeze(test.fvalue)), "F"),
        "f_p_value": min(1.0, float(test.pvalue)),
    }


def _r_squared(
    base: Any,  # noqa: ANN401
    y: NDArray[np.float64],
    *,
    constant: bool,
) -> dict[str, Any]:
    total = base.centered_tss if constant else base.uncentered_tss
    if not (has_spread(y.tolist()) if constant else total > 0):
        warn(
            "no_variation",
            "y does not vary about its mean (with a constant) or is all zero "
            "(without one), so R-squared is undefined",
        )
        return {"r_squared": None, "adjusted_r_squared": None}
    r2 = min(1.0, max(0.0, 1.0 - base.ssr / total))
    n, df = base.nobs, base.df_resid
    adjusted = 1.0 - (n - int(constant)) / df * (1.0 - r2)
    return {"r_squared": r2, "adjusted_r_squared": max(-ROWS_MAX, min(1.0, adjusted))}


def _vifs(fit: _Fit, x: NDArray[np.float64], *, constant: bool) -> tuple[float, ...]:
    """Regress each regressor on the others: VIF = 1 / (1 - R_j^2)."""
    vifs = []
    for j in range(int(constant), x.shape[1]):
        others = np.delete(x, j, axis=1)
        if others.shape[1] == 0:
            vifs.append(1.0)
            continue
        aux = fit.sm.OLS(x[:, j], others, hasconst=constant).fit(method="qr")
        total = aux.centered_tss if constant else aux.uncentered_tss
        if not aux.ssr > 0:
            msg = "a regressor is a linear combination of the others"
            raise DomainError(msg)
        vifs.append(_bounded(max(1.0, float(total / aux.ssr)), 1.0, OUT_MAX, "VIF"))
    return tuple(vifs)


def _reset(
    fit: _Fit,
    y: NDArray[np.float64],
    x: NDArray[np.float64],
    base: Any,  # noqa: ANN401
    power: int,
) -> dict[str, Any]:
    """RESET on a refit with y scaled so the largest fitted value is one.

    The F statistic does not change with the scale of y, and the powers of
    fitted values of magnitude at most one keep the augmented design's columns
    comparable, so its rank is judged as statsmodels will judge it.
    """
    none = {"reset_f": None, "reset_p_value": None}
    peak = float(np.max(np.abs(base.fittedvalues)))
    if peak > float(np.max(np.abs(y))) * 1e-100:
        scaled = fit.sm.OLS(y / peak, x, hasconst=base.k_constant > 0).fit()
        fitted = np.asarray(scaled.fittedvalues, dtype=np.float64)
        augmented = np.column_stack([x, *(fitted**p for p in range(2, power + 1))])
        n, width = augmented.shape
        defined = (
            n > width
            and _well_conditioned(augmented)
            and not _fits_exactly(augmented, y / peak)
        )
        if defined:
            test = fit.diagnostic.linear_reset(
                scaled, power=power, test_type="fitted", use_f=True
            )
            return {
                "reset_f": _statistic_value(float(np.squeeze(test.fvalue)), "RESET F"),
                "reset_p_value": min(1.0, float(test.pvalue)),
            }
    warn(
        "reset_undefined",
        "the powers of the fitted values are collinear with the regressors, fit "
        "exactly or leave no degrees of freedom, so RESET is undefined",
    )
    return none


def _breusch_pagan(
    fit: _Fit, resid: NDArray[np.float64], x: NDArray[np.float64], *, constant: bool
) -> dict[str, Any]:
    none = {"breusch_pagan": None, "breusch_pagan_p_value": None}
    het = x if constant else np.column_stack([np.ones(len(x)), x])
    squares = resid * resid
    defined = (
        het.shape[0] > het.shape[1]
        and has_spread(squares.tolist())
        and _well_conditioned(het)
    )
    # statsmodels also reports the auxiliary regression's F, which divides by
    # its residual variance: an exact fit of e^2 leaves none.
    defined = defined and not _fits_exactly(het, squares)
    if not defined:
        warn(
            "breusch_pagan_undefined",
            "Breusch-Pagan needs varying squared residuals, more observations "
            "than auxiliary terms, regressors that do not span a constant "
            "already, and an auxiliary regression that does not fit exactly",
        )
        return none
    lm, lm_p, _, _ = fit.diagnostic.het_breuschpagan(resid, het)
    return {
        "breusch_pagan": _statistic_value(float(lm), "Breusch-Pagan"),
        "breusch_pagan_p_value": min(1.0, float(lm_p)),
    }


def _normality(fit: _Fit, resid: NDArray[np.float64]) -> dict[str, Any]:
    result: dict[str, Any] = dict.fromkeys(
        ("jarque_bera", "jarque_bera_p_value", "omnibus", "omnibus_p_value")
    )
    if not has_spread(resid.tolist()):
        warn("constant_residuals", "the residuals do not vary: no normality test")
        return result
    jb, jb_p, _, _ = fit.stattools.jarque_bera(resid)
    result["jarque_bera"] = _statistic_value(float(jb), "Jarque-Bera")
    result["jarque_bera_p_value"] = min(1.0, float(jb_p))
    if len(resid) < _OMNIBUS_MIN:
        warn("small_sample", "the omnibus test needs at least 20 observations")
        return result
    k2, k2_p = fit.stattools.omni_normtest(resid)
    result["omnibus"] = _statistic_value(float(k2), "omnibus")
    result["omnibus_p_value"] = min(1.0, float(k2_p))
    return result


_DIAGNOSTICS: Final = (
    "durbin_watson",
    "breusch_pagan",
    "breusch_pagan_p_value",
    "jarque_bera",
    "jarque_bera_p_value",
    "omnibus",
    "omnibus_p_value",
    "reset_f",
    "reset_p_value",
)


def _residual_diagnostics(  # noqa: PLR0913 - the fit's parts
    fit: _Fit,
    y: NDArray[np.float64],
    x: NDArray[np.float64],
    base: Any,  # noqa: ANN401
    inputs: OlsInputs,
    *,
    perfect: bool,
) -> dict[str, Any]:
    if perfect:
        return dict.fromkeys(_DIAGNOSTICS)
    resid = np.asarray(base.resid, dtype=np.float64)
    # Every residual diagnostic is invariant to the residuals' scale; scaling to
    # a largest magnitude of one keeps tiny residuals from squaring to zero.
    resid = resid / np.max(np.abs(resid))
    return {
        "durbin_watson": min(4.0, float(fit.stattools.durbin_watson(resid))),
        **_breusch_pagan(fit, resid, x, constant=inputs.add_constant),
        **_normality(fit, resid),
        **_reset(fit, y, x, base, inputs.reset_power),
    }


def _estimate(inputs: OlsInputs, fit: _Fit) -> OlsOutputs:
    """Fit with y and each regressor scaled to a largest magnitude of one.

    Equilibrating changes no test statistic or VIF, and scaling back restores
    the coefficients, errors, fitted values and residuals; it keeps the QR fit
    accurate, statsmodels' rank checks on comparable columns, and tiny or huge
    responses away from underflow and overflow.
    """
    # Adding zero turns -0.0 into 0.0, which canonical JSON cannot tell apart
    # but LAPACK's Householder reflections can: a result must reproduce from
    # its own canonical inputs.
    y = np.asarray(inputs.response, dtype=np.float64) + 0.0
    design = np.asarray(inputs.design, dtype=np.float64) + 0.0
    n, width = design.shape
    names = inputs.names or tuple(f"x{j + 1}" for j in range(width))
    constant = inputs.add_constant
    raw = np.column_stack([np.ones(n), design]) if constant else design
    scales = _column_scales(raw)
    x = raw / scales
    if not _well_conditioned(x):
        msg = (
            "the design is collinear to working precision (a regressor is, or is "
            "nearly, a linear combination of the others or of the constant), so "
            "the coefficients are not identified"
        )
        raise DomainError(msg)
    if inputs.covariance in {"hc2", "hc3"} and _max_leverage(x) >= 1 - _LEVERAGE_SLACK:
        msg = (
            "an observation has leverage one, so HC2 and HC3, which divide by "
            "1 - h, are undefined"
        )
        raise DomainError(msg)
    peak = float(np.max(np.abs(y)))
    unit = peak if peak > 0 else 1.0
    ys = y / unit
    model_ = fit.sm.OLS(ys, x, hasconst=constant)
    base = model_.fit(method="qr")
    kwargs, lags = _covariance_kwargs(inputs, n)
    res = model_.fit(method="qr", use_t=True, **kwargs) if kwargs else base
    perfect = _exact(ys, np.asarray(base.resid, dtype=np.float64), constant=constant)
    if perfect:
        warn(
            "perfect_fit",
            "the fit is exact to rounding: no t statistic, F statistic or "
            "residual diagnostic",
        )
    # Scaling back can overflow for regressors near the smallest doubles; an
    # infinite standard error is then caught by its bound (DomainError).
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        params = np.asarray(res.params, dtype=np.float64) / scales * unit
        cov = np.asarray(res.cov_params(), dtype=np.float64)
        # In units of y / unit: a standard error is scaled back after its root,
        # so a tiny response cannot underflow its variance.
        cov = cov / scales[:, None] / scales[None, :]
    df = int(base.df_resid)
    return OlsOutputs(
        names=((_CONSTANT,) if constant else ()) + tuple(names),
        coefficients=_values(params, "coefficient"),
        vif=_vifs(fit, x, constant=constant),
        observations=n,
        degrees_of_freedom=df,
        hac_lags=lags,
        residual_std_error=_bounded(
            math.sqrt(max(0.0, float(base.scale))) * unit, 0, OUT_MAX, "residual SE"
        ),
        fitted=_values(np.asarray(base.fittedvalues) * unit, "fitted value"),
        residuals=_values(np.asarray(base.resid) * unit, "residual"),
        **_inference(params, cov, unit, df, inputs.alpha, perfect=perfect),
        **_f_test(res, constant=constant, perfect=perfect),
        **_r_squared(base, ys, constant=constant),
        **_residual_diagnostics(fit, ys, x, base, inputs, perfect=perfect),
    )


# --- the model ---------------------------------------------------------------

_STATSMODELS = Reference(
    key="seabold2010",
    citation=(
        "Seabold, S. and Perktold, J. (2010). statsmodels: Econometric and "
        "statistical modeling with Python. Proceedings of the 9th Python in "
        "Science Conference, 92-96."
    ),
    doi="10.25080/Majora-92bf1922-011",
    locator="The OLS model, its covariance types and statsmodels.stats.diagnostic",
)
_WHITE = Reference(
    key="white1980",
    citation=(
        "White, H. (1980). A heteroskedasticity-consistent covariance matrix "
        "estimator and a direct test for heteroskedasticity. Econometrica, 48(4), "
        "817-838."
    ),
    doi="10.2307/1912934",
    locator="Theorem 1 (the HC0 estimator)",
)
_MACKINNON = Reference(
    key="mackinnon1985",
    citation=(
        "MacKinnon, J. G. and White, H. (1985). Some heteroskedasticity-consistent "
        "covariance matrix estimators with improved finite sample properties. "
        "Journal of Econometrics, 29(3), 305-325."
    ),
    doi="10.1016/0304-4076(85)90158-7",
    locator="Section 2 (HC1, HC2 and HC3)",
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
_NEWEY_WEST_1994 = Reference(
    key="newey1994",
    citation=(
        "Newey, W. K. and West, K. D. (1994). Automatic lag selection in "
        "covariance matrix estimation. The Review of Economic Studies, 61(4), "
        "631-653."
    ),
    doi="10.2307/2297912",
    locator="The Bartlett-kernel rule of thumb, 4 (n / 100)^(2/9)",
)
_DURBIN_WATSON = Reference(
    key="durbin1950",
    citation=(
        "Durbin, J. and Watson, G. S. (1950). Testing for serial correlation in "
        "least squares regression. I. Biometrika, 37(3-4), 409-428."
    ),
    doi="10.1093/biomet/37.3-4.409",
    locator="The statistic d",
)
_BREUSCH_PAGAN = Reference(
    key="breusch1979",
    citation=(
        "Breusch, T. S. and Pagan, A. R. (1979). A simple test for "
        "heteroscedasticity and random coefficient variation. Econometrica, "
        "47(5), 1287-1294."
    ),
    doi="10.2307/1911963",
    locator="The Lagrange multiplier test",
)
_KOENKER = Reference(
    key="koenker1981",
    citation=(
        "Koenker, R. (1981). A note on studentizing a test for "
        "heteroscedasticity. Journal of Econometrics, 17(1), 107-112."
    ),
    doi="10.1016/0304-4076(81)90062-2",
    locator="The studentized statistic n R^2",
)
_JARQUE_BERA = Reference(
    key="jarque1980",
    citation=(
        "Jarque, C. M. and Bera, A. K. (1980). Efficient tests for normality, "
        "homoscedasticity and serial independence of regression residuals. "
        "Economics Letters, 6(3), 255-259."
    ),
    doi="10.1016/0165-1765(80)90024-5",
    locator="The normality statistic from skewness and kurtosis",
)
_DAGOSTINO = Reference(
    key="dag1973",
    citation=(
        "D'Agostino, R. and Pearson, E. S. (1973). Tests for departure from "
        "normality. Biometrika, 60(3), 613-622."
    ),
    doi="10.1093/biomet/60.3.613",
    locator="The omnibus K-squared statistic",
)
_RAMSEY = Reference(
    key="ramsey1969",
    citation=(
        "Ramsey, J. B. (1969). Tests for specification errors in classical "
        "linear least-squares regression analysis. Journal of the Royal "
        "Statistical Society: Series B, 31(2), 350-371."
    ),
    doi="10.1111/j.2517-6161.1969.tb00796.x",
    locator="RESET with powers of the fitted values",
)
_MARQUARDT = Reference(
    key="marquardt1970",
    citation=(
        "Marquardt, D. W. (1970). Generalized inverses, ridge regression, biased "
        "linear estimation, and nonlinear estimation. Technometrics, 12(3), "
        "591-612."
    ),
    doi="10.2307/1267205",
    locator="The variance inflation factor",
)
_NIST = Reference(
    key="nist_strd",
    citation=(
        "NIST (2003). Statistical Reference Datasets: linear least squares "
        "regression. National Institute of Standards and Technology."
    ),
    url="https://www.itl.nist.gov/div898/strd/lls/lls.shtml",
    locator="Norris, Pontius, Longley, Wampler1 and Wampler2: certified values",
)


@model(
    id="econometrics.ols",
    version=1,
    title="Ordinary least squares",
    summary=(
        "OLS over statsmodels, with classical, HC0-HC3 and HAC standard errors, "
        "and the Durbin-Watson, Breusch-Pagan, Jarque-Bera, omnibus, RESET and "
        "VIF diagnostics."
    ),
    formula=(
        r"\hat\beta = (X'X)^{-1}X'y, \quad e = y - X\hat\beta",
        (
            r"V_{HC} = (X'X)^{-1}X'\,\mathrm{diag}(\omega_i e_i^2)"
            r"\,X(X'X)^{-1}, \quad \omega_i \in \{1, \tfrac{n}{n-k}, "
            r"\tfrac{1}{1-h_i}, \tfrac{1}{(1-h_i)^2}\}"
        ),
        (
            r"V_{HAC} = (X'X)^{-1}\left[\sum_{l=-L}^{L}"
            r"\left(1 - \tfrac{|l|}{L+1}\right)"
            r"\sum_t x_t e_t e_{t-l} x_{t-l}'\right](X'X)^{-1}"
        ),
        (
            r"R^2 = 1 - \frac{SSR}{TSS}, \quad d = \frac{\sum (e_t - e_{t-1})^2}"
            r"{\sum e_t^2}, \quad VIF_j = \frac{1}{1 - R_j^2}"
        ),
        (
            r"JB = \frac{n}{6}\left(S^2 + \frac{(K - 3)^2}{4}\right), "
            r"\quad LM_{BP} = n R^2_{e^2}"
        ),
    ),
    assumptions=(
        (
            "statsmodels fits by QR decomposition; inference uses Student's t "
            "with n - k degrees of freedom for every covariance type."
        ),
        (
            "HAC uses Bartlett weights and no small-sample correction; with no "
            "lag count, Newey and West's (1994) rule of thumb picks one."
        ),
        (
            "R-squared is centered with a constant and uncentered without; the "
            "F statistic tests every slope (every coefficient without a "
            "constant) under the chosen covariance."
        ),
        (
            "Breusch-Pagan is Koenker's studentized n R^2, regressing e^2 on the "
            "regressors and a constant; RESET is an F test on the fitted values' "
            "powers 2 to reset_power; each VIF regresses one regressor on the "
            "others."
        ),
    ),
    limitations=(
        (
            "A perfectly collinear design, or one whose equilibrated condition "
            "number exceeds 1e7, has no fit: DomainError."
        ),
        (
            "HC2 and HC3 are undefined when an observation has leverage one: "
            "DomainError."
        ),
        (
            "A fit exact to rounding has no t statistics, F statistic or "
            "residual diagnostics (each null, with a warning); the omnibus test "
            "needs 20 observations; RESET and Breusch-Pagan are null when their "
            "auxiliary regression is collinear, fits exactly or leaves no "
            "degrees of freedom."
        ),
        (
            "An output beyond 1e300 in magnitude (a near-collinear design) "
            "raises DomainError."
        ),
        "Needs the econometrics extra: pip install 'pyeconomics[econometrics]'.",
    ),
    references=(
        _STATSMODELS,
        _WHITE,
        _MACKINNON,
        _NEWEY_WEST,
        _NEWEY_WEST_1994,
        _DURBIN_WATSON,
        _BREUSCH_PAGAN,
        _KOENKER,
        _JARQUE_BERA,
        _DAGOSTINO,
        _RAMSEY,
        _MARQUARDT,
        _NIST,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=("regression", "ols", "heteroskedasticity", "newey-west", "diagnostics"),
    invariants=(
        Invariant(
            id="residuals_orthogonal_to_regressors",
            statement="The residuals are orthogonal to every regressor: X'e = 0.",
        ),
        Invariant(
            id="r_squared_in_unit_interval",
            statement="R-squared lies in [0, 1].",
        ),
        Invariant(
            id="coefficients_invariant_to_row_order",
            statement="Reordering the observations leaves the coefficients unchanged.",
        ),
    ),
    examples=(
        Example(
            name="nist_norris_head",
            inputs={
                "response": [0.1, 338.8, 118.1, 888.0, 9.2, 228.1, 668.5, 998.5],
                "design": [
                    [0.2],
                    [337.4],
                    [118.2],
                    [884.6],
                    [10.1],
                    [226.5],
                    [666.3],
                    [996.3],
                ],
                "names": ["x"],
            },
            note="The first eight observations of NIST's Norris dataset.",
        ),
    ),
    charts=(
        ChartSpec(
            id="residuals_vs_fitted",
            title="Residuals against fitted values",
            kind=ChartKind.SCATTER,
            x="fitted",
            y=("residuals",),
            x_label="Fitted value",
            y_label="Residual",
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
    # A literal: the import allowlist reads it with ast to admit statsmodels.
    extra="econometrics",
)
def ols(inputs: OlsInputs) -> OlsOutputs:
    """Fit the regression with statsmodels, imported here (the econometrics extra)."""
    try:
        import statsmodels.api as sm  # noqa: PLC0415 - the extra, imported on use
        from statsmodels.stats import (  # noqa: PLC0415
            diagnostic,
            stattools,
        )
    except ImportError as error:
        package = "statsmodels"
        raise MissingOptionalDependencyError(package, extra=EXTRA) from error
    return _estimate(inputs, _Fit(sm, diagnostic, stattools))
