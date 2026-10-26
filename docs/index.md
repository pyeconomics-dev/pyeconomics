# pyeconomics 1.0 preview

```{warning}
This is the **1.0 alpha preview**, built from `main`. APIs may change.
For the current stable release, use the [0.2.6 documentation](https://pyeconomics.readthedocs.io/en/stable/).
```

pyeconomics is an open library of economics and finance models with typed
inputs, cited formulas and reproducible results. The preview includes 50
model families across 13 domains: foundations, fixed income, derivatives,
international, equity, corporate, accounting, portfolio, performance, risk,
econometrics, macroeconomics and asset pricing. The data platform provides 31
sources, 171 catalog concepts and live bindings with real-time vintages.
OLS, GARCH and time-series models require the `econometrics` extra; result
charts use the `plot` extra.
Each has a generated card with units, bounds, assumptions, limitations and a
worked example. The Python API, the `pyeconomics` command line, the local
REST API and the MCP server for AI assistants are available in this checkout;
the web app follows.

```{toctree}
:maxdepth: 2

installation
quickstart
cli
api
mcp
mcp-evaluations
tutorials/first-model
conventions
results
data/index
data/bindings
data/keys
data/cache
data/international
data/research
data/research-finance
data/writing-a-provider
reference/models/index
reference/providers/index
reference/concepts/index
reference/sources
problems
registry
exports
autoapi/index
errata
notices
changelog
```

Educational and informational use only; not investment advice.
