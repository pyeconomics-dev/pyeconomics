# docs/wasm/time_value.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyeconomics==1.0.0b1"]
# ///
"""The time value of money, in the browser (scripts/docs/export_wasm.py)."""

import marimo

__generated_with = "0.25.2"
app = marimo.App(app_title="Time value of money")


@app.cell
def _():
    import marimo as mo

    import pyeconomics

    return mo, pyeconomics


@app.cell
def _(mo):
    mo.md(r"""
    # The time value of money

    This page runs entirely in your browser and needs no install. Python and
    pyeconomics load as WebAssembly, the numbers below are worked out on your
    machine, and nothing you type leaves the page.

    Money you will receive later is worth less than the same money today, because
    today's money could be earning a return in the meantime. Discounting turns a
    later sum, and any level payments on the way, into a single value now. Change
    a number and the answer follows.
    """)
    return


@app.cell
def _(mo):
    rate = mo.ui.number(
        start=0.0, stop=1.0, step=0.005, value=0.05, label="Rate per period"
    )
    periods = mo.ui.number(start=0, stop=600, step=1, value=10, label="Periods")
    payment = mo.ui.number(
        start=0, stop=1_000_000, step=10, value=0, label="Payment each period"
    )
    future_value = mo.ui.number(
        start=0, stop=1_000_000, step=10, value=100, label="Final sum"
    )
    mo.vstack([rate, periods, payment, future_value])
    return future_value, payment, periods, rate


@app.cell
def _(future_value, mo, payment, periods, pyeconomics, rate):
    result = pyeconomics.run(
        "foundations.time_value",
        calculation="present_value",
        rate=rate.value,
        periods=periods.value,
        payment=payment.value,
        future_value=future_value.value,
    )
    mo.md(f"**Present value:** {result.outputs.present_value:,.2f}")
    return


@app.cell
def _(mo):
    mo.md(r"""
    The model behind this page is `foundations.time_value`, and its
    [page in the reference](https://pyeconomics.readthedocs.io/en/main/reference/models/foundations/time_value.html)
    gives the formula and its sources. To use it on your own machine, see the
    [install tutorial](https://pyeconomics.readthedocs.io/en/main/tutorials/install.html).

    This example is educational, not investment advice.
    """)
    return


if __name__ == "__main__":
    app.run()
