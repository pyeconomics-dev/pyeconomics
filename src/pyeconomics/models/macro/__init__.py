# src/pyeconomics/models/macro/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Macroeconomics: monetary-policy rules and the neutral rate of interest.

The launch catalog's live-data macro entries, registered through the ``macro``
entry point in the ``pyeconomics.models`` group. Each declares data bindings, so
``pyeconomics.bind`` fills its inputs from the catalog as of a date.
"""

from pyeconomics.models.macro.neutral_rate import neutral_rate
from pyeconomics.models.macro.policy_rule import policy_rule

__all__ = ["neutral_rate", "policy_rule"]
