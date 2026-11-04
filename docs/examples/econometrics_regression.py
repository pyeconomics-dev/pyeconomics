# docs/examples/econometrics_regression.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
A regression and its residuals
==============================

Ordinary least squares fits a line through a cloud of points, and the residuals
say whether a line was the right thing to fit. This script runs
:doc:`/reference/models/econometrics/ols` on a small made-up sample. It needs the
``econometrics`` extra.
"""

import pyeconomics

regression = pyeconomics.run(
    "econometrics.ols",
    response=[1.1, 2.3, 2.8, 4.2, 4.9, 6.3, 6.8, 8.1],
    design=[[1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0], [8.0]],
    names=["x"],
)
outputs = regression.outputs

for name, coefficient, error in zip(
    outputs.names, outputs.coefficients, outputs.standard_errors, strict=True
):
    print(f"{name}: {coefficient:.3f} (standard error {error:.3f})")
print(f"R-squared: {outputs.r_squared:.3f}")

# %%
# Plotting the residuals against the fitted values is the first check on a fit.
# A pattern here would mean the line has missed something; a shapeless scatter
# around zero is what you want.

regression.plot()
