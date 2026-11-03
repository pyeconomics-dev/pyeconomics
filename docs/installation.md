# Installation

Python 3.12 or later is required. Request pre-releases explicitly:

```console
pip install --pre pyeconomics
```

A plain `pip install pyeconomics` continues to install 0.2.6 until 1.0.0 is
released; that release has a different API. See the
[stable documentation](https://pyeconomics.readthedocs.io/en/stable/), and the
{doc}`migration guide <migration>` to move from it.

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
