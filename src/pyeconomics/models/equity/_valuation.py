# src/pyeconomics/models/equity/_valuation.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Shared annual DCF arithmetic for the equity domain."""

from __future__ import annotations

import math

from pyeconomics.core import (
    DomainError,
    growing_annuity_factor,
    growing_perpetuity_factor,
    growth_factor,
    present_value_factor,
)

MONEY_LIMIT = 1e15


def bounded(value: float) -> float:
    """Reject valuations outside the money output bounds."""
    if not math.isfinite(value) or abs(value) > MONEY_LIMIT:
        msg = "valuation is outside [-1e15, 1e15]; no representable result"
        raise DomainError(msg)
    return value


def dcf(first: float, rate: float, growth: float, years: int, terminal: float) -> float:
    """Discount the next cash flow and an optional high-growth stage.

    ``first`` is the flow at t=1, not t=0. With zero high-growth years,
    terminal growth applies after that first flow.
    """
    if rate <= terminal:
        growing_perpetuity_factor(rate, terminal)
    gap = rate - terminal
    if years == 0:
        return bounded(first / gap)
    stream = first * growing_annuity_factor(rate, growth, years)
    last = first * growth_factor(growth, years - 1)
    tail = (last / gap) * (1 + terminal) * present_value_factor(rate, years)
    return bounded(stream + tail)
