# docs/wasm/bond_price_duration.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyeconomics==1.0.0b1"]
# ///
"""A bond's price and duration, in the browser (scripts/docs/export_wasm.py)."""

import marimo

__generated_with = "0.25.2"
app = marimo.App(app_title="A bond's price and duration")


@app.cell
def _():
    import datetime as dt

    import marimo as mo

    import pyeconomics

    return dt, mo, pyeconomics


@app.cell
def _(mo):
    mo.md(r"""
    # A bond's price and duration

    This page runs entirely in your browser and needs no install. Python and
    pyeconomics load as WebAssembly, the numbers below are worked out on your
    machine, and nothing you type leaves the page.

    A bond's price is the value today of its coupons and its redemption, each
    discounted at the yield, so the two move in opposite directions. Duration
    says how far: it is the average time until the money comes back, and the
    longer that is, the more the price moves for a given change in the yield.
    Try a longer bond, or a smaller coupon, and watch it grow.
    """)
    return


@app.cell
def _(mo):
    coupon = mo.ui.number(
        start=0.0, stop=0.25, step=0.0025, value=0.045, label="Coupon rate"
    )
    yield_to_maturity = mo.ui.number(
        start=0.0, stop=0.25, step=0.0025, value=0.05, label="Yield to maturity"
    )
    years = mo.ui.number(start=1, stop=50, step=1, value=10, label="Years to maturity")
    mo.vstack([coupon, yield_to_maturity, years])
    return coupon, years, yield_to_maturity


@app.cell
def _(coupon, dt, mo, pyeconomics, years, yield_to_maturity):
    settlement = dt.date(2026, 1, 15)
    bond = {
        "settlement": settlement,
        "maturity": settlement.replace(year=settlement.year + years.value),
        "coupon_rate": coupon.value,
        "yield_to_maturity": yield_to_maturity.value,
    }
    price = pyeconomics.run(
        "fixed_income.bond_pricing", calculation="price_from_yield", **bond
    ).outputs
    duration = pyeconomics.run(
        "fixed_income.duration", calculation="macaulay_modified", **bond
    ).outputs
    change = -duration.modified_duration * price.full_price * 0.0001
    mo.md(
        f"""
        **Price per 100 of face value:** {price.flat_price:,.2f}

        **Macaulay duration:** {duration.macaulay_duration:,.2f} years

        **Modified duration:** {duration.modified_duration:,.2f}

        A rise of one hundredth of a percentage point in the yield moves the price
        by about {change:,.4f}.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    The coupons here are paid twice a year, and the bond settles on a coupon date,
    so it carries no accrued interest. The models behind this page are
    [`fixed_income.bond_pricing`](https://pyeconomics.readthedocs.io/en/main/reference/models/fixed_income/bond_pricing.html)
    and
    [`fixed_income.duration`](https://pyeconomics.readthedocs.io/en/main/reference/models/fixed_income/duration.html),
    whose pages give the formulas and their sources. To use them on your own
    machine, see the
    [install tutorial](https://pyeconomics.readthedocs.io/en/main/tutorials/install.html).

    This example is educational, not investment advice.
    """)
    return


if __name__ == "__main__":
    app.run()
