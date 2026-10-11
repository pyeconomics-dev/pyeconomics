# src/pyeconomics/models/international/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""International economics: the parity conditions between currencies.

The launch catalog's international entry, registered through the
``international`` entry point in the ``pyeconomics.models`` group.
"""

from pyeconomics.models.international.parity_conditions import parity_conditions

__all__ = ["parity_conditions"]
