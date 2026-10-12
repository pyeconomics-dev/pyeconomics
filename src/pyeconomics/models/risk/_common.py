# src/pyeconomics/models/risk/_common.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the risk models share: confidence levels, horizons, series and bounds.

A loss is positive: a value-at-risk of ``0.02`` is a loss of 2% of the
position's value. Each bound below is sized so that the largest valid input
stays inside the outputs' bounds; where an expansion or a near-zero density can
still leave them, :func:`bounded` raises :class:`~pyeconomics.core.DomainError`
and the model lists the case in its limitations (ADR-0008 decision 10).
"""

from __future__ import annotations

import math
from typing import Any, Final

from pydantic import Field

from pyeconomics.core import DomainError

__all__ = [
    "CONFIDENCE_MAX",
    "CONFIDENCE_MIN",
    "HORIZON_MAX",
    "LOSS_MAX",
    "POSITION_MAX",
    "SERIES_MAX",
    "bounded",
    "confidence_field",
    "horizon_field",
    "position_field",
]

#: The confidence levels a VaR or a backtest may use. 99.99% leaves one
#: observation in ten thousand in the tail.
CONFIDENCE_MIN: Final = 0.5
CONFIDENCE_MAX: Final = 0.9999
#: The longest horizon, in periods: four years of trading days.
HORIZON_MAX: Final = 1_000.0
#: The most observations a return, exception or P&L series may hold: forty
#: years of trading days.
SERIES_MAX: Final = 10_080
#: The largest loss, as a decimal of the position. A return of 100 (the default
#: bound) over a horizon of 1,000 periods, at 99.99%, is a loss of about 12,800.
LOSS_MAX: Final = 1e5
#: The largest position value, so that a loss in money stays within the default
#: money bound of 1e15.
POSITION_MAX: Final = 1e10


def confidence_field(default: float = 0.99) -> Any:  # noqa: ANN401 - pydantic's Field
    """Return the ``Field`` of a one-tailed confidence level."""
    return Field(
        default,
        ge=CONFIDENCE_MIN,
        le=CONFIDENCE_MAX,
        description="One-tailed confidence level, such as 0.99",
    )


def horizon_field() -> Any:  # noqa: ANN401 - pydantic's Field
    """Return the ``Field`` of a horizon in periods of the inputs."""
    return Field(
        1.0,
        ge=1.0,
        le=HORIZON_MAX,
        description="Horizon in periods of the returns, such as 10 days",
    )


def position_field() -> Any:  # noqa: ANN401 - pydantic's Field
    """Return the ``Field`` of the position value that turns decimals into money."""
    return Field(
        1.0,
        gt=0,
        le=POSITION_MAX,
        description="Position value; the default of 1 makes the amounts the decimals",
    )


def bounded(value: float, low: float, high: float, what: str) -> float:
    """Return ``value`` if it is finite and within ``[low, high]``.

    Raises
    ------
    DomainError
        Otherwise, naming the output and its bounds.
    """
    if not (math.isfinite(value) and low <= value <= high):
        msg = (
            f"the {what} is {value!r}, outside its bounds [{low:g}, {high:g}]; "
            "the inputs have no answer this model can represent"
        )
        raise DomainError(msg)
    return value
