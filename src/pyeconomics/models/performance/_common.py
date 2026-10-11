# src/pyeconomics/models/performance/_common.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the performance models share: series bounds and undefined results.

An output that is undefined while the others stand, such as a ratio over a zero
denominator, is ``None`` with a warning saying why (ADR-0008 decision 10);
:func:`optional` and :func:`ratio` produce it.
"""

from __future__ import annotations

import math
from typing import Final

import numpy as np
from pydantic import BeforeValidator

from pyeconomics.core import DomainError, annualized_log_return, warn

__all__ = [
    "MATRIX_INPUT",
    "MATRIX_ITEMS_MAX",
    "MONEY_IN",
    "RATIO_OUT",
    "RETURN_MAX",
    "SERIES_MAX",
    "annualize",
    "bounded",
    "optional",
    "ratio",
]

#: The most periods a series may hold: forty years of trading days.
SERIES_MAX: Final = 10_080
#: The largest amount of money an input may hold.
MONEY_IN: Final = 1e12
#: The highest return of one period (ADR-0008's default bound, 10,000%).
RETURN_MAX: Final = 100.0
#: The largest ratio in size: ADR-0008's default bound for a ratio.
RATIO_OUT: Final = 1e6
#: Relative rounding allowed past a bound before it counts as overflow.
_ROUNDING: Final = 1e-12
#: The most entries a 2-D array input may hold before it is converted.
MATRIX_ITEMS_MAX: Final = 60_000


def _to_rows(value: object) -> object:
    """Turn a 2-D array or a DataFrame into rows; leave anything else alone."""
    to_numpy = getattr(value, "to_numpy", None)
    array = to_numpy() if callable(to_numpy) else value
    if isinstance(array, np.ndarray) and array.ndim == 2:  # noqa: PLR2004
        if array.size > MATRIX_ITEMS_MAX:
            msg = f"a matrix may hold at most {MATRIX_ITEMS_MAX} entries"
            raise ValueError(msg)
        return array.tolist()
    return value


#: The before-validator that lets a matrix field take a 2-D NumPy array or a
#: DataFrame as well as a list of rows.
MATRIX_INPUT: Final = BeforeValidator(_to_rows)


def optional(value: float, low: float, high: float, name: str) -> float | None:
    """Return ``value`` if it is finite and within bounds; else warn and return None."""
    if not math.isfinite(value) or not (low <= value <= high):
        warn(
            "unrepresentable_result",
            f"the {name} is {value!r}, outside its bounds [{low:g}, {high:g}]",
        )
        return None
    return value


def ratio(
    numerator: float, denominator: float, name: str, limit: float = RATIO_OUT
) -> float | None:
    """Return a ratio, or None with a warning for a zero denominator or overflow."""
    if denominator == 0:
        warn("zero_denominator", f"the {name} has a zero denominator")
        return None
    return optional(numerator / denominator, -limit, limit, name)


def bounded(value: float, low: float, high: float, name: str) -> float:
    """Return ``value`` clamped into ``[low, high]`` if only rounding puts it out.

    Raises
    ------
    DomainError
        If it is further out: the inputs have no answer the bounds can hold.
    """
    slack = _ROUNDING * max(abs(low), abs(high))
    if not (math.isfinite(value) and low - slack <= value <= high + slack):
        msg = (
            f"the {name} is {value!r}, outside its bounds [{low:g}, {high:g}]; the "
            "inputs have no answer this model can represent"
        )
        raise DomainError(msg)
    return min(max(value, low), high)


def annualize(
    log_total: float, periods: float, periods_per_year: float | None, high: float
) -> float | None:
    """Return a log return compounded to a year, or None with a warning saying why.

    The log return (:func:`~pyeconomics.core.log_return`) is the input, not the
    compound return, so a long run of losses that rounds to -100% or of gains
    that overflows still annualizes to its true value.
    """
    if periods_per_year is None:
        warn(
            "not_annualized",
            "no periods_per_year was given, so the return is not annualized",
        )
        return None
    return optional(
        annualized_log_return(log_total, periods, periods_per_year),
        -1.0,
        high,
        "annualized return",
    )
