# src/pyeconomics/models/derivatives/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Derivatives: forwards, swaps, and European and American options.

The five entries of the launch catalog's derivatives domain. Each is
registered through the ``derivatives`` entry point in the
``pyeconomics.models`` group. Their outputs are formula values for the inputs
given, not trading advice.
"""

from pyeconomics.models.derivatives.binomial_tree import binomial_tree
from pyeconomics.models.derivatives.black_scholes_merton import black_scholes_merton
from pyeconomics.models.derivatives.forwards import forwards
from pyeconomics.models.derivatives.futures_fx_options import futures_fx_options
from pyeconomics.models.derivatives.interest_rate_swap import interest_rate_swap

__all__ = [
    "binomial_tree",
    "black_scholes_merton",
    "forwards",
    "futures_fx_options",
    "interest_rate_swap",
]
