# docs/examples/fixed_income_bond_price.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
A bond's price and yield
========================

A bond's price and its yield are two ways of stating one fact, and each can be
worked out from the other. This script prices a ten-year bond with a 4.5% coupon
at three yields with :doc:`/reference/models/fixed_income/bond_pricing`, then
recovers the yield from a price.
"""

import datetime as dt

import pyeconomics

bond = {
    "settlement": dt.date(2026, 1, 15),
    "maturity": dt.date(2036, 1, 15),
    "coupon_rate": 0.045,
}

for yield_to_maturity in (0.04, 0.045, 0.05):
    priced = pyeconomics.run(
        "fixed_income.bond_pricing",
        calculation="price_from_yield",
        yield_to_maturity=yield_to_maturity,
        **bond,
    )
    print(f"At a yield of {yield_to_maturity:.1%}: {priced.outputs.flat_price:.3f}")

# %%
# At a yield equal to its coupon the bond is priced at par. Below it, the price
# is above par; above it, below. Going the other way gives the yield back:

solved = pyeconomics.run(
    "fixed_income.bond_pricing",
    calculation="yield_from_price",
    price=96.5,
    price_type="flat",
    **bond,
)
print(f"A price of 96.5 yields {solved.outputs.yield_to_maturity:.4%}")
