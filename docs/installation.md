# Installation

Python 3.12 or later is required:

```console
pip install pyeconomics
```

0.2.x, which has a different API, reached end of life with 1.0.0. Its
documentation stays at
[docs.pyeconomics.dev/en/v0.2.6](https://docs.pyeconomics.dev/en/v0.2.6/), and the
{doc}`migration guide <migration>` moves code from it.

The {doc}`install tutorial <tutorials/install>` covers pip, uv and pipx, and
lists every extra. To work from a source checkout:

```console
git clone https://github.com/pyeconomics-dev/pyeconomics.git
cd pyeconomics
uv sync --locked
```

Use `uv run` for commands in the checkout.

The optional `pyeconomics[plot]` extra adds Plotly, and
`pyeconomics[keyring]` lets data sources read their keys from the operating
system's keyring (see [Keys and configuration](data/keys.md)). Polars and
PyArrow are optional table integrations, installed separately when needed.
