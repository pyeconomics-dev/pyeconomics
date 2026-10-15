# Installation

Python 3.12 or later is required. Request pre-releases explicitly:

```console
pip install --pre pyeconomics
```

The `1.0.0a1` catalog release is still being prepared. Until it is published,
the current preview code is available from a source checkout:

```console
git clone https://github.com/pyeconomics-dev/pyeconomics.git
cd pyeconomics
uv sync --locked
```

Use `uv run` for commands in the checkout. A plain `pip install pyeconomics`
continues to install 0.2.6; that release has a different API. See the
[stable documentation](https://pyeconomics.readthedocs.io/en/stable/).

The optional `pyeconomics[plot]` extra adds Plotly, and
`pyeconomics[keyring]` lets data sources read their keys from the operating
system's keyring (see [Keys and configuration](data/keys.md)). Polars and
PyArrow are optional table integrations, installed separately when needed.
