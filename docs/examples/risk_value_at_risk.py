# docs/examples/risk_value_at_risk.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
Value-at-risk, two ways
=======================

Value-at-risk states a loss that a position should exceed only rarely over a
given horizon. This script runs :doc:`/reference/models/risk/value_at_risk` on a
position of one million, first under a normal distribution, then allowing for a
fat left tail.
"""

import pyeconomics

position = {
    "volatility": 0.012,
    "confidence": 0.99,
    "horizon": 1,
    "position_value": 1_000_000,
}

normal = pyeconomics.run(
    "risk.value_at_risk", calculation="parametric", mean=0, **position
).outputs
adjusted = pyeconomics.run(
    "risk.value_at_risk",
    calculation="cornish_fisher",
    mean=0,
    skewness=-0.5,
    excess_kurtosis=2,
    **position,
).outputs

print(f"Normal: {normal.value_at_risk_amount:,.0f}")
print(f"Cornish-Fisher: {adjusted.value_at_risk_amount:,.0f}")

# %%
# Allowing for skew and fat tails raises the figure. Expected shortfall goes
# further, and asks how large the loss is on the days the limit is passed:

print(f"Normal expected shortfall: {normal.expected_shortfall_amount:,.0f}")
