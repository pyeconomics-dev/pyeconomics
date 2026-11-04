# docs/examples/foundations_loan_schedule.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
Paying off a loan
=================

A loan repaid in equal payments pays mostly interest at first and mostly
principal at the end, because interest falls on what is still owed. This script
builds the schedule of a three-year loan of 10,000 at 0.5% a month with
:doc:`/reference/models/foundations/time_value`.
"""

import pyeconomics

loan = pyeconomics.run(
    "foundations.time_value",
    calculation="amortization",
    principal=10_000,
    rate=0.005,
    periods=36,
)
print(f"Level payment: {loan.outputs.level_payment:,.2f}")
print(f"Total interest: {loan.outputs.total_interest:,.2f}")

# %%
# The first payment is split very differently from the last:

schedule = loan.outputs
for index in (0, -1):
    print(
        f"Payment {schedule.period[index]}: "
        f"{schedule.interest[index]:,.2f} interest, "
        f"{schedule.principal[index]:,.2f} principal"
    )

# %%
# The balance falls slowly, then faster, as more of each payment goes to principal.

loan.plot()
