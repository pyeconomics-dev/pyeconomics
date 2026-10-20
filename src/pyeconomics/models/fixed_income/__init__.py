# src/pyeconomics/models/fixed_income/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Fixed income: bond prices and yields, money markets, curves, duration, credit.

The launch catalog's fixed-income domain: Phase 2's six entries, built on the
date layer in :mod:`pyeconomics.core`, and Phase 3's Nelson-Siegel and Svensson
curves and binomial interest-rate tree. Each is registered through the
``fixed_income`` entry point in the ``pyeconomics.models`` group.
"""

from pyeconomics.models.fixed_income.bond_pricing import bond_pricing
from pyeconomics.models.fixed_income.convexity import convexity
from pyeconomics.models.fixed_income.credit_spread import credit_spread
from pyeconomics.models.fixed_income.curve_bootstrap import curve_bootstrap
from pyeconomics.models.fixed_income.curve_fitting import curve_fitting
from pyeconomics.models.fixed_income.duration import duration
from pyeconomics.models.fixed_income.interest_rate_tree import interest_rate_tree
from pyeconomics.models.fixed_income.money_market import money_market

__all__ = [
    "bond_pricing",
    "convexity",
    "credit_spread",
    "curve_bootstrap",
    "curve_fitting",
    "duration",
    "interest_rate_tree",
    "money_market",
]
