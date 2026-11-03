# pyeconomics 1.0 preview

```{warning}
This is the **1.0 preview**, built from `main`. APIs may change.
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
worked example. The Python API, the `pyeconomics` command line ({doc}`cli`),
tabular exports and reproducibility bundles ({doc}`exports`), the local and
hosted REST API ({doc}`api`), the web app ({doc}`how-to/local-app`), the MCP
server for AI assistants ({doc}`mcp`) and an optional AI narrative of a result
({doc}`ai`) are available in this checkout.

**New here?** The {doc}`tutorials <tutorials/index>` take you from install to a
model, live data, the command line, the REST API, the local app and an AI
assistant. **Know what you want?** The {doc}`how-to guides <how-to/index>` get
results into pandas, R and Excel. **Studying?** The
{doc}`study paths <study-paths/index>` list our model pages by syllabus topic.
**Coming from 0.2.x?** Read the {doc}`migration guide <migration>`.

```{toctree}
:maxdepth: 2
:caption: Learn

installation
quickstart
tutorials/index
how-to/index
study-paths/index
migration
```

```{toctree}
:maxdepth: 2
:caption: Surfaces

cli
api
mcp
mcp-evaluations
ai
exports
```

```{toctree}
:maxdepth: 2
:caption: Data

data/index
data/bindings
data/keys
data/cache
data/international
data/research
data/research-finance
data/writing-a-provider
```

```{toctree}
:maxdepth: 2
:caption: Reference

conventions
results
reference/models/index
reference/providers/index
reference/concepts/index
reference/sources
problems
registry
autoapi/index
errata
notices
changelog
```

Educational and informational use only; not investment advice.
