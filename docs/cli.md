# The command line

`pyeconomics` runs every registered model and reads every data source from a
shell, so a script, R (`system2`) or Excel Power Query can use them. A model
runs through the same path as the Python API, and `--format json` prints the
same canonical result `Result.to_json()` gives, byte for byte, followed by one
newline. The command line comes with the core package: no extra is needed.

## Installation

Install it as a tool, isolated from your projects, with
[pipx](https://pipx.pypa.io/) or [uv](https://docs.astral.sh/uv/):

```text
pipx install --pre pyeconomics
uv tool install --prerelease allow pyeconomics
```

`--pre` and `--prerelease allow` are needed while 1.0 is in pre-release. To
store providers' keys in the OS keyring, install the extra too:
`pipx install --pre "pyeconomics[keyring]"`.

```console
$ pyeconomics --version
```

## The commands

| Command | What it does |
|---------|--------------|
| `models list [--domain D]` | List the registered models |
| `models search TEXT [--limit N]` | Search models by id, title, tags, domain and summary |
| `models describe ID [--format markdown\|json]` | Print a model's card, or its full description |
| `models run ID [OPTIONS]` | Run a model; its inputs are options |
| `data search TEXT [--limit N]` | Search catalog concepts, then providers' series |
| `data get TARGET [--start] [--end] [--as-of] [--vintage] [--provider]` | Get a concept's or a series' data |
| `data describe TARGET` | Describe a concept, a series or a provider |
| `data vintages TARGET` | List the dates a series changed |
| `data sources [--check-keys]` | List the providers with their licences and keys |
| `keys set PROVIDER [--stdin]` | Store a provider's key in the OS keyring |
| `keys list` | Name where each key would be read from |
| `keys delete PROVIDER` | Delete a key from the OS keyring |
| `cache ls [--provider P]`, `cache info`, `cache clear [--provider P]`, `cache path` | Inspect and clear the data cache |
| `registry export --out DIR [--no-figures]` | Write `DIR/registry.json` ({doc}`registry`) |
| `completion SHELL`, `--install-completion` | Shell completion |

Every command takes `--help`, and `--debug` (anywhere on the line) adds a
traceback to a failure. A *target* is a catalog concept id
(`us.unemployment.rate`) or a provider series (`fred:UNRATE`), never a URL.

```console
$ pyeconomics --help
$ pyeconomics models list --domain fixed_income
$ pyeconomics models search "present value annuity" --limit 3
$ pyeconomics models describe fixed_income.bond_pricing
```

## Running a model

`models run ID` takes one option per input field of the model, its name written
with hyphens (`present_value` is `--present-value`). A number, a date, a choice
or text is written as it is, a boolean as `true` or `false`, and an array as a
JSON literal. A model with several calculations needs `--calculation`.
`pyeconomics models run ID --help` lists the model's own options with their
units, and the values each calculation takes.

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100
$ pyeconomics models run foundations.time_value --calculation irr --cash-flows "[-100, 30, 40, 50]" --format table
$ pyeconomics models run foundations.time_value --help
```

The first prints the result as canonical JSON (abridged here):

```text
{"inputs":{"calculation":"present_value",...},"manifest":{...},"model_id":"foundations.time_value","model_version":2,"outputs":{"calculation":"present_value","present_value":61.391325354075946},"warnings":[]}
```

The inputs can also come as a JSON object, from a file or from standard input
(`-`); options given beside them override the file's values. The codec reads at
most 16 MiB and refuses repeated keys, NaN and infinity:

```text
pyeconomics models run foundations.time_value --inputs inputs.json --rate 0.06
cat inputs.json | pyeconomics models run foundations.time_value --inputs -
```

### Binding data

A model that declares data bindings reads its inputs from the data catalog
when any of `--as-of DATE`, `--vintage real_time|latest`, `--profile NAME`,
`--concept FIELD=ID` or `--param NAME=VALUE` is given. `--as-of` reads the data
as published on that date; without it the latest data is read (`--profile
default` binds the default profile so), which a binding that reads a window up
to a date refuses. Options for its fields then override the values bound, and
the result's manifest records every series, vintage and retrieval time
({doc}`data/bindings`):

```shell
$ pyeconomics models run macro.recession_probability --as-of 2024-06-28
$ pyeconomics models run macro.recession_probability --as-of 2024-06-28 --format table
$ pyeconomics models run macro.policy_rule --calculation taylor_1993 --profile default
```

The table prints the data's sources and, below them, every attribution and
notice the data requires.

## Data, keys and the cache

The data commands wrap the {doc}`data API <data/index>` unchanged, with its
modes, licences and keys. `data get --format json` prints the frame with its
source records and the attributions its data must be shown with:

```console
$ pyeconomics data search "unemployment rate" --limit 2
$ pyeconomics data describe us.unemployment.rate
$ pyeconomics data sources
```

```shell
$ pyeconomics data get us.treasury.nominal_10y --start 2024-01-01 --end 2024-01-31 --format table
$ pyeconomics data vintages fred:UNRATE
```

A key is never an argument, which shell history would keep. `keys set` asks
for it with a hidden prompt, or reads the first line of standard input with
`--stdin`, checks it and stores it in the OS keyring ({doc}`data/keys`):

```text
pyeconomics keys set fred
my-secrets-tool read fred | pyeconomics keys set fred --stdin
```

`keys list` names where each key would be read from (`environment`, `dotenv`,
`keyring` or `none`) and never its value:

```console
$ pyeconomics keys list
$ pyeconomics data sources --check-keys
```

The cache commands show what is cached, never a payload, and create nothing
({doc}`data/cache`):

```console
$ pyeconomics cache info
$ pyeconomics cache ls
$ pyeconomics cache path
$ pyeconomics cache clear
```

`registry export` writes the description of every model, the file the web app
is built from:

```console
$ pyeconomics registry export --out site --no-figures
```

## Formats

| `--format` | Output |
|------------|--------|
| `json` | Canonical JSON (RFC 8785) followed by one newline; the default of `models run` and `data get` |
| `table` | Tables, drawn with borders on a terminal and as aligned plain text in a pipe or a file, with attributions and notices below; the default of the listing commands |
| `markdown` | The model card (`models describe` only, its default) |

`--out PATH` writes the same bytes to a file instead of standard output. Output
is UTF-8 on every operating system, Windows included, whatever the console's
code page.

## Exit codes

A failure prints one line on standard error, the problem's slug and a detail
that never holds a key, a file path, a host or an upstream URL
({doc}`problems`), and exits with its code:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Internal error, an invalid setting or an inconsistent registry |
| 2 | The command line does not parse (`usage-error`) |
| 3 | Invalid input |
| 4 | The inputs have no defined result, or the method found none |
| 5 | Not found: a model, a provider, a concept or a series |
| 6 | Not permitted: the source's licence refuses this use |
| 7 | Data unavailable: a key, the source, offline mode or a rate limit |
| 8 | An optional extra is not installed |

```text
$ pyeconomics models run foundations.time_value --calculation present_value --rate 7
invalid-input: The inputs failed validation: present_value.rate: Input should be less than or equal to 1.
```

## Shell completion

`pyeconomics --install-completion` writes the completion script where the
current shell looks for it. `pyeconomics completion bash` (or `zsh`, `fish`,
`powershell`) prints the script instead, to install by hand:

```console
$ pyeconomics completion bash
```

Completion covers the commands and their options; a model's run options are
generated when the command line names the model, so they are listed by
`pyeconomics models run ID --help`.
