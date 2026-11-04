# docs/examples/corporate_cost_of_capital.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
A firm's cost of capital
========================

A firm pays for its money in two ways, and the blend of the two is the rate a
project has to beat. This script uses
:doc:`/reference/models/corporate/cost_of_capital` twice: the capital asset
pricing model gives the cost of equity, and that goes into the weighted average.
"""

import pyeconomics

equity = pyeconomics.run(
    "corporate.cost_of_capital",
    calculation="capm",
    risk_free_rate=0.03,
    equity_risk_premium=0.05,
    beta=1.2,
)
print(f"Cost of equity: {equity.outputs.cost_of_equity:.2%}")

# %%
# Interest is tax-deductible, so debt costs less after tax than its rate suggests.

blended = pyeconomics.run(
    "corporate.cost_of_capital",
    calculation="wacc",
    equity=600,
    debt=400,
    cost_of_equity=equity.outputs.cost_of_equity,
    cost_of_debt=0.06,
    tax_rate=0.25,
)
print(f"Weighted average cost of capital: {blended.outputs.wacc:.2%}")
