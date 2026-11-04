# docs/examples/equity_dividend_discount.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
Valuing a growing dividend
==========================

A share can be valued as the present value of its dividends. When they grow at a
steady rate forever, the sum has a closed form, the Gordon growth model. This
script runs :doc:`/reference/models/equity/dividend_discount` and shows how much
of the value rests on the growth assumption.
"""

import pyeconomics

for growth in (0.0, 0.02, 0.04, 0.06):
    gordon = pyeconomics.run(
        "equity.dividend_discount",
        calculation="gordon",
        next_dividend=2,
        required_return=0.1,
        growth=growth,
    )
    print(f"Growth of {growth:.0%}: {gordon.outputs.value:.2f}")

# %%
# The value climbs faster as growth nears the required return, and the formula
# has no answer once growth reaches it. That is a reason to treat a single
# number from this model with care.
