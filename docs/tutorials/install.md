# Install pyeconomics

This lesson puts pyeconomics on your machine and proves it works. It takes about
five minutes. You need Python 3.12 or later; check with `python --version`.

```{note}
1.0 is in pre-release, so each command below asks for pre-releases by name
(`--pre`, or `--prerelease allow` in uv). Without it, `pip install pyeconomics`
gives you 0.2.6, which has a different API.
```

## Choose how to install

**To use it in your own Python code,** install it into your project's virtual
environment with [pip](https://pip.pypa.io/):

```text
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install --pre pyeconomics
```

**If your project uses [uv](https://docs.astral.sh/uv/),** add it there:

```text
uv add --prerelease allow pyeconomics
```

**To use only the command line,** install it as a tool of its own, kept apart
from your projects, with [pipx](https://pipx.pypa.io/) or uv:

```text
pipx install --pre pyeconomics
uv tool install --prerelease allow pyeconomics
```

## Check that it works

Ask the command line for its version:

```console
$ pyeconomics --version
```

Then run a model from Python. Fifty model families come with the package:

```python
>>> import pyeconomics
>>> result = pyeconomics.run(
...     "foundations.time_value",
...     calculation="present_value",
...     rate=0.05,
...     periods=10,
...     future_value=100,
... )
>>> round(result.outputs.present_value, 2)
61.39
```

100 received in ten years, at 5% a year, is worth 61.39 today. If you see that
number, pyeconomics is installed.

## Add what you need

The core package holds every model that needs nothing more, the data layer and
the command line. Extras add the rest. Ask for them in square brackets, such as
`pip install --pre "pyeconomics[server,keyring]"`:

| Extra | What it adds |
|-------|--------------|
| `server` | The REST API, through `pyeconomics serve` |
| `app` | The web app at `/` of `pyeconomics serve`, with what `server` brings |
| `mcp` | The MCP server for AI assistants |
| `keyring` | Stores data sources' keys in your operating system's keyring |
| `plot` | Charts of a result, with Plotly |
| `econometrics` | The OLS, GARCH and time-series models, with statsmodels and arch |
| `sdmx` | The international sources that speak SDMX |
| `yfinance` | Market prices from Yahoo Finance, for personal use |
| `ai` | The optional AI narrative of a result, on your own key |
| `all` | Every extra above but `app` and `ai` |

Parquet and Arrow exports need [pyarrow](https://arrow.apache.org/docs/python/),
which pyeconomics never installs for you: add it with `pip install pyarrow`.

## Next

{doc}`first-model` runs a model and reads what comes back.
