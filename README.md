<p align="center">
  <img src="https://raw.githubusercontent.com/pyeconomics-dev/pyeconomics/main/docs/_static/brand/pyeconomics-banner.png" width="100%" alt="pyeconomics: Empowering Economic Insight">
</p>

# pyeconomics

[![CI](https://github.com/pyeconomics-dev/pyeconomics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pyeconomics-dev/pyeconomics/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pyeconomics)](https://pypi.org/project/pyeconomics/)
[![Licence](https://img.shields.io/github/license/pyeconomics-dev/pyeconomics)](https://github.com/pyeconomics-dev/pyeconomics/blob/main/LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/pyeconomics-dev/pyeconomics/badge)](https://scorecard.dev/viewer/?uri=github.com/pyeconomics-dev/pyeconomics)

> **Status: pyeconomics 1.0 is in development.** `pip install pyeconomics`
> installs **0.2.6**, the current stable release. The 1.0 pre-releases install
> only when asked for, with `pip install --pre pyeconomics` or an exact version,
> and they carry no stability promise until 1.0.0.

pyeconomics 1.0 is being rebuilt from the ground up as an open platform of
economics and finance models: a registry of tested, cited models, each written
once and served identically to Python, a command line, a REST API, an MCP server
and a web app. Every result will carry a provenance manifest. It implements
formulas commonly covered in the CFA® Program curriculum, and the wider
economics, econometrics, risk and quant canon after them.

So far, the repository holds the 1.0 package skeleton, its toolchain, security
gate and release pipeline: there is nothing to use yet. The plan, phase by
phase, is in the
[project roadmap](https://github.com/pyeconomics-dev/pyeconomics/blob/main/docs/roadmap/ROADMAP.md),
and the decisions behind it are in the
[architecture decision records](https://github.com/pyeconomics-dev/pyeconomics/tree/main/docs/adr).

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
