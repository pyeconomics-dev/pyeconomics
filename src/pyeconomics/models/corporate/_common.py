# src/pyeconomics/models/corporate/_common.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Undefined partial results in corporate finance."""

from __future__ import annotations

import math

from pyeconomics.core import warn


def optional(value: float, limit: float, name: str) -> float | None:
    """Return a bounded result, or warn and return null."""
    if not math.isfinite(value) or abs(value) > limit:
        warn("unrepresentable_result", f"{name} is outside its output bounds")
        return None
    return value


def divide(numerator: float, denominator: float, name: str) -> float | None:
    """Return a ratio, warning on zero denominator or unrepresentable output."""
    if denominator == 0:
        warn("zero_denominator", f"{name} has a zero denominator")
        return None
    return optional(numerator / denominator, 1e6, name)
