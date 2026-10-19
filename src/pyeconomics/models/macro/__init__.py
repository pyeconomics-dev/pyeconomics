# src/pyeconomics/models/macro/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Macroeconomics: policy rules, r*, the output gap, growth, debt and recessions.

The launch catalog's live-data macro entries, registered through the ``macro``
entry point in the ``pyeconomics.models`` group. Each declares data bindings, so
``pyeconomics.bind`` fills its inputs from the catalog as of a date.
"""

from pyeconomics.models.macro.debt_dynamics import debt_dynamics
from pyeconomics.models.macro.neutral_rate import neutral_rate
from pyeconomics.models.macro.okun_law import okun_law
from pyeconomics.models.macro.output_gap import output_gap
from pyeconomics.models.macro.phillips_curve import phillips_curve
from pyeconomics.models.macro.policy_rule import policy_rule
from pyeconomics.models.macro.recession_probability import recession_probability
from pyeconomics.models.macro.solow_growth import solow_growth

__all__ = [
    "debt_dynamics",
    "neutral_rate",
    "okun_law",
    "output_gap",
    "phillips_curve",
    "policy_rule",
    "recession_probability",
    "solow_growth",
]
