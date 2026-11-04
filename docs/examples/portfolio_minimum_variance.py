# docs/examples/portfolio_minimum_variance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
The portfolio with the least risk
=================================

Assets that do not move in step partly cancel each other's swings. This script
asks :doc:`/reference/models/portfolio/mean_variance` for the mix of three
made-up assets with the smallest volatility. Short sales are allowed, and the
inputs are assumptions, not estimates.
"""

import pyeconomics

assets = {
    "expected_returns": [0.08, 0.12, 0.15],
    "volatilities": [0.15, 0.20, 0.25],
    "correlations": [[1.0, 0.3, 0.2], [0.3, 1.0, 0.5], [0.2, 0.5, 1.0]],
}

least_risk = pyeconomics.run(
    "portfolio.mean_variance", calculation="minimum_variance", **assets
).outputs

print("Weights:", [round(weight, 3) for weight in least_risk.weights])
print(f"Expected return: {least_risk.expected_return:.2%}")
print(f"Volatility: {least_risk.volatility:.2%}")

# %%
# The result is less volatile than any one of the three, which is the whole
# argument for diversifying. See the
# :doc:`portfolio tutorial </tutorials/finance/portfolio-mathematics>` for the
# rest of the frontier.
