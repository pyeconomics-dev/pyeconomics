<p align="center">
  <img src="https://raw.githubusercontent.com/pyeconomics-dev/pyeconomics/main/docs/_static/brand/pyeconomics-banner.png" width="100%" alt="pyeconomics: Empowering Economic Insight">
</p>

# pyeconomics

<!-- mcp-name: io.github.pyeconomics-dev/pyeconomics -->

[![CI](https://github.com/pyeconomics-dev/pyeconomics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pyeconomics-dev/pyeconomics/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pyeconomics)](https://pypi.org/project/pyeconomics/)
[![Licence](https://img.shields.io/github/license/pyeconomics-dev/pyeconomics)](https://github.com/pyeconomics-dev/pyeconomics/blob/main/LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/pyeconomics-dev/pyeconomics/badge)](https://scorecard.dev/viewer/?uri=github.com/pyeconomics-dev/pyeconomics)

> **Status: 1.0.0b1 is a beta pre-release on PyPI.** Install explicitly with
> `pip install --pre pyeconomics==1.0.0b1` (Python 3.12 or later).
> Plain `pip install pyeconomics` still installs **0.2.6**, the stable release.
> Pre-releases carry no stability promise until 1.0.0.

pyeconomics provides 50 tested, cited economics and finance model
families across 13 domains: foundations, fixed income, derivatives,
international, equity, corporate, accounting, portfolio, performance, risk,
econometrics, macroeconomics and asset pricing. The data platform adds 31
providers, 171 catalog concepts and live bindings with real-time vintages.
Every model is served identically through the Python API, the `pyeconomics`
command line, the REST API (`pyeconomics serve`), the MCP server
(`pyeconomics mcp`) and tabular or reproducibility-bundle exports.
Typed inputs declare units and bounds; every result carries
a reproducible provenance manifest. Rates and percentages are decimals:
`0.05` means 5%.

Use the [1.0 documentation preview](https://pyeconomics.readthedocs.io/en/main/)
for formulas, assumptions and examples, and the
[beta release notes](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/releases/1.0.0b1.md)
for the shipped surfaces and known limitations. See the
[CLI guide](https://pyeconomics.readthedocs.io/en/main/cli.html),
[REST API guide](https://pyeconomics.readthedocs.io/en/main/api.html),
[MCP server guide](https://pyeconomics.readthedocs.io/en/main/mcp.html),
[exports guide](https://pyeconomics.readthedocs.io/en/main/exports.html),
[AI narrative guide](https://pyeconomics.readthedocs.io/en/main/ai.html),
[data guide](https://pyeconomics.readthedocs.io/en/main/data/index.html) and
[keys guide](https://pyeconomics.readthedocs.io/en/main/data/keys.html) to get
started. Install optional econometrics, plotting, REST API and MCP support
with `pip install --pre "pyeconomics[econometrics,plot,server,mcp]==1.0.0b1"`,
or run the MCP server directly with
`uvx --from "pyeconomics[mcp]==1.0.0b1" pyeconomics mcp`.

This beta replaces the 0.2.x API and adds the command line, exports and
reproducibility bundles, REST API, MCP server and optional AI narrative on top
of the model engine and data platform. The web app arrives in Phase 5; the
[project roadmap](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/roadmap/ROADMAP.md)
and [architecture decisions](https://github.com/pyeconomics-dev/pyeconomics/tree/main/docs/adr)
record that plan. Keep legacy workloads in a separate environment.

## pyeconomics 0.2.x

0.2.6 is the current stable release of the 0.2.x line: four monetary-policy
rules over FRED data.

- It is MIT-licensed. Its source lives on the
  [`legacy/0.2.x`](https://github.com/pyeconomics-dev/pyeconomics/tree/legacy/0.2.x)
  branch, and its documentation at <https://pyeconomics.readthedocs.io/>.
- It receives security fixes only, and reaches end of life when 1.0.0 is
  released. Pins such as `pyeconomics<1` keep working.
- 0.2.0 to 0.2.5 log the FRED API key at DEBUG level. Upgrade to 0.2.6 and
  rotate any key those versions used: see advisory
  [GHSA-j6rp-vwwv-jrr8](https://github.com/pyeconomics-dev/pyeconomics/security/advisories/GHSA-j6rp-vwwv-jrr8).

## Not to be confused with

This project is not [`davidrpugh/pyeconomics`](https://github.com/davidrpugh/pyeconomics)
(computational-economics course code from 2013–14) or
[pyecon.org](https://pyecon.org/) (a site teaching Python for economics). The
three share only the name.

## Contributing and security

- [CONTRIBUTING](https://github.com/pyeconomics-dev/pyeconomics/blob/main/CONTRIBUTING.md):
  setup, DCO sign-off, commit conventions and the model definition of done.
- [SECURITY](https://github.com/pyeconomics-dev/pyeconomics/blob/main/SECURITY.md):
  report a vulnerability privately, never in a public issue.
- [Code of Conduct](https://github.com/pyeconomics-dev/pyeconomics/blob/main/CODE_OF_CONDUCT.md).
- [Changelog](https://github.com/pyeconomics-dev/pyeconomics/blob/main/CHANGELOG.md).

## Licence

From 1.0, pyeconomics is licensed under the
[Apache License 2.0](https://github.com/pyeconomics-dev/pyeconomics/blob/main/LICENSE);
see also [NOTICE](https://github.com/pyeconomics-dev/pyeconomics/blob/main/NOTICE).
Releases up to and including 0.2.x remain MIT-licensed.

## Notices

As is; not investment advice. pyeconomics is for educational and informational
use only, and is not registered with any regulator.

<!-- Keep the CFA notice on one line: it is quoted verbatim from ROADMAP §5. -->
CFA® and Chartered Financial Analyst® are trademarks owned by CFA Institute. pyeconomics is not affiliated with, endorsed by, or a Prep Provider of CFA Institute.
