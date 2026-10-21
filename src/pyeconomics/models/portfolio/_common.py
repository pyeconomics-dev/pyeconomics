# src/pyeconomics/models/portfolio/_common.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the portfolio models share: matrix inputs, their checks and bounds.

A covariance matrix arrives as rows (a list of lists, a 2-D NumPy array or a
DataFrame) and must be symmetric and positive definite: a matrix that is not has
no minimum-variance portfolio, so :func:`covariance` raises
:class:`~pyeconomics.core.DomainError` (ADR-0008 decision 10). So does one so
close to singular that its inverse is rounding error. A model that never
inverts the matrix (risk-based allocation) accepts a singular one with
``definite=False``, as long as every asset has some variance.

A window of returns arrives as rows too, one per period, one value per asset
(:data:`ReturnWindow`); :func:`sample_covariance` turns it into the matrix.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final

import numpy as np
from pydantic import BeforeValidator, Field

from pyeconomics.core import Correlation, DomainError, Ratio, Return
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

__all__ = [
    "ASSETS_MAX",
    "COVARIANCE_MAX",
    "PERIODS_MAX",
    "RETURN_MAX",
    "CorrelationMatrix",
    "CovarianceMatrix",
    "ReturnWindow",
    "bounded",
    "covariance",
    "matrix_field",
    "sample_covariance",
    "square",
    "window_field",
]

#: The most assets a portfolio input may hold. A 100 x 100 matrix inverts in
#: well under a millisecond.
ASSETS_MAX: Final = 100
#: The largest covariance entry: a volatility of 10 (ADR-0008's bound) squared.
COVARIANCE_MAX: Final = 100.0
#: The most periods a window of returns holds: ten years of trading days, or two
#: centuries of months.
PERIODS_MAX: Final = 2_520
#: A return per period in a window is from -100% to 500% (the Ken French size
#: portfolios reach 148% in a month), so a sample variance is at most
#: 6^2 * 2 / 4 = 18 and stays inside COVARIANCE_MAX.
RETURN_MAX: Final = 5.0
#: The smallest ratio of the smallest to the largest eigenvalue: below it the
#: matrix is singular to working precision.
_CONDITION_MIN: Final = 1e-12
#: How far a matrix may be from symmetric, relative to its largest entry.
_SYMMETRY: Final = 1e-12
#: How negative an eigenvalue of a semidefinite matrix may round, relative to
#: the largest: a perfectly correlated pair gives about -1e-16.
_SEMIDEFINITE: Final = 1e-10
#: A variance below this fraction of the largest is no variance: its asset's
#: weight would be 1e100 times another's, past what the solves can carry.
_VARIANCE_FLOOR: Final = 1e-200


def _to_rows(value: object) -> object:
    """Turn a 2-D array or a DataFrame into rows; leave anything else alone."""
    to_numpy = getattr(value, "to_numpy", None)
    array = to_numpy() if callable(to_numpy) else value
    if isinstance(array, np.ndarray) and array.ndim == 2:  # noqa: PLR2004
        if array.size > ASSETS_MAX * ASSETS_MAX:
            msg = f"a matrix may hold at most {ASSETS_MAX} x {ASSETS_MAX} entries"
            raise ValueError(msg)
        return array.tolist()
    return value


def _to_window(value: object) -> object:
    """Turn a 2-D array or a DataFrame of returns into rows of periods."""
    to_numpy = getattr(value, "to_numpy", None)
    array = to_numpy() if callable(to_numpy) else value
    if isinstance(array, np.ndarray) and array.ndim == 2:  # noqa: PLR2004
        if array.size > PERIODS_MAX * ASSETS_MAX:
            msg = (
                f"a window may hold at most {PERIODS_MAX} periods of {ASSETS_MAX} "
                "returns"
            )
            raise ValueError(msg)
        return array.tolist()
    return value


_MATRIX_INPUT: Final = BeforeValidator(_to_rows)
_WINDOW_INPUT: Final = BeforeValidator(_to_window)

_CovarianceRow = Annotated[
    tuple[Annotated[Ratio, Field(ge=-COVARIANCE_MAX, le=COVARIANCE_MAX)], ...],
    Field(min_length=1, max_length=ASSETS_MAX),
    ARRAY_INPUT,
]
_CorrelationRow = Annotated[
    tuple[Annotated[Correlation, Field(ge=-1.0, le=1.0)], ...],
    Field(min_length=1, max_length=ASSETS_MAX),
    ARRAY_INPUT,
]

_ReturnRow = Annotated[
    tuple[Annotated[Return, Field(ge=-1.0, le=RETURN_MAX)], ...],
    Field(min_length=1, max_length=ASSETS_MAX),
    ARRAY_INPUT,
]

CovarianceMatrix = Annotated[tuple[_CovarianceRow, ...], _MATRIX_INPUT]
"""A square matrix of covariances of returns, as rows."""
CorrelationMatrix = Annotated[tuple[_CorrelationRow, ...], _MATRIX_INPUT]
"""A square matrix of correlations of returns, as rows."""
ReturnWindow = Annotated[tuple[_ReturnRow, ...], _WINDOW_INPUT]
"""Returns of the assets, as rows, one per period, each one value per asset."""


def window_field(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    """Return the ``Field`` of an optional window of 2 to PERIODS_MAX periods."""
    return Field(None, min_length=2, max_length=PERIODS_MAX, description=description)


def sample_covariance(rows: Sequence[Sequence[float]]) -> NDArray[np.float64]:
    """Return the sample covariance of a window of returns, divisor ``T - 1``.

    Raises
    ------
    DomainError
        If an asset's return is the same in every period: it has no variance.
    """
    returns = np.asarray(rows, dtype=np.float64)
    centred = returns - returns.mean(axis=0)
    matrix = (centred.T @ centred) / (len(returns) - 1)
    if np.any(np.diag(matrix) <= 0):
        msg = "an asset's return is the same in every period: it has no variance"
        raise DomainError(msg)
    return matrix


def matrix_field(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    """Return the ``Field`` of an optional square matrix of up to ASSETS_MAX rows."""
    return Field(None, min_length=1, max_length=ASSETS_MAX, description=description)


def square(rows: Sequence[Sequence[float]], size: int, what: str) -> str | None:
    """Return why ``rows`` is not a ``size`` x ``size`` matrix, or ``None``."""
    if len(rows) != size or any(len(row) != size for row in rows):
        return f"the {what} must be {size} x {size}, one row and column per asset"
    return None


def covariance(
    covariances: Sequence[Sequence[float]] | None,
    volatilities: Sequence[float] | None,
    correlations: Sequence[Sequence[float]] | None,
    *,
    definite: bool = True,
) -> NDArray[np.float64]:
    """Return the covariance matrix, checked symmetric and positive definite.

    It is ``covariances`` when given, else ``D R D`` for ``D`` the diagonal of
    ``volatilities`` and ``R`` the correlations, whose diagonal must be one.
    With ``definite=False`` a positive semidefinite matrix passes, as long as
    every asset has some variance.

    Raises
    ------
    DomainError
        If the matrix is not symmetric, a correlation matrix's diagonal is not
        one, or the matrix is not positive definite to working precision (or,
        with ``definite=False``, has a negative eigenvalue beyond rounding or
        an asset without variance).
    """
    if covariances is not None:
        matrix = np.asarray(covariances, dtype=np.float64)
        what = "covariance matrix"
    else:
        vols = np.asarray(volatilities, dtype=np.float64)
        corr = np.asarray(correlations, dtype=np.float64)
        if not np.all(np.diag(corr) == 1.0):
            msg = "a correlation matrix has ones on its diagonal"
            raise DomainError(msg)
        _symmetric(corr, "correlation matrix")
        matrix = corr * np.outer(vols, vols)
        what = "covariance matrix the volatilities and correlations make"
    _symmetric(matrix, what)
    matrix = (matrix + matrix.T) / 2
    # Eigenvalues of the matrix scaled to a largest entry of one: their ratio
    # is the scale-free test, and tiny entries cannot underflow it.
    scale = float(np.max(np.abs(matrix)))
    eigenvalues = np.linalg.eigvalsh(matrix / scale) if scale > 0 else np.zeros(1)
    smallest, largest = float(eigenvalues[0]), float(eigenvalues[-1])
    if not definite:
        if (
            largest <= 0
            or smallest < -largest * _SEMIDEFINITE
            or np.any(
                np.diag(matrix) <= _VARIANCE_FLOOR * float(np.max(np.diag(matrix)))
            )
        ):
            msg = (
                f"the {what} is not positive semidefinite with a variance for every "
                f"asset (smallest to largest eigenvalue "
                f"{smallest / largest if largest > 0 else 0.0:.3g})"
            )
            raise DomainError(msg)
        return matrix
    if largest <= 0 or smallest <= largest * _CONDITION_MIN:
        msg = (
            f"the {what} is not positive definite to working precision (smallest "
            f"to largest eigenvalue {smallest / largest if largest > 0 else 0.0:.3g}): "
            "some combination of the assets has no variance, and this model needs "
            "every one to have some"
        )
        raise DomainError(msg)
    return matrix


def _symmetric(matrix: NDArray[np.float64], what: str) -> None:
    scale = float(np.max(np.abs(matrix)))
    if float(np.max(np.abs(matrix - matrix.T))) > _SYMMETRY * scale:
        msg = f"the {what} is not symmetric"
        raise DomainError(msg)


def bounded(value: float, limit: float, what: str) -> float:
    """Return ``value`` if it is finite and at most ``limit`` in magnitude.

    Raises
    ------
    DomainError
        Otherwise: the matrix is so ill-conditioned that the answer leaves the
        output's bounds.
    """
    if not (math.isfinite(value) and abs(value) <= limit):
        msg = (
            f"the {what} is {value!r}, outside its bounds [-{limit:g}, {limit:g}]; "
            "the inputs have no representable answer (a covariance matrix close "
            "to singular, a near-equal pair of returns, or tiny variances)"
        )
        raise DomainError(msg)
    return value
