# docs/examples/macro_policy_rule.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
What a Taylor rule prescribes
=============================

A policy rule turns inflation and the state of the economy into a suggested
short-term interest rate. This script runs
:doc:`/reference/models/macro/policy_rule` on Taylor's 1993 rule for one set of
typed-in conditions, then over a forecast path.
"""

import pyeconomics

today = pyeconomics.run(
    "macro.policy_rule",
    calculation="taylor_1993",
    inflation=0.03,
    inflation_target=0.02,
    output_gap=0.01,
    neutral_real_rate=0.01,
).outputs

print(f"Prescribed rate: {today.prescribed_rate:.2%}")
print(f"From inflation: {today.inflation_gap_term:.2%}")
print(f"From the output gap: {today.resource_gap_term:.2%}")

# %%
# A forecast comes with a range, and so does the rule's prescription. Each path
# holds one figure a quarter: the central forecast, and the low and high ends of
# its range, for inflation and for the output gap.

path = pyeconomics.run(
    "macro.policy_rule",
    calculation="path",
    rule="taylor_1993",
    inflation_target=0.02,
    neutral_real_rate=0.01,
    inflation_path=[0.03, 0.028, 0.026, 0.024, 0.022],
    inflation_low_path=[0.027, 0.024, 0.022, 0.02, 0.019],
    inflation_high_path=[0.033, 0.032, 0.03, 0.028, 0.026],
    output_gap_path=[0.01, 0.008, 0.006, 0.004, 0.002],
    output_gap_low_path=[0.005, 0.002, 0.0, -0.002, -0.003],
    output_gap_high_path=[0.015, 0.013, 0.011, 0.009, 0.007],
)

# %%
# The band shows how far the rule's answer moves across that range. A rule is a
# benchmark for discussion, not a forecast of what a central bank will do.

path.plot()
