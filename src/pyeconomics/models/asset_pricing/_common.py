# src/pyeconomics/models/asset_pricing/_common.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the asset-pricing models share: bounds, return series and matrices.

Every input is bounded: at most :data:`PERIODS_MAX` periods, :data:`ASSETS_MAX`
test assets and :data:`FACTORS_MAX` factors, so no input is an unbounded
workload. A matrix of returns arrives as rows, one per period (a list of lists,
a 2-D NumPy array or a DataFrame whose index is the dates), as the factor and
portfolio sets of the Ken French Data Library are laid out.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Final, Literal

import numpy as np
from pydantic import BeforeValidator, Field

from pyeconomics.core import Count, DomainError, ModelInputs, Ratio, Return
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

__all__ = [
    "ASSETS_MAX",
    "ESTIMATE_MAX",
    "FACTORS_MAX",
    "LAGS_MAX",
    "PERIODS_MAX",
    "RETURN_MAX",
    "CovarianceName",
    "FactorMatrix",
    "Inference",
    "ReturnMatrix",
    "ReturnSeries",
    "bounded",
    "excess",
    "matrix",
]

#: The most periods a series or a matrix holds: ten years of trading days, or
#: two centuries of months.
PERIODS_MAX: Final = 2_520
#: The most test assets (columns of a returns matrix).
ASSETS_MAX: Final = 100
#: The most factors (columns of a factors matrix).
FACTORS_MAX: Final = 10
#: The most Newey-West lags.
LAGS_MAX: Final = 100
#: A return per period, as a decimal, is within this of zero: 1,000%.
RETURN_MAX: Final = 10.0
#: Estimates beyond this come from a regressor or a cross-section that barely
#: varies; the models raise DomainError rather than report them.
ESTIMATE_MAX: Final = 1e9

type CovarianceName = Literal["classical", "hc1", "newey_west"]

_ReturnValue = Annotated[Return, Field(ge=-RETURN_MAX, le=RETURN_MAX)]
ReturnSeries = Annotated[tuple[_ReturnValue, ...], ARRAY_INPUT]
"""A tuple of returns per period, each within 1,000% of zero."""


def _to_rows(value: object) -> object:
    """Turn a 2-D array or a DataFrame into rows; leave anything else alone."""
    to_numpy = getattr(value, "to_numpy", None)
    array = to_numpy() if callable(to_numpy) else value
    if isinstance(array, np.ndarray) and array.ndim == 2:  # noqa: PLR2004
        if array.size > PERIODS_MAX * ASSETS_MAX:
            msg = f"a matrix may hold at most {PERIODS_MAX} rows of {ASSETS_MAX} values"
            raise ValueError(msg)
        return array.tolist()
    return value


_MATRIX_INPUT: Final = BeforeValidator(_to_rows)

_AssetRow = Annotated[
    tuple[_ReturnValue, ...],
    Field(min_length=1, max_length=ASSETS_MAX),
    ARRAY_INPUT,
]
_FactorRow = Annotated[
    tuple[_ReturnValue, ...],
    Field(min_length=1, max_length=FACTORS_MAX),
    ARRAY_INPUT,
]
ReturnMatrix = Annotated[tuple[_AssetRow, ...], _MATRIX_INPUT]
"""Returns of the test assets, as rows, one per period, each one value per asset."""
FactorMatrix = Annotated[tuple[_FactorRow, ...], _MATRIX_INPUT]
"""Returns of the factors, as rows, one per period, each one value per factor."""


class Inference(ModelInputs):
    """How a time-series regression's standard errors are computed."""

    covariance: CovarianceName = Field(
        "newey_west",
        description=(
            "Standard errors: 'newey_west' (heteroskedasticity and autocorrelation "
            "consistent), 'hc1' (heteroskedasticity consistent) or 'classical'"
        ),
    )
    lags: Count | None = Field(
        None,
        ge=0,
        le=LAGS_MAX,
        description=(
            "Newey-West lags; left out, Newey and West's rule floor(4 (n/100)^(2/9))"
        ),
    )


def matrix(rows: Sequence[Sequence[float]], what: str) -> NDArray[np.float64]:
    """Return ``rows`` as a matrix, refusing rows of unequal length (``ValueError``)."""
    widths = {len(row) for row in rows}
    if len(widths) != 1:
        msg = f"every row of the {what} holds one value per column; the rows differ"
        raise ValueError(msg)
    return np.asarray(rows, dtype=np.float64)


def excess(
    returns: NDArray[np.float64], risk_free: Sequence[float] | None
) -> NDArray[np.float64]:
    """Return the returns less the risk-free return of each period, if given.

    ``returns`` is a vector of periods or a matrix of periods by assets.
    """
    if risk_free is None:
        return returns
    rate = np.asarray(risk_free, dtype=np.float64)
    return returns - (rate[:, None] if returns.ndim == 2 else rate)  # noqa: PLR2004


def bounded(
    values: Sequence[float], what: str, limit: float = ESTIMATE_MAX
) -> tuple[float, ...]:
    """Return ``values`` if each is finite and within ``limit`` of zero.

    Raises
    ------
    DomainError
        Otherwise: the data cannot identify the estimate to any useful precision.
    """
    for value in values:
        if not (math.isfinite(value) and abs(value) <= limit):
            msg = (
                f"a {what} is {value!r}, beyond {limit:g} in size: a regressor or "
                "the cross-section of betas barely varies, so it is not identified "
                "to any useful precision"
            )
            raise DomainError(msg)
    return tuple(float(v) for v in values)


def ratio_bound(value: float, limit: float) -> Ratio:
    """Return ``value`` clamped into ``[-limit, limit]`` (for rounding at a bound)."""
    return max(-limit, min(limit, value))
