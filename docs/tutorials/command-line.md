# The command line

Everything so far ran in Python. The `pyeconomics` command runs the same models
and reads the same data from a shell, so a script, R or Excel can use them. It
comes with the core package. This lesson takes about fifteen minutes; run each
command as you go.

## Find a model

Search by what you want to calculate, then read its card:

```console
$ pyeconomics models search "present value annuity" --limit 3
foundations.time_value  2        foundations  Time value of money
$ pyeconomics models describe foundations.time_value
Model `foundations.time_value`, version 2.
```

`models describe` prints the same card as the
{doc}`model's page </reference/models/foundations/time_value>`: its formula,
inputs, assumptions, limitations and sources.

## Run it

`models run` takes one option per input, written with hyphens, so
`future_value` is `--future-value`. This model has several calculations, so name
one. By default you get the canonical JSON the Python API gives, byte for byte:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100
..."outputs":{"calculation":"present_value","present_value":61.3913253540...
```

Rates are decimals here too: `--rate 0.05` is five percent. `--help` lists a
model's own options with their units:

```console
$ pyeconomics models run foundations.time_value --help
```

## Choose a format

JSON suits a program. `--format table` suits you:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100 --format table
Time value of money (foundations.time_value, version 2)
present_value  61.3913253540...  money
```

`--format csv` gives a row a spreadsheet can read, below a block of `#` lines
that say what it is. An export always carries that record:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100 --format csv
# model: foundations.time_value version 2
```

`--out` writes the same bytes to a file. A binary format such as `xlsx` goes to
a file or a pipe, never to your terminal:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 0.05 --periods 10 --future-value 100 --format xlsx --out present-value.xlsx
```

The workbook has a `data` sheet and a `manifest` sheet. {doc}`/exports` lists
every format.

## Bind a model to data

Some models can read their inputs from the data catalog. `--as-of` reads each
series as it was published on that date, and the result records every source it
read. This one estimates the probability of a recession from the yield curve:

```shell
$ pyeconomics models run macro.recession_probability --as-of 2024-06-28 --format table
```

Real-time data matters for history: a figure revised last year was not what
anyone knew in 2024. A table prints the data's sources and, below them, every
attribution and notice the data requires. Keep those with the numbers.

The command reads live data, so it needs the network, and the keys the sources
ask for ({doc}`data-and-keys`). In offline mode it stops with code 7.

## Exit codes

A script can tell what went wrong from the exit code. Ask for a rate of 700%:

```console
$ pyeconomics models run foundations.time_value --calculation present_value --rate 7 --periods 10 --future-value 100
invalid-input: The inputs failed validation: present_value.rate: Input should be less than or equal to 1.
$ echo $?
3
```

The message names the field and the rule, and never a key or a file path. Code 5
means something was not found:

```console
$ pyeconomics models run foundations.no_such_model
model-not-found: no model is registered with id 'foundations.no_such_model'
$ echo $?
5
```

On Windows PowerShell, read the code from `$LASTEXITCODE` instead of `$?`.

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Internal error, an invalid setting or an inconsistent registry |
| 2 | The command line does not parse |
| 3 | Invalid input |
| 4 | The inputs have no defined result, or the method found none |
| 5 | Not found: a model, a provider, a concept or a series |
| 6 | Not permitted: the source's licence refuses this use |
| 7 | Data unavailable: a key, the source, offline mode or a rate limit |
| 8 | An optional extra is not installed |

## Next

{doc}`/cli` is the full reference. {doc}`rest-api` serves the same models over
HTTP, so any language can reach them.
