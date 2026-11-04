# docs/examples/asset_pricing_factor_loadings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
An asset's exposure to the market
=================================

The capital asset pricing model explains an asset's excess return by its exposure
to the market, and an alpha is what that leaves over. This script runs
:doc:`/reference/models/asset_pricing/factor_regression` on ten months of made-up
returns, then reads the expected return off the security market line.
"""

import pyeconomics

regression = pyeconomics.run(
    "asset_pricing.factor_regression",
    calculation="capm",
    returns=[0.021, -0.013, 0.034, 0.008, -0.022, 0.015, 0.027, -0.004, 0.012, 0.019],
    risk_free=[
        0.004,
        0.004,
        0.004,
        0.0045,
        0.0045,
        0.0045,
        0.0042,
        0.0042,
        0.0041,
        0.0041,
    ],
    market=[0.018, -0.02, 0.03, 0.006, -0.025, 0.012, 0.022, -0.006, 0.009, 0.016],
    periods_per_year=12,
    market_premium=0.005,
    risk_free_rate=0.004,
).outputs

print(f"Market beta: {regression.market_beta:.2f}")
print(f"Alpha a year: {regression.alpha_annualized:.2%}")
print(f"R-squared: {regression.r_squared:.3f}")
print(f"Expected return a month: {regression.expected_return:.2%}")

# %%
# With ten observations the alpha is mostly noise: its t-statistic is
# printed below, and the sample could not tell it from zero.

print(f"Alpha's t-statistic: {regression.alpha_t_statistic:.2f}")
