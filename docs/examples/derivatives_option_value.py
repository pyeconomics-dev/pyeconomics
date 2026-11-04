# docs/examples/derivatives_option_value.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""
An option's value and its sensitivities
=======================================

The Black-Scholes-Merton formula values a European option from the price of the
asset, the strike, the time left, a risk-free rate and the volatility. This
script runs :doc:`/reference/models/derivatives/black_scholes_merton` on a
six-month call, then goes backwards, from a price to the volatility it implies.
"""

import pyeconomics

call = pyeconomics.run(
    "derivatives.black_scholes_merton",
    calculation="price",
    option_type="call",
    spot=42,
    strike=40,
    years=0.5,
    risk_free_rate=0.1,
    volatility=0.2,
)
print(f"Value: {call.outputs.price:.2f}")
print(f"Delta: {call.outputs.delta:.3f}")
print(f"Vega: {call.outputs.vega:.3f}")

# %%
# Delta says how far the value moves with the asset. Traders usually quote the
# volatility a market price implies rather than the price itself:

implied = pyeconomics.run(
    "derivatives.black_scholes_merton",
    calculation="implied_volatility",
    option_type="call",
    spot=42,
    strike=40,
    years=0.5,
    risk_free_rate=0.1,
    option_price=call.outputs.price,
)
print(f"Implied volatility: {implied.outputs.implied_volatility:.2%}")
