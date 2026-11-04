# docs/examples/international_forward_rate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
A forward exchange rate
=======================

If you can borrow in one currency, lend in another and fix the exchange rate
today, the forward rate has to cancel the difference in interest rates, or there
is a free profit. This script runs
:doc:`/reference/models/international/parity_conditions` on covered interest
parity.
"""

import pyeconomics

forward = pyeconomics.run(
    "international.parity_conditions",
    calculation="covered_interest_parity",
    spot=0.75,
    quote_rate=0.01,
    base_rate=0.03,
    years=2,
    compounding="continuous",
).outputs

print(f"Two-year forward rate: {forward.forward_rate:.4f}")
print(f"Forward points: {forward.forward_points:.4f}")

# %%
# The base currency has the higher interest rate, so it trades at a forward
# discount: the rate for delivery in two years is below the spot rate of 0.75.
