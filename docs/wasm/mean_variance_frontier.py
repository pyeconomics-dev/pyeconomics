# docs/wasm/mean_variance_frontier.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyeconomics==1.0.0b1"]
# ///
"""A mean-variance frontier, in the browser (scripts/docs/export_wasm.py)."""

import marimo

__generated_with = "0.25.2"
app = marimo.App(app_title="A mean-variance frontier")


@app.cell
def _():
    import json

    import marimo as mo

    import pyeconomics

    return json, mo, pyeconomics


@app.cell
def _(mo):
    mo.md(r"""
    # A mean-variance frontier

    This page runs entirely in your browser and needs no install. Python and
    pyeconomics load as WebAssembly, the numbers below are worked out on your
    machine, and nothing you type leaves the page.

    Mixing assets that do not move together gives a portfolio with less risk than
    the average of its parts. For each target return there is one mix with the
    smallest volatility, and those mixes trace the frontier Harry Markowitz
    described in 1952. Change what you assume about three assets below, and see
    how it moves. The numbers are made up, and short sales are allowed.
    """)
    return


@app.cell
def _(mo):
    def share(value, label):
        return mo.ui.number(start=0.0, stop=1.0, step=0.01, value=value, label=label)

    expected = [
        share(0.08, "Expected return A"),
        share(0.12, "Expected return B"),
        share(0.15, "Expected return C"),
    ]
    volatility = [
        share(0.15, "Volatility A"),
        share(0.20, "Volatility B"),
        share(0.25, "Volatility C"),
    ]
    assets = mo.ui.array(expected + volatility)
    mo.hstack([mo.vstack(assets[:3]), mo.vstack(assets[3:])], justify="start")
    return (assets,)


@app.cell
def _(assets, mo, pyeconomics):
    frontier = pyeconomics.run(
        "portfolio.mean_variance",
        calculation="frontier",
        expected_returns=assets.value[:3],
        volatilities=assets.value[3:],
        correlations=[[1.0, 0.3, 0.2], [0.3, 1.0, 0.5], [0.2, 0.5, 1.0]],
        points=15,
    ).outputs
    mo.md(
        f"""
        **Minimum-variance portfolio:** a return of
        {frontier.minimum_variance_return:.2%} at a volatility of
        {frontier.minimum_variance_volatility:.2%}.
        """
    )
    return (frontier,)


@app.cell
def _(frontier, json):
    class Chart:
        """A Vega-Lite chart, which marimo's page draws with what it already has."""

        def __init__(self, spec):
            self.spec = spec

        def _mime_(self):
            return "application/vnd.vegalite.v5+json", json.dumps(self.spec)

    Chart(
        {
            "title": "The frontier",
            "width": 480,
            "height": 300,
            "data": {
                "values": [
                    {"volatility": volatility, "expected return": target}
                    for volatility, target in zip(
                        frontier.volatilities, frontier.target_returns, strict=True
                    )
                ]
            },
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {
                    "field": "volatility",
                    "type": "quantitative",
                    "axis": {"format": ".0%"},
                    "scale": {"zero": False},
                },
                "y": {
                    "field": "expected return",
                    "type": "quantitative",
                    "axis": {"format": ".1%"},
                    "scale": {"zero": False},
                },
            },
        }
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    The correlations stay fixed here: 0.3 between A and B, 0.2 between A and C and
    0.5 between B and C. The model behind this page is
    [`portfolio.mean_variance`](https://pyeconomics.readthedocs.io/en/main/reference/models/portfolio/mean_variance.html),
    whose page gives the formulas and their sources. To use it on your own machine,
    see the
    [install tutorial](https://pyeconomics.readthedocs.io/en/main/tutorials/install.html).

    This example is educational, not investment advice, and no portfolio here is a
    suggestion to hold it.
    """)
    return


if __name__ == "__main__":
    app.run()
