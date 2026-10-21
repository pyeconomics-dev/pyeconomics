# src/pyeconomics/core/regression.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Ordinary least squares with classical, HC1 and Newey-West standard errors.

:func:`least_squares` fits :math:`y = X\beta + e` by a QR decomposition of the
design and returns the coefficients, their standard errors and t statistics,
R² and the residuals. Three covariance estimators are named:

- classical: :math:`s^2 (X'X)^{-1}` with :math:`s^2 = e'e / (n - k)`;
- HC1 (MacKinnon and White, 1985): :math:`\frac{n}{n-k} (X'X)^{-1}
  X'\mathrm{diag}(e_i^2) X (X'X)^{-1}`, White's estimator with a degrees-of-freedom
  correction;
- Newey-West (1987): :math:`(X'X)^{-1} S (X'X)^{-1}` with
  :math:`S = \sum_t e_t^2 x_t x_t' + \sum_{l=1}^{L} \left(1 - \frac{l}{L+1}\right)
  \sum_{t > l} e_t e_{t-l} (x_t x_{t-l}' + x_{t-l} x_t')`, Bartlett weights and
  no small-sample correction. The truncation lag :math:`L` is an input; left
  out, it is Newey and West's (1994) rule of thumb, :func:`newey_west_lags`.

The design's columns and the response are scaled to a largest magnitude of one
before the fit and the results scaled back, which changes no coefficient,
standard error or t statistic but keeps the decomposition accurate; a design
whose scaled condition number exceeds :data:`CONDITION_MAX` is collinear to
working precision and has no fit. Residuals within rounding of zero mean an
exact fit, which has no t statistics (their standard errors are zero).

The inputs are bounded (:data:`ROWS_MAX` observations, :data:`COLUMNS_MAX`
regressors, :data:`LAGS_MAX` lags), so no call is an unbounded workload. The
models that estimate a relationship (``macro.phillips_curve``,
``macro.okun_law``, and the Phase 3 asset-pricing regressions) share it.

Examples
--------
>>> from pyeconomics.core import least_squares
>>> fit = least_squares([1.0, 3.0, 5.0, 7.5], [[0.0], [1.0], [2.0], [3.0]])
>>> [round(c, 12) for c in fit.coefficients]
[0.9, 2.15]
>>> fit.observations, fit.degrees_of_freedom
(4, 2)

"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

import numpy as np

from pyeconomics.core.errors import DomainError, InputError

if TYPE_CHECKING:
    from numpy.typing import ArrayLike, NDArray

__all__ = [
    "COLUMNS_MAX",
    "CONDITION_MAX",
    "LAGS_MAX",
    "ROWS_MAX",
    "Covariance",
    "LeastSquares",
    "least_squares",
    "newey_west_lags",
]

#: The most observations, regressors (with the constant) and Newey-West lags a
#: fit takes: a 10,000 x 20 fit with 100 lags takes well under a second.
ROWS_MAX: Final = 10_000
COLUMNS_MAX: Final = 20
LAGS_MAX: Final = 100
#: The largest condition number of the scaled design: beyond it the columns are
#: collinear to working precision and the coefficients are not identified.
CONDITION_MAX: Final = 1e7
#: Residuals this small, relative to the response's variation, are rounding error.
_EXACT_RESIDUAL: Final = 1e-12
_ROUNDING_ULPS: Final = 64

type _Matrix = NDArray[np.float64]


class Covariance(StrEnum):
    """The covariance estimator behind the standard errors."""

    CLASSICAL = "classical"
    """Homoskedastic: :math:`s^2 (X'X)^{-1}`."""
    HC1 = "hc1"
    """White's heteroskedasticity-consistent estimator times ``n / (n - k)``."""
    NEWEY_WEST = "newey_west"
    """Heteroskedasticity and autocorrelation consistent, Bartlett weights."""


@dataclass(frozen=True, slots=True, kw_only=True)
class LeastSquares:
    """A least-squares fit: its coefficients, their errors and the residuals.

    The coefficients follow the design's columns, the constant first when one
    was added.
    """

    coefficients: tuple[float, ...]
    standard_errors: tuple[float, ...]
    t_statistics: tuple[float, ...] | None
    """``None`` for an exact fit, whose standard errors are zero."""
    r_squared: float | None
    """Centered with a constant, uncentered without; ``None`` when the response
    does not vary (about its mean, with a constant)."""
    fitted: tuple[float, ...]
    residuals: tuple[float, ...]
    observations: int
    degrees_of_freedom: int
    """``n - k``: observations less coefficients."""
    covariance: Covariance
    lags: int
    """The Newey-West truncation lag; 0 for the other estimators."""
    exact: bool
    """Whether the residuals are rounding error: the fit is exact."""


def newey_west_lags(observations: int) -> int:
    """Return Newey and West's (1994) lag rule, ``floor(4 (n / 100) ** (2 / 9))``.

    It is capped at ``n - 1`` and at :data:`LAGS_MAX`.

    Examples
    --------
    >>> newey_west_lags(100), newey_west_lags(240)
    (4, 4)

    """
    if observations < 1:
        msg = f"the lag rule needs at least one observation, not {observations}"
        raise InputError(msg)
    rule = math.floor(4 * math.pow(observations / 100, 2 / 9))
    return min(rule, observations - 1, LAGS_MAX)


def _matrix(response: ArrayLike, design: ArrayLike) -> tuple[_Matrix, _Matrix]:
    y = np.asarray(response, dtype=np.float64)
    x = np.asarray(design, dtype=np.float64)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if y.ndim != 1 or x.ndim != 2:  # noqa: PLR2004 - a matrix has two axes
        msg = "the response is a vector and the design a matrix of rows"
        raise InputError(msg)
    if not (np.all(np.isfinite(y)) and np.all(np.isfinite(x))):
        msg = "the response and the design must hold finite numbers"
        raise InputError(msg)
    if len(y) != x.shape[0]:
        msg = f"the response has {len(y)} observations and the design {x.shape[0]} rows"
        raise InputError(msg)
    # Adding zero turns -0.0 into 0.0: the sign of a zero changes the QR
    # decomposition's reflections, and a result must reproduce from canonical
    # inputs, which cannot tell the two apart.
    return y + 0.0, x + 0.0


def _check_size(rows: int, columns: int, lags: int | None) -> None:
    if rows > ROWS_MAX:
        msg = f"a fit takes at most {ROWS_MAX} observations, not {rows}"
        raise InputError(msg)
    if not 1 <= columns <= COLUMNS_MAX:
        msg = f"a fit takes 1 to {COLUMNS_MAX} coefficients, not {columns}"
        raise InputError(msg)
    if rows <= columns:
        msg = f"{columns} coefficients need more than {columns} observations"
        raise InputError(msg)
    if lags is not None and not 0 <= lags <= min(LAGS_MAX, rows - 1):
        msg = (
            f"the Newey-West lag is a whole number from 0 to "
            f"{min(LAGS_MAX, rows - 1)}, not {lags}"
        )
        raise InputError(msg)


def _scales(x: _Matrix) -> _Matrix:
    scales = np.max(np.abs(x), axis=0)
    if np.any(scales == 0):
        msg = "a regressor is zero in every observation, so it is not identified"
        raise DomainError(msg)
    return scales


def _exact(y: _Matrix, residuals: _Matrix, *, constant: bool) -> bool:
    """Return whether the residuals are within rounding of zero."""
    level = float(np.max(np.abs(y)))
    spread = float(np.max(np.abs(y - np.mean(y)))) if constant else level
    eps = float(np.finfo(np.float64).eps)
    rounding = _ROUNDING_ULPS * eps * level * math.sqrt(len(y))
    largest = float(np.max(np.abs(residuals)))
    return largest <= max(_EXACT_RESIDUAL * spread, rounding)


def _sandwich(
    projection: _Matrix, e: _Matrix, covariance: Covariance, lags: int
) -> _Matrix:
    r"""Return the robust covariance from the rows of ``(X'X)^-1 X'`` and residuals.

    With :math:`u_t = (X'X)^{-1} x_t e_t`, the sandwich is :math:`\sum_t u_t u_t'`
    plus the weighted cross products of lagged :math:`u`. Building it from
    :math:`u` keeps each variance a sum of squares; multiplying the inverse of
    :math:`X'X` into the middle instead cancels digits when the design is near
    collinear.
    """
    scores = projection * e[None, :]
    covariance_matrix = scores @ scores.T
    if covariance is Covariance.NEWEY_WEST:
        for lag in range(1, lags + 1):
            weight = 1.0 - lag / (lags + 1)
            cross = scores[:, lag:] @ scores[:, :-lag].T
            covariance_matrix += weight * (cross + cross.T)
    return covariance_matrix


def _r_squared(y: _Matrix, residuals: _Matrix, *, constant: bool) -> float | None:
    centred = y - np.mean(y) if constant else y
    total = float(centred @ centred)
    level = float(np.max(np.abs(y)))
    if constant:
        eps = float(np.finfo(np.float64).eps)
        if float(np.max(np.abs(centred))) <= _ROUNDING_ULPS * eps * level:
            return None
    elif total == 0:
        return None
    return min(1.0, max(0.0, 1.0 - float(residuals @ residuals) / total))


def _unscaled(
    beta: _Matrix, roots: _Matrix, scales: _Matrix, unit: float
) -> tuple[_Matrix, _Matrix]:
    """Return the coefficients and errors in the data's units.

    Dividing by a subnormal column scale first overflows when the response and
    the regressors are both tiny; then the ratio ``unit / scales``, which is
    moderate, carries them back instead.

    Raises
    ------
    DomainError
        If a coefficient is still past the floating-point range: a regressor
        tiny next to the response.
    """
    with np.errstate(over="ignore", invalid="ignore"):
        coefficients = beta / scales * unit
        errors = roots / scales * unit
        if not (np.all(np.isfinite(coefficients)) and np.all(np.isfinite(errors))):
            ratio = unit / scales
            coefficients = beta * ratio
            errors = roots * ratio
    if not (np.all(np.isfinite(coefficients)) and np.all(np.isfinite(errors))):
        msg = (
            "a regressor is so small next to the response that its coefficient "
            "is beyond the floating-point range"
        )
        raise DomainError(msg)
    return coefficients, errors


def least_squares(
    response: ArrayLike,
    design: ArrayLike,
    *,
    constant: bool = True,
    covariance: Covariance | str = Covariance.CLASSICAL,
    lags: int | None = None,
) -> LeastSquares:
    """Fit ``response`` on ``design`` by ordinary least squares.

    Parameters
    ----------
    response
        The dependent variable, ``n`` values.
    design
        The regressors: ``n`` rows of values, or ``n`` values for one regressor.
    constant
        Add an intercept as the first coefficient.
    covariance
        ``classical``, ``hc1`` or ``newey_west``.
    lags
        The Newey-West truncation lag; left out, :func:`newey_west_lags` of
        ``n``. Only the Newey-West estimator reads it.

    Returns
    -------
    LeastSquares
        The coefficients, standard errors, t statistics, R² and residuals.

    Raises
    ------
    InputError
        For values that are not finite, mismatched lengths, a fit with no
        degrees of freedom, a lag out of range or more than the bounds allow.
    DomainError
        When a regressor is zero throughout or the design is collinear to
        working precision: the coefficients are not identified; or when a
        coefficient is beyond the floating-point range.

    Examples
    --------
    >>> fit = least_squares(
    ...     [2.0, 4.1, 5.9, 8.2, 9.8], [1.0, 2.0, 3.0, 4.0, 5.0], covariance="hc1"
    ... )
    >>> round(fit.coefficients[1], 12), fit.covariance.value
    (1.97, 'hc1')

    """
    try:
        kind = Covariance(covariance)
    except ValueError:
        choices = ", ".join(c.value for c in Covariance)
        msg = f"covariance is one of {choices}, not {covariance!r}"
        raise InputError(msg) from None
    if lags is not None and (isinstance(lags, bool) or not isinstance(lags, int)):
        msg = f"lags is a whole number or None, not {lags!r}"
        raise InputError(msg)
    y, given = _matrix(response, design)
    rows = len(y)
    x_raw = np.column_stack([np.ones(rows), given]) if constant else given
    columns = x_raw.shape[1]
    _check_size(rows, columns, lags)
    used = 0
    if kind is Covariance.NEWEY_WEST:
        used = newey_west_lags(rows) if lags is None else lags
    scales = _scales(x_raw)
    x = x_raw / scales
    if np.linalg.cond(x) > CONDITION_MAX:
        msg = (
            "the design is collinear to working precision (a regressor is, or is "
            "nearly, a linear combination of the others), so the coefficients "
            "are not identified"
        )
        raise DomainError(msg)
    peak = float(np.max(np.abs(y)))
    unit = peak if peak > 0 else 1.0
    ys = y / unit
    q, r = np.linalg.qr(x)
    from scipy.linalg import solve_triangular  # noqa: PLC0415 - SciPy on first use

    beta = solve_triangular(r, q.T @ ys)
    fitted = x @ beta
    residuals = ys - fitted
    # (X'X)^-1 X' = R^-1 Q', one row per coefficient.
    projection = solve_triangular(r, q.T)
    dof = rows - columns
    if kind is Covariance.CLASSICAL:
        cov = float(residuals @ residuals) / dof * (projection @ projection.T)
    else:
        cov = _sandwich(projection, residuals, kind, used)
        if kind is Covariance.HC1:
            cov *= rows / dof
    roots = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    coefficients, errors = _unscaled(beta, roots, scales, unit)
    exact = _exact(ys, residuals, constant=constant)
    t_statistics = None
    if not exact and np.all(errors > 0):
        t_statistics = tuple(float(v) for v in coefficients / errors)
    return LeastSquares(
        coefficients=tuple(float(v) for v in coefficients),
        standard_errors=tuple(float(v) for v in errors),
        t_statistics=t_statistics,
        r_squared=_r_squared(ys, residuals, constant=constant),
        fitted=tuple(float(v) for v in fitted * unit),
        residuals=tuple(float(v) for v in residuals * unit),
        observations=rows,
        degrees_of_freedom=dof,
        covariance=kind,
        lags=used,
        exact=exact,
    )
