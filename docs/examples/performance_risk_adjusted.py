# docs/examples/performance_risk_adjusted.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
Measuring return against risk
=============================

A higher return means little if it took more risk to earn it. This script runs
:doc:`/reference/models/performance/risk_adjusted` on twelve months of made-up
fund and benchmark returns, and prints a few of the ratios it computes.
"""

import pyeconomics

measures = pyeconomics.run(
    "performance.risk_adjusted",
    returns=[
        0.021,
        -0.013,
        0.034,
        0.008,
        -0.022,
        0.015,
        0.027,
        -0.005,
        0.012,
        0.019,
        -0.031,
        0.024,
    ],
    benchmark_returns=[
        0.018,
        -0.010,
        0.029,
        0.011,
        -0.025,
        0.012,
        0.022,
        -0.002,
        0.010,
        0.016,
        -0.028,
        0.020,
    ],
    risk_free_returns=[0.002] * 12,
    periods_per_year=12,
).outputs

print(f"Sharpe ratio: {measures.sharpe_ratio:.2f}")
print(f"Sortino ratio: {measures.sortino_ratio:.2f}")
print(f"Beta: {measures.beta:.2f}")
print(f"Information ratio: {measures.information_ratio:.2f}")
print(f"Maximum drawdown: {measures.max_drawdown:.2%}")

# %%
# Twelve observations are far too few to tell skill from luck, which is why the
# card lists small samples among this model's limitations.
