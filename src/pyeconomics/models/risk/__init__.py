# src/pyeconomics/models/risk/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Risk: value-at-risk and expected shortfall, and backtests of VaR exceptions.

Each entry is registered through the ``risk`` entry point in the
``pyeconomics.models`` group.
"""

from pyeconomics.models.risk.value_at_risk import value_at_risk
from pyeconomics.models.risk.var_backtest import var_backtest

__all__ = ["value_at_risk", "var_backtest"]
