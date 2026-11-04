# docs/examples/accounting_dupont.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
Taking apart a return on equity
===============================

Two firms can show the same return on equity for different reasons. The DuPont
identity splits it into margin, asset turnover and leverage. This script runs
:doc:`/reference/models/accounting/financial_ratios` on the figures of a made-up
firm.
"""

import pyeconomics

firm = pyeconomics.run(
    "accounting.financial_ratios",
    current_assets=200,
    inventory=50,
    prepayments=10,
    cash=40,
    marketable_securities=10,
    current_liabilities=100,
    revenue=1000,
    cost_of_goods_sold=600,
    purchases=500,
    average_receivables=100,
    average_inventory=150,
    average_payables=100,
    average_assets=800,
    average_equity=400,
    total_assets=900,
    total_debt=300,
    equity=450,
    ebit=200,
    interest_expense=40,
    pretax_income=160,
    net_income=120,
).outputs

print(f"Net margin: {firm.net_margin:.1%}")
print(f"Asset turnover: {firm.asset_turnover:.2f}")
print(f"Financial leverage: {firm.financial_leverage:.2f}")
print(f"Return on equity: {firm.roe:.1%}")

# %%
# Multiplying the three gives the return on equity back:

print(f"{firm.net_margin * firm.asset_turnover * firm.financial_leverage:.1%}")
